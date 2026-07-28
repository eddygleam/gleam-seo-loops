import unittest
from dataclasses import dataclass

from gleam_seo.ctr import ctr_at, ctr_curve


@dataclass
class Row:
    clicks: float
    impressions: float
    position: float


class TestCtrCurve(unittest.TestCase):
    def test_impression_weighted_within_bucket(self):
        rows = [
            Row(clicks=50, impressions=100, position=1.1),  # 50% ctr, 100 imps
            Row(clicks=10, impressions=900, position=1.4),  # ~1.1% ctr, 900 imps
        ]
        curve = ctr_curve(rows)
        # bucket 1: (50 + 10) / (100 + 900) = 0.06, not the simple mean of ~25.5%
        self.assertAlmostEqual(curve[1], 60 / 1000)

    def test_buckets_by_rounded_position(self):
        rows = [Row(clicks=1, impressions=10, position=3.4)]
        curve = ctr_curve(rows)
        self.assertIn(3, curve)
        self.assertNotIn(4, curve)

    def test_zero_impression_rows_skipped(self):
        rows = [Row(clicks=0, impressions=0, position=2.0)]
        self.assertEqual(ctr_curve(rows), {})


class TestCtrAt(unittest.TestCase):
    def setUp(self):
        self.curve = {1: 0.30, 3: 0.10, 8: 0.02}

    def test_exact_bucket(self):
        self.assertEqual(ctr_at(self.curve, 3.0), 0.10)

    def test_rounds_to_bucket(self):
        self.assertEqual(ctr_at(self.curve, 2.6), 0.10)  # rounds to 3

    def test_nearest_when_missing(self):
        # position 5 -> bucket 5 missing; nearest is 3 (distance 2) vs 8 (3)
        self.assertEqual(ctr_at(self.curve, 5.0), 0.10)

    def test_none_position_returns_none(self):
        self.assertIsNone(ctr_at(self.curve, None))

    def test_empty_curve_returns_none(self):
        self.assertIsNone(ctr_at({}, 1.0))


if __name__ == "__main__":
    unittest.main()
