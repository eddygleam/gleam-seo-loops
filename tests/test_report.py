import json
import unittest

from gleam_seo.report import NOT_PULLED, build_report


def _ahrefs_payload():
    """Ahrefs-variant snapshot: manual six-field block + Ahrefs GSC rows."""
    return {
        "today": "2026-07-28",
        "manual": {
            "brand_spend": 4700.0,
            "brand_conversions": 112,
            "brand_roas": 0.92,
            "brand_rank_lost_is": 0.452,
            "brand_budget_lost_is": 0.033,
            "conquest_cpa": 244.35,
        },
        "ctr_by_position": [
            {"position": 1, "average_ctr_percent": 30.0},
            {"position": 3, "average_ctr_percent": 10.0},
            {"position": 12, "average_ctr_percent": 2.0},
        ],
        "keyword_metrics": {"giveaway tool": {"volume": 5000, "cpc": 11.0}},
        "gsc_keywords": {
            "this_week": [
                {"query": "gleam", "clicks": 300, "impressions": 10000, "position": 1.2, "top_url": "https://gleam.io/"},
                {"query": "gleam app", "clicks": 19, "impressions": 1180, "position": 3.4, "top_url": "https://gleam.io/app"},
                {"query": "gleam competition", "clicks": 200, "impressions": 1000, "position": 3.0, "top_url": "https://gleam.io/competitions"},
                {"query": "giveaway tool", "clicks": 10, "impressions": 500, "position": 12.0, "top_url": "https://gleam.io/tool"},
                {"query": "gleam alternative", "clicks": 30, "impressions": 400, "position": 8.0, "top_url": "https://gleam.io/blog/comparisons/"},
                {"query": "steam key", "clicks": 99, "impressions": 5000, "position": 1.0, "top_url": "https://gleam.io/x"},
            ],
            "prior_week": [
                {"query": "gleam", "clicks": 310, "impressions": 10200, "position": 1.1, "top_url": "https://gleam.io/"},
                {"query": "gleam app", "clicks": 25, "impressions": 1200, "position": 3.3, "top_url": "https://gleam.io/app"},
                {"query": "giveaway tool", "clicks": 30, "impressions": 500, "position": 8.0, "top_url": "https://gleam.io/tool"},
                {"query": "gleam alternative", "clicks": 25, "impressions": 400, "position": 8.0, "top_url": "https://gleam.io/pricing"},
                {"query": "steam key", "clicks": 12, "impressions": 5000, "position": 9.0, "top_url": "https://gleam.io/x"},
            ],
        },
    }


class TestAhrefsVariant(unittest.TestCase):
    def setUp(self):
        self.report = build_report(_ahrefs_payload())

    def test_serialisable(self):
        json.dumps(self.report, default=str)

    def test_has_all_twelve_section_keys(self):
        for key in ["headline", "value_chart", "movers_up", "movers_down",
                    "priority_actions", "brand_paid", "conquest", "cannibalisation",
                    "ctr_gaps", "informational", "ga4_organic_revenue", "referral_revenue"]:
            self.assertIn(key, self.report)

    def test_brand_paid_from_manual_block(self):
        bp = self.report["brand_paid"]
        self.assertEqual(bp["spend"], 4700.0)
        self.assertEqual(bp["roas"], 0.92)
        self.assertAlmostEqual(bp["cpa"], round(4700.0 / 112, 2))
        self.assertIn("outranked", bp["lost_share_reading"])

    def test_conquest_vs_brand_multiple(self):
        self.assertIn("x brand CPA", self.report["conquest"]["vs_brand"])

    def test_ga4_sections_not_pulled(self):
        self.assertEqual(self.report["ga4_organic_revenue"], NOT_PULLED)
        self.assertEqual(self.report["referral_revenue"], NOT_PULLED)
        self.assertEqual(self.report["headline"]["organic_revenue"], NOT_PULLED)

    def test_ctr_curve_from_ahrefs_endpoint(self):
        self.assertEqual(self.report["ctr_curve_source"], "ahrefs gsc-ctr-by-position")
        self.assertAlmostEqual(self.report["ctr_curve"]["3"], 0.10)

    def test_ctr_gap_flags_gleam_app(self):
        self.assertIn("gleam app", {g["query"] for g in self.report["ctr_gaps"]})

    def test_cannibalisation_from_top_url(self):
        flagged = {c["query"] for c in self.report["cannibalisation"]}
        self.assertIn("gleam alternative", flagged)

    def test_excluded_query_absent(self):
        self.assertNotIn("steam key", {m["query"] for m in self.report["movers"]})

    def test_value_chart_only_has_computable_movers(self):
        for row in self.report["value_chart"]:
            self.assertIsNotNone(row["value_change"])

    def test_priority_actions_carry_a_where(self):
        for a in self.report["priority_actions"]:
            self.assertTrue(a.get("where"))

    def test_completion_counts_present(self):
        self.assertIn("queries_checked", self.report["counts"])
        self.assertIn("findings", self.report["counts"])


class TestManualBlockGuards(unittest.TestCase):
    def test_missing_manual_fields_render_not_pulled(self):
        payload = {
            "today": "2026-07-28",
            "manual": {"brand_spend": 4700.0},  # only one of six supplied
            "gsc_keywords": {"this_week": [], "prior_week": []},
        }
        report = build_report(payload)
        bp = report["brand_paid"]
        self.assertEqual(bp["spend"], 4700.0)
        self.assertEqual(bp["roas"], NOT_PULLED)
        self.assertEqual(bp["conversions"], NOT_PULLED)
        self.assertEqual(report["conquest"]["cpa"], NOT_PULLED)

    def test_unexpected_manual_field_rejected(self):
        payload = {
            "today": "2026-07-28",
            "manual": {"brand_spend": 1, "ga4_revenue": 999},  # not one of the six
            "gsc_keywords": {"this_week": [], "prior_week": []},
        }
        with self.assertRaises(ValueError):
            build_report(payload)


class TestRepoVariantPaidPath(unittest.TestCase):
    """The original repo loop feeds raw keyword_view; that path must still work."""

    def test_keyword_view_aggregates_into_brand_paid(self):
        payload = {
            "today": "2026-07-28",
            "gsc_keywords": {"this_week": [], "prior_week": []},
            "paid": {
                "keyword_view": [
                    {"keyword": "Gleam App", "cost_micros": 100_000_000, "clicks": 20, "impressions": 500, "conversions": 0},
                    {"keyword": "gleam app", "cost_micros": 85_690_000, "clicks": 23, "impressions": 400, "conversions": 0},
                ],
                "rank_lost": 0.452,
                "budget_lost": 0.033,
            },
        }
        report = build_report(payload)
        self.assertAlmostEqual(report["brand_paid"]["spend"], 185.69)
        self.assertIn("outranked", report["brand_paid"]["lost_share_reading"])


class TestWeekRanges(unittest.TestCase):
    def test_week_ranges_present(self):
        report = build_report(_ahrefs_payload())
        self.assertEqual(tuple(report["week_ranges"]["this_week"]), ("2026-07-21", "2026-07-27"))


if __name__ == "__main__":
    unittest.main()
