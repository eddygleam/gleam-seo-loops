import json
import unittest

from gleam_seo.render_html import END, START, render
from gleam_seo.report import NOT_PULLED, build_report
from tests.test_render_html import _template


def _payload():
    """Ahrefs-variant snapshot: manual six-field block + Ahrefs GSC data."""
    return {
        "today": "2026-07-28",
        "meta": {"units": {"ahrefs": 1840, "semrush": 0}},
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
            {"position": 8, "average_ctr_percent": 5.0},
            {"position": 11, "average_ctr_percent": 2.0},
        ],
        "keyword_metrics": {
            "live draw": {"volume": 590, "cpc": 11.24, "cluster": "Tool"},
            "contest platform": {"volume": 110, "cpc": 8.10},
        },
        "gsc_keywords": {
            "this_week": [
                {"query": "gleam", "clicks": 300, "impressions": 10000, "position": 1.2, "top_url": "https://gleam.io/"},
                {"query": "gleam app", "clicks": 19, "impressions": 1180, "position": 3.4, "top_url": "https://gleam.io/app"},
                {"query": "gleam competition", "clicks": 200, "impressions": 1000, "position": 3.0, "top_url": "https://gleam.io/c"},
                {"query": "live draw", "clicks": 8, "impressions": 500, "position": 11.0, "top_url": "https://gleam.io/templates/live-draw"},
                {"query": "contest platform", "clicks": 40, "impressions": 500, "position": 2.0, "top_url": "https://gleam.io/app/competitions"},
                {"query": "gleam alternative", "clicks": 30, "impressions": 400, "position": 8.0, "top_url": "https://gleam.io/blog/comparisons/"},
                {"query": "steam key", "clicks": 99, "impressions": 5000, "position": 1.0, "top_url": "https://gleam.io/x"},
            ],
            "prior_week": [
                {"query": "gleam", "clicks": 310, "impressions": 10200, "position": 1.1, "top_url": "https://gleam.io/"},
                {"query": "gleam app", "clicks": 25, "impressions": 1200, "position": 3.3, "top_url": "https://gleam.io/app"},
                {"query": "live draw", "clicks": 20, "impressions": 500, "position": 8.0, "top_url": "https://gleam.io/templates/live-draw"},
                {"query": "contest platform", "clicks": 30, "impressions": 500, "position": 4.0, "top_url": "https://gleam.io/app/competitions"},
                {"query": "gleam alternative", "clicks": 25, "impressions": 400, "position": 8.0, "top_url": "https://gleam.io/pricing"},
                {"query": "steam key", "clicks": 12, "impressions": 5000, "position": 9.0, "top_url": "https://gleam.io/x"},
            ],
        },
    }


class TestReportShape(unittest.TestCase):
    def setUp(self):
        self.r = build_report(_payload())

    def test_all_top_level_keys_present(self):
        for k in ["week", "period", "generated", "findings", "priority1", "units",
                  "status", "kpis", "kpisrc", "diverge", "gained", "lost", "cannib",
                  "ctrgap", "sov", "displace", "newpages", "ai", "queue", "brand",
                  "rev", "ref", "info", "method"]:
            self.assertIn(k, self.r)

    def test_nested_sections_have_required_keys(self):
        self.assertEqual(set(self.r["ai"]) >= {"kpis", "rows"}, True)
        self.assertEqual(set(self.r["rev"]) >= {"kpis", "rows", "note"}, True)
        self.assertEqual(set(self.r["ref"]) >= {"kpis", "rows", "note"}, True)
        self.assertEqual(set(self.r["info"]) >= {"kpis", "rows", "paid"}, True)
        for k in ["_source", "kpis", "paid", "paidsrc", "serp", "attack", "note", "datagap"]:
            self.assertIn(k, self.r["brand"])

    def test_week_and_period_derived(self):
        self.assertTrue(self.r["week"].startswith("2026-W"))
        self.assertIn("July 2026", self.r["period"])

    def test_brand_kpis_from_manual_block(self):
        vals = {k["k"]: k for k in self.r["brand"]["kpis"]}
        self.assertEqual(vals["Brand rank-lost impression share"]["v"], "45.2%")
        self.assertEqual(vals["Brand paid ROAS"]["v"], "0.92")
        self.assertTrue(vals["Brand paid CPA"]["v"].startswith("A$"))
        self.assertIn("cheaper", vals["Brand paid CPA"]["d"])

    def test_ga4_sections_not_pulled(self):
        self.assertEqual(self.r["rev"]["note"], NOT_PULLED)
        self.assertEqual(self.r["ref"]["note"], NOT_PULLED)
        self.assertEqual(self.r["rev"]["rows"], [])

    def test_diverge_pos_string_and_value(self):
        kws = {d["kw"]: d for d in self.r["diverge"]}
        self.assertIn("live draw", kws)
        self.assertEqual(kws["live draw"]["pos"], "8→11")
        self.assertIsInstance(kws["live draw"]["d"], int)

    def test_lost_has_diagnosis_and_dtype(self):
        lost = {row["kw"]: row for row in self.r["lost"]}
        self.assertIn("live draw", lost)
        self.assertIn(lost["live draw"]["dtype"], {"rank", "cannib", "serp"})

    def test_cannibalisation_from_top_url(self):
        self.assertIn("gleam alternative", {c["kw"] for c in self.r["cannib"]})

    def test_ctrgap_flags_gleam_app(self):
        self.assertIn("gleam app", {g["kw"] for g in self.r["ctrgap"]})

    def test_excluded_query_absent_everywhere(self):
        allkw = ({d["kw"] for d in self.r["diverge"]}
                 | {g["kw"] for g in self.r["gained"]}
                 | {l["kw"] for l in self.r["lost"]})
        self.assertNotIn("steam key", allkw)

    def test_queue_seeded_with_where_on_every_item(self):
        self.assertTrue(self.r["queue"])
        for q in self.r["queue"]:
            for item in q["items"]:
                self.assertTrue(item["where"])

    def test_units_passed_through(self):
        self.assertEqual(self.r["units"], {"ahrefs": 1840, "semrush": 0})


class TestNarrativeMerge(unittest.TestCase):
    def test_narrative_overrides_prose_sections(self):
        payload = _payload()
        payload["narrative"] = {
            "kpis": [{"k": "Commercial visibility", "v": "34.2%", "d": "+0.8 WoW", "dir": "up", "note": "x"}],
            "rev": {"kpis": [], "rows": [{"pg": "/pricing", "rev": 1920, "sess": 890, "q": "gleam pricing", "pos": 11, "clicks": 64, "read": "fix"}], "note": "GA4 pulled"},
            "status": {"level": "action", "line": "custom line", "quiet_line": "q"},
        }
        r = build_report(payload)
        self.assertEqual(r["kpis"][0]["k"], "Commercial visibility")
        self.assertEqual(r["rev"]["note"], "GA4 pulled")
        self.assertEqual(r["rev"]["rows"][0]["pg"], "/pricing")
        self.assertEqual(r["status"]["line"], "custom line")


class TestManualGuard(unittest.TestCase):
    def test_unexpected_manual_field_rejected(self):
        payload = {"today": "2026-07-28", "manual": {"brand_spend": 1, "ga4_revenue": 9},
                   "gsc_keywords": {"this_week": [], "prior_week": []}}
        with self.assertRaises(ValueError):
            build_report(payload)

    def test_missing_manual_fields_render_not_pulled(self):
        payload = {"today": "2026-07-28", "manual": {"brand_spend": 4700.0},
                   "gsc_keywords": {"this_week": [], "prior_week": []}}
        r = build_report(payload)
        vals = {k["k"]: k["v"] for k in r["brand"]["kpis"]}
        self.assertEqual(vals["Brand rank-lost impression share"], NOT_PULLED)


class TestRepoVariantPaidPath(unittest.TestCase):
    def test_keyword_view_path_feeds_brand(self):
        payload = {
            "today": "2026-07-28",
            "gsc_keywords": {"this_week": [], "prior_week": []},
            "paid": {
                "keyword_view": [
                    {"keyword": "Gleam App", "cost_micros": 100_000_000, "clicks": 20, "impressions": 500, "conversions": 4},
                ],
                "roas": 0.9, "rank_lost": 0.452, "budget_lost": 0.033,
            },
        }
        r = build_report(payload)
        vals = {k["k"]: k["v"] for k in r["brand"]["kpis"]}
        self.assertEqual(vals["Brand paid ROAS"], "0.90")
        self.assertEqual(vals["Brand rank-lost impression share"], "45.2%")


class TestEndToEndRender(unittest.TestCase):
    def test_build_then_render_is_valid_html(self):
        r = build_report(_payload())
        html = render(r, _template())
        self.assertIn("const REPORT =", html)
        self.assertNotIn("live draw\",", html.split(START, 1)[0])  # only in injected data
        between = html.split(START, 1)[1].split(END, 1)[0]
        self.assertIn('"live draw"', between)
        # serialisable
        json.dumps(r, default=str)


if __name__ == "__main__":
    unittest.main()
