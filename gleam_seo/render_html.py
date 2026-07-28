"""Render ``findings.json`` into the standalone HTML report.

The template ``templates/weekly-report.html`` owns the structure (all twelve
sections) and the diverging value chart. This module only injects the findings
JSON into it — no layout decisions live here, so the report can never drift
into a "reduced version": every section in the template is always emitted.

    python -m gleam_seo.render_html \
        --findings findings.json \
        --template templates/weekly-report.html \
        --output report.html

The output is a single self-contained HTML file (no external assets), suitable
for writing straight to Google Drive alongside the run's snapshots.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

PLACEHOLDER = "/*__REPORT_DATA__*/"

_DEFAULT_TEMPLATE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "templates",
    "weekly-report.html",
)


def render(findings: dict, template: str) -> str:
    """Return the template with the findings JSON injected at the placeholder.

    Raises ``ValueError`` if the template is missing the data placeholder, so a
    silently-empty report can never be produced.
    """

    if PLACEHOLDER not in template:
        raise ValueError(
            f"template is missing the {PLACEHOLDER!r} placeholder; refusing to "
            f"render a report with no data hook"
        )
    # Escape </script> so an injected string can't break out of the data block.
    blob = json.dumps(findings, default=str).replace("</", "<\\/")
    return template.replace(PLACEHOLDER, blob)


def render_file(findings_path: str, template_path: str, output_path: str) -> None:
    with open(findings_path, encoding="utf-8") as fh:
        findings = json.load(fh)
    with open(template_path, encoding="utf-8") as fh:
        template = fh.read()
    html = render(findings, template)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render findings JSON into the HTML report.")
    parser.add_argument("--findings", "-f", default="-", help="Findings JSON path, or - for stdin.")
    parser.add_argument("--template", "-t", default=_DEFAULT_TEMPLATE, help="HTML template path.")
    parser.add_argument("--output", "-o", default="-", help="Output HTML path, or - for stdout.")
    args = parser.parse_args(argv)

    raw = sys.stdin.read() if args.findings == "-" else open(args.findings, encoding="utf-8").read()
    findings = json.loads(raw)
    with open(args.template, encoding="utf-8") as fh:
        template = fh.read()
    html = render(findings, template)

    if args.output == "-":
        print(html)
    else:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(html)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
