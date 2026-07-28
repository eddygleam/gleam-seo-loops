"""Date-range helpers.

Two traps handled here:

* GSC "this week" is the 7 days *ending yesterday* — never including today,
  whose data is incomplete.
* GAQL has no ``LAST_90_DAYS`` literal, so brand paid pulls must build an
  explicit ``segments.date BETWEEN '<start>' AND '<end>'`` clause.

Every function takes an explicit ``today`` so the logic is deterministic and
testable (and so a back-fill run can pass a past date).
"""

from __future__ import annotations

from datetime import date, timedelta


def week_ranges(today: date) -> dict[str, tuple[str, str]]:
    """Return ISO date bounds for the two comparison weeks.

    ``this_week``  = the 7 days ending yesterday.
    ``prior_week`` = the 7 days before that.

    Bounds are inclusive ``YYYY-MM-DD`` strings, ready for
    ``gsc:get_advanced_search_analytics`` start/end dates.
    """

    yesterday = today - timedelta(days=1)
    this_start = yesterday - timedelta(days=6)
    prior_end = this_start - timedelta(days=1)
    prior_start = prior_end - timedelta(days=6)
    return {
        "this_week": (this_start.isoformat(), yesterday.isoformat()),
        "prior_week": (prior_start.isoformat(), prior_end.isoformat()),
    }


def gaql_date_between(today: date, lookback_days: int = 90) -> str:
    """Build a GAQL ``segments.date BETWEEN ...`` clause ending yesterday."""

    end = today - timedelta(days=1)
    start = end - timedelta(days=lookback_days - 1)
    return f"segments.date BETWEEN '{start.isoformat()}' AND '{end.isoformat()}'"
