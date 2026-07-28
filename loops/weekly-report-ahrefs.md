# Gleam.io weekly SEO report — Ahrefs variant (repo attached)

Use this variant when the session has **Ahrefs, Google Drive, Slack and Linear** but **no
direct Google Search Console, Google Ads, GA4 or Semrush connectors** — which is the current
setup. It pulls GSC‑equivalent data and keyword volume/CPC from **Ahrefs**, and takes the
Google Ads + GA4 numbers from a small **manual block** a human fills in at the top of the
snapshot. All arithmetic is done by the tested code in `gleam_seo/`; you pull and you write,
you do not compute.

Connectors this variant needs: **Ahrefs, Google Drive, Slack, Linear.**

Two things about Ahrefs' GSC integration, confirmed for this account:

- The gleam.io Search Console property is linked to Ahrefs **project_id `684395`** ("Gleam.io
  Main", verified, subdomains). **Use `project_id: 684395` for every `gsc-*` call.**
- `gsc-ctr-by-position` returns live own‑data at **0 API units** — use it for the CTR curve.

Currency note, because it matters and must be labelled honestly: Ahrefs reports **CPC in USD
cents**. The driver converts it to dollars but cannot convert USD→AUD (there is no FX source,
and the manual block is capped at six fields). So **organic value figures are indicative USD**;
**brand paid figures in the manual block are the real A$** from Google Ads. The report labels
both. The value‑change *ranking* is unaffected by the FX gap (it is scale‑invariant).

---

You are producing the weekly SEO report for gleam.io. Work through every step. Be terse in
chat; the deliverable is the HTML report, the Slack canvas and the Linear issues.

## Rule 0 — never report a number you did not pull

The driver enforces this: any manual field you leave unset renders as `"not pulled this run"`,
and value fields stay `null` when volume or CPC is missing. Do not fill those in. In this
variant GA4 revenue has **no** source at all, so sections 11 and 12 and the "organic revenue"
headline will read `"not pulled this run"` every week until a GA4 connector or field exists —
that is correct, not a failure.

The two competitor/SERP traps from the original still apply: quote competitor ad text, never
infer it; and never claim Gleam is absent from a SERP without checking (Gleam ranks #8 for
"gleam alternative" via /blog/comparisons/).

## Rule 1 — every recommendation carries a location

The driver seeds each priority action with a `where` (the `top_url` Ahrefs attaches to the
query, or the GSC query itself). Keep it when you refine wording. An item without a `where`
does not ship.

## Rule 2 — three tracks, never mixed

Classification is done by `gleam_seo.classify`. Brand = contains "gleam"; commercial =
tool/software/platform/app/…/alternative(conquest)/action phrasings; informational =
ideas/examples/how‑to/rules/legal; excluded = software giveaway(s)/free software/giveaway of
the day/steam key/nft giveaway/crypto giveaway.

## The manual block — Google Ads + GA4, exactly six fields

At the **top** of the snapshot JSON, before any Ahrefs data, put a `manual` block with
**exactly** these six fields. Fill what you have from Google Ads (account 9047806202, AUD);
leave anything you cannot get out — the driver renders it as "not pulled this run", and it
**rejects any seventh field** so the block cannot quietly grow:

```json
{
  "manual": {
    "brand_spend":          4700.0,   // A$, brand campaign, last 7 days
    "brand_conversions":    112,
    "brand_roas":           0.92,
    "brand_rank_lost_is":   0.452,    // search_rank_lost_impression_share (fraction or %)
    "brand_budget_lost_is": 0.033,    // search_budget_lost_impression_share
    "conquest_cpa":         244.35    // A$, competitors campaign
  }
}
```

Baselines from 2026-07-28 to sanity‑check against (suspect the pull, not the baseline, if they
disagree without cause): brand CPA A$41.69, ROAS 0.92; conquest CPA A$244.35 (≈5.9× brand);
rank‑lost 45.2% vs budget‑lost 3.3%.

## Step 1 — Ahrefs GSC pulls (project_id 684395)

Use `gleam_seo.dates.week_ranges(today)` for the bounds. For each week call:

- `mcp__Ahrefs__gsc-keywords` — `{project_id: 684395, date_from, date_to, limit: 250}`. Returns
  per keyword: `clicks, impressions, position, ctr, top_url`. **Keep `top_url`** — it is what
  the driver uses to detect cannibalisation, so no separate query+page pull is needed.
- `mcp__Ahrefs__gsc-pages` — `{project_id: 684395, date_from, date_to, limit: 100}` for the
  page‑level view.
- `mcp__Ahrefs__gsc-ctr-by-position` — `{project_id: 684395, date_from, date_to}` (0 units).
  Returns `[{position, average_ctr_percent, keyword_count}]`.

Map each `gsc-keywords` row to `{query: <keyword>, clicks, impressions, position, top_url}`
(drop `ctr`; the driver derives it from clicks/impressions to avoid unit ambiguity). Put the
ctr‑by‑position rows into the snapshot's `ctr_by_position` field verbatim.

## Step 2 — keyword volume & CPC from Ahrefs (replaces Semrush)

For the top three movers and any brand‑modifier term, call
`mcp__Ahrefs__keywords-explorer-overview` with `{select: "keyword,volume,cpc", country: "AU",
keywords: "<comma list>"}`. `cpc` is **USD cents** — divide by 100 to dollars. Put results in
the snapshot's `keyword_metrics` block, keyed by the (normalised) query:

```json
"keyword_metrics": { "giveaway tool": { "volume": 5000, "cpc": 11.0 } }
```

The driver only ever reads volume and CPC from here; **position always comes from the GSC
rows**, never from Ahrefs' organic position (they disagree, and GSC wins).

## Step 3 — run the driver, then render

```bash
python -m gleam_seo.report      --input snapshot.json  --output findings.json
python -m gleam_seo.render_html --findings findings.json --output report.html
```

`findings.json` contains all twelve sections' data. `report.html` is the self‑contained report
built from `templates/weekly-report.html` — **all 12 sections, same diverging value chart**.
Do not hand‑edit either to shorten the report; the template always emits every section, with an
empty/"not pulled" state where there is nothing to show.

The twelve sections: (1) headline numbers, (2) movers by estimated value change — the diverging
chart, (3) top movers up, (4) top movers down, (5) priority actions, (6) brand paid, (7)
conquest, (8) cannibalisation, (9) CTR gaps, (10) informational queue, (11) organic revenue by
landing page (GA4), (12) referral revenue. Sections 11 and 12 read "not pulled this run" in this
variant.

## Step 4 — snapshot to Drive

Write the run's raw pulls to Google Drive as JSON in folder `Gleam SEO snapshots`, named
`YYYY-MM-DD-<kind>.json` for kinds `gsc_keywords`, `gsc_pages`, `ctr_by_position`,
`keyword_metrics`, `manual`, and the computed `findings`. Also write `report.html`. Next week's
run reads the prior `gsc_keywords` snapshot as `prior_week` instead of a second live pull.

## Step 5 — output

**Slack** — create a canvas in `#seo` titled `SEO — <ISO week>` reproducing **all twelve
sections** from `findings.json` (headline six numbers with WoW; the value‑change movers; top
three up/down; priority actions each with its `where`; brand paid with the rank‑lost reading;
conquest; cannibalisation; CTR gaps; informational queue; and the two GA4 sections shown as
"not pulled this run"). Attach or link `report.html`. Then post a short message linking the
canvas: headline finding, count of priority items, nothing else.

**Linear** — one issue per priority action, team Marketing, title `[SEO] <rule> — <keyword or
page>`, first description line is the `where`. Do not duplicate open issues; comment instead.

**Do not write to Directus.** Content changes go to Linear for a human.

## Silence, completion line, budget

If there are no movers past threshold, the canvas is two lines: "No commercial movement past
threshold. N informational items queued." Always post the completion line from `counts`: "run
completed, N queries checked, M findings". Stop and report a partial before exceeding **15,000
Ahrefs API units** (`gsc-*` and `gsc-ctr-by-position` are cheap/free; `keywords-explorer-overview`
is ~10 units per keyword line) — do not silently truncate.
