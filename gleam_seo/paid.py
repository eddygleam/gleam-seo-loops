"""Google Ads normalisation for the brand paid section (Step 4).

Three traps handled here:

* Costs come back in micros — divide by 1,000,000.
* The same keyword splits across rows unless case is normalised and
  ``gleam.io`` is folded to ``gleam io`` before aggregating.
* ``search_rank_lost_impression_share`` and
  ``search_budget_lost_impression_share`` exist only on the campaign resource,
  and mean opposite things: rank-lost = outranked (fix bids / quality /
  landing pages); budget-lost = out of money (raise budget). They must never
  be conflated.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Optional

MICROS = 1_000_000


def micros_to_units(micros: float) -> float:
    """Convert a Google Ads micros amount to currency units."""

    return micros / MICROS


def fold_keyword(text: str) -> str:
    """Normalise a keyword so equivalent variants aggregate into one row.

    Lower-cases, folds ``gleam.io`` -> ``gleam io``, and collapses whitespace.
    """

    folded = text.lower().replace("gleam.io", "gleam io")
    return " ".join(folded.split())


@dataclass
class PaidAggregate:
    keyword: str
    cost: float  # currency units (already divided out of micros)
    clicks: float
    impressions: float
    conversions: float

    @property
    def cpa(self) -> Optional[float]:
        if self.conversions <= 0:
            return None
        return self.cost / self.conversions

    @property
    def cost_per_click(self) -> Optional[float]:
        if self.clicks <= 0:
            return None
        return self.cost / self.clicks


def aggregate_keywords(rows: Iterable[dict]) -> list[PaidAggregate]:
    """Aggregate ``keyword_view`` rows by folded keyword text.

    Each row is a mapping with ``keyword`` (text), ``cost_micros``, ``clicks``,
    ``impressions`` and ``conversions``. Cost is returned in currency units.
    Results are sorted by cost descending.
    """

    cost: dict[str, float] = defaultdict(float)
    clicks: dict[str, float] = defaultdict(float)
    imps: dict[str, float] = defaultdict(float)
    conv: dict[str, float] = defaultdict(float)

    for row in rows:
        key = fold_keyword(row["keyword"])
        cost[key] += row.get("cost_micros", 0) or 0
        clicks[key] += row.get("clicks", 0) or 0
        imps[key] += row.get("impressions", 0) or 0
        conv[key] += row.get("conversions", 0) or 0

    aggregates = [
        PaidAggregate(
            keyword=key,
            cost=micros_to_units(cost[key]),
            clicks=clicks[key],
            impressions=imps[key],
            conversions=conv[key],
        )
        for key in cost
    ]
    aggregates.sort(key=lambda a: -a.cost)
    return aggregates


def lost_share_reading(rank_lost: float | None, budget_lost: float | None) -> str:
    """One-line interpretation of the two impression-share losses.

    Inputs are fractions in [0, 1] (or percentages 0-100; both are handled).
    Returns "not pulled this run" if either input is missing (Rule 0).
    """

    if rank_lost is None or budget_lost is None:
        return "not pulled this run"

    rl = rank_lost / 100 if rank_lost > 1 else rank_lost
    bl = budget_lost / 100 if budget_lost > 1 else budget_lost

    if rl > bl:
        return (
            f"rank-lost {rl:.0%} dwarfs budget-lost {bl:.0%}: we are being "
            f"outranked, not outspent — a bid / quality / landing-page problem, "
            f"not a budget one"
        )
    if bl > rl:
        return (
            f"budget-lost {bl:.0%} exceeds rank-lost {rl:.0%}: we are running "
            f"out of money before the day ends — raising budget captures more "
            f"impressions"
        )
    return f"rank-lost and budget-lost both {rl:.0%}"
