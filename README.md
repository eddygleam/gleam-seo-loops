# gleam-seo-loops

Tested, deterministic backbone for Gleam.io's recurring SEO Routines ("loops").

The weekly SEO report was originally a single self-contained Routine prompt that asked the
agent to pull data from a dozen connectors **and** do all the arithmetic — matching queries
across two weeks, computing position and value deltas, ranking movers, deriving a CTR curve,
spotting cannibalisation, normalising Google Ads spend. Asking a language model to do that
arithmetic in its head produced wrong output more than once (a fabricated competitor
ad-copy claim; a false "Gleam is absent from this SERP" finding).

This repo fixes that by splitting the job in two:

- **The agent still pulls the data and writes the output** (Slack canvas, Linear issues).
  That is judgement and tool-calling, which is what it is good at.
- **The arithmetic lives in `gleam_seo/`** — pure, unit-tested Python that cannot silently
  drift and never invents a number.

## Layout

```
loops/
  weekly-report.md              Routine prompt (repo attached, full connector set). Pulls raw
                                Google Ads keyword_view etc. into the driver.
  weekly-report-ahrefs.md       Routine prompt for a session with Ahrefs + Drive + Slack +
                                Linear but no GSC/Google Ads/GA4/Semrush connectors. Pulls
                                GSC-equivalent data + volume/CPC from Ahrefs (project_id
                                684395); Google Ads + GA4 come from a six-field manual block.
  weekly-report-v1-standalone.md  The original no-repo prompt, kept for reference / fallback.
templates/
  weekly-report.html            The canonical report: all twelve sections + the diverging
                                value chart, self-contained (no external assets).
gleam_seo/
  classify.py    Track classification: brand / commercial / informational / other / excluded (Rule 2).
  dates.py       GSC week ranges (7 days ending yesterday) and the GAQL BETWEEN clause.
  ctr.py         CTR-by-position curve derived from this week's own data; CTR-at-position lookup.
  movement.py    Match queries across weeks, apply movement + materiality gates, rank by value change.
  diagnostics.py Cannibalisation (top ranking page moved) and CTR-gap detection.
  paid.py        Google Ads micros → currency, keyword folding, aggregation, rank- vs budget-lost reading.
  thresholds.py  Every movement / materiality / scope threshold, in one auditable place.
  report.py      Driver: snapshot JSON in → computed findings JSON out (`python -m gleam_seo.report`).
  render_html.py Inject findings into templates/weekly-report.html (`python -m gleam_seo.render_html`).
tests/           unittest-based tests for every module (also run under pytest).
```

## Two Routine variants, one driver

Both prompts feed the same `build_report` driver; they differ only in where the data comes
from. The driver accepts either a `manual` block (six pre-aggregated Google Ads + GA4 fields —
the Ahrefs variant) **or** a `paid` block of raw `keyword_view` rows it aggregates itself (the
full-connector variant). `manual` wins if both are present, and it rejects any seventh field so
it cannot silently grow. In the Ahrefs variant, GA4 revenue has no source, so those sections
render `"not pulled this run"` — by design, per Rule 0. Ahrefs CPC is USD; the manual paid
figures are A$; the report labels both, and the value-change ranking is unaffected by the FX
gap because it is scale-invariant.

## The two design rules that shape everything

- **Rule 0 — never report a number you did not pull.** Functions return `None` / omit fields
  when an input is missing; the driver emits `"not pulled this run"` for absent sections.
  Nothing here fabricates a fallback value.
- **Rule 2 — three tracks, never mixed in one average.** Brand (anything containing "gleam"),
  commercial (tool/software/conquest/…), informational (ideas/how-to/…). `gleam` alone is
  ~10k weekly impressions and would swamp any average it sits in, so the tracks are scored
  and reported separately.

## Running the driver

```bash
python -m gleam_seo.report --input snapshot.json --output findings.json
```

See `loops/weekly-report.md` for the snapshot input shape and how each Routine step feeds it.

## Tests

No third-party dependencies required — the tests are `unittest.TestCase` classes:

```bash
python -m unittest discover -s tests     # stdlib, zero installs
python -m pytest -q                       # if pytest is available
```

## Why "loops"

Each Routine is a loop: pull → snapshot to Drive → diff against last week's snapshot →
report → repeat next week. The snapshots are the loop's memory; the code in `gleam_seo/` is
the part of the loop that must be right every time, so it is tested rather than reasoned.
