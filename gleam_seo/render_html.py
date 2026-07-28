"""Render a computed ``REPORT`` object into the standalone HTML report.

The template ``templates/weekly-report.html`` owns the structure (all twelve
numbered sections), the diverging value strip and the fixed JS renderer. It
ships with a sample ``REPORT`` object between these two markers::

    /* @@REPORT_DATA_START@@ */
    const REPORT = { ... };
    /* @@REPORT_DATA_END@@ */

Per the template's own contract — "the loop overwrites this whole object each
run; everything below the object is pure rendering, leave it alone" — this
module replaces only the text between those markers with a freshly computed
``const REPORT = {...};``. The renderer is never touched.

    python -m gleam_seo.render_html \
        --report report.json \
        --template templates/weekly-report.html \
        --output report.html

``report.json`` is the output of ``gleam_seo.report`` (the REPORT-shaped object).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

START = "/* @@REPORT_DATA_START@@ */"
END = "/* @@REPORT_DATA_END@@ */"

_DEFAULT_TEMPLATE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "templates",
    "weekly-report.html",
)


def render(report: dict, template: str) -> str:
    """Return the template with its REPORT object replaced by ``report``.

    Raises ``ValueError`` if either marker is missing or they are out of order,
    so a malformed template can never silently drop the data.
    """

    start = template.find(START)
    end = template.find(END)
    if start == -1 or end == -1 or end < start:
        raise ValueError(
            f"template must contain {START!r} then {END!r}; refusing to render"
        )
    start += len(START)

    # Escape </ so a string value containing "</script>" cannot close the block.
    blob = json.dumps(report, default=str, ensure_ascii=False).replace("</", "<\\/")
    injected = "\n" + "const REPORT = " + blob + ";\n"
    return template[:start] + injected + template[end:]


def render_file(report_path: str, template_path: str, output_path: str) -> None:
    with open(report_path, encoding="utf-8") as fh:
        report = json.load(fh)
    with open(template_path, encoding="utf-8") as fh:
        template = fh.read()
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(render(report, template))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a REPORT object into the HTML report.")
    parser.add_argument("--report", "-r", default="-", help="REPORT JSON path, or - for stdin.")
    parser.add_argument("--template", "-t", default=_DEFAULT_TEMPLATE, help="HTML template path.")
    parser.add_argument("--output", "-o", default="-", help="Output HTML path, or - for stdout.")
    args = parser.parse_args(argv)

    raw = sys.stdin.read() if args.report == "-" else open(args.report, encoding="utf-8").read()
    report = json.loads(raw)
    with open(args.template, encoding="utf-8") as fh:
        template = fh.read()
    html = render(report, template)

    if args.output == "-":
        print(html)
    else:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(html)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
