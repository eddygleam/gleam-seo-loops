"""Driver: turn this-week / prior-week snapshot JSON into computed findings.

This is the seam the Routine crosses from *pulling* to *reasoning*. The
Routine (``loops/weekly-report.md``) pulls data from the connectors, writes it
to Google Drive as snapshot JSON, then hands the snapshots to this driver:

    python -m gleam_seo.report --input snapshots.json --output findings.json

Everything numeric — matching queries across weeks, movement/materiality
filtering, value-change ranking, CTR curve, cannibalisation, CTR gaps, paid
aggregation — happens here, deterministically and under test. The Routine then
formats ``findings.json`` into the Slack canvas and Linear issues. It does no
arithmetic of its own.

Input JSON shape (all sections optional except ``gsc_keywords``)::

    {
      "today": "2026-07-28",
      "gsc_keywords":   {"this_week": [row, ...], "prior_week": [row, ...]},
      "gsc_query_pages":{"this_week": [qp, ...],  "prior_week": [qp, ...]},
      "semrush":        {"gleam app": {"volume": 1200, "cpc": 4.3}, ...},
      "paid": {"keyword_view": [kw, ...], "rank_lost": 0.452, "budget_lost": 0.033}
    }

where a GSC ``row`` is ``{query, clicks, impressions, position, ctr?}`` and a
``qp`` adds ``page``. The ``semrush`` map is keyed by the *normalised* query.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from functools import partial
from typing import Any

from gleam_seo.classify import classify, normalize
from gleam_seo.ctr import ctr_at, ctr_curve
from gleam_seo.dates import week_ranges
from gleam_seo.diagnostics import QueryPageRow, cannibalisation, ctr_gaps
from gleam_seo.movement import QueryRow, rank_movers
from gleam_seo.paid import aggregate_keywords, lost_share_reading


def _query_rows(rows: list[dict]) -> list[QueryRow]:
    return [
        QueryRow(
            query=r["query"],
            clicks=r.get("clicks", 0) or 0,
            impressions=r.get("impressions", 0) or 0,
            position=r.get("position"),
            ctr=r.get("ctr"),
        )
        for r in rows
    ]


def _totals(rows: list[QueryRow]) -> dict[str, float]:
    clicks = sum(r.clicks for r in rows)
    impressions = sum(r.impressions for r in rows)
    weighted_pos = (
        sum((r.position or 0) * r.impressions for r in rows) / impressions
        if impressions
        else None
    )
    return {
        "clicks": clicks,
        "impressions": impressions,
        "avg_position": weighted_pos,
    }


def _wow(now: dict[str, float], prev: dict[str, float]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in now:
        n, p = now[key], prev.get(key)
        if n is None or p is None:
            out[key] = {"this_week": n, "prior_week": p, "change": None}
        else:
            out[key] = {"this_week": n, "prior_week": p, "change": n - p}
    return out


def build_report(payload: dict) -> dict:
    today = date.fromisoformat(payload["today"]) if payload.get("today") else None

    gsc = payload.get("gsc_keywords", {})
    now_rows = _query_rows(gsc.get("this_week", []))
    prev_rows = _query_rows(gsc.get("prior_week", []))

    curve = ctr_curve(now_rows)
    ctr_fn = partial(ctr_at, curve)

    metadata = payload.get("semrush") or {}
    # Allow callers to key semrush data by raw query; normalise defensively.
    metadata = {normalize(k): v for k, v in metadata.items()}

    movers = rank_movers(now_rows, prev_rows, ctr_fn, metadata=metadata)

    result: dict[str, Any] = {
        "generated_for": payload.get("today"),
        "week_ranges": week_ranges(today) if today else None,
        "gsc_totals": _wow(_totals(now_rows), _totals(prev_rows)),
        "ctr_curve": {str(k): v for k, v in sorted(curve.items())},
        "movers": [_mover_dict(m) for m in movers],
        "ctr_gaps": [g.__dict__ for g in ctr_gaps(now_rows, curve)],
    }

    qp = payload.get("gsc_query_pages")
    if qp:
        now_qp = [QueryPageRow(**r) for r in qp.get("this_week", [])]
        prev_qp = [QueryPageRow(**r) for r in qp.get("prior_week", [])]
        result["cannibalisation"] = [c.__dict__ for c in cannibalisation(now_qp, prev_qp)]
    else:
        result["cannibalisation"] = "not pulled this run"

    paid = payload.get("paid")
    if paid:
        aggregates = aggregate_keywords(paid.get("keyword_view", []))
        result["paid"] = {
            "top_keywords": [
                {
                    "keyword": a.keyword,
                    "cost": round(a.cost, 2),
                    "clicks": a.clicks,
                    "impressions": a.impressions,
                    "conversions": a.conversions,
                    "cpa": (round(a.cpa, 2) if a.cpa is not None else None),
                }
                for a in aggregates
            ],
            "lost_share_reading": lost_share_reading(
                paid.get("rank_lost"), paid.get("budget_lost")
            ),
        }
    else:
        result["paid"] = "not pulled this run"

    result["counts"] = {
        "queries_checked": len({normalize(r.query) for r in now_rows} | {normalize(r.query) for r in prev_rows}),
        "movers": len(movers),
        "ctr_gaps": len(result["ctr_gaps"]),
        "brand": sum(1 for m in movers if m.track.value == "brand"),
        "commercial": sum(1 for m in movers if m.track.value == "commercial"),
        "informational": sum(1 for m in movers if m.track.value == "informational"),
    }
    return result


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
