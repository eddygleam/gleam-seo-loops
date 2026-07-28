# Gleam.io weekly SEO report — Routine prompt (v1, no repository required)

> **Status: superseded.** This is the original self-contained version, kept for
> reference and for running the report when the repo cannot be attached. When
> the repo *is* attached, use [`weekly-report.md`](./weekly-report.md) instead —
> it replaces the agent-reasoned arithmetic in Step 2 (and the paid/CTR maths)
> with the tested, deterministic code in `gleam_seo/`.

Paste everything below the line into the prompt field of a weekly Routine at
claude.ai/code/routines. It is deliberately self-contained: no repo, no Python, snapshots in
Google Drive. Once the git repo exists, attach it and switch to `loops/weekly-report.md`,
which uses the tested diffing scripts instead of agent reasoning.

Connectors this Routine needs: **Google Search Console, Google Ads, GA4, Semrush, Ahrefs,
Google Drive, Slack, Linear.**

---

You are producing the weekly SEO report for gleam.io. Work through every step. Be terse in
chat; the deliverable is the Slack canvas and the Linear issues, not commentary.

## Rule 0 — never report a number you did not pull

If a value was not returned by a tool call in this run, write "not pulled this run". Do not
estimate it, do not carry last week's figure forward as current, do not reason your way to a
number that seems about right. If a pull fails, say which one failed and leave that section
empty. An empty section is information; a confident guess is a liability.

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

- **Brand** — anything containing "gleam". Scored on SERP position and rank-lost impression
  share. `gleam` alone is ~10,000 weekly impressions and would swamp any average it sits in.
- **Commercial** — tool, software, platform, app, picker, generator, maker, websites, plus
  action phrasings (run a / host a / create a). Scored on estimated traffic value.
- **Informational** — anything with ideas, examples, how to, rules, legal. Scored on
  impressions. These return roughly a third the paid ROAS of tool terms, so they are
  candidates for moving out of paid into organic, never commercial wins.

Terms containing "gleam" are brand, not conquest. "rafflecopter alternative" is conquest;
"gleam alternative" is brand defence.

Exclude entirely, as irrelevant intent: software giveaway, software giveaways, free
software, giveaway of the day, steam key, nft giveaway, crypto giveaway.

## Step 1 — Search Console

Property is **`https://gleam.io/`** — a URL-prefix property. `sc-domain:gleam.io` returns
403. Use `gsc:get_advanced_search_analytics`.

Pull four sets:

1. Queries, this week (the 7 days ending yesterday), `row_limit` 250, sorted by clicks.
2. Queries, the 7 days before that, `row_limit` 250.
3. Pages, this week, `dimensions="page"`, `row_limit` 100.
4. Pages, prior week, `dimensions="page"`, `row_limit` 100.

## Step 2 — derive movement yourself

Match queries across the two weeks and compute, for each: position this week, position last
week, the change, clicks change, and whether it is brand, commercial or informational.

Report a query only if it clears **both** a movement and a materiality test:

| Track | Movement trigger | Materiality |
|---|---|---|
| Brand | any change ≥1 position, **or** sitting worse than position 3 with no movement | ≥20 impressions |
| Commercial | ≥3 positions, or left the top 10, or lost position 1 | ≥40 impressions |
| Informational | ≥5 positions | ≥250 impressions |

Ignore anything worse than position 20 unless its CPC is above A$6.

Rank the movers by **estimated value change**, not by position change: `volume × CTR at
position × CPC`. Position 47→29 is dramatic and worth nothing; a top-3 term slipping two
places on an A$11 CPC matters. Derive the CTR-by-position curve from this week's own query
data — do not use a generic table.

Also flag:

- **Cannibalisation** — any query whose ranking page differs between the two weeks. Compare
  the page dimension.
- **CTR gap** — any query with 250+ impressions whose CTR is more than 40% below your own
  average CTR at that position. Known example to verify: "gleam app" drew ~1,180 impressions
  at 1.6% CTR from position 3.4, which is severely below benchmark.

## Step 3 — Semrush, for volume and CPC only

Call `semrush_domain_organic_keywords` for gleam.io, and `semrush_keyword_organic_results`
(10 units per line) for the top three movers plus any brand-modifier term.

**Semrush positions and GSC positions disagree materially** — Semrush reported "giveaway
platform" at #1 whilst GSC shows average position 9.1. GSC is own, impression-weighted data
and wins every conflict. Take volume and CPC from Semrush; take position from GSC.

`semrush_keyword_ads_history` costs **100 units per line**. Use it only for brand-modifier
terms (gleam alternative, gleam pricing, gleam reviews), and only in the first week of the
month.

## Step 4 — Brand, from Google Ads

Account **9047806202**, AUD. GAQL has **no `LAST_90_DAYS` literal** — use
`segments.date BETWEEN '<90 days ago>' AND '<yesterday>'`.

1. `keyword_view` where `ad_group_criterion.keyword.text LIKE '%gleam%'`. Costs are micros —
   divide by 1,000,000. Normalise keyword case and fold `gleam.io` to `gleam io` before
   aggregating, or the same term splits across rows.
2. `campaign` resource for `search_rank_lost_impression_share` and
   `search_budget_lost_impression_share`. **These exist only on the campaign resource, not
   on keyword_view**, and the distinction is the whole point: rank-lost means outranked,
   budget-lost means out of money, and they need opposite responses.

Baselines from 2026-07-28 to compare against. If the new pull contradicts these without an
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

Before writing, read the most recent existing snapshots and use them as the comparison
baseline in step 2 in preference to a second live GSC pull.

## Step 7 — output

**Slack** — create a canvas in `#seo` titled `SEO — <ISO week>`, containing: the six
headline numbers with week-on-week change; top three movers up and down with their value
change; the priority actions each with its `where`; and one line on brand rank-lost share.
Then post a short message linking the canvas: headline finding, count of priority items,
nothing else.

**Linear** — one issue per priority action, team Marketing. Title
`[SEO] <rule> — <keyword or page>`. First line of the description is the `where`. Do not
create duplicates; if an issue with that title is open, comment on it instead.

**Do not write to Directus.** Content changes go to Linear for a human.

## Silence is a valid result

If nothing clears threshold, the canvas is two lines: "No commercial movement past
threshold. N informational items queued." Do not pad it. A report that always finds twelve
things trains the reader to stop reading it.

Always post the completion line, even on a quiet week: "run completed, N queries checked, M
findings". A Monday with no Slack message is ambiguous between "nothing moved" and "the auth
token expired".

## Budget

Stop and report a partial if this run would exceed 15,000 Semrush API units. Do not silently
truncate.
