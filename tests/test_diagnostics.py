import unittest
from dataclasses import dataclass

from gleam_seo.diagnostics import QueryPageRow, cannibalisation, ctr_gaps


@dataclass
class Row:
    query: str
    clicks: float
    impressions: float
    position: float
    ctr: float = None


class TestCannibalisation(unittest.TestCase):
    def test_flags_query_whose_top_page_moved(self):
        now = [QueryPageRow("gleam alternative", "/blog/comparisons/", 50, 800)]
        prev = [QueryPageRow("gleam alternative", "/pricing/", 40, 800)]
        flagged = cannibalisation(now, prev)
        self.assertEqual(len(flagged), 1)
        self.assertEqual(flagged[0].page_now, "/blog/comparisons/")
        self.assertEqual(flagged[0].page_prev, "/pricing/")

    def test_no_flag_when_top_page_stable(self):
        now = [QueryPageRow("gleam alternative", "/blog/comparisons/", 50, 800)]
        prev = [QueryPageRow("gleam alternative", "/blog/comparisons/", 40, 800)]
        self.assertEqual(cannibalisation(now, prev), [])

    def test_top_page_is_highest_clicks(self):
        now = [
            QueryPageRow("q", "/a/", 10, 100),
            QueryPageRow("q", "/b/", 90, 100),
        ]
        prev = [QueryPageRow("q", "/b/", 90, 100)]
        # top page both weeks is /b/ -> no cannibalisation
        self.assertEqual(cannibalisation(now, prev), [])


class TestCtrGaps(unittest.TestCase):
    def test_flags_gleam_app_style_underperformer(self):
        # "gleam app": ~1180 imps at 1.6% CTR from position 3.4; own average at
        # position 3 is ~10%. Deficit ~84% -> flagged.
        curve = {3: 0.10}
        rows = [Row("gleam app", clicks=19, impressions=1180, position=3.4)]
        gaps = ctr_gaps(rows, curve)
        self.assertEqual(len(gaps), 1)
        self.assertGreater(gaps[0].deficit, 0.40)

    def test_not_flagged_when_close_to_benchmark(self):
        curve = {3: 0.10}
        rows = [Row("ok query", clicks=90, impressions=1000, position=3.0)]  # 9% vs 10%
        self.assertEqual(ctr_gaps(rows, curve), [])

    def test_below_impression_floor_ignored(self):
        curve = {3: 0.10}
        rows = [Row("small", clicks=0, impressions=100, position=3.0)]
        self.assertEqual(ctr_gaps(rows, curve), [])

    def test_uses_explicit_ctr_when_present(self):
        curve = {1: 0.30}
        rows = [Row("q", clicks=0, impressions=500, position=1.0, ctr=0.05)]
        gaps = ctr_gaps(rows, curve)
        self.assertEqual(len(gaps), 1)


if __name__ == "__main__":
    unittest.main()
