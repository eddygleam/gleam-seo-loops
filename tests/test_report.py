import json
import unittest

from gleam_seo.report import build_report


class TestBuildReport(unittest.TestCase):
    def _payload(self):
        return {
            "today": "2026-07-28",
            "gsc_keywords": {
                "this_week": [
                    {"query": "gleam", "clicks": 300, "impressions": 10000, "position": 1.2},
                    {"query": "gleam app", "clicks": 19, "impressions": 1180, "position": 3.4},
                    # A healthy position-3 brand query sets the position-3
                    # benchmark that "gleam app" falls short of.
                    {"query": "gleam competition", "clicks": 200, "impressions": 1000, "position": 3.0},
                    {"query": "giveaway tool", "clicks": 10, "impressions": 500, "position": 12.0},
                    {"query": "steam key", "clicks": 99, "impressions": 5000, "position": 1.0},
                ],
                "prior_week": [
                    {"query": "gleam", "clicks": 310, "impressions": 10200, "position": 1.1},
                    {"query": "gleam app", "clicks": 25, "impressions": 1200, "position": 3.3},
                    {"query": "giveaway tool", "clicks": 30, "impressions": 500, "position": 8.0},
                    {"query": "steam key", "clicks": 12, "impressions": 5000, "position": 9.0},
                ],
            },
            "semrush": {
                "giveaway tool": {"volume": 5000, "cpc": 11.0},
            },
            "paid": {
                "keyword_view": [
                    {"keyword": "Gleam App", "cost_micros": 185_690_000, "clicks": 43,
                     "impressions": 900, "conversions": 0},
                ],
                "rank_lost": 0.452,
                "budget_lost": 0.033,
            },
        }

    def test_report_is_json_serialisable(self):
        report = build_report(self._payload())
        json.dumps(report, default=str)  # must not raise

    def test_excluded_query_absent_from_movers(self):
        report = build_report(self._payload())
        queries = {m["query"] for m in report["movers"]}
        self.assertNotIn("steam key", queries)

    def test_commercial_mover_captured(self):
        report = build_report(self._payload())
        queries = {m["query"] for m in report["movers"]}
        self.assertIn("giveaway tool", queries)

    def test_week_ranges_present(self):
        report = build_report(self._payload())
        self.assertEqual(tuple(report["week_ranges"]["this_week"]), ("2026-07-21", "2026-07-27"))

    def test_paid_lost_share_reading_computed(self):
        report = build_report(self._payload())
        self.assertIn("outranked", report["paid"]["lost_share_reading"])

    def test_paid_cost_in_currency_units(self):
        report = build_report(self._payload())
        self.assertAlmostEqual(report["paid"]["top_keywords"][0]["cost"], 185.69)

    def test_ctr_gap_flags_gleam_app(self):
        report = build_report(self._payload())
        gap_queries = {g["query"] for g in report["ctr_gaps"]}
        self.assertIn("gleam app", gap_queries)

    def test_counts_present(self):
        report = build_report(self._payload())
        self.assertEqual(report["counts"]["queries_checked"], 5)

    def test_cannibalisation_not_pulled_without_query_pages(self):
        report = build_report(self._payload())
        self.assertEqual(report["cannibalisation"], "not pulled this run")


if __name__ == "__main__":
    unittest.main()
