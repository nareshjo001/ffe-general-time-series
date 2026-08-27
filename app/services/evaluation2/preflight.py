"""Phase F.3: backend-owned Phase 2 preflight rules.

IMPORTANT - what this module is NOT:
    This module is NOT Steven's authoritative HC1-HC4 validator. The Phase
    F.2 audit confirmed no bundled, importable HC1-HC4 enforcer exists
    anywhere in the delivered handout (the referenced tool,
    `eval/query_recommendation/framework/validate_spec.py`, was never
    shipped). Everything in this module is a backend-owned preflight rule
    derived from the supplied Phase 2 docs (`04_SPEC_FORMAT.md` etc.) and
    explicit product/mentor policy - not a claim about querylib's own
    behavior, and not a substitute for a real validator if one is ever
    delivered.

    This module does NOT modify `querylib.spec.validate()` and does NOT
    duplicate its structural validation. It runs strictly after
    `handout_adapter.load_spec()` has already produced a structurally valid
    spec, and only adds two additional backend-policy checks:

        1. HC1 - grouping attributes must not be `dataset.id` or
           `dataset.time` (see `validate_backend_hc1`).
        2. HC2 - the spec's static, dataset-free instance count must be
           strictly less than 200 (see `validate_hc2_instance_count`).

    HC3 (Setting-C O(n^2) cardinality restriction) and HC4 (min_len /
    insufficient-data query classification) were explicitly NOT implemented
    in Phase F.3 - see that phase's report "Explicitly Deferred" section.

    Phase F.6 adds a NARROW slice of each, informed by the read-only Phase
    F.5 audit:
        - HC3: a data-aware Setting-C raw-group-cardinality safeguard (see
          `run_data_preflight` / `validate_hc3_group_cardinality` below).
        - HC4: ONLY the whole-view time-bin-count-vs-`min_len` safeguard
          (see `validate_hc4_time_bins` below) - every OTHER HC4 sub-rule
          the F.5 audit catalogued (matrix-profile window minimums, STL/
          Mann-Kendall/turning-point-rate/VAR minimums, Setting-B/C
          minimum-series-count guards, etc.) remains deliberately
          unimplemented here. Those are Stage-2, query-specific semantics
          with mixed placeholder/omission/fallback behavior (see the F.5
          report's Parts 9-13) - reimplementing them in the backend would
          mean duplicating querylib's query logic itself, which this
          module's own docstring has always disclaimed doing.

    This module is split into two conceptual stages, both still living in
    this one file (Part 25 of the Phase F.6 spec: prefer not to fragment
    into many tiny files):
        - SPEC-level preflight (`run_backend_preflight`, aliased as
          `run_spec_preflight` for new call sites - Phase F.6 did not
          rename the original function to avoid unnecessary churn in
          existing callers/tests): HC1 + HC2, spec-dict-only, no DataFrame
          needed.
        - DATA-level preflight (`run_data_preflight`, new in Phase F.6):
          HC3 + the HC4 time-bin safeguard, requires the loaded (and, for
          real_synthetic, schema-validated) DataFrame(s).

Failed/omitted query-instance detection (missing_instance_ids,
failed_instances, or any exception-message recovery from querylib) is also
explicitly out of scope for this module - see the Phase F.2 audit's
finding that the current public querylib/handout_lib API does not reliably
preserve failure reasons, and that dataset-aware `enumerate_instances` is
not an independent oracle (it runs the same lower-level battery and can
suffer the same silent omission as `run_real`/`run_pair`). That is why HC2
below uses ONLY the dataset-free, Stage-1-free, Stage-2-free static call
(`enumerate_instances(spec)`, `real_df=None`) - never the dataset-aware
form, and never for missing-instance comparison.

Phase F.6 also does NOT attempt to fix, work around, or preflight the
Phase F.5 audit's real-vs-synthetic Stage-1 "zero-fill asymmetry" finding
(a group present on only one side of a comparison can be silently
zero-filled on the missing side under querylib's default fill policy,
rather than dropped) - that is a querylib Stage-1 semantic, explicitly
deferred pending a product/querylib-API decision, not something this
module reimplements or rejects against.
"""
from __future__ import annotations

import json
from typing import Any

import pandas as pd

from app.services.evaluation2 import handout_adapter as adapter

# ============================================================================
#  structured, application-owned preflight error
# ============================================================================
class Phase2PreflightError(ValueError):
    """A backend-owned Phase 2 preflight rejection (HC1/HC2 today).

    Deliberately structured (``code`` / ``message`` / ``details``) rather
    than a free-form string, so a frontend can branch on ``code`` instead of
    parsing prose. ``str(error)`` returns a deterministic JSON encoding of
    the same three fields (see :meth:`to_dict/to_json`) - this is what
    `JobExecutor` persists into the job store's existing ``error`` TEXT
    column for this specific exception type (see job_executor.py), so a
    structured payload survives all the way to the status API without any
    database schema change.
    """

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        self.code = code
        self.message = message
        self.details = dict(details) if details else {}
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}

    def to_json(self) -> str:
        # sort_keys for a deterministic, testable string representation.
        return json.dumps(self.to_dict(), sort_keys=True)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.to_json()


# ============================================================================
#  HC1 - backend-owned grouping-constraint preflight
# ============================================================================
def validate_backend_hc1(spec: dict) -> None:
    """Backend-owned preflight rule derived from the supplied Phase 2 docs'
    HC1 description: a group-by key's attribute must be an entity
    attribute, never ``dataset.id`` or ``dataset.time``.

    This is NOT Steven's authoritative validator (none is bundled - see
    the Phase F.2 audit and this module's docstring); it is a backend
    policy check applied before any data reaches `handout_adapter`.

    Reads (never mutates) the already-validated spec dict:
        - ``spec["dataset"]["id"]`` / ``spec["dataset"]["time"]``
        - every grouping key's ``attr``, across either a single ``groupby``
          block or every view in ``groupbys`` (multi-view specs) - the same
          shape ``input_validator.required_columns`` already reads, so this
          works for any valid spec on any dataset, never hardcoding NOAA (or
          any other) column names.

    Raises:
        Phase2PreflightError (code ``HC1_GROUPING_CONSTRAINT``) on the
        first offending grouping attribute found, scanning views and keys
        in their existing order (deterministic - not dependent on set
        iteration order). A duplicate attribute across multiple views is
        only ever reported once (the first occurrence), not once per view.
    """
    dataset = spec.get("dataset") or {}
    id_col = dataset.get("id")
    time_col = dataset.get("time")

    views = spec["groupbys"] if spec.get("groupbys") else [spec]

    seen: set[str] = set()
    for view in views:
        groupby = view.get("groupby") or {}
        for key in groupby.get("keys") or []:
            attr = key.get("attr")
            if not attr or attr in seen:
                continue
            seen.add(attr)

            if id_col and attr == id_col:
                raise Phase2PreflightError(
                    code="HC1_GROUPING_CONSTRAINT",
                    message=(
                        f"HC1 violation: grouping attribute {attr!r} cannot "
                        f"use dataset.id"
                    ),
                    details={"attribute": attr, "role": "dataset.id"},
                )
            if time_col and attr == time_col:
                raise Phase2PreflightError(
                    code="HC1_GROUPING_CONSTRAINT",
                    message=(
                        f"HC1 violation: grouping attribute {attr!r} cannot "
                        f"use dataset.time"
                    ),
                    details={"attribute": attr, "role": "dataset.time"},
                )


# ============================================================================
#  HC2 - backend-owned static instance-count preflight
# ============================================================================
# The supplied handout docs (04_SPEC_FORMAT.md, 01_CONCEPTS.md,
# 02_TAXONOMY.md - all confirmed consistent in the Phase F.2 audit) say
# "<= 200". Our backend/product policy is INTENTIONALLY STRICTER: fewer
# than 200 instances are allowed. This constant is that backend policy, not
# a restatement of the handout's own limit - the distinction is deliberate
# and must not be blurred:
#     handout docs (unenforced anywhere in the bundle):  count <= 200
#     this backend's policy (enforced here):             count <  200
# 199 is therefore the largest static instance count this backend accepts;
# 200 is rejected, even though the handout docs alone would allow it.
HC2_MAX_SUPPORTED_INSTANCES = 199


def validate_hc2_instance_count(spec: dict) -> None:
    """Backend-owned preflight rule enforcing this backend's HC2 policy
    (see the module-level constant `HC2_MAX_SUPPORTED_INSTANCES` above for
    the exact <=200-vs-<200 distinction).

    Uses ONLY `handout_adapter.enumerate_instances(spec)` with no `real_df`
    argument (the dataset-free, Stage-1-free, Stage-2-free static form).
    This is a deliberate, F.2-audit-driven choice:
        - the dataset-*aware* form (`enumerate_instances(spec,
          real_df=...)`) runs the same lower-level query battery as
          `run_real`/`run_pair` and can therefore suffer the same silent
          instance omission - it is not a safe "expected count" oracle and
          must never be used for this rule.
        - the static form never touches a dataset, never runs Stage 1
          (grouping) or Stage 2 (the query battery) - it is a pure,
          spec-only layout preview, which is exactly what a *configured*
          instance-count check should measure.

    Raises:
        Phase2PreflightError (code ``INSTANCE_LIMIT_EXCEEDED``) if the
        static instance count is 200 or more. Never raises for any lower
        count, including 0.
    """
    expected_df = adapter.enumerate_instances(spec)  # real_df=None (default)
    count = len(expected_df)

    if count >= 200:
        raise Phase2PreflightError(
            code="INSTANCE_LIMIT_EXCEEDED",
            message=(
                f"Specification produces {count} instances; fewer than "
                f"200 are supported."
            ),
            details={
                "expected_instance_count": count,
                "max_supported_instances": HC2_MAX_SUPPORTED_INSTANCES,
            },
        )


# ============================================================================
#  combined entry point
# ============================================================================
def run_backend_preflight(spec: dict) -> None:
    """Run every backend-owned Phase 2 preflight rule, in order (HC1, then
    HC2). Intended to be called once per evaluation, immediately after
    `handout_adapter.load_spec()` and before any CSV/DataFrame validation
    or querylib execution (see evaluation_service.py's
    `run_real_only`/`run_real_synthetic`).

    Raises the first `Phase2PreflightError` encountered; does not attempt
    to collect and report every violation at once.
    """
    validate_backend_hc1(spec)
    validate_hc2_instance_count(spec)


# Phase F.6: explicit alias so new call sites can name this stage clearly
# as "spec preflight" without renaming (and thereby breaking) the original
# function or its existing callers/tests.
run_spec_preflight = run_backend_preflight


# ============================================================================
#  view extraction (shared by HC3 and HC4 - Phase F.6)
# ============================================================================
def _iter_views(spec: dict):
    """Yield ``(view_name, view)`` for every configured group-by view in an
    already-validated spec (i.e. the dict `handout_adapter.load_spec`
    returns), handling both supported spec shapes without mutating `spec`:

        - single-view: the spec dict itself IS the one view (``groupby``/
          ``queries``/``dataset`` live at the top level) -> ``view_name`` is
          ``None``. This is the stable, canonical "no multi-view name"
          marker used consistently in every HC3/HC4 error's ``details.view``
          field, so a frontend never has to special-case a missing key vs.
          an explicit null.
        - multi-view (``spec["groupbys"]``): a list of named sub-specs, each
          with its own ``groupby``/``queries``/``dataset`` and a ``__name``
          key that querylib's own ``spec.validate()`` sets (confirmed by
          reading ``querylib/spec.py``'s multi-groupby handling) ->
          ``view_name`` is that ``__name``.
    """
    if spec.get("groupbys"):
        for view in spec["groupbys"]:
            yield view.get("__name"), view
    else:
        yield None, spec


def _view_label(view_name: str | None) -> str:
    """Human-readable view label for an error message (never used for
    `details.view`, which always carries the raw `view_name` - `None` for a
    single-view spec, so a frontend can distinguish "no multi-view name"
    from any real string)."""
    return view_name if view_name is not None else "(default)"


# ============================================================================
#  HC3 - backend-owned Setting-C population-safety classification
# ============================================================================
# Backend-owned classification derived from the supplied Phase 2 docs
# (04_SPEC_FORMAT.md's HC3 section, quoted in full in the Phase F.5 audit)
# cross-referenced BY HAND against the audited querylib/catalog.py Setting-C
# query catalog. This is a STATIC, SELF-CONTAINED mirror - it is never
# imported from querylib.catalog at runtime (this application never imports
# querylib directly; see handout_bootstrap.py's module docstring) and is
# NOT automatically kept in sync with any future querylib catalog change.
# If Steven's catalog changes, this mirror must be updated by hand to match.
HC3_V3_POPULATION_SAFE_C_QIDS = frozenset({
    "series_mean_distribution",
    "series_variance_distribution",
    "series_quantile_distribution",
    "system_avg_trajectory",
    "system_dominant_frequency",
    "system_spectral_concentration",
    "shared_dominant_freq_count",
})

HC3_V3_RESTRICTED_C_QIDS = frozenset({
    "cross_series_corr_variation",
    "cross_series_corr_changepoint_location",
    "cross_series_corr_changepoint_strength",
    "crosscorr_max_matrix",
    "best_lag_matrix",
    "max_cross_lag_dependence",
    "lagged_dependency_graph",
    "lagged_dependency_density",
    "max_coherence",
    "coherent_pair_count",
    "cross_series_motif_count|shape",
    "cross_series_motif_count|amp",
    "cross_series_discord_count|shape",
    "cross_series_discord_count|amp",
    "series_discord_contribution|shape",
    "series_discord_contribution|amp",
})

# v2 taxonomy: the SAME underlying queries carry the SAME complexity
# classification (O(n^2)-ness is a property of the query, not the taxonomy
# version) - but v2's Setting-C catalog does not include
# crosscorr_max_matrix/best_lag_matrix at all (those exist only under
# Setting B in v2 - confirmed against querylib/catalog.py's
# QUERY_CATALOG["C"]), and v2 has no |shape/|amp mode suffix (matrix-profile
# queries are unmoded in v2). These two sets are therefore DERIVED from the
# v3 sets above, keeping only the qids that actually exist in v2's Setting-C
# catalog - never a blind copy of the v3 lists, and never assuming a v3-only
# qid could be selected under taxonomy_version: v2 (it cannot - querylib's
# own spec.validate() would reject an unknown qid for the resolved taxonomy
# before this backend ever sees the spec).
HC3_V2_POPULATION_SAFE_C_QIDS = frozenset({
    "series_mean_distribution",
    "series_variance_distribution",
    "series_quantile_distribution",
    "system_avg_trajectory",
    "system_dominant_frequency",
    "system_spectral_concentration",
    "shared_dominant_freq_count",
})

HC3_V2_RESTRICTED_C_QIDS = frozenset({
    "cross_series_corr_variation",
    "cross_series_corr_changepoint_location",
    "cross_series_corr_changepoint_strength",
    "max_cross_lag_dependence",
    "lagged_dependency_graph",
    "lagged_dependency_density",
    "max_coherence",
    "coherent_pair_count",
    "cross_series_motif_count",
    "cross_series_discord_count",
    "series_discord_contribution",
})

_HC3_CLASSIFICATION_BY_VERSION: dict[str, tuple[frozenset, frozenset]] = {
    "v2": (HC3_V2_POPULATION_SAFE_C_QIDS, HC3_V2_RESTRICTED_C_QIDS),
    "v3": (HC3_V3_POPULATION_SAFE_C_QIDS, HC3_V3_RESTRICTED_C_QIDS),
}


def classify_hc3_c_qid(qid: str, taxonomy_version: str) -> str:
    """Classify one selected Setting-C query id as ``"safe"``,
    ``"restricted"``, or ``"unknown"`` for the given taxonomy version.

    ``"unknown"`` (Phase F.6 Part 24 policy - deliberately FAILS CLOSED):
    a qid absent from BOTH audited sets for this taxonomy version, e.g. a
    future catalog addition this backend's static mirror has not been
    updated for. An unknown qid is NEVER treated as population-safe -
    see `validate_hc3_group_cardinality` for how this drives a dedicated
    ``HC3_UNCLASSIFIED_QUERY`` rejection when it matters (i.e. only when
    the view's raw cardinality is already > 50; an unknown qid on a
    <=50-group view is never blocked, since HC3 would not restrict
    anything on that view regardless of classification).

    An unrecognized `taxonomy_version` falls back to the v2 classification
    (matching querylib's own `spec.py` default-to-"v2" convention).
    """
    safe, restricted = _HC3_CLASSIFICATION_BY_VERSION.get(
        taxonomy_version, (HC3_V2_POPULATION_SAFE_C_QIDS, HC3_V2_RESTRICTED_C_QIDS)
    )
    if qid in safe:
        return "safe"
    if qid in restricted:
        return "restricted"
    return "unknown"


HC3_GROUP_CARDINALITY_THRESHOLD = 50  # strictly "more than 50" (F.5 audit); 50 itself passes


def count_observed_raw_groups(df: pd.DataFrame, keys: list[str]) -> int:
    """Count DISTINCT observed, non-null raw grouping-key tuples in `df`.

    Backend-owned HC3 cardinality primitive. Reproduces ONLY the handout
    doc's bare formula (``groupby(raw keys).ngroups``) against the RAW,
    unbinned column values - no ``bin_edges`` digitization, no time-window
    binning, no fill, no ``min_len`` filtering (the Phase F.5 audit
    confirmed HC3's cardinality must be computed independently of, and
    prior to, every Stage-1 mechanism - using a post-Stage-1 kept-group
    count here would be a materially different, and wrong, number).

    BACKEND POLICY (the handout's bare formula does not specify either of
    these - documented explicitly here because the ambiguity is real, per
    the Phase F.5 audit's open questions):
        - null-containing tuples are excluded (pandas ``dropna=True``).
        - unused categorical levels are excluded (pandas ``observed=True``
          - only affects categorical-dtype columns; harmless/no-op for any
          other dtype).
    Multiple keys are counted as distinct COMBINED tuples (ordinary
    pandas multi-key groupby semantics), never summed per-key
    cardinalities. Duplicate rows contribute at most one group each
    (`.ngroups` counts distinct keys, not row counts). Never mutates `df`.
    """
    if not keys:
        return 0
    return int(df.groupby(list(keys), dropna=True, observed=True).ngroups)


def count_observed_raw_group_union(
    real_df: pd.DataFrame, synth_df: pd.DataFrame, keys: list[str]
) -> int:
    """BACKEND COMPARISON POLICY (Phase F.6 - NOT stated by the handout,
    which does not address real+synthetic HC3 semantics at all): for
    real_synthetic mode, HC3's cardinality is the count of DISTINCT
    observed raw grouping-key tuples across the UNION of `real_df` and
    `synth_df` - never `real_df` alone, never
    ``max(real_count, synth_count)``, never `synth_df` alone.

    Reason: the Stage-1 comparison collection querylib actually builds is
    the union of group labels seen on EITHER side (confirmed in the Phase
    F.5 audit, Part 15: ``groups = sorted(set(ra["__g"]) | set(ga["__g"]))``
    in ``querylib/groupby.py``) - so only counting one side could
    undercount the true comparison population this rule exists to protect
    against. Example (from the Phase F.6 spec): real has 40 groups,
    synthetic has 40 groups, but if they only partially overlap the true
    union could be as high as 65 - HC3 must gate on 65, not 40.

    Same null/categorical policy as `count_observed_raw_groups`. Never
    mutates either DataFrame.
    """
    if not keys:
        return 0
    cols = list(keys)
    combined = pd.concat([real_df[cols], synth_df[cols]], ignore_index=True)
    return int(combined.groupby(cols, dropna=True, observed=True).ngroups)


def validate_hc3_group_cardinality(
    view_name: str | None, view: dict, real_df: pd.DataFrame, synth_df: pd.DataFrame | None = None
) -> None:
    """HC3 backend-owned safeguard for ONE view.

    Rejects ONLY when the view's raw grouping cardinality is strictly
    greater than 50 AND the view's selected Setting-C queries include at
    least one HC3-restricted (population-unsafe) query - never rejects a
    <=50-group view regardless of selected queries, and never rejects a
    >50-group view whose selected Setting-C queries are all
    population-safe (or empty). Setting A/B selections are never
    considered - HC3 is a Setting-C-only rule.

    `real_df`-only cardinality for real_only mode; the UNION-based
    cardinality (`count_observed_raw_group_union`) for real_synthetic mode
    when `synth_df` is given - see that function's docstring for why.

    Raises:
        Phase2PreflightError, code ``HC3_UNCLASSIFIED_QUERY`` if the view
            is >50 groups and selects at least one Setting-C query this
            backend's static classification cannot place as safe or
            restricted (fails closed - Part 24 policy).
        Phase2PreflightError, code ``HC3_GROUP_CARDINALITY_EXCEEDED`` if
            the view is >50 groups and selects at least one classified
            HC3-restricted query. ``details.blocked_queries`` contains
            ONLY the restricted selected qids, sorted deterministically -
            population-safe selected qids are never included.
    """
    gb = view.get("groupby") or {}
    keys = [k["attr"] for k in (gb.get("keys") or []) if k.get("attr")]
    if not keys:
        return  # no grouping key configured -> no Setting-C collection exists for this view

    if synth_df is None:
        group_count = count_observed_raw_groups(real_df, keys)
    else:
        group_count = count_observed_raw_group_union(real_df, synth_df, keys)

    if group_count <= HC3_GROUP_CARDINALITY_THRESHOLD:
        return

    selected_c = list((view.get("queries") or {}).get("C") or [])
    if not selected_c:
        return

    taxonomy_version = view.get("taxonomy_version") or "v2"
    blocked: list[str] = []
    unknown: list[str] = []
    for qid in selected_c:
        verdict = classify_hc3_c_qid(qid, taxonomy_version)
        if verdict == "restricted":
            blocked.append(qid)
        elif verdict == "unknown":
            unknown.append(qid)

    if unknown:
        raise Phase2PreflightError(
            code="HC3_UNCLASSIFIED_QUERY",
            message=(
                f"View {_view_label(view_name)!r} has {group_count} raw "
                f"groups (> {HC3_GROUP_CARDINALITY_THRESHOLD}) and selects "
                f"Setting-C queries this backend cannot classify as "
                f"population-safe or restricted: {sorted(unknown)}."
            ),
            details={
                "view": view_name,
                "group_count": group_count,
                "max_group_count": HC3_GROUP_CARDINALITY_THRESHOLD,
                "unclassified_queries": sorted(unknown),
            },
        )

    if blocked:
        raise Phase2PreflightError(
            code="HC3_GROUP_CARDINALITY_EXCEEDED",
            message=(
                f"View {_view_label(view_name)!r} has {group_count} raw "
                f"groups (> {HC3_GROUP_CARDINALITY_THRESHOLD}); selected "
                f"Setting-C queries include population-unsafe queries."
            ),
            details={
                "view": view_name,
                "group_count": group_count,
                "max_group_count": HC3_GROUP_CARDINALITY_THRESHOLD,
                "blocked_queries": sorted(blocked),
            },
        )


# ============================================================================
#  HC4 - whole-view time-bin safeguard ONLY (Phase F.6 scope; see module
#  docstring for every OTHER HC4 sub-rule this deliberately does not cover)
# ============================================================================
def _time_bin_labels(df: pd.DataFrame, time_col: str, window: dict) -> set:
    """Backend HC4 time-bin safeguard: mirrors ONLY the time-BINNING half
    of querylib's documented Stage-1 window semantics
    (``querylib/groupby.py::_bin_time``, read for this phase's audit) far
    enough to compute the set of distinct time-bin LABELS a view would
    produce - it does NOT reproduce grouping-key binning, fill, or
    aggregation, and does NOT call into querylib (no import of querylib
    internals; this mirrors the documented/observed behavior only).

    Two window forms, matching `_bin_time` exactly:
        - ``window["steps"]``: fixed-length blocks of N consecutive
          (dense-ranked) timestamps - `pd.Series.rank(method="dense")`
          then integer-divided by N.
        - ``window["unit"]``: a calendar period (day/week/month/quarter/
          year) via `pandas.Period` - the exact same
          `dt.to_period(<code>)` mapping `_bin_time` uses.

    Returns a plain Python `set` of bin labels (steps -> ints; unit ->
    period strings) - only used for its length/union elsewhere, never
    displayed. Never mutates `df`.
    """
    if window.get("steps"):
        n = int(window["steps"])
        ts = df[time_col]
        order = ts.rank(method="dense").astype(int) - 1
        binid = (order // n).astype(int)
        return set(binid.tolist())

    unit = window["unit"]
    dt = pd.to_datetime(df[time_col])
    _UNIT_TO_PERIOD_CODE = {
        "day": "D", "week": "W", "month": "M", "quarter": "Q", "year": "Y",
    }
    per = dt.dt.to_period(_UNIT_TO_PERIOD_CODE[unit])
    return set(per.astype(str).tolist())


def validate_hc4_time_bins(
    view_name: str | None, view: dict, real_df: pd.DataFrame, synth_df: pd.DataFrame | None = None
) -> None:
    """HC4 backend-owned safeguard for ONE view - ONLY the whole-view
    time-bin-count-vs-``min_len`` rule (see this module's docstring for
    the many OTHER HC4 sub-rules deliberately NOT covered here).

    Computes `k` = the number of DISTINCT time-bin labels the view's
    ``groupby.window`` would produce, and rejects iff `k < min_len`.
    `k == min_len` passes (matches the Phase F.5 audit's confirmed `k <
    min_len` - not `<=` - source semantics).

    real_only: `k` from `real_df` alone.
    real_synthetic: `k` = the size of the UNION of real_df's and
    synth_df's time-bin label sets (BACKEND COMPARISON POLICY - the
    handout does not address this case either; consistent with HC3's
    union policy and with the Phase F.5 audit's finding that querylib
    itself builds its shared Stage-1 time-bin axis from the union of both
    tables' bins, never real_df's bins alone).

    Raises:
        Phase2PreflightError, code ``HC4_INSUFFICIENT_TIME_BINS``, if
            `k < min_len`. Deliberately NOT named
            ``INSUFFICIENT_SERIES_LENGTH`` - the F.5 audit proved `min_len`
            gates the whole-view TIME-BIN count, not any individual
            series's or raw row's length.
    """
    gb = view.get("groupby") or {}
    min_len = gb.get("min_len")
    if min_len is None:
        return  # spec.py always sets a default (8) once validated; defensive only

    time_col = (view.get("dataset") or {}).get("time")
    window = gb.get("window") or {}
    if not time_col or not window:
        return  # defensive: querylib's own spec.validate() already requires both

    real_bins = _time_bin_labels(real_df, time_col, window)
    if synth_df is None:
        k = len(real_bins)
    else:
        synth_bins = _time_bin_labels(synth_df, time_col, window)
        k = len(real_bins | synth_bins)

    if k < min_len:
        raise Phase2PreflightError(
            code="HC4_INSUFFICIENT_TIME_BINS",
            message=(
                f"View {_view_label(view_name)!r} produces {k} time bins; "
                f"groupby.min_len requires at least {min_len}."
            ),
            details={"view": view_name, "bin_count": k, "min_len": min_len},
        )


# ============================================================================
#  data-level preflight - combined entry point (Phase F.6)
# ============================================================================
def run_data_preflight(
    spec: dict, real_df: pd.DataFrame, synth_df: pd.DataFrame | None = None
) -> None:
    """Data-aware Phase 2 preflight: HC3 (Setting-C raw-group-cardinality
    safeguard) and the HC4 whole-view time-bin safeguard ONLY - see this
    module's docstring for exactly what HC4 sub-rules remain deliberately
    unimplemented.

    Must be called AFTER the relevant DataFrame(s) are loaded and column-
    validated (`input_validator.validate_dataframe`), and - for
    real_synthetic - AFTER `input_validator.validate_real_synthetic_schema`
    has already confirmed dtype compatibility (so a grouping-key dtype
    mismatch is caught there, before HC3's union-tuple counting here could
    ever silently compare incompatible values). Must be called BEFORE
    `handout_adapter.run_real`/`run_pair`. See `evaluation_service.py` for
    the exact sequencing.

    Evaluates every configured view independently, in stable spec order
    (`_iter_views`), running HC3 then HC4 for each view before moving to
    the next. Raises on the FIRST violation found across all views/rules -
    not a multi-error batch - consistent with `run_backend_preflight`'s
    existing fail-fast contract. A violation in one view does not
    misattribute itself to any other, valid view.
    """
    for view_name, view in _iter_views(spec):
        validate_hc3_group_cardinality(view_name, view, real_df, synth_df)
        validate_hc4_time_bins(view_name, view, real_df, synth_df)


__all__ = [
    "Phase2PreflightError",
    "HC2_MAX_SUPPORTED_INSTANCES",
    "HC3_GROUP_CARDINALITY_THRESHOLD",
    "HC3_V2_POPULATION_SAFE_C_QIDS",
    "HC3_V2_RESTRICTED_C_QIDS",
    "HC3_V3_POPULATION_SAFE_C_QIDS",
    "HC3_V3_RESTRICTED_C_QIDS",
    "validate_backend_hc1",
    "validate_hc2_instance_count",
    "run_backend_preflight",
    "run_spec_preflight",
    "classify_hc3_c_qid",
    "count_observed_raw_groups",
    "count_observed_raw_group_union",
    "validate_hc3_group_cardinality",
    "validate_hc4_time_bins",
    "run_data_preflight",
]
