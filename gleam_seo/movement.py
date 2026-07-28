"""Query matching across two weeks, movement/materiality filtering, and
value-change ranking (Step 2 of the Routine prompt).

The whole point of ranking by *estimated value change* rather than by position
change: a 47->29 jump is dramatic and worth nothing, while a top-3 term
slipping two places on an A$11 CPC is what actually costs money.

    value = volume x CTR-at-position x CPC

Volume and CPC come from Semrush; CTR-at-position comes from the curve derived
from this week's GSC data (:mod:`gleam_seo.ctr`). When volume or CPC is missing
for a query, the value fields are left ``None`` and the mover is ranked after
every mover that does have a computable value change (Rule 0: no invented
numbers).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Mapping, Optional

from gleam_seo.classify import Track, classify, normalize
from gleam_seo.thresholds import (
    MATERIALITY_IMPRESSIONS,
    MIN_CPC_TO_KEEP_BELOW_POS_20,
    POSITION_FLOOR,
)


@dataclass
class QueryRow:
    """One GSC query row for a single week."""

    query: str
    clicks: float
    impressions: float
    position: float
    ctr: Optional[float] = None  # GSC returns this; derived if absent
    top_url: Optional[str] = None  # Ahrefs gsc-keywords returns this per keyword

    def resolved_ctr(self) -> Optional[float]:
        if self.ctr is not None:
            return self.ctr
        if self.impressions and self.impressions > 0:
            return self.clicks / self.impressions
        return None


@dataclass
class Mover:
    query: str
    track: Track
    pos_now: Optional[float]
    pos_prev: Optional[float]
    pos_change: Optional[float]  # positive = worsened (moved down the SERP)
    clicks_now: float
    clicks_prev: float
    clicks_change: float
    impressions_now: float
    is_new: bool
    is_dropped: bool
    value_now: Optional[float] = None
    value_prev: Optional[float] = None
    value_change: Optional[float] = None
    volume: Optional[float] = None
    cpc: Optional[float] = None
    top_url: Optional[str] = None
    reasons: list[str] = field(default_factory=list)


def _passes_movement(track: Track, pos_now: float | None, pos_prev: float | None,
                     is_new: bool, is_dropped: bool) -> tuple[bool, list[str]]:
    """Apply the per-track movement trigger, returning (passed, reasons)."""

    reasons: list[str] = []

    # Appearing or disappearing is itself movement.
    if is_new:
        reasons.append("entered results")
        return True, reasons
    if is_dropped:
        reasons.append("dropped out of results")
        return True, reasons

    assert pos_now is not None and pos_prev is not None
    change = pos_now - pos_prev  # positive => worsened

    if track is Track.BRAND:
        if abs(change) >= 1:
            reasons.append(f"moved {abs(change):.1f} positions")
        if pos_now > 3 and abs(change) < 1:
            reasons.append("stuck worse than position 3")
    elif track in (Track.COMMERCIAL, Track.OTHER):
        if abs(change) >= 3:
            reasons.append(f"moved {abs(change):.1f} positions")
        if pos_prev <= 10 and pos_now > 10:
            reasons.append("left the top 10")
        if pos_prev <= 1.5 and pos_now > 1.5:
            reasons.append("lost position 1")
    elif track is Track.INFORMATIONAL:
        if abs(change) >= 5:
            reasons.append(f"moved {abs(change):.1f} positions")

    return bool(reasons), reasons


def _passes_materiality(track: Track, impressions_now: float) -> bool:
    return impressions_now >= MATERIALITY_IMPRESSIONS.get(track, float("inf"))


def _in_scope(pos_now: float | None, cpc: float | None) -> bool:
    """Ignore anything worse than position 20 unless its CPC is above the floor."""

    if pos_now is None:
        return True
    if pos_now <= POSITION_FLOOR:
        return True
    return cpc is not None and cpc > MIN_CPC_TO_KEEP_BELOW_POS_20


def estimated_value(volume: float | None, ctr_at_pos: float | None,
                    cpc: float | None) -> float | None:
    """volume x CTR-at-position x CPC, or ``None`` if any input is missing."""

    if volume is None or ctr_at_pos is None or cpc is None:
        return None
    return volume * ctr_at_pos * cpc


def rank_movers(
    this_week: Iterable[QueryRow],
    prior_week: Iterable[QueryRow],
    ctr_at_position: Callable[[float | None], float | None],
    metadata: Optional[Mapping[str, Mapping[str, float]]] = None,
) -> list[Mover]:
    """Match queries across weeks, filter, and rank by estimated value change.

    ``ctr_at_position`` maps an average position to an estimated CTR — pass
    ``functools.partial(gleam_seo.ctr.ctr_at, curve)``.

    ``metadata`` is an optional ``{normalized_query: {"volume": v, "cpc": c}}``
    mapping sourced from Semrush (volume and CPC only; positions always come
    from GSC per the prompt). CPC is expressed in the same currency the report
    uses (A$).

    Excluded-intent queries are dropped. Movers are returned sorted by absolute
    value change descending; movers without a computable value change sort
    last (Rule 0 — they are not guessed into an order).
    """

    metadata = metadata or {}
    now_by_query = {normalize(r.query): r for r in this_week}
    prev_by_query = {normalize(r.query): r for r in prior_week}
    all_keys = set(now_by_query) | set(prev_by_query)

    movers: list[Mover] = []
    for key in all_keys:
        now = now_by_query.get(key)
        prev = prev_by_query.get(key)
        display = (now or prev).query
        track = classify(display)
        if track is Track.EXCLUDED:
            continue

        is_new = now is not None and prev is None
        is_dropped = now is None and prev is not None

        pos_now = now.position if now else None
        pos_prev = prev.position if prev else None
        pos_change = (pos_now - pos_prev) if (pos_now is not None and pos_prev is not None) else None
        clicks_now = now.clicks if now else 0.0
        clicks_prev = prev.clicks if prev else 0.0
        impressions_now = now.impressions if now else 0.0

        meta = metadata.get(key, {})
        volume = meta.get("volume")
        cpc = meta.get("cpc")

        # Scope gate uses this-week position where available, else prior week.
        scope_pos = pos_now if pos_now is not None else pos_prev
        if not _in_scope(scope_pos, cpc):
            continue

        passed_movement, reasons = _passes_movement(
            track, pos_now, pos_prev, is_new, is_dropped
        )
        # Materiality is judged on whichever week has the query.
        material_impressions = impressions_now if now else (prev.impressions if prev else 0.0)
        if not (passed_movement and _passes_materiality(track, material_impressions)):
            continue

        value_now = estimated_value(volume, ctr_at_position(pos_now), cpc) if now else 0.0
        value_prev = estimated_value(volume, ctr_at_position(pos_prev), cpc) if prev else 0.0
        if value_now is None or value_prev is None:
            value_change = None
        else:
            value_change = value_now - value_prev

        movers.append(
            Mover(
                query=display,
                track=track,
                pos_now=pos_now,
                pos_prev=pos_prev,
                pos_change=pos_change,
                clicks_now=clicks_now,
                clicks_prev=clicks_prev,
                clicks_change=clicks_now - clicks_prev,
                impressions_now=impressions_now,
                is_new=is_new,
                is_dropped=is_dropped,
                value_now=value_now,
                value_prev=value_prev,
                value_change=value_change,
                volume=volume,
                cpc=cpc,
                top_url=(now.top_url if now else (prev.top_url if prev else None)),
                reasons=reasons,
            )
        )

    # Sort: computable value change first (by magnitude desc), then the rest
    # ordered by clicks change magnitude so they are at least deterministic.
    def sort_key(m: Mover) -> tuple:
        has_value = m.value_change is not None
        return (
            0 if has_value else 1,
            -abs(m.value_change) if has_value else 0.0,
            -abs(m.clicks_change),
            m.query,
        )

    movers.sort(key=sort_key)
    return movers
