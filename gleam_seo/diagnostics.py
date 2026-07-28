"""Cannibalisation and CTR-gap detection (Step 2 of the Routine prompt)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Mapping, Optional

from gleam_seo.classify import normalize
from gleam_seo.ctr import ctr_at
from gleam_seo.thresholds import CTR_GAP_MIN_IMPRESSIONS, CTR_GAP_THRESHOLD


@dataclass
class QueryPageRow:
    """A GSC row from a query+page pull (dimensions=["query", "page"])."""

    query: str
    page: str
    clicks: float
    impressions: float


@dataclass
class Cannibalisation:
    query: str
    page_now: str
    page_prev: str


@dataclass
class CtrGap:
    query: str
    impressions: float
    position: float
    actual_ctr: float
    expected_ctr: float
    deficit: float  # fractional shortfall vs expected, in [0, 1]
    top_url: Optional[str] = None  # the page to edit, when the source supplies it


def _top_page(rows: Iterable[QueryPageRow]) -> dict[str, str]:
    """Map each query to the page that earned the most clicks (impressions as
    a tie-break)."""

    best: dict[str, tuple[float, float, str]] = {}
    for row in rows:
        key = normalize(row.query)
        score = (row.clicks, row.impressions)
        if key not in best or score > (best[key][0], best[key][1]):
            best[key] = (row.clicks, row.impressions, row.page)
    return {q: v[2] for q, v in best.items()}


def cannibalisation(
    this_week: Iterable[QueryPageRow],
    prior_week: Iterable[QueryPageRow],
) -> list[Cannibalisation]:
    """Flag queries whose top-ranking page changed between the two weeks.

    A moving ranking page is the signature of two Gleam URLs competing for the
    same query. Requires query+page pulls; a query-only pull cannot detect it.
    """

    now_top = _top_page(this_week)
    prev_top = _top_page(prior_week)
    out: list[Cannibalisation] = []
    for key in sorted(set(now_top) & set(prev_top)):
        if now_top[key] != prev_top[key]:
            out.append(
                Cannibalisation(query=key, page_now=now_top[key], page_prev=prev_top[key])
            )
    return out


def ctr_gaps(
    rows: Iterable,
    curve: Mapping[int, float],
    min_impressions: float = CTR_GAP_MIN_IMPRESSIONS,
    threshold: float = CTR_GAP_THRESHOLD,
) -> list[CtrGap]:
    """Flag high-impression queries whose CTR is far below the property's own
    average CTR at that position.

    The known example to verify: "gleam app" drew ~1,180 impressions at 1.6%
    CTR from position ~3.4 — far below the position-3 benchmark.

    Rows must expose ``query``, ``impressions``, ``position`` and either
    ``ctr`` or a ``resolved_ctr()`` returning clicks/impressions.
    """

    out: list[CtrGap] = []
    for row in rows:
        impressions = getattr(row, "impressions", 0) or 0
        if impressions < min_impressions:
            continue
        position = getattr(row, "position", None)
        expected = ctr_at(curve, position)
        if expected is None or expected <= 0:
            continue
        actual = _row_ctr(row)
        if actual is None:
            continue
        deficit = (expected - actual) / expected
        if deficit > threshold:
            out.append(
                CtrGap(
                    query=getattr(row, "query"),
                    impressions=impressions,
                    position=position,
                    actual_ctr=actual,
                    expected_ctr=expected,
                    deficit=deficit,
                    top_url=getattr(row, "top_url", None),
                )
            )
    out.sort(key=lambda g: (-g.deficit, -g.impressions))
    return out


def _row_ctr(row) -> Optional[float]:
    resolver = getattr(row, "resolved_ctr", None)
    if callable(resolver):
        return resolver()
    ctr = getattr(row, "ctr", None)
    if ctr is not None:
        return ctr
    impressions = getattr(row, "impressions", 0) or 0
    if impressions > 0:
        return (getattr(row, "clicks", 0) or 0) / impressions
    return None
