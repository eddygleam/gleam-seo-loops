import os
import unittest

from gleam_seo.render_html import END, START, render

TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "templates",
    "weekly-report.html",
)


def _template():
    with open(TEMPLATE_PATH, encoding="utf-8") as fh:
        return fh.read()


class TestTemplateStructure(unittest.TestCase):
    def test_template_has_twelve_numbered_sections(self):
        self.assertEqual(_template().count('class="snum"'), 12)

    def test_template_has_both_markers_in_order(self):
        t = _template()
        self.assertIn(START, t)
        self.assertIn(END, t)
        self.assertLess(t.find(START), t.find(END))

    def test_template_keeps_the_fixed_renderer(self):
        # The signature diverging strip and the render section must survive.
        t = _template()
        self.assertIn("SIGNATURE: diverging value-delta strip", t)
        self.assertIn("================= RENDER =================", t)


class TestRender(unittest.TestCase):
    def test_injects_report_and_replaces_sample(self):
        out = render({"week": "2099-W01", "period": "test"}, _template())
        self.assertIn('const REPORT = {"week": "2099-W01"', out)
        # the sample data ("live draw" etc.) must be gone
        self.assertNotIn("live draw", out)

    def test_markers_survive_for_reinjection(self):
        out = render({"week": "x"}, _template())
        self.assertIn(START, out)
        self.assertIn(END, out)

    def test_between_markers_is_only_our_object(self):
        out = render({"week": "x"}, _template())
        between = out.split(START, 1)[1].split(END, 1)[0]
        self.assertIn("const REPORT =", between)
        self.assertNotIn("diverge:", between)  # sample object is gone

    def test_script_closing_tag_escaped(self):
        out = render({"note": "x </script><script>bad</script>"}, _template())
        between = out.split(START, 1)[1].split(END, 1)[0]
        self.assertNotIn("</script>", between)
        self.assertIn("<\\/script>", between)

    def test_missing_marker_raises(self):
        with self.assertRaises(ValueError):
            render({"a": 1}, "<html>no markers</html>")

    def test_markers_out_of_order_raises(self):
        with self.assertRaises(ValueError):
            render({"a": 1}, END + " ... " + START)


if __name__ == "__main__":
    unittest.main()
