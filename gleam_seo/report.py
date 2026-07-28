"""Driver: turn a weekly snapshot into the ``REPORT`` object the template renders.

``templates/weekly-report.html`` carries a single ``REPORT`` object and a fixed
JS renderer. This driver builds that object: it **computes** the deterministic,
diff-derived sections from the tested code in ``gleam_seo/`` (the diverging
value strip, gained/lost movers, cannibalisation, CTR gaps, the informational
rows, the brand KPI trio, status and counts) and **merges** agent-authored prose
and other-source sections supplied under ``narrative`` (the scorecard KPIs, share
of voice, AI search, the per-keyword brand paid table, revenue/referral tables,
the method log, etc.).

    python -m gleam_seo.report      --input snapshot.json --output report.json
    python -m gleam_seo.render_html --report report.json --output report.html

Snapshot shape (all optional except ``gsc_keywords``)::

    {
      "today": "2026-07-28",
      "meta":  {"week": "...", "period": "...", "generated": "...",
                "units": {"ahrefs": 1840, "semrush": 0}},
      "manual": {                       # Google Ads paid, exactly six fields
        "brand_spend_aud", "brand_conversions", "brand_roas",
        "brand_rank_lost_is_pct", "brand_budget_lost_is_pct", "conquest_cpa_aud"
      },
      "gsc_keywords":   {"this_week": [row, ...], "prior_week": [row, ...]},
      "ctr_by_position":[{"position": 1, "average_ctr_percent": 30.1}, ...],
      "keyword_metrics":{"live draw": {"volume": 590, "cpc": 11.24, "cluster": "Tool"}},
      "narrative": { ... }              # agent-authored sections, merged verbatim
    }

Every section the renderer reads is always emitted, so the template never errors
on a missing key. Anything with no source in this session is emitted empty or as
"not pulled this run" — never guessed (Rule 0).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from functools import partial
from typing import Any, Optional

from gleam_seo.classify import normalize
from gleam_seo.ctr import ctr_at, ctr_curve
from gleam_seo.dates import week_ranges
from gleam_seo.diagnostics import QueryPageRow, cannibalisation, ctr_gaps
from gleam_seo.movement import QueryRow, rank_movers
from gleam_seo.paid import aggregate_keywords, lost_share_reading

NOT_PULLED = "not pulled this run"

# Exactly the six fields of the human-pasted YYYY-MM-DD-manual.json (see the
# Ahrefs-backed Routine prompt, Step 4). Names and units are part of the
# contract: *_aud = AUD, *_pct = a percentage (e.g. 45.2, not 0.452).
MANUAL_FIELDS = (
    "brand_spend_aud",
    "brand_conversions",
    "brand_roas",
    "brand_rank_lost_is_pct",
    "brand_budget_lost_is_pct",
    "conquest_cpa_aud",
)


# --------------------------------------------------------------------------- #
# input parsing
# --------------------------------------------------------------------------- #

def _query_rows(rows: list[dict]) -> list[QueryRow]:
    return [
        QueryRow(
            query=r["query"],
            clicks=r.get("clicks", 0) or 0,
            impressions=r.get("impressions", 0) or 0,
            position=r.get("position"),
            ctr=None,  # derive from clicks/impressions to avoid unit ambiguity
            top_url=r.get("top_url"),
        )
        for r in rows
    ]


def _curve_from_ctr_by_position(entries: list[dict]) -> dict[int, float]:
    curve: dict[int, float] = {}
    for e in entries:
        pos = e.get("position")
        if pos is None:
            continue
        if e.get("average_ctr_percent") is not None:
            curve[int(round(pos))] = e["average_ctr_percent"] / 100.0
        elif e.get("ctr") is not None:
            curve[int(round(pos))] = e["ctr"]
    return curve


def _brand_paid_source(payload: dict) -> dict[str, Any]:
    """Resolve the six canonical brand-paid values (Rule 0 -> NOT_PULLED)."""

    if payload.get("manual") is not None:
        manual = payload["manual"]
        unexpected = set(manual) - set(MANUAL_FIELDS)
        if unexpected:
            raise ValueError(
                f"manual block accepts exactly {MANUAL_FIELDS}; got unexpected {sorted(unexpected)}"
            )
        return {f: (manual[f] if manual.get(f) is not None else NOT_PULLED) for f in MANUAL_FIELDS}

    paid = payload.get("paid")
    if paid is not None:
        aggregates = aggregate_keywords(paid.get("keyword_view", []))
        spend = round(sum(a.cost for a in aggregates), 2) if aggregates else NOT_PULLED
        conversions = sum(a.conversions for a in aggregates) if aggregates else NOT_PULLED
        return {
            "brand_spend_aud": spend,
            "brand_conversions": conversions,
            "brand_roas": paid["roas"] if paid.get("roas") is not None else NOT_PULLED,
            "brand_rank_lost_is_pct": paid["rank_lost"] if paid.get("rank_lost") is not None else NOT_PULLED,
            "brand_budget_lost_is_pct": paid["budget_lost"] if paid.get("budget_lost") is not None else NOT_PULLED,
            "conquest_cpa_aud": paid["conquest_cpa"] if paid.get("conquest_cpa") is not None else NOT_PULLED,
        }

    return {f: NOT_PULLED for f in MANUAL_FIELDS}


# --------------------------------------------------------------------------- #
# small formatters
# --------------------------------------------------------------------------- #

def _n(v: Any) -> Optional[float]:
    return v if isinstance(v, (int, float)) else None


def _pct(v: Any) -> Optional[float]:
    """Normalise a share to a percentage number (accepts fraction or percent)."""
    n = _n(v)
    if n is None:
        return None
    return n * 100 if n <= 1 else n


def _pos(p: Optional[float]) -> Any:
    return int(round(p)) if isinstance(p, (int, float)) else "—"


def _derived_cpa(spend: Any, conversions: Any) -> Optional[float]:
    if isinstance(spend, (int, float)) and isinstance(conversions, (int, float)) and conversions > 0:
        return round(spend / conversions, 2)
    return None


def _period(this_week: tuple[str, str]) -> str:
    s, e = date.fromisoformat(this_week[0]), date.fromisoformat(this_week[1])
    if (s.month, s.year) == (e.month, e.year):
        return f"{s.day}–{e.day} {s.strftime('%B %Y')}"
    return f"{s.day} {s.strftime('%b')} – {e.day} {e.strftime('%b %Y')}"


# --------------------------------------------------------------------------- #
# computed sections
# --------------------------------------------------------------------------- #

def _mover_row(m, meta: dict, cannib_keys: set) -> dict:
    md = meta.get(normalize(m.query), {})
    row = {
        "kw": m.query,
        "cl": md.get("cluster") or m.track.value.title(),
        "was": _pos(m.pos_prev),
        "now": _pos(m.pos_now),
        "vol": md.get("volume", "n/a"),
        "cpc": float(md["cpc"]) if md.get("cpc") is not None else 0.0,
        "d": int(round(m.value_change)) if m.value_change is not None else 0,
        "url": m.top_url or "",
    }
    return row


def _lost_row(m, meta: dict, cannib_keys: set) -> dict:
    row = _mover_row(m, meta, cannib_keys)
    is_cannib = normalize(m.query) in cannib_keys
    row["dtype"] = "cannib" if is_cannib else "rank"
    row["diag"] = (
        "URL flip — ranking page changed between weeks"
        if is_cannib
        else "Ranking loss — " + ("; ".join(m.reasons) if m.reasons else "position slipped")
    )
    return row


def _brand_kpis(manual: dict) -> list[dict]:
    rank, budget = manual["brand_rank_lost_is_pct"], manual["brand_budget_lost_is_pct"]
    roas, spend = manual["brand_roas"], manual["brand_spend_aud"]
    conquest = manual["conquest_cpa_aud"]
    cpa = _derived_cpa(spend, manual["brand_conversions"])
    kpis: list[dict] = []

    rp = _pct(rank)
    if rp is not None:
        bp = _pct(budget)
        d = f"budget-lost only {bp:.1f}%" if bp is not None else "budget-lost " + NOT_PULLED
        kpis.append({"k": "Brand rank-lost impression share", "v": f"{rp:.1f}%", "d": d, "dir": "dn"})
    else:
        kpis.append({"k": "Brand rank-lost impression share", "v": NOT_PULLED, "d": "", "dir": "flat"})

    if cpa is not None:
        if isinstance(conquest, (int, float)) and cpa > 0:
            d = f"vs A${conquest:,.2f} on conquest · {conquest / cpa:.1f}× cheaper"
        else:
            d = "conquest " + NOT_PULLED
        kpis.append({"k": "Brand paid CPA", "v": f"A${cpa:,.2f}", "d": d, "dir": "up"})
    else:
        kpis.append({"k": "Brand paid CPA", "v": NOT_PULLED, "d": "", "dir": "flat"})

    if isinstance(roas, (int, float)):
        d = f"A${spend:,.0f} spend" if isinstance(spend, (int, float)) else ""
        kpis.append({"k": "Brand paid ROAS", "v": f"{roas:.2f}", "d": d, "dir": "flat"})
    else:
        kpis.append({"k": "Brand paid ROAS", "v": NOT_PULLED, "d": "", "dir": "flat"})

    return kpis


def _seed_queue(movers, gaps, cannibals) -> list[dict]:
    queue: list[dict] = []
    if cannibals:
        items = [{
            "do": f'{c.query} — ranking page changed {c.page_prev} → {c.page_now}; consolidate or differentiate.',
            "where": f'{c.page_prev} → {c.page_now}',
        } for c in cannibals]
        queue.append({"id": "DECANNIBALISE", "p": 1, "title": "Consolidate cannibalised URLs",
                      "n": len(items), "items": items,
                      "why": "Two Gleam URLs alternating in one SERP split signals; repointing internal links resolves it."})
    losers = [m for m in movers if (m.value_change or 0) < 0]
    if losers:
        items = [{"do": f'{m.query} — {"; ".join(m.reasons) or "position slipped"}.',
                  "where": m.top_url or f'GSC query "{m.query}"'} for m in losers[:5]]
        queue.append({"id": "INTERNAL_LINK", "p": 1, "title": "Recover losing commercial terms",
                      "n": len(items), "items": items,
                      "why": "Highest value per position gained; the pages already exist."})
    if gaps:
        items = [{"do": f'{g.query} — #{_pos(g.position)}, CTR {g.actual_ctr * 100:.1f}% vs {g.expected_ctr * 100:.1f}% expected.',
                  "where": g.top_url or f'GSC query "{g.query}"'} for g in gaps[:5]]
        queue.append({"id": "METADATA", "p": 2, "title": "Rewrite title/meta — CTR below benchmark",
                      "n": len(items), "items": items,
                      "why": "Under-earning existing rankings; cheapest wins, no new content."})
    return queue


def _status(movers, narrative: dict, meta_line: Optional[str]) -> dict:
    n = narrative.get("status") or {}
    level = n.get("level") or ("quiet" if not movers else "action")
    quiet = n.get("quiet_line") or "No commercial movement past threshold."
    if n.get("line"):
        line = n["line"]
    elif meta_line:
        line = meta_line
    else:
        line = "See sections below."
    return {"level": level, "line": line, "quiet_line": quiet}


# --------------------------------------------------------------------------- #
# main build
# --------------------------------------------------------------------------- #

def build_report(payload: dict) -> dict:
    today = date.fromisoformat(payload["today"]) if payload.get("today") else None
    meta = payload.get("meta") or {}
    narrative = payload.get("narrative") or {}

    gsc = payload.get("gsc_keywords", {})
    now_rows = _query_rows(gsc.get("this_week", []))
    prev_rows = _query_rows(gsc.get("prior_week", []))

    if payload.get("ctr_by_position"):
        curve = _curve_from_ctr_by_position(payload["ctr_by_position"])
    else:
        curve = ctr_curve(now_rows)
    ctr_fn = partial(ctr_at, curve)

    metadata = payload.get("keyword_metrics") or payload.get("semrush") or {}
    metadata = {normalize(k): v for k, v in metadata.items()}

    movers = rank_movers(now_rows, prev_rows, ctr_fn, metadata=metadata)
    gaps = ctr_gaps(now_rows, curve)

    # Cannibalisation from an explicit query+page pull, else from gsc-keywords top_url.
    qp = payload.get("gsc_query_pages")
    if qp:
        cannibals = cannibalisation(
            [QueryPageRow(**r) for r in qp.get("this_week", [])],
            [QueryPageRow(**r) for r in qp.get("prior_week", [])],
        )
    elif any(r.top_url for r in now_rows) and any(r.top_url for r in prev_rows):
        cannibals = cannibalisation(
            [QueryPageRow(r.query, r.top_url, r.clicks, r.impressions) for r in now_rows if r.top_url],
            [QueryPageRow(r.query, r.top_url, r.clicks, r.impressions) for r in prev_rows if r.top_url],
        )
    else:
        cannibals = []
    cannib_keys = {normalize(c.query) for c in cannibals}

    manual = _brand_paid_source(payload)

    # ---- computed sections ------------------------------------------------ #
    diverge = [
        {"kw": m.query,
         "pos": f"{_pos(m.pos_prev)}→{_pos(m.pos_now)}",
         "d": int(round(m.value_change)),
         "track": m.track.value if m.track.value in ("commercial", "informational") else "commercial"}
        for m in movers
        if m.value_change is not None and m.pos_now is not None and m.pos_prev is not None
    ]
    gained = [_mover_row(m, metadata, cannib_keys) for m in movers
              if m.value_change is not None and m.value_change > 0
              and m.pos_now is not None and m.pos_prev is not None]
    lost = [_lost_row(m, metadata, cannib_keys) for m in movers
            if m.value_change is not None and m.value_change < 0
            and m.pos_now is not None and m.pos_prev is not None]

    cannib = [{
        "kw": c.query,
        "cpc": float(metadata.get(normalize(c.query), {}).get("cpc") or 0.0),
        "a": c.page_prev, "b": c.page_now,
        "flips": "—",
        "winner": c.page_now,
        "act": "Pick the winner on evidence (ranking keywords, referring domains, conversion rate), then 301 or differentiate and repoint internal links.",
    } for c in cannibals]

    ctrgap = [{
        "kw": g.query, "pos": _pos(g.position), "impr": int(g.impressions),
        "actual": f"{g.actual_ctr * 100:.1f}%", "expected": f"{g.expected_ctr * 100:.1f}%",
        "gap": f"−{g.deficit * 100:.0f}%", "page": g.top_url or "",
    } for g in gaps]

    info_rows = [{
        "pg": m.top_url or m.query, "impr": "—",
        "clicks": (f"+{m.clicks_change:.0f}" if m.clicks_change >= 0 else f"{m.clicks_change:.0f}"),
        "wks": "—", "v": "; ".join(m.reasons) or "moved",
    } for m in movers if m.track.value == "informational"]

    brand_kpis = _brand_kpis(manual)
    cpa = _derived_cpa(manual["brand_spend_aud"], manual["brand_conversions"])
    if isinstance(manual["brand_spend_aud"], (int, float)) and cpa is not None:
        paidsrc = (f"Brand total (manual block, Google Ads 9047806202): "
                   f"A${manual['brand_spend_aud']:,.2f} spend, CPA A${cpa:,.2f}, "
                   f"ROAS {manual['brand_roas'] if isinstance(manual['brand_roas'], (int, float)) else NOT_PULLED}.")
    else:
        paidsrc = "Per-keyword brand paid detail " + NOT_PULLED + " (six-field manual block only)."

    # status headline seeded from the biggest loss
    worst = min((m for m in movers if m.value_change is not None), key=lambda m: m.value_change, default=None)
    meta_line = None
    if worst is not None and (worst.value_change or 0) < 0:
        md = metadata.get(normalize(worst.query), {})
        cpc_txt = f" on an A${float(md['cpc']):,.2f} CPC term" if md.get("cpc") is not None else ""
        meta_line = (f"The largest single loss this week is <b>{worst.query}</b> — "
                     f"#{_pos(worst.pos_prev)} → #{_pos(worst.pos_now)}{cpc_txt}, "
                     f"worth about A${abs(int(round(worst.value_change)))}/mo in estimated traffic value.")

    # ---- meta ------------------------------------------------------------- #
    if today:
        iso = today.isocalendar()
        wr = week_ranges(today)
        week = meta.get("week") or f"{iso[0]}-W{iso[1]:02d}"
        period = meta.get("period") or _period(wr["this_week"])
    else:
        week, period = meta.get("week", ""), meta.get("period", "")
    generated = meta.get("generated") or (today.isoformat() if today else "")
    units = meta.get("units") or {"ahrefs": 0, "semrush": 0}

    queue = narrative.get("queue") or _seed_queue(movers, gaps, cannibals)
    priority1 = sum(1 for q in queue if q.get("p") == 1)
    findings = len(movers) + len(gaps) + len(cannibals)

    def _sec(name: str, default: dict) -> dict:
        """Merge an agent-authored section over required-key defaults."""
        src = narrative.get(name) or {}
        return {**default, **src}

    report = {
        "week": week,
        "period": period,
        "generated": generated,
        "findings": narrative.get("findings", findings),
        "priority1": narrative.get("priority1", priority1),
        "units": units,

        "status": _status(movers, narrative, meta_line),

        "kpis": narrative.get("kpis", []),
        "kpisrc": narrative.get("kpisrc", ""),

        "diverge": diverge,
        "gained": gained,
        "lost": lost,
        "cannib": cannib,
        "ctrgap": ctrgap,

        "sov": narrative.get("sov", []),
        "displace": narrative.get("displace", []),
        "newpages": narrative.get("newpages", []),
        "ai": _sec("ai", {"kpis": [], "rows": []}),
        "queue": queue,

        "brand": {
            "_source": narrative.get("brand", {}).get("_source",
                       "Brand KPIs from the six-field manual block (Google Ads 9047806202)."),
            "kpis": narrative.get("brand", {}).get("kpis") or brand_kpis,
            "paid": narrative.get("brand", {}).get("paid", []),
            "paidsrc": narrative.get("brand", {}).get("paidsrc", paidsrc),
            "serp": narrative.get("brand", {}).get("serp", []),
            "attack": narrative.get("brand", {}).get("attack", []),
            "note": narrative.get("brand", {}).get("note", ""),
            "datagap": narrative.get("brand", {}).get("datagap", ""),
        },

        "rev": _sec("rev", {"kpis": [], "rows": [], "note": NOT_PULLED}),
        "ref": _sec("ref", {"kpis": [], "rows": [], "note": NOT_PULLED}),
        "info": _sec("info", {"kpis": [], "rows": info_rows, "paid": ""}),

        "method": narrative.get("method", [
            "Search Console via Ahrefs gsc-* (project_id 684395) — clicks, impressions, CTR, position, top_url.",
            "CTR benchmark from Ahrefs gsc-ctr-by-position (own 90-day data, 0 units).",
            "Volume and CPC from Ahrefs keywords-explorer-overview; positions always from GSC.",
            "Brand paid from the six-field manual block (Google Ads 9047806202, AUD).",
            "GA4 revenue and referral revenue have no connector this run — sections 05 and 06 read 'not pulled this run'.",
            "Value delta = Δ(volume × own-site CTR at position) × CPC. Snapshots written to Drive and diffed.",
        ]),
    }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute the weekly REPORT object from snapshot JSON.")
    parser.add_argument("--input", "-i", default="-", help="Input snapshot JSON path, or - for stdin.")
    parser.add_argument("--output", "-o", default="-", help="Output REPORT JSON path, or - for stdout.")
    args = parser.parse_args(argv)

    raw = sys.stdin.read() if args.input == "-" else open(args.input, encoding="utf-8").read()
    report = build_report(json.loads(raw))
    text = json.dumps(report, indent=2, default=str)

    if args.output == "-":
        print(text)
    else:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
