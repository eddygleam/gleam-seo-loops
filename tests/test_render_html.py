import json
import os
import re
import unittest

from gleam_seo.render_html import PLACEHOLDER, render

TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "templates",
    "weekly-report.html",
)


def _template():
    with open(TEMPLATE_PATH, encoding="utf-8") as fh:
        return fh.read()


class TestTemplateStructure(unittest.TestCase):
    def test_template_has_exactly_twelve_sections(self):
        template = _template()
        self.assertEqual(template.count('data-section="'), 12)

    def test_template_has_all_expected_section_ids(self):
        template = _template()
        for name in ["headline", "value-chart", "movers-up", "movers-down",
                     "priority-actions", "brand-paid", "conquest", "cannibalisation",
                     "ctr-gaps", "informational", "ga4-organic-revenue", "referral-revenue"]:
            self.assertIn('data-section="%s"' % name, template)

    def test_template_has_data_placeholder(self):
        self.assertIn(PLACEHOLDER, _template())


class TestRender(unittest.TestCase):
    def test_injects_findings_and_consumes_placeholder(self):
        out = render({"generated_for": "2026-07-28", "counts": {"findings": 3}}, _template())
        self.assertNotIn(PLACEHOLDER, out)
        self.assertIn('"generated_for"', out)

    def test_injected_json_is_recoverable(self):
        findings = {"headline": {"organic_clicks": {"this_week": 529}}, "value_chart": []}
        out = render(findings, _template())
        m = re.search(r'<script id="report-data" type="application/json">(.*?)</script>',
                      out, re.DOTALL)
        self.assertIsNotNone(m)
        recovered = json.loads(m.group(1))
        self.assertEqual(recovered["headline"]["organic_clicks"]["this_week"], 529)

    def test_script_closing_tag_in_data_is_escaped(self):
        findings = {"note": "danger </script><script>alert(1)</script>"}
        out = render(findings, _template())
        # The injected data must not contain a raw </script> that would close
        # the block early; it is escaped to <\/script>.
        m = re.search(r'<script id="report-data" type="application/json">(.*?)</script>',
                      out, re.DOTALL)
        self.assertIsNotNone(m)
        self.assertNotIn("</script>", m.group(1))
        self.assertIn("<\\/script>", m.group(1))

    def test_missing_placeholder_raises(self):
        with self.assertRaises(ValueError):
            render({"a": 1}, "<html>no placeholder here</html>")


if __name__ == "__main__":
    unittest.main()
