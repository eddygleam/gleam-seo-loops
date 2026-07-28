"""Movement, materiality and scope thresholds (Step 2 of the Routine prompt).

Kept in one place so the report's judgement calls are auditable and can be
tuned without touching logic.

    | Track         | Movement trigger                                   | Materiality |
    |---------------|----------------------------------------------------|-------------|
    | Brand         | >=1 position, or worse than pos 3 with no movement | >=20 imps   |
    | Commercial    | >=3 positions, or left top 10, or lost position 1  | >=40 imps   |
    | Informational | >=5 positions                                      | >=250 imps  |

Ignore anything worse than position 20 unless its CPC is above A$6.
"""

from __future__ import annotations

from gleam_seo.classify import Track

MATERIALITY_IMPRESSIONS: dict[Track, float] = {
    Track.BRAND: 20,
    Track.COMMERCIAL: 40,
    Track.INFORMATIONAL: 250,
    Track.OTHER: 40,  # treat unclassified like commercial for materiality
}

# Minimum position-change (in ranks) to count as movement, per track.
MOVEMENT_MIN_POSITIONS: dict[Track, float] = {
    Track.BRAND: 1,
    Track.COMMERCIAL: 3,
    Track.INFORMATIONAL: 5,
    Track.OTHER: 3,
}

# Anything ranking worse (numerically larger) than this is ignored ...
POSITION_FLOOR: float = 20

# ... unless CPC (A$) exceeds this floor, in which case it is still worth money.
MIN_CPC_TO_KEEP_BELOW_POS_20: float = 6.0

# CTR-gap detection (Step 2).
CTR_GAP_MIN_IMPRESSIONS: float = 250
CTR_GAP_THRESHOLD: float = 0.40  # flag when >40% below own average at position
