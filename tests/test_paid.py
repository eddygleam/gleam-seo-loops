import unittest

from gleam_seo.paid import (
    aggregate_keywords,
    fold_keyword,
    lost_share_reading,
    micros_to_units,
)


class TestMicros(unittest.TestCase):
    def test_divides_by_million(self):
        self.assertEqual(micros_to_units(185_690_000), 185.69)


class TestFoldKeyword(unittest.TestCase):
    def test_lowercases(self):
        self.assertEqual(fold_keyword("Gleam App"), "gleam app")

    def test_folds_gleam_io(self):
        self.assertEqual(fold_keyword("gleam.io"), "gleam io")
        self.assertEqual(fold_keyword("Gleam.io reviews"), "gleam io reviews")

    def test_collapses_whitespace(self):
        self.assertEqual(fold_keyword("  gleam   app "), "gleam app")


class TestAggregateKeywords(unittest.TestCase):
    def test_folded_variants_merge_into_one_row(self):
        rows = [
            {"keyword": "Gleam App", "cost_micros": 100_000_000, "clicks": 20,
             "impressions": 500, "conversions": 0},
            {"keyword": "gleam app", "cost_micros": 85_690_000, "clicks": 23,
             "impressions": 400, "conversions": 0},
        ]
        agg = aggregate_keywords(rows)
        self.assertEqual(len(agg), 1)
        self.assertEqual(agg[0].keyword, "gleam app")
        self.assertAlmostEqual(agg[0].cost, 185.69)
        self.assertEqual(agg[0].clicks, 43)

    def test_gleam_io_folds_with_gleam_io_spaced(self):
        rows = [
            {"keyword": "gleam.io", "cost_micros": 10_000_000, "clicks": 1,
             "impressions": 10, "conversions": 0},
            {"keyword": "gleam io", "cost_micros": 20_000_000, "clicks": 2,
             "impressions": 20, "conversions": 0},
        ]
        agg = aggregate_keywords(rows)
        self.assertEqual(len(agg), 1)

    def test_cpa_none_when_no_conversions(self):
        rows = [{"keyword": "gleam app", "cost_micros": 185_690_000, "clicks": 43,
                 "impressions": 900, "conversions": 0}]
        self.assertIsNone(aggregate_keywords(rows)[0].cpa)

    def test_sorted_by_cost_descending(self):
        rows = [
            {"keyword": "cheap", "cost_micros": 1_000_000, "clicks": 1,
             "impressions": 1, "conversions": 0},
            {"keyword": "pricey", "cost_micros": 9_000_000, "clicks": 1,
             "impressions": 1, "conversions": 0},
        ]
        agg = aggregate_keywords(rows)
        self.assertEqual(agg[0].keyword, "pricey")


class TestLostShareReading(unittest.TestCase):
    def test_rank_lost_dominant_says_outranked(self):
        msg = lost_share_reading(0.452, 0.033)
        self.assertIn("outranked", msg)

    def test_budget_lost_dominant_says_out_of_money(self):
        msg = lost_share_reading(0.10, 0.60)
        self.assertIn("out of money", msg)

    def test_accepts_percentages(self):
        msg = lost_share_reading(45.2, 3.3)
        self.assertIn("outranked", msg)

    def test_missing_input_is_not_pulled(self):
        self.assertEqual(lost_share_reading(None, 0.033), "not pulled this run")


if __name__ == "__main__":
    unittest.main()
