# Gleam.io weekly SEO report — Routine prompt (Ahrefs-backed, v2)

Paste everything below the line into the prompt field of a weekly Routine.

Connectors required — all present in the cloud session:
**Ahrefs, Google Drive, Slack, Linear, Zapier.** There is no native Search Console, Google Ads,
GA4 or Semrush connector: Search Console data comes from Ahrefs, and **Google Ads is reached
through Zapier**. Nothing in this report is entered by hand — every figure is pulled by a tool.

---

You are producing the weekly SEO report for gleam.io. Deliver it as a Slack canvas plus a
direct message to Eddy, and open Linear issues for the priority actions. Be terse in the
session itself; the deliverable is the canvas, not commentary.

## Rule 0 — never report a number you did not pull

If a value was not returned by a tool call in this run, write "not pulled this run". Do not
estimate it, do not carry a previous week's figure forward as current, do not reason toward a
number that seems plausible. If a pull fails, name the failure in the method section and leave
that section empty. An empty section is information; a confident guess is a liability.

Two traps that have already produced wrong output in this project:

- **Never claim what a competitor's ad says** unless you are quoting ad text returned by an
  API. Never allege trademark misuse on inference. A previous draft accused two companies of
  trademark violation with no evidence; the data contradicted it.
- **Never assert Gleam is absent from a SERP without checking.** Gleam ranks #8 for
  "gleam alternative" via /blog/comparisons/. Check before recommending a new page.

## Rule 1 — every recommendation carries a location

Each action item has two parts: what to do, and **where** — an exact URL, a proposed new
slug, or a system such as "Google Ads → Gleam - Brand campaign". No `where`, no ship.

## Rule 2 — three tracks, never mixed in one average

- **Brand** — anything containing "gleam". Scored on position and SERP ownership. `gleam`
  alone is ~10,000 weekly impressions and would swamp any average it sits inside.
- **Commercial** — software, platform, app, tool, picker, generator, maker, websites, plus
  action phrasings (run a / host a / create a). Scored on estimated traffic value.
- **Informational** — ideas, examples, how to, rules, legal. Scored on impressions.

Terms containing "gleam" are brand, not conquest. "rafflecopter alternative" is conquest;
"gleam alternative" is brand defence — different owner, different action.

Exclude as irrelevant intent: software giveaway, software giveaways, free software, giveaway
of the day, steam key, nft giveaway, crypto giveaway.

## Step 1 — Ahrefs, Search Console data

**Use `project_id: 684395`** — "Gleam.io Main", verified, subdomains mode. Confirmed to have
Search Console linked and returning live data at zero API unit cost.

Pull, for the 7 days ending yesterday:

- `gsc-keywords` — queries with clicks, impressions, CTR, position
- `gsc-pages` — pages with the same
- `gsc-ctr-by-position` — the own-data CTR benchmark curve. Use this rather than deriving your
  own; it is built from 100+ keywords per position, where a hand-rolled curve from a small
  sample produces nonsense at the tail.
- `gsc-positions-history` and `gsc-page-history` — for trend context

Note: project 684395 is *subdomains* mode while the raw GSC property is URL-prefix
`https://gleam.io/`. They cover slightly different URL sets. Use Ahrefs consistently; do not
mix the two sources within one report.

## Step 2 — read last week's snapshot from Drive, then diff

Read the most recent files in the Google Drive folder `Gleam SEO snapshots`. Compare this
week's pull against them: position now, position then, change, clicks change, track.

If no prior snapshot exists, say "building history — week 1 of 4" in the movers sections
rather than leaving them blank without explanation.

Report a query only if it clears **both** tests:

| Track | Movement | Materiality |
|---|---|---|
| Brand | any change ≥1 position, or sitting worse than position 3 with no movement | ≥20 impressions |
| Commercial | ≥3 positions, or left top 10, or lost position 1 | ≥40 impressions |
| Informational | ≥5 positions | ≥250 impressions |

Ignore worse than position 20 unless CPC is above A$6.

Rank movers by **estimated value change**: `volume × CTR at position × CPC`, using the Ahrefs
CTR curve from step 1. Position 47→29 is dramatic and worth nothing; a top-3 term slipping two
places on an A$11 CPC matters.

Also flag:

- **Cannibalisation** — any query whose ranking page changed between snapshots.
- **CTR gap** — any query with 250+ impressions whose CTR is more than 40% below the Ahrefs
  benchmark for its position. Verify `gleam app` specifically: it drew ~1,180 impressions at
  1.6% CTR from position 3.4, far below benchmark, and is corroborated by zero paid
  conversions on the same term.

## Step 3 — Ahrefs, volume and CPC

`keywords-explorer-overview` and `site-explorer-organic-keywords` for the keywords that
surfaced in step 2 only, not the whole set. This replaces Semrush entirely — and is an
improvement, since Semrush position data was found to contradict Search Console materially.

Also pull `site-explorer-organic-competitors`, `serp-overview` for the top movers and brand
modifier terms, and `site-audit-issues` filtered to commercial URLs.

## Step 4 — brand paid, pulled from Google Ads via Zapier

No native Google Ads connector, but **Zapier reaches it** — account **9047806202**, AUD. Pull it
with a tool; do not paste anything by hand and do not read a manual file.

Use the Zapier Google Ads actions (call `inspect_zapier_actions` for their exact parameters):

- **Campaign metrics** — `google_ads_create_report`, resource `campaign`, dates `LAST_7_DAYS`,
  account 9047806202. Needs spend, conversions, conversions value (→ ROAS) and, critically,
  `search_rank_lost_impression_share` and `search_budget_lost_impression_share`. If the Create
  Report column set omits the impression-share metrics, fall back to raw GAQL via
  `google_ads_make_api_get_request` / `..._mutating_request` against
  `customers/9047806202/googleAds:search`:

  ```sql
  SELECT campaign.name, metrics.cost_micros, metrics.conversions, metrics.conversions_value,
         metrics.search_rank_lost_impression_share, metrics.search_budget_lost_impression_share
  FROM campaign WHERE segments.date DURING LAST_7_DAYS
  ```
  Cost is micros — divide by 1,000,000. GAQL has no `LAST_90_DAYS` literal; for the 90-day view
  use `segments.date BETWEEN '<90 days ago>' AND '<yesterday>'`.

- **Conquest CPA** — the same query narrowed to the Competitors campaign (`campaign.name`).

Reduce the pull to exactly these six values and hand them to the report as its brand-paid block:
`brand_spend_aud`, `brand_conversions`, `brand_roas`, `brand_rank_lost_is_pct`,
`brand_budget_lost_is_pct`, `conquest_cpa_aud`. **Any value the pull does not return renders
"not pulled this run" — never inferred, never carried forward (Rule 0).** If the Zapier Google
Ads connection is unauthorised (a token error), say so in the method section and leave the six
fields empty; do not fall back to a hand-typed number.

Baselines from 2026-07-28 for sanity-checking: brand spend A$4,700, CPA A$41.69, ROAS 0.92,
rank-lost 45.2%, budget-lost 3.3%, conquest CPA A$244.35. If the pulled figures contradict these
without obvious cause, suspect the pull and flag it rather than reporting it silently.

The rank-lost versus budget-lost distinction is the single most valuable number in this report:
rank-lost means outranked, budget-lost means out of money, and they need opposite responses. Say
so whenever it is present.

*(GA4 — sections 05 and 06.)* There is no GA4 connector today. GA4 is available in Zapier's
catalogue (`Google Analytics 4`) but not yet connected; once it is, organic revenue by landing
page and referral revenue can be pulled the same way. Until then, render 05 and 06 as
"not pulled this run — requires GA4".

## Step 5 — build the report, all 12 sections

Reproduce the structure of `templates/weekly-report.html` **exactly** — all twelve sections,
including the diverging value-change chart in section 02. Do not produce a shortened version;
a previous run emitted an 8-section variant and it was rejected.

The sections are: 01 scorecard · 02 what moved (diverging value chart) · 03 movers with
diagnosis · 04 flags, cannibalisation and CTR gap · 05 revenue · 06 referral revenue ·
07 brand · 08 competition · 09 AI search · 10 where to make changes · 11 informational track ·
12 method and run log.

Sections 05 and 06 have no data source in this configuration. Render them with a clear
"not pulled this run — requires GA4" note rather than omitting them, so the structure stays
stable week to week.

Build the action queue from the rules: on-page for commercial positions 4–8, internal links
for 9–15, consolidate on cannibalisation, metadata rewrite on CTR gap, brand defence for any
brand term worse than position 3, and new-page briefs for commercial terms with no ranking.
Every item carries its `where`.

## Step 6 — snapshot to Drive

Write this run's pulls to Google Drive folder `Gleam SEO snapshots` as
`YYYY-MM-DD-<kind>.json` for kinds `gsc_keywords`, `gsc_pages`, `ctr_curve`, `movers`, and
`brand_paid` (the six figures pulled from Google Ads, for history and week-on-week paid deltas).
Next week's diff depends on this; skip it and every week looks like week one.

## Step 7 — deliver

The report people read is a **Slack channel canvas in `#seo`** carrying the **full twelve
sections** — not a summary. Slack renders canvas markdown (headings, tables, callouts) natively
and privately to the workspace, with no link to break and nothing to download, so the canvas is
the primary artifact. This report contains internal paid spend and strategy, so **never publish
it to a public URL** (no GitHub Pages, no public link).

Build every section into the canvas from the computed data: the headline table; section 02
movers as a ranked table (keyword · was→now · Δ value · a simple text bar like `+████`); the
gained/lost tables with diagnosis; cannibalisation and CTR-gap tables; the brand paid table with
the rank-lost vs budget-lost reading; competition; AI search; the action queue with each item's
`where`; informational; and the method log. Sections 05–06 show
"not pulled this run — requires GA4".

Rules that avoid the failures already seen in testing:

- **Create a NEW channel canvas in `#seo` (channel `C08F23HCDQA`) each run.** Do not reuse or
  link a canvas ID from a previous run, and never create it in a DM — the Slack connector is
  authenticated as Eddy, so an unscoped canvas lands in his personal space (that is where the
  first run's canvas went).
- **Post one short plain-text message in `#seo`** — headline finding, P1/P2 count, Linear IDs.
  Let Slack auto-link any bare URL; **never hand-build a `<url|label>` link, and never put a
  line break or extra text inside a URL** — that is exactly what produced the broken link last
  run.
- Write the rendered `report.html` (from `gleam_seo.render_html`) to the Drive folder
  `Gleam SEO reports` as `SEO-<ISO week>.html` **only as a downloadable archive**, and say in
  the message that it must be downloaded and opened in a browser to render (Drive's inline
  viewer shows source, not the page). Do not present the Drive link as the way to "view" the
  report — the canvas is.

**DM heads-up to Eddy** — three lines: the single most important finding, the P1/P2 count, and
"full report is the canvas in #seo". Not the report itself.

**Linear** — one issue per priority-1 and priority-2 action, team Marketing, title
`[SEO] <rule> — <keyword or page>`, the `where` as the first line of the description.
De-duplicate on title: comment on an existing open issue rather than creating a second.

**Do not write to Directus.** Content changes go to Linear for a human.

## Silence is a valid result

If nothing clears threshold, the DM is two lines: "No commercial movement past threshold.
N informational items queued." Do not pad it. A report that always finds twelve things trains
the reader to stop opening it.

Always send the DM, even on a quiet week, and always end with "run completed, N queries
checked, M findings". A Monday with no message is ambiguous between "nothing moved" and "the
run failed".
