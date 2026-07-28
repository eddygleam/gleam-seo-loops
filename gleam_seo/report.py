"""Driver: turn this-week / prior-week snapshot JSON into computed findings.

This is the seam the Routine crosses from *pulling* to *reasoning*. The Routine
(``loops/weekly-report.md`` or ``loops/weekly-report-ahrefs.md``) pulls data
from the connectors, writes it to Google Drive as snapshot JSON, then hands the
snapshots to this driver::

    python -m gleam_seo.report --input snapshots.json --output findings.json

Everything numeric — matching queries across weeks, movement/materiality
filtering, value-change ranking, CTR curve, cannibalisation, CTR gaps, paid
aggregation — happens here, deterministically and under test. The Routine then
renders ``findings.json`` into the HTML report (``gleam_seo.render_html``) and
into the Slack canvas / Linear issues. It does no arithmetic of its own.

Input JSON shape (all sections optional except ``gsc_keywords``)::

    {
      "today": "2026-07-28",
      "manual": {                       # Google Ads + GA4, keyed by exactly six fields
        "brand_spend": 4700.0,          # A$
        "brand_conversions": 112,
        "brand_roas": 0.92,
        "brand_rank_lost_is": 0.452,    # fraction or percent
        "brand_budget_lost_is": 0.033,
        "conquest_cpa": 244.35          # A$
      },
      "gsc_keywords":   {"this_week": [row, ...], "prior_week": [row, ...]},
      "gsc_query_pages":{"this_week": [qp, ...],  "prior_week": [qp, ...]},
      "ctr_by_position":[{"position": 1, "average_ctr_percent": 30.1}, ...],
      "keyword_metrics":{"gleam app": {"volume": 1200, "cpc": 4.3}, ...},
      "semrush":        {...}           # accepted as an alias for keyword_metrics
    }

A GSC ``row`` is ``{query, clicks, impressions, position, ctr?, top_url?}``. When
rows carry ``top_url`` (Ahrefs ``gsc-keywords`` does), cannibalisation is
detected from them and no separate query+page pull is needed.

Every field the manual block does not supply is rendered as
``"not pulled this run"`` — never guessed (Rule 0).
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

# The manual block carries exactly these six fields — Google Ads + GA4 data
# that no connector in the Ahrefs-only session can reach. Anything absent
# renders as NOT_PULLED.
MANUAL_FIELDS = (
    "brand_spend",
    "brand_conversions",
    "brand_roas",
    "brand_rank_lost_is",
    "brand_budget_lost_is",
    "conquest_cpa",
)


def _query_rows(rows: list[dict]) -> list[QueryRow]:
    return [
        QueryRow(
            query=r["query"],
            clicks=r.get("clicks", 0) or 0,
            impressions=r.get("impressions", 0) or 0,
            position=r.get("position"),
            # Prefer deriving CTR from clicks/impressions so we never depend on
            # whether the source reported ctr as a fraction or a percent.
            ctr=None,
            top_url=r.get("top_url"),
        )
        for r in rows
    ]


def _totals(rows: list[QueryRow]) -> dict[str, Optional[float]]:
    clicks = sum(r.clicks for r in rows)
    impressions = sum(r.impressions for r in rows)
    weighted_pos = (
        sum((r.position or 0) * r.impressions for r in rows) / impressions
        if impressions
        else None
    )
    return {"clicks": clicks, "impressions": impressions, "avg_position": weighted_pos}


def _wow(now: Optional[float], prev: Optional[float]) -> dict[str, Any]:
    change = (now - prev) if (now is not None and prev is not None) else None
    return {"this_week": now, "prior_week": prev, "change": change}


def _curve_from_ctr_by_position(entries: list[dict]) -> dict[int, float]:
    """Build a CTR curve from Ahrefs ``gsc-ctr-by-position`` output.

    Each entry is ``{"position": int, "average_ctr_percent": float}`` (percent),
    or ``{"position": int, "ctr": float}`` (already a fraction).
    """

    curve: dict[int, float] = {}
    for e in entries:
        pos = e.get("position")
        if pos is None:
            continue
        if "average_ctr_percent" in e and e["average_ctr_percent"] is not None:
            curve[int(round(pos))] = e["average_ctr_percent"] / 100.0
        elif e.get("ctr") is not None:
            curve[int(round(pos))] = e["ctr"]
    return curve


def _brand_paid_source(payload: dict) -> dict[str, Any]:
    """Resolve the six canonical brand-paid values from whichever source the
    snapshot provides, substituting NOT_PULLED for anything absent (Rule 0).

    Two sources are supported:

    * ``manual`` — the Ahrefs-variant block: exactly the six MANUAL_FIELDS,
      pre-aggregated Google Ads + GA4 numbers a human filled in. Unexpected
      keys are rejected so the block cannot silently grow.
    * ``paid``   — the repo-variant block: raw ``keyword_view`` rows (which the
      driver aggregates and divides out of micros) plus ``rank_lost`` /
      ``budget_lost`` / optional ``roas`` / ``conquest_cpa``.

    ``manual`` wins if both are present.
    """

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
            "brand_spend": spend,
            "brand_conversions": conversions,
            "brand_roas": paid["roas"] if paid.get("roas") is not None else NOT_PULLED,
            "brand_rank_lost_is": paid["rank_lost"] if paid.get("rank_lost") is not None else NOT_PULLED,
            "brand_budget_lost_is": paid["budget_lost"] if paid.get("budget_lost") is not None else NOT_PULLED,
            "conquest_cpa": paid["conquest_cpa"] if paid.get("conquest_cpa") is not None else NOT_PULLED,
        }

    return {f: NOT_PULLED for f in MANUAL_FIELDS}


def _derived_cpa(spend: Any, conversions: Any) -> Any:
    if isinstance(spend, (int, float)) and isinstance(conversions, (int, float)) and conversions > 0:
        return round(spend / conversions, 2)
    return NOT_PULLED


def _seed_actions(movers, gaps, cannibals) -> list[dict]:
    """Seed priority actions from the computed findings, each carrying a
    ``where`` (Rule 1). The Routine may refine the wording; the location is
    already attached so nothing ships without one."""

    actions: list[dict] = []
    for g in gaps:
        actions.append({
            "rule": "CTR gap",
            "what": (f'"{g.query}" earns {g.actual_ctr:.1%} CTR at position '
                     f'{g.position:.1f} vs a {g.expected_ctr:.1%} benchmark — rewrite '
                     f'title/meta to close the gap'),
            "where": g.__dict__.get("top_url") or f'GSC query "{g.query}"',
        })
    for c in cannibals:
        actions.append({
            "rule": "Cannibalisation",
            "what": (f'"{c.query}" changed ranking page {c.page_prev} -> {c.page_now}; '
                     f'consolidate or disambiguate'),
            "where": f"{c.page_prev} vs {c.page_now}",
        })
    for m in movers:
        if m.value_change is not None and m.value_change < 0:
            actions.append({
                "rule": f"{m.track.value.title()} decline",
                "what": (f'"{m.query}" lost est. value ({", ".join(m.reasons)})'),
                "where": m.__dict__.get("top_url") or f'GSC query "{m.query}"',
            })
    return actions


def build_report(payload: dict) -> dict:
    today = date.fromisoformat(payload["today"]) if payload.get("today") else None

    gsc = payload.get("gsc_keywords", {})
    now_rows = _query_rows(gsc.get("this_week", []))
    prev_rows = _query_rows(gsc.get("prior_week", []))

    # CTR curve: prefer Ahrefs gsc-ctr-by-position (own data, 0 units) when
    # supplied, else derive from this week's own query rows.
    if payload.get("ctr_by_position"):
        curve = _curve_from_ctr_by_position(payload["ctr_by_position"])
        curve_source = "ahrefs gsc-ctr-by-position"
    else:
        curve = ctr_curve(now_rows)
        curve_source = "derived from this week's gsc-keywords"
    ctr_fn = partial(ctr_at, curve)

    metadata = payload.get("keyword_metrics") or payload.get("semrush") or {}
    metadata = {normalize(k): v for k, v in metadata.items()}

    movers = rank_movers(now_rows, prev_rows, ctr_fn, metadata=metadata)

    # Cannibalisation: from an explicit query+page pull if given, else from the
    # top_url that Ahrefs gsc-keywords attaches to every keyword row.
    qp = payload.get("gsc_query_pages")
    if qp:
        now_qp = [QueryPageRow(**r) for r in qp.get("this_week", [])]
        prev_qp = [QueryPageRow(**r) for r in qp.get("prior_week", [])]
        cannibals = cannibalisation(now_qp, prev_qp)
    elif any(r.top_url for r in now_rows) and any(r.top_url for r in prev_rows):
        now_qp = [QueryPageRow(r.query, r.top_url, r.clicks, r.impressions)
                  for r in now_rows if r.top_url]
        prev_qp = [QueryPageRow(r.query, r.top_url, r.clicks, r.impressions)
                   for r in prev_rows if r.top_url]
        cannibals = cannibalisation(now_qp, prev_qp)
    else:
        cannibals = None

    gaps = ctr_gaps(now_rows, curve)

    manual = _brand_paid_source(payload)
    now_totals = _totals(now_rows)
    prev_totals = _totals(prev_rows)

    result: dict[str, Any] = {
        "generated_for": payload.get("today"),
        "week_ranges": week_ranges(today) if today else None,
        "ctr_curve": {str(k): v for k, v in sorted(curve.items())},
        "ctr_curve_source": curve_source,

        # Section 1 — six headline numbers, week on week.
        "headline": {
            "organic_clicks": _wow(now_totals["clicks"], prev_totals["clicks"]),
            "organic_impressions": _wow(now_totals["impressions"], prev_totals["impressions"]),
            "avg_position": _wow(now_totals["avg_position"], prev_totals["avg_position"]),
            "organic_revenue": NOT_PULLED,  # GA4 — no connector, no manual field
            "brand_paid_spend": manual["brand_spend"],
            "brand_roas": manual["brand_roas"],
        },

        # Section 2 — diverging value chart data (organic, est. value change).
        "value_chart": [
            {"query": m.query, "track": m.track.value, "value_change": m.value_change}
            for m in movers if m.value_change is not None
        ],

        # Sections 3 & 4 — movers up / down.
        "movers": [_mover_dict(m) for m in movers],
        "movers_up": [_mover_dict(m) for m in movers
                      if (m.value_change or 0) > 0 or m.clicks_change > 0][:3],
        "movers_down": [_mover_dict(m) for m in movers
                        if (m.value_change or 0) < 0 or m.clicks_change < 0][:3],

        # Section 5 — priority actions, each with a where (Rule 1).
        "priority_actions": _seed_actions(movers, gaps, cannibals or []),

        # Section 6 — brand paid (Google Ads), from the manual block.
        "brand_paid": {
            "spend": manual["brand_spend"],
            "conversions": manual["brand_conversions"],
            "cpa": _derived_cpa(manual["brand_spend"], manual["brand_conversions"]),
            "roas": manual["brand_roas"],
            "rank_lost_is": manual["brand_rank_lost_is"],
            "budget_lost_is": manual["brand_budget_lost_is"],
            "lost_share_reading": lost_share_reading(
                _num_or_none(manual["brand_rank_lost_is"]),
                _num_or_none(manual["brand_budget_lost_is"]),
            ),
        },

        # Section 7 — conquest / competitors campaign.
        "conquest": {
            "cpa": manual["conquest_cpa"],
            "vs_brand": _conquest_vs_brand(manual["conquest_cpa"],
                                           _derived_cpa(manual["brand_spend"],
                                                        manual["brand_conversions"])),
        },

        # Section 8 — cannibalisation.
        "cannibalisation": ([c.__dict__ for c in cannibals] if cannibals is not None
                            else NOT_PULLED),

        # Section 9 — CTR gaps.
        "ctr_gaps": [g.__dict__ for g in gaps],

        # Section 10 — informational queue.
        "informational": [_mover_dict(m) for m in movers
                          if m.track.value == "informational"],

        # Sections 11 & 12 — GA4 organic revenue and referral revenue.
        # No GA4 connector and no manual field for them, so both are NOT_PULLED.
        "ga4_organic_revenue": NOT_PULLED,
        "referral_revenue": NOT_PULLED,
    }

    result["counts"] = {
        "queries_checked": len({normalize(r.query) for r in now_rows}
                               | {normalize(r.query) for r in prev_rows}),
        "movers": len(movers),
        "findings": len(movers) + len(gaps) + (len(cannibals) if cannibals else 0),
        "ctr_gaps": len(gaps),
        "brand": sum(1 for m in movers if m.track.value == "brand"),
        "commercial": sum(1 for m in movers if m.track.value == "commercial"),
        "informational": sum(1 for m in movers if m.track.value == "informational"),
    }
    return result


def _num_or_none(v: Any) -> Optional[float]:
    return v if isinstance(v, (int, float)) else None


def _conquest_vs_brand(conquest_cpa: Any, brand_cpa: Any) -> Any:
    if isinstance(conquest_cpa, (int, float)) and isinstance(brand_cpa, (int, float)) and brand_cpa > 0:
        return f"{conquest_cpa / brand_cpa:.1f}x brand CPA"
    return NOT_PULLED


def _mover_dict(m) -> dict:
    d = dict(m.__dict__)
    d["track"] = m.track.value
    return d


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute weekly SEO findings from snapshot JSON.")
    parser.add_argument("--input", "-i", default="-", help="Input JSON path, or - for stdin.")
    parser.add_argument("--output", "-o", default="-", help="Output JSON path, or - for stdout.")
    args = parser.parse_args(argv)

    raw = sys.stdin.read() if args.input == "-" else open(args.input, encoding="utf-8").read()
    payload = json.loads(raw)
    report = build_report(payload)
    text = json.dumps(report, indent=2, default=str)

    if args.output == "-":
        print(text)
    else:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
