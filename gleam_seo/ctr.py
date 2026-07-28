"""CTR-by-position curve, derived from this week's own query data.

The Routine prompt is explicit: *"Derive the CTR-by-position curve from this
week's own query data — do not use a generic table."* A generic curve would be
wrong for a brand-heavy property like gleam.io, where position-1 CTR is far
higher than any published benchmark.

The curve buckets queries by rounded average position and takes the
impression-weighted mean CTR in each bucket. Impression weighting stops a
single low-volume query from distorting a bucket.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Mapping, Protocol


class _HasPositionMetrics(Protocol):
    clicks: float
    impressions: float
    position: float


def ctr_curve(rows: Iterable[_HasPositionMetrics]) -> dict[int, float]:
    """Return ``{rounded_position: impression_weighted_ctr}``.

    Rows with non-positive impressions or a missing position are skipped.
    """

    clicks: dict[int, float] = defaultdict(float)
    imps: dict[int, float] = defaultdict(float)
    for row in rows:
        position = getattr(row, "position", None)
        impressions = getattr(row, "impressions", 0) or 0
        if position is None or impressions <= 0:
            continue
        bucket = int(round(position))
        clicks[bucket] += getattr(row, "clicks", 0) or 0
        imps[bucket] += impressions
    return {b: clicks[b] / imps[b] for b in imps if imps[b] > 0}


def ctr_at(curve: Mapping[int, float], position: float | None) -> float | None:
    """Estimate CTR at ``position`` using the derived curve.

    Uses the exact rounded bucket when present, otherwise the nearest
    populated bucket. Returns ``None`` when the curve is empty or the position
    is unknown — never a fabricated fallback (Rule 0).
    """

    if position is None or not curve:
        return None
    bucket = int(round(position))
    if bucket in curve:
        return curve[bucket]
    nearest = min(curve, key=lambda b: (abs(b - bucket), b))
    return curve[nearest]
