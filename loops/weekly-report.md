# Gleam.io weekly SEO report — Routine prompt (repo version)

Paste this into the weekly Routine at claude.ai/code/routines **with this repository
attached**. It is the same report as [`weekly-report-v1-standalone.md`](./weekly-report-v1-standalone.md),
except that all the arithmetic — matching queries across weeks, movement/materiality
filtering, value-change ranking, the CTR-by-position curve, cannibalisation, CTR-gap
detection and Google Ads normalisation — is done by the tested code in `gleam_seo/`, not by
you. You still pull the data and write the Slack canvas and Linear issues; you do **not** do
maths in your head.

Connectors this Routine needs: **Google Search Console, Google Ads, GA4, Semrush, Ahrefs,
Google Drive, Slack, Linear.**

Why the split: agent-reasoned arithmetic has already produced wrong output (a competitor
ad-copy claim that was never in the returned text; a "Gleam is absent from this SERP"
finding that was false). The rules below that begin "run the script" are not negotiable —
if you find yourself computing a position delta or a value change by hand, stop and call the
driver instead.

---

You are producing the weekly SEO report for gleam.io. Work through every step. Be terse in
chat; the deliverable is the Slack canvas and the Linear issues, not commentary.

## Rule 0 — never report a number you did not pull

If a value was not returned by a tool call in this run, write "not pulled this run". Do not
estimate it, do not carry last week's figure forward as current, do not reason your way to a
number that seems about right. The driver already follows this rule: it emits
`"not pulled this run"` for any section whose input you did not supply, and leaves
value fields `null` when volume or CPC is missing. Do not fill those in.

Two specific traps, both of which have already produced wrong output:

- **Claims about a competitor's ad copy** must quote the ad text returned by the API. Never
  infer wording, and never allege trademark misuse unless the mark appears in the returned
  ad text.
- **Never assert Gleam is absent from a SERP without checking.** Gleam ranks #8 for
  "gleam alternative" via /blog/comparisons/. Check before recommending a new page.

## Rule 1 — every recommendation carries a location

Each action item is two parts: what to do, and **where** — an exact URL, a proposed new
slug, or a system such as "Google Ads → Gleam - Brand campaign". An item without a `where`
does not ship.

## Rule 2 — three tracks, never mixed in one average

Classification is done for you by `gleam_seo.classify.classify()`; the driver applies it.
The rules it encodes (for your reference when explaining a finding):

- **Brand** — anything containing "gleam". `gleam` alone is ~10,000 weekly impressions and
  would swamp any average it sits in.
- **Commercial** — tool, software, platform, app, picker, generator, maker, websites,
  alternative/competitor (conquest), plus action phrasings (run a / host a / create a).
- **Informational** — ideas, examples, how to, rules, legal.

Terms containing "gleam" are brand, not conquest. "rafflecopter alternative" is conquest;
"gleam alternative" is brand defence. Excluded entirely as irrelevant intent: software
giveaway(s), free software, giveaway of the day, steam key, nft giveaway, crypto giveaway.

## Step 1 — Search Console

Property is **`https://gleam.io/`** — a URL-prefix property. `sc-domain:gleam.io` returns
403. Use `gsc:get_advanced_search_analytics`. Use `gleam_seo.dates.week_ranges(today)` for
the exact date bounds ("this week" is the 7 days ending yesterday).

Pull:

1. Queries, this week, `row_limit` 250, sorted by clicks.
2. Queries, prior week, `row_limit` 250.
3. Pages, this week, `dimensions="page"`, `row_limit` 100.
4. Pages, prior week, `dimensions="page"`, `row_limit` 100.
5. *(optional, for cannibalisation)* Queries+pages, both weeks,
   `dimensions=["query","page"]`, `row_limit` 250. Without this the driver reports
   cannibalisation as "not pulled this run" — it cannot be inferred from query-only data.

## Step 2 — run the diffing script (do not compute movement yourself)

Assemble the pulls into one snapshot JSON and hand it to the driver:

```bash
python -m gleam_seo.report --input snapshot.json --output findings.json
```

Input shape (all sections optional except `gsc_keywords`):

```json
{
  "today": "2026-07-28",
  "gsc_keywords":    {"this_week": [{"query","clicks","impressions","position","ctr?"}], "prior_week": [...]},
  "gsc_query_pages": {"this_week": [{"query","page","clicks","impressions"}], "prior_week": [...]},
  "semrush":         {"<normalised query>": {"volume": 5000, "cpc": 11.0}},
  "paid":            {"keyword_view": [{"keyword","cost_micros","clicks","impressions","conversions"}],
                      "rank_lost": 0.452, "budget_lost": 0.033}
}
```

`findings.json` gives you all twelve report sections: `headline` (week-on-week clicks /
impressions / avg position / organic revenue / brand spend / ROAS), the derived `ctr_curve`,
the `value_chart` data, ranked `movers` / `movers_up` / `movers_down` (each with track,
position change, value change and the human-readable `reasons` it cleared threshold),
`priority_actions` (each already carrying a `where`), `brand_paid` with its
`lost_share_reading`, `conquest`, `cannibalisation`, `ctr_gaps`, `informational`, the two GA4
revenue sections, and `counts`. The driver already applies every threshold in the table below,
ranks by estimated value change (`volume × CTR at position × CPC`, CTR curve derived from this
week's own data), and drops excluded intent — so read the movers straight out; do not
re-filter or re-rank.

Then render the self-contained HTML report (all twelve sections + the diverging value chart):

```bash
python -m gleam_seo.render_html --findings findings.json --output report.html
```

For reference, the thresholds it enforces (`gleam_seo/thresholds.py`):

| Track | Movement trigger | Materiality |
|---|---|---|
| Brand | any change ≥1 position, **or** worse than position 3 with no movement | ≥20 impressions |
| Commercial | ≥3 positions, or left the top 10, or lost position 1 | ≥40 impressions |
| Informational | ≥5 positions | ≥250 impressions |

Anything worse than position 20 is ignored unless its CPC is above A$6.

## Step 3 — Semrush, for volume and CPC only

Call `semrush_domain_organic_keywords` for gleam.io, and `semrush_keyword_organic_results`
(10 units per line) for the top three movers plus any brand-modifier term. Feed the
volume and CPC into the `semrush` block of the snapshot (keyed by query) **before** running
the driver, so the value-change ranking is populated.

**Semrush positions and GSC positions disagree materially** — Semrush reported "giveaway
platform" at #1 whilst GSC shows average position 9.1. GSC is own, impression-weighted data
and wins every conflict. Take volume and CPC from Semrush; take position from GSC. (The
driver only ever reads volume and CPC from the `semrush` block — positions always come from
the GSC rows.)

`semrush_keyword_ads_history` costs **100 units per line**. Use it only for brand-modifier
terms (gleam alternative, gleam pricing, gleam reviews), and only in the first week of the
month.

## Step 4 — Brand, from Google Ads

Account **9047806202**, AUD. GAQL has **no `LAST_90_DAYS` literal** — build the clause with
`gleam_seo.dates.gaql_date_between(today)`.

1. `keyword_view` where `ad_group_criterion.keyword.text LIKE '%gleam%'`. Put the raw rows
   (cost in micros, keyword text untouched) into `paid.keyword_view`; the driver folds case,
   folds `gleam.io` → `gleam io`, aggregates, and divides micros out. Do not pre-aggregate.
2. `campaign` resource for `search_rank_lost_impression_share` and
   `search_budget_lost_impression_share` — these exist **only** on the campaign resource.
   Put them in `paid.rank_lost` / `paid.budget_lost`; the driver's `lost_share_reading`
   states which dominates and therefore whether the fix is bids/quality (outranked) or
   budget (out of money).

Baselines from 2026-07-28 to sanity-check against. If a pull contradicts these without an
obvious cause, suspect the pull before believing the finding:

- Brand: A$4,700 spend, CPA A$41.69, ROAS 0.92
- Competitors campaign (conquest): CPA A$244.35, ROAS 0.50 — 5.9× worse than brand
- Brand rank-lost impression share 45.2%, budget-lost only 3.3%
- "gleam app": A$185.69 across 43 clicks, zero conversions, 60% impression share

## Step 5 — GA4 revenue

Property ID is not yet recorded. Call `ga4-mcp-server:get_account_summaries` to find the
gleam.io property, then report it in the output so it can be pinned into this prompt.

- Organic revenue by landing page: dimensions `landingPagePlusQueryString`, metrics
  `sessions` and `purchaseRevenue`, filtered to `sessionDefaultChannelGroup` = Organic
  Search. Join each page to its highest-click GSC query from step 1.
- Referral revenue: dimension `sessionSourceMedium`, filtered to medium = referral. For the
  domains that earned money, pull Ahrefs `site-explorer-anchors` and report the dominant
  anchor by link count.

GA4 gives **no keyword** for organic sessions, so the page-to-query join is indicative, not
measured. Revenue per session is sound. Label it that way. Referral revenue cannot be split
below domain level.

## Step 6 — snapshot to Drive

Write this run's raw pulls to Google Drive as JSON, in a folder `Gleam SEO snapshots`, named
`YYYY-MM-DD-<kind>.json` for kinds: `gsc_keywords`, `gsc_pages`, `brand_paid`,
`ga4_revenue`. Next week's run reads these to compute deltas, so this step is not optional —
without it there is no history and every week looks like week one.

Before writing, read the most recent existing snapshots and use them as the `prior_week`
input to the driver in preference to a second live GSC pull.

## Step 7 — output

**Slack** — create a canvas in `#seo` titled `SEO — <ISO week>`, containing: the six
headline numbers with week-on-week change (from `gsc_totals` plus GA4 revenue and brand
spend/ROAS); top three movers up and down with their value change (straight from `movers`);
the priority actions each with its `where`; and one line on brand rank-lost share (the
driver's `lost_share_reading`). Then post a short message linking the canvas: headline
finding, count of priority items, nothing else.

**Linear** — one issue per priority action, team Marketing. Title
`[SEO] <rule> — <keyword or page>`. First line of the description is the `where`. Do not
create duplicates; if an issue with that title is open, comment on it instead.

**Do not write to Directus.** Content changes go to Linear for a human.

## Silence is a valid result

If `movers` is empty, the canvas is two lines: "No commercial movement past threshold. N
informational items queued." Do not pad it.

Always post the completion line, even on a quiet week, from `counts`: "run completed, N
queries checked, M findings". A Monday with no Slack message is ambiguous between "nothing
moved" and "the auth token expired".

## Budget

Stop and report a partial if this run would exceed 15,000 Semrush API units. Do not silently
truncate.
