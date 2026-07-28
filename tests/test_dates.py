import unittest
from datetime import date

from gleam_seo.dates import gaql_date_between, week_ranges


class TestWeekRanges(unittest.TestCase):
    def test_this_week_ends_yesterday_and_is_seven_days(self):
        r = week_ranges(date(2026, 7, 28))
        self.assertEqual(r["this_week"], ("2026-07-21", "2026-07-27"))

    def test_prior_week_is_the_seven_days_before(self):
        r = week_ranges(date(2026, 7, 28))
        self.assertEqual(r["prior_week"], ("2026-07-14", "2026-07-20"))

    def test_no_overlap_and_contiguous(self):
        r = week_ranges(date(2026, 1, 1))
        # prior_week end is the day before this_week start
        self.assertEqual(r["prior_week"][1], "2025-12-24")
        self.assertEqual(r["this_week"][0], "2025-12-25")


class TestGaqlBetween(unittest.TestCase):
    def test_ninety_day_window_ends_yesterday(self):
        clause = gaql_date_between(date(2026, 7, 28), lookback_days=90)
        self.assertEqual(
            clause,
            "segments.date BETWEEN '2026-04-29' AND '2026-07-27'",
        )

    def test_no_last_90_days_literal(self):
        self.assertNotIn("LAST_90_DAYS", gaql_date_between(date(2026, 7, 28)))


if __name__ == "__main__":
    unittest.main()
