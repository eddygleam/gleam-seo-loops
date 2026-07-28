import unittest
from functools import partial

from gleam_seo.classify import Track
from gleam_seo.ctr import ctr_at
from gleam_seo.movement import QueryRow, estimated_value, rank_movers


def flat_curve(_position):
    """A CTR function that returns 10% at every position (for value tests)."""
    return 0.10


class TestEstimatedValue(unittest.TestCase):
    def test_product(self):
        self.assertAlmostEqual(estimated_value(1000, 0.1, 5.0), 500.0)

    def test_missing_input_returns_none(self):
        self.assertIsNone(estimated_value(None, 0.1, 5.0))
        self.assertIsNone(estimated_value(1000, None, 5.0))
        self.assertIsNone(estimated_value(1000, 0.1, None))


class TestBrandMovement(unittest.TestCase):
    def test_brand_one_position_move_is_material(self):
        now = [QueryRow("gleam app", clicks=20, impressions=1180, position=4.4)]
        prev = [QueryRow("gleam app", clicks=25, impressions=1200, position=3.4)]
        movers = rank_movers(now, prev, flat_curve)
        self.assertEqual(len(movers), 1)
        self.assertIs(movers[0].track, Track.BRAND)

    def test_brand_stuck_worse_than_pos_3_with_no_movement(self):
        now = [QueryRow("gleam giveaway", clicks=5, impressions=200, position=6.0)]
        prev = [QueryRow("gleam giveaway", clicks=5, impressions=200, position=6.0)]
        movers = rank_movers(now, prev, flat_curve)
        self.assertEqual(len(movers), 1)
        self.assertIn("stuck worse than position 3", movers[0].reasons)

    def test_brand_below_materiality_dropped(self):
        now = [QueryRow("gleam thing", clicks=1, impressions=10, position=5.0)]
        prev = [QueryRow("gleam thing", clicks=1, impressions=10, position=8.0)]
        self.assertEqual(rank_movers(now, prev, flat_curve), [])


class TestCommercialMovement(unittest.TestCase):
    def test_left_top_10(self):
        now = [QueryRow("giveaway tool", clicks=10, impressions=500, position=12.0)]
        prev = [QueryRow("giveaway tool", clicks=30, impressions=500, position=8.0)]
        movers = rank_movers(now, prev, flat_curve)
        self.assertIn("left the top 10", movers[0].reasons)

    def test_small_commercial_move_ignored(self):
        # 2-position move, below the 3-position commercial trigger
        now = [QueryRow("giveaway tool", clicks=10, impressions=500, position=6.0)]
        prev = [QueryRow("giveaway tool", clicks=10, impressions=500, position=4.0)]
        self.assertEqual(rank_movers(now, prev, flat_curve), [])

    def test_lost_position_one(self):
        now = [QueryRow("giveaway app", clicks=10, impressions=500, position=3.0)]
        prev = [QueryRow("giveaway app", clicks=40, impressions=500, position=1.0)]
        movers = rank_movers(now, prev, flat_curve)
        self.assertIn("lost position 1", movers[0].reasons)


class TestScopeGate(unittest.TestCase):
    def test_below_position_20_ignored_without_high_cpc(self):
        now = [QueryRow("giveaway tool", clicks=1, impressions=500, position=29.0)]
        prev = [QueryRow("giveaway tool", clicks=1, impressions=500, position=47.0)]
        # 18-position move but both worse than pos 20 and no CPC -> ignored
        self.assertEqual(rank_movers(now, prev, flat_curve), [])

    def test_below_position_20_kept_when_cpc_above_floor(self):
        now = [QueryRow("giveaway tool", clicks=1, impressions=500, position=29.0)]
        prev = [QueryRow("giveaway tool", clicks=1, impressions=500, position=47.0)]
        meta = {"giveaway tool": {"volume": 1000, "cpc": 7.0}}
        movers = rank_movers(now, prev, flat_curve, metadata=meta)
        self.assertEqual(len(movers), 1)


class TestValueRanking(unittest.TestCase):
    def test_ranks_by_value_change_not_position_change(self):
        # A: huge position jump deep in the SERP, cheap CPC -> tiny value.
        # B: small slip near the top, expensive CPC -> large value.
        now = [
            QueryRow("giveaway tool", clicks=1, impressions=500, position=29.0),
            QueryRow("contest platform", clicks=30, impressions=500, position=3.0),
        ]
        prev = [
            QueryRow("giveaway tool", clicks=1, impressions=500, position=47.0),
            QueryRow("contest platform", clicks=45, impressions=500, position=1.0),
        ]
        meta = {
            "giveaway tool": {"volume": 100, "cpc": 0.5},
            "contest platform": {"volume": 5000, "cpc": 11.0},
        }

        def curve(pos):
            # steep curve so the top-3 slip actually costs CTR
            return {1: 0.4, 3: 0.15, 29: 0.01, 47: 0.005}.get(round(pos), 0.01)

        movers = rank_movers(now, prev, curve, metadata=meta)
        self.assertEqual(movers[0].query, "contest platform")
        self.assertIsNotNone(movers[0].value_change)

    def test_missing_metadata_sorts_after_valued_movers(self):
        now = [
            QueryRow("contest platform", clicks=30, impressions=500, position=5.0),
            QueryRow("giveaway tool", clicks=10, impressions=500, position=5.0),
        ]
        prev = [
            QueryRow("contest platform", clicks=45, impressions=500, position=1.0),
            QueryRow("giveaway tool", clicks=40, impressions=500, position=1.0),
        ]
        meta = {"contest platform": {"volume": 5000, "cpc": 11.0}}
        movers = rank_movers(now, prev, flat_curve, metadata=meta)
        self.assertEqual(movers[0].query, "contest platform")
        self.assertIsNone(movers[-1].value_change)


class TestNewAndDropped(unittest.TestCase):
    def test_new_query_flagged(self):
        now = [QueryRow("gleam app", clicks=10, impressions=500, position=2.0)]
        movers = rank_movers(now, [], flat_curve)
        self.assertTrue(movers[0].is_new)
        self.assertIn("entered results", movers[0].reasons)

    def test_dropped_query_flagged(self):
        prev = [QueryRow("gleam app", clicks=10, impressions=500, position=2.0)]
        movers = rank_movers([], prev, flat_curve)
        self.assertTrue(movers[0].is_dropped)
        self.assertIn("dropped out of results", movers[0].reasons)


class TestExclusionsDropped(unittest.TestCase):
    def test_excluded_query_never_a_mover(self):
        now = [QueryRow("steam key", clicks=100, impressions=5000, position=1.0)]
        prev = [QueryRow("steam key", clicks=10, impressions=5000, position=9.0)]
        self.assertEqual(rank_movers(now, prev, flat_curve), [])


if __name__ == "__main__":
    unittest.main()
