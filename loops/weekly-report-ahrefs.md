# Gleam.io weekly SEO report — Routine prompt (Ahrefs-backed, v2)

Paste everything below the line into the prompt field of a weekly Routine.

Connectors required — all present in the cloud session:
**Ahrefs, Google Drive, Slack, Linear, Directus, Zapier.** Search Console data comes from Ahrefs.
This is an organic report: there is **no paid-ads and no GA4 data** in it — GA4 is not connected
and is not reachable through Ahrefs, so never present GA4 revenue or imply it is wired up.
Directus is used to check whether informational content already exists (§11). Nothing in this
report is entered by hand — every figure is pulled by a tool.

---

You are producing the weekly SEO report for gleam.io. **This report is ORGANIC COMMERCIAL
only** — organic search performance for Gleam's commercial keyword set. It is NOT a paid-ads
report and NOT a GA4 report: do not present Google Ads spend/ROAS/impression-share as the
report's subject, and do not imply GA4 is connected (it is not, and GA4 is not wired through
Ahrefs). Deliver the report as a rendered HTML file in a **direct message to Eddy**
(`D0BMAL0MZMW`), and open Linear issues for the priority actions. Be terse in the session
itself; the deliverable is the HTML file, not commentary.

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

All three tracks are **organic**. There is no paid track in this report.

- **Brand** — anything containing "gleam". Scored on organic position and SERP ownership. `gleam`
  alone is ~10,000 weekly impressions and would swamp any average it sits inside.
- **Commercial** — software, platform, app, tool, picker, generator, maker, websites, plus
  action phrasings (run a / host a / create a). Scored on estimated organic traffic value.
- **Informational** — ideas, examples, how to, rules, legal. Scored on impressions.

Terms containing "gleam" are brand, not conquest. "rafflecopter alternative" is conquest;
"gleam alternative" is brand defence — different owner, different action.

Exclude as irrelevant intent: software giveaway, software giveaways, free software, giveaway
of the day, steam key, nft giveaway, crypto giveaway.

## Rule 3 — every section renders populated; never a bare table

No section may ship as a table with only a header and no body. Each section has a primary source
and an **Ahrefs fallback**; pull the fallback whenever the primary is unavailable. Only if a
genuine tool call returns zero rows may a section replace its table with a one-line callout naming
the exact tool called and why it came back empty — a blank table is a defect, an explained gap is
acceptable. Per section:

- **05 Organic value** (NOT "revenue") — Ahrefs top pages by organic traffic value
  (`gsc-pages` / `site-explorer-top-pages`, using `traffic_value`). Label it *organic traffic
  value*, an Ahrefs estimate — never call it booked revenue, and never imply GA4 is connected.
  Column headers are Value/wk, Organic visits, Value/visit.
- **06 Referring domains** (NOT "referral revenue") — the Ahrefs backlink profile:
  `site-explorer-referring-domains` (domain, DR, dofollow/links_to_target, filtered `is_spam=false`)
  plus `site-explorer-anchors` for anchor text. There is no GA4 connector, so session/revenue
  columns read "—"; the domains, DR, links and anchors are real. Do not frame this as revenue.
- **07 Brand defence (ORGANIC)** — no paid table, ever. Brand SERP: `serp-overview` for
  "gleam alternatives" and "gleam alternative" (organic rows → domain, position, DR, page type;
  gleam.io's own row flagged). KPIs are organic: brand queries owned at #1, the brand-head CTR gap
  (§04), and gleam.io's own rank on "gleam alternatives". The finding is the organic alternatives
  SERP owned by third-party comparison pages — recommend an owned comparison page + homepage
  authority, never a bid change.
- **08 Competition — Share of Voice must include gleam.io.** Compute SoV as each domain's share
  of estimated organic traffic across the **direct contest/giveaway platform set** (gleam.io +
  sweepwidget, viralsweep, woobox, easypromosapp, rafflepress), traffic from
  `site-explorer-organic-competitors` + `site-explorer-metrics` (org_traffic). gleam.io is the
  self row (typically the leader, ~55%). Note that giveaway-listing aggregators (app-sorteos,
  thefreebieguy) have larger raw traffic but a directory audience — keep them out of the platform
  SoV and in the competitor grid. **Displacement** from the competitor grid (any tracked keyword
  where a competitor outranks gleam.io — e.g. contest software, contest platform).
- **09 AI search** — check `management-brand-radar-reports` first. If a Brand Radar report exists,
  read `brand-radar-*` for AI-answer mentions / citation share / SoV. If none exists (currently 0),
  the section renders "Not configured" **and states what to enable**: (a) a Brand Radar report for
  the `gleam` entity with the commercial prompts, or (b) the commercial keyword set added to a Rank
  Tracker project so each keyword reports the `ai_overview` / `ai_overview_found` SERP feature.
  Until then the KPIs are the AEO-readiness proxy (branded-entity + informational #1s), labelled
  as such. Never imply AI Overview presence is being measured when it is not.

Populate every section from a real pull, label the source, and never leave a header with no rows.

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

## Step 4 — organic brand defence (NO paid ads)

This report does not include Google Ads spend, ROAS or impression share. Do not pull, and do not
present, any paid-search figures — the previous paid-brand block was removed because it mixes
objectives (the user was explicit: this is organic commercial, not paid ads).

Pull the **organic** brand-defence picture instead:

- `serp-overview` for "gleam alternatives" and "gleam alternative" — organic rows only: domain,
  position, DR, page type, and gleam.io's own row flagged. The finding is which third-party
  comparison pages (rafflepress, bloggingwizard, Reddit, Capterra…) outrank Gleam's homepage on
  its own alternatives SERP.
- `gsc-keywords` filtered to brand terms — the brand-head CTR gap (e.g. `gleam` ~10.5% vs ~33%
  benchmark) and brand-query cannibalisation (urls_count) — both already in §04.

The recommendation is always organic: an owned gleam-alternatives comparison page, homepage
authority signals, brand-query consolidation. Never a bid change.

*(Sections 05 and 06.)* There is no GA4 connector, and GA4 is **not** reachable through Ahrefs.
Render 05 as organic traffic value (Ahrefs, §Rule 3) and 06 as the referring-domains backlink
profile. Never state or imply that GA4 is connected or that these are booked revenue figures.

## Step 5 — build the report, all 12 sections

Reproduce the structure of `templates/weekly-report.html` **exactly** — all twelve sections,
including the diverging value-change chart in section 02. Do not produce a shortened version;
a previous run emitted an 8-section variant and it was rejected.

The sections are: 01 scorecard · 02 what moved (diverging value chart) · 03 movers with
diagnosis · 04 flags, cannibalisation and CTR gap · 05 organic value · 06 referring domains ·
07 brand defence (organic) · 08 competition (share of voice incl. gleam.io) · 08 competitor grid ·
09 AI search · 10 where to make changes (Linear-deduped) · 11 informational track (diagnose
existing content) · 12 method and run log. All organic — no paid-ads section.

**Section 08 competitor grid** is a Semrush-style Position-Tracking add-on kept **in addition to**
the existing sections — it never replaces 02–04. Fixed competitor set
`app-sorteos.com, easypromosapp.com, woobox.com, viralsweep.com` plus gleam.io. Build two fields:
- **`compvis`** — `site-explorer-metrics` (mode subdomains, country us) per domain →
  `{dom, kw:org_keywords, top3:org_keywords_1_3, traf:org_traffic, val:org_cost÷100, self}`.
- **`grid`** — a fixed tracked keyword list of commercial/category terms (giveaway, giveaways,
  sweepstakes websites, giveaway platform, contest platform, contest software, social media
  contest, giveaway creator, run a giveaway, online giveaway…). For each of the five domains call
  `site-explorer-organic-keywords` with a `where` OR-filter on those keywords and
  `select keyword,best_position,volume`; assemble
  `{domains:[…5…], rows:[{kw, vol, pos:{"<domain>":best_position}}]}`. A domain absent from a row
  = not ranking (top 100). All positions are Ahrefs crawl, comparable across columns.

**Section 03 also carries a `clusters` block** below the Gained/Lost winners & losers. Group the
**commercial keywords only** into these SEVEN fixed pillars, in this display order:

1. **gleam (brand)** — any term containing "gleam" (except comparison terms → pillar 6).
2. **giveaways** — giveaway / give away / giveaways / raffle, prize-led terms (pc, laptop, GPU,
   console…), and giveaway platform / creator / manager.
3. **competitions** — "competition(s)" terms.
4. **contests** — "contest(s)" terms (contest platform, contest software…).
5. **sweepstakes** — "sweepstake(s)" terms.
6. **gleam vs (competitors)** — comparison / conquest: "X alternative(s)", "gleam vs", "vs gleam".
7. **social** — channel-tied terms (social media, instagram, tiktok, twitter, twitch, youtube,
   facebook).

Assign each keyword to the FIRST pillar it matches in this **priority order**: competitors →
brand → social → sweepstakes → contests → competitions → giveaways. Exclude informational terms
(how-to, ideas, rules, "what is", "is X legit") — those are §11. Build
`clusters: [{name, up, down, flat, net, kws:[{kw, was, now, vol, url}]}]`, `net = Σ(was − now)`
(+ = net improvement). Keep all seven pillars every week, in order. A pillar with no ranking
commercial keyword this run renders a one-line note ("no ranking terms this run") rather than an
empty table (Rule 3) — an empty pillar is itself a finding: a coverage gap worth a queue item.

Seed the **gleam vs (competitors)** and **competitions** pillars from the project's Google Ads
target keyword database in Drive — `Competitors-Keywords_list_*.csv` and the keyword-export whose
campaigns map to the pillars (`Core KW | Competitor | Global`, `Core KW | Competitions | Global`).
For each targeted term, show gleam.io's organic position from Ahrefs (`site-explorer-organic-keywords`,
where-filter, no `date_compared` so keyword text populates), or `—` when we target it in Ads but do
not rank organically. That `—` is the point: a paid-only term with no organic coverage is the gap.

Sections 05 and 06 are organic (traffic value; referring domains) per Rule 3 — never framed as
revenue and never implying GA4 is connected.

**Section 11 informational — check Directus for existing content before proposing anything new.**
For each informational term that surfaced (how-to, guide, "what is", rules), query Directus
(`Blog_Post` and `Article` where `type` in guides/modern_blog; the slug field on `Article` is
`slug`, on `Blog_Post` it is `url` — `slug` does NOT exist on `Blog_Post`) to see whether a page
already exists. If it does, the recommendation is **not** "write a guide" — it is a diagnosis of
whether that page's keyword is being cannibalised and how to fix it: pull `gsc-keywords` for the
term and check `top_url`. If Google shows a different URL (e.g. the product page /app/competitions
or the homepage) instead of the guide, that is the finding — recommend consolidating the
informational intent onto the existing guide (internal link with exact anchor, canonical intent,
keep the product page on the commercial term). Worked example: the "How to Create a Social Media
Contest" guide (Directus Article 4904, /guides/how-to-create-a-social-media-contest) exists and is
published, but "how to create a social media contest" is won by /app/competitions (#8.1) — so the
action is de-cannibalisation, not a new guide.

**Section 10 action queue — check Linear first, then build from the rules.** Before recommending
anything, list Linear issues (team **Marketing**, label **SEO**) and de-duplicate against them so
the queue never re-recommends work already implemented, queued, or explicitly declined the prior
week:
- If an open issue already covers the action (matched on the page/keyword, not just title), show
  it as **tracked** (e.g. "already queued — MAR-####, assigned <owner>") and do not raise a
  duplicate.
- If the action was raised last week and **Cancelled** (e.g. MAR-1509 homepage metadata), show it
  as **declined — not re-raised**; only re-open if the underlying decision changed.
- Only genuinely new actions become fresh Linear issues.
Then build the rest from the rules: on-page for commercial positions 4–8, internal links for 9–15,
consolidate on cannibalisation, metadata rewrite on CTR gap, brand defence (organic) for any brand
term worse than position 3, de-cannibalisation for informational terms whose existing page is
outranked by a product/home page, and new-page briefs only for commercial terms with no ranking
AND no existing Directus page. Every item carries its `where`.

## Step 6 — snapshot to Drive

Write this run's pulls to Google Drive folder `Gleam SEO snapshots` as
`YYYY-MM-DD-<kind>.json` for kinds `gsc_keywords`, `gsc_pages`, `ctr_curve`, `movers`, and
`brand_paid` (the six figures pulled from Google Ads, for history and week-on-week paid deltas).
Next week's diff depends on this; skip it and every week looks like week one.

## Step 7 — deliver

The report people open is the **rendered `report.html`** (from `gleam_seo.render_html` — the
exact twelve-section template with the diverging chart), delivered as a **native HTML file in a
direct message to Eddy** (`D0BMAL0MZMW`). When clicked, Slack opens the attachment and the
browser renders the full styled page. **The HTML attachment is the report** — not a canvas, not
a link. **Never publish it to a public URL** (no GitHub Pages, no public link); a native Slack
file stays inside the workspace.

The loop uploads the file itself using Slack's **external upload flow** (the modern replacement
for the deprecated `files.upload`). This was verified working end to end; do NOT use the dead
ends below, all of which were tested and fail:

- Slack MCP connector — **no file-upload tool**.
- Zapier `channel_message` `file` field with inline HTML → Slack stores a **`.txt` binary**
  (`application/octet-stream`), not an `.html`.
- Slack `files.upload` → **`method_deprecated`** on this workspace.
- Private Drive URL handed to Zapier's `file` field → **not fetchable** (no auth).

**Working upload — three steps.** Deliver to Eddy's DM channel `D0BMAL0MZMW`.

1. **Get an upload URL** (Zapier `_zap_raw_request`, `SlackCLIAPI`, which injects the Slack
   token): `POST https://slack.com/api/files.getUploadURLExternal` with querystring
   `filename=GleamSEO-<ISO week>.html` and `length=<exact byte size of report.html>` (use
   `wc -c`). It returns `upload_url` and `file_id`.

2. **Push the bytes** with Bash `curl` — the file is read straight from disk, so size is a
   non-issue: `curl -sS -X POST --data-binary @report.html "<upload_url>"`. (`_zap_raw_request`
   is locked to the `slack.com` domain and CANNOT post to the `files.slack.com` upload URL —
   that is why the byte push must go through `curl`, not Zapier.)

3. **Finalize and share to the DM** (Zapier `_zap_raw_request`):
   `POST https://slack.com/api/files.completeUploadExternal` with querystring
   `files=[{"id":"<file_id>","title":"Gleam SEO — Weekly Report <ISO week>"}]`,
   `channel_id=D0BMAL0MZMW`, and `initial_comment=<the summary: biggest finding · P1/P2 count ·
   Linear MAR-#### ids, distinguishing newly-raised from tracked/declined>`. Confirm the
   response is `ok:true`. Slack renders the `.html` on click.

4. **Archive to Drive.** Also write the same `GleamSEO-<ISO week>.html` to the Drive folder
   `Gleam SEO reports` (`mcp__Google_Drive__create_file`, `contentMimeType: text/html`,
   `disableConversionToGoogleType: true`) as the durable archive and for next week's diff.

The `initial_comment` on the file is the heads-up — the single most important finding and the
P1 count. No separate message.

**Linear** — one issue per priority-1 and priority-2 action, **team Marketing**. A task that
only states a problem is a defect; every issue must be actionable on its own. Each issue MUST
set:

- **Title**: `[SEO] <rule> — <keyword or page>`.
- **Assignee**: `eduardo@gleam.io` (the report owner) — never leave unassigned.
- **Label**: `SEO` (add `CRO` as well for conversion-path items). Never leave label-less.
- **Priority**: map the tier — **P1 → High (2)**, **P2 → Medium (3)**. Never leave at None.
- **Description**, in this order, written so someone can act without opening the report:
  1. **Recommendation — do this**: the concrete change(s) — what to write / build / redirect /
     rebid — specific enough to start work. NOT a restatement of the finding.
  2. **Where**: the exact URL, slug, or system (Rule 1).
  3. **Why (evidence)**: the metric(s) that triggered it, with numbers and source
     (Ahrefs / GSC / Google Ads).
  4. **Expected impact**: rough upside (clicks or value) where derivable.
  5. **Acceptance**: how we'll know it's done.

De-duplicate against the Linear check from §10 (team Marketing, label SEO): match on the
page/keyword the action targets, not just the title string. If an open issue already covers it,
comment on it instead of creating a second and show it as *tracked* in the queue; if it was
Cancelled last week, show it as *declined* and do not recreate it. Only genuinely new actions
become fresh issues. See MAR-1509 for the required description shape.

**Do not write to Directus.** Content changes go to Linear for a human.

## Silence is a valid result

If nothing clears threshold, the DM is two lines: "No commercial movement past threshold.
N informational items queued." Do not pad it. A report that always finds twelve things trains
the reader to stop opening it.

Always send the DM, even on a quiet week, and always end with "run completed, N queries
checked, M findings". A Monday with no message is ambiguous between "nothing moved" and "the
run failed".
