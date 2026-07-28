"""Tested diffing logic for the Gleam.io weekly SEO report.

This package replaces the fragile, agent-reasoned parts of the weekly report
(query matching across weeks, movement/materiality filtering, value-change
ranking, CTR-by-position curve derivation, cannibalisation, CTR-gap detection
and Google Ads normalisation) with deterministic, unit-tested code.

The Routine (see ``loops/weekly-report.md``) is responsible for pulling data
from the connectors and for writing the Slack canvas and Linear issues. It is
NOT responsible for arithmetic: everything numeric lives here so it can be
tested and cannot silently drift.

Design rules carried over verbatim from the Routine prompt:

* Rule 0 — never invent a number. Functions here return ``None`` (or omit a
  field) when an input is missing; they never fabricate a value.
* Rule 2 — three tracks (brand / commercial / informational), never mixed in
  one average. See :mod:`gleam_seo.classify`.
"""

from gleam_seo.classify import Track, classify, is_excluded, normalize
from gleam_seo.ctr import ctr_at, ctr_curve
from gleam_seo.dates import gaql_date_between, week_ranges
from gleam_seo.diagnostics import CtrGap, Cannibalisation, ctr_gaps, cannibalisation
from gleam_seo.movement import Mover, QueryRow, rank_movers
from gleam_seo.paid import (
    PaidAggregate,
    aggregate_keywords,
    fold_keyword,
    lost_share_reading,
    micros_to_units,
)
from gleam_seo.report import NOT_PULLED, MANUAL_FIELDS, build_report
from gleam_seo.render_html import render

__all__ = [
    "Track",
    "classify",
    "is_excluded",
    "normalize",
    "ctr_at",
    "ctr_curve",
    "gaql_date_between",
    "week_ranges",
    "CtrGap",
    "Cannibalisation",
    "ctr_gaps",
    "cannibalisation",
    "Mover",
    "QueryRow",
    "rank_movers",
    "PaidAggregate",
    "aggregate_keywords",
    "fold_keyword",
    "lost_share_reading",
    "micros_to_units",
    "NOT_PULLED",
    "MANUAL_FIELDS",
    "build_report",
    "render",
]
