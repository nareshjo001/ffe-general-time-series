"""Phase F.6 tests: data-aware HC3 (raw group cardinality) and HC4
(whole-view time-bin count) preflight (app/services/evaluation2/preflight.py
- run_data_preflight and its helpers).

These are unit tests against hand-built pandas DataFrames + spec dicts (same
convention as test_phase2_preflight.py) - no real handout/querylib needed,
since HC3/HC4's data-aware pieces are entirely backend-owned logic that only
mirrors documented querylib behavior (raw groupby cardinality, Stage-1 time
binning), never calls into querylib itself.
"""
from __future__ import annotations

import copy
import os

import pandas as pd
import pytest
import yaml

from app.services.evaluation2.preflight import (
    HC3_GROUP_CARDINALITY_THRESHOLD,
    HC3_V2_POPULATION_SAFE_C_QIDS,
    HC3_V2_RESTRICTED_C_QIDS,
    HC3_V3_POPULATION_SAFE_C_QIDS,
    HC3_V3_RESTRICTED_C_QIDS,
    Phase2PreflightError,
    classify_hc3_c_qid,
    count_observed_raw_group_union,
    count_observed_raw_groups,
    run_data_preflight,
    validate_hc3_group_cardinality,
    validate_hc4_time_bins,
)

SAFE_V3_QID = next(iter(HC3_V3_POPULATION_SAFE_C_QIDS))
RESTRICTED_V3_QID = next(iter(HC3_V3_RESTRICTED_C_QIDS))
SAFE_V2_QID = next(iter(HC3_V2_POPULATION_SAFE_C_QIDS))
RESTRICTED_V2_QID = next(iter(HC3_V2_RESTRICTED_C_QIDS))


# ============================================================================
#  spec fixtures (shape mirrors querylib/spec.py::validate + test_phase2_
#  preflight.py's convention)
# ============================================================================
def _single_view_spec(
    *, groupby_attr="LATITUDE", time_col="DATE", taxonomy_version="v3",
    min_len=12, window=None, c_queries=None,
):
    return {
        "taxonomy_version": taxonomy_version,
        "dataset": {"name": "noaa", "id": "STATION_ID", "time": time_col,
                    "measurements": ["PRCP", "TMAX", "TMIN"]},
        "groupby": {
            "keys": [{"attr": groupby_attr}],
            "window": window or {"unit": "month"},
            "agg": {"default": "avg"},
            "fill": "interp",
            "min_len": min_len,
        },
        "focus": {"A": [], "B": [], "C": []},
        "queries": {"A": [], "B": [], "C": list(c_queries or [])},
    }


def _multi_view_spec(views):
    """`views` is a list of (name, single_view_spec) - each single_view_spec
    built via `_single_view_spec`; only `groupby`/`queries`/`dataset` are
    pulled out, matching querylib's own multi-view sub-spec shape."""
    dataset = views[0][1]["dataset"]
    out = []
    for name, v in views:
        out.append({
            "__name": name,
            "taxonomy_version": v.get("taxonomy_version", "v3"),
            "dataset": v["dataset"],
            "groupby": v["groupby"],
            "focus": v["focus"],
            "queries": v["queries"],
        })
    return {"taxonomy_version": "v3", "dataset": dataset, "groupbys": out}


def _monthly_df(n_months, group_attr="LATITUDE", group_value=10, time_col="DATE", start="2020-01-01"):
    """`n_months` distinct calendar months, one row per month, single group."""
    dates = pd.date_range(start, periods=n_months, freq="MS")
    return pd.DataFrame({time_col: dates, group_attr: [group_value] * n_months})


def _cardinality_df(n_groups, group_attr="LATITUDE", time_col="DATE", rows_per_group=3):
    """`n_groups` distinct values of `group_attr`, `rows_per_group` rows
    each, arbitrary monthly dates (cardinality tests don't care about time
    binning)."""
    rows = []
    dates = pd.date_range("2020-01-01", periods=rows_per_group, freq="MS")
    for g in range(n_groups):
        for d in dates:
            rows.append({group_attr: g, time_col: d})
    return pd.DataFrame(rows)


# ============================================================================
#  HC3 boundary: 50 passes, 51 triggers
# ============================================================================
def test_hc3_exactly_50_groups_passes(monkeypatch):
    df = _cardinality_df(50)
    spec = _single_view_spec(c_queries=[RESTRICTED_V3_QID])
    validate_hc3_group_cardinality(None, spec, df)  # no raise


def test_hc3_51_groups_with_restricted_query_rejects():
    df = _cardinality_df(51)
    spec = _single_view_spec(c_queries=[RESTRICTED_V3_QID])
    with pytest.raises(Phase2PreflightError) as exc_info:
        validate_hc3_group_cardinality(None, spec, df)
    err = exc_info.value
    assert err.code == "HC3_GROUP_CARDINALITY_EXCEEDED"
    assert err.details["group_count"] == 51
    assert err.details["max_group_count"] == HC3_GROUP_CARDINALITY_THRESHOLD == 50
    assert err.details["blocked_queries"] == [RESTRICTED_V3_QID]
    assert err.details["view"] is None


# ============================================================================
#  HC3 safe / unsafe / mixed query selection
# ============================================================================
def test_hc3_over_50_groups_all_safe_queries_passes():
    df = _cardinality_df(60)
    spec = _single_view_spec(c_queries=[SAFE_V3_QID])
    validate_hc3_group_cardinality(None, spec, df)  # no raise


def test_hc3_over_50_groups_mixed_safe_and_restricted_rejects_only_restricted():
    df = _cardinality_df(60)
    other_safe = sorted(HC3_V3_POPULATION_SAFE_C_QIDS)[1] if len(HC3_V3_POPULATION_SAFE_C_QIDS) > 1 else SAFE_V3_QID
    spec = _single_view_spec(c_queries=[SAFE_V3_QID, other_safe, RESTRICTED_V3_QID])
    with pytest.raises(Phase2PreflightError) as exc_info:
        validate_hc3_group_cardinality(None, spec, df)
    assert exc_info.value.details["blocked_queries"] == [RESTRICTED_V3_QID]


def test_hc3_over_50_groups_no_c_queries_passes():
    df = _cardinality_df(60)
    spec = _single_view_spec(c_queries=[])
    validate_hc3_group_cardinality(None, spec, df)  # no raise


def test_hc3_under_50_groups_restricted_query_passes():
    df = _cardinality_df(10)
    spec = _single_view_spec(c_queries=[RESTRICTED_V3_QID])
    validate_hc3_group_cardinality(None, spec, df)  # no raise


# ============================================================================
#  HC3 multi-key grouping
# ============================================================================
def test_hc3_multi_key_counts_combined_distinct_tuples():
    # 3 x 3 = 9 combined tuples even though each key alone only has 3
    # distinct values - proves combined-tuple counting, not per-key.
    rows = [{"A": a, "B": b, "DATE": pd.Timestamp("2020-01-01")}
            for a in range(3) for b in range(3)]
    df = pd.DataFrame(rows)
    spec = {
        "taxonomy_version": "v3",
        "dataset": {"name": "x", "id": "id", "time": "DATE", "measurements": ["M"]},
        "groupby": {"keys": [{"attr": "A"}, {"attr": "B"}], "window": {"unit": "month"},
                    "agg": {"default": "avg"}, "fill": "interp", "min_len": 1},
        "focus": {"A": [], "B": [], "C": []},
        "queries": {"A": [], "B": [], "C": [RESTRICTED_V3_QID]},
    }
    assert count_observed_raw_groups(df, ["A", "B"]) == 9
    validate_hc3_group_cardinality(None, spec, df)  # 9 <= 50, no raise


# ============================================================================
#  HC3 duplicates do not inflate count
# ============================================================================
def test_hc3_duplicate_rows_do_not_inflate_count():
    df = pd.concat([_cardinality_df(10)] * 5, ignore_index=True)  # 5x duplication
    assert count_observed_raw_groups(df, ["LATITUDE"]) == 10


# ============================================================================
#  HC3 nulls excluded (dropna=True semantics)
# ============================================================================
def test_hc3_null_containing_tuples_excluded():
    df = pd.DataFrame({
        "LATITUDE": [1, 2, 3, None],
        "DATE": pd.date_range("2020-01-01", periods=4, freq="MS"),
    })
    assert count_observed_raw_groups(df, ["LATITUDE"]) == 3


# ============================================================================
#  HC3 unused categorical levels excluded (observed=True semantics)
# ============================================================================
def test_hc3_unused_categorical_levels_excluded():
    cat = pd.Categorical(["a", "b", "a"], categories=["a", "b", "c", "d"])
    df = pd.DataFrame({
        "LATITUDE": cat,
        "DATE": pd.date_range("2020-01-01", periods=3, freq="MS"),
    })
    # 4 declared categories, only 2 observed -> must count 2, not 4.
    assert count_observed_raw_groups(df, ["LATITUDE"]) == 2


# ============================================================================
#  HC3 real+synthetic union (not max, not real-only)
# ============================================================================
def test_hc3_real_synthetic_union_not_max():
    # real: groups 1-40 (40 groups); synth: groups 26-65 (40 groups);
    # true union: 1-65 = 65 groups. max(40, 40) would wrongly be 40.
    real_df = _cardinality_df(40, group_attr="LATITUDE")  # groups 0..39
    synth_rows = []
    dates = pd.date_range("2020-01-01", periods=3, freq="MS")
    for g in range(25, 65):  # groups 25..64 (40 groups), overlapping 25-39
        for d in dates:
            synth_rows.append({"LATITUDE": g, "DATE": d})
    synth_df = pd.DataFrame(synth_rows)

    union_count = count_observed_raw_group_union(real_df, synth_df, ["LATITUDE"])
    assert union_count == 65  # groups 0..64 inclusive

    spec = _single_view_spec(c_queries=[RESTRICTED_V3_QID])
    with pytest.raises(Phase2PreflightError) as exc_info:
        validate_hc3_group_cardinality(None, spec, real_df, synth_df)
    assert exc_info.value.details["group_count"] == 65


def test_hc3_real_synthetic_union_passes_when_each_side_alone_would_fail_boundary():
    # real: 30 groups, synth: 30 overlapping groups (union = 30) -> passes,
    # sanity check that union isn't naively summed (30+30=60 would wrongly fail).
    real_df = _cardinality_df(30)
    synth_df = _cardinality_df(30)
    spec = _single_view_spec(c_queries=[RESTRICTED_V3_QID])
    validate_hc3_group_cardinality(None, spec, real_df, synth_df)  # no raise


# ============================================================================
#  HC3 multi-view independence
# ============================================================================
def test_hc3_multi_view_independent_only_violating_view_reported():
    good_view = _single_view_spec(groupby_attr="LATITUDE", c_queries=[SAFE_V3_QID])
    bad_view = _single_view_spec(groupby_attr="ELEVATION", c_queries=[RESTRICTED_V3_QID])
    spec = _multi_view_spec([("good", good_view), ("bad", bad_view)])

    small_df = _cardinality_df(10, group_attr="LATITUDE")
    small_df["ELEVATION"] = 0
    big_df = _cardinality_df(60, group_attr="ELEVATION")
    big_df["LATITUDE"] = 0

    # good view sees only small cardinality via LATITUDE, bad view sees the
    # 60-group cardinality via ELEVATION - the SAME real_df is reused for
    # both by run_data_preflight since keys differ per view.
    combined = pd.concat([small_df, big_df], ignore_index=True)
    combined["DATE"] = pd.date_range("2020-01-01", periods=len(combined), freq="MS")

    with pytest.raises(Phase2PreflightError) as exc_info:
        run_data_preflight(spec, combined)
    assert exc_info.value.code == "HC3_GROUP_CARDINALITY_EXCEEDED"
    assert exc_info.value.details["view"] == "bad"


# ============================================================================
#  HC3 v2 vs v3 classification
# ============================================================================
def test_hc3_v3_classification_safe_and_restricted():
    assert classify_hc3_c_qid(SAFE_V3_QID, "v3") == "safe"
    assert classify_hc3_c_qid(RESTRICTED_V3_QID, "v3") == "restricted"


def test_hc3_v2_classification_safe_and_restricted():
    assert classify_hc3_c_qid(SAFE_V2_QID, "v2") == "safe"
    assert classify_hc3_c_qid(RESTRICTED_V2_QID, "v2") == "restricted"


def test_hc3_v2_does_not_contain_v3_only_matrix_qids():
    # v3-only matrix-profile qids must not exist in v2's classification sets
    v3_only = {"crosscorr_max_matrix", "best_lag_matrix"}
    assert not (v3_only & HC3_V2_POPULATION_SAFE_C_QIDS)
    assert not (v3_only & HC3_V2_RESTRICTED_C_QIDS)


def test_hc3_unknown_taxonomy_version_falls_back_to_v2():
    assert classify_hc3_c_qid(SAFE_V2_QID, "vNEXT") == "safe"


# ============================================================================
#  HC3 unknown qid fails closed
# ============================================================================
def test_hc3_unknown_qid_classification():
    assert classify_hc3_c_qid("totally_made_up_qid", "v3") == "unknown"


def test_hc3_unclassified_qid_at_over_50_groups_fails_closed():
    df = _cardinality_df(60)
    spec = _single_view_spec(c_queries=["totally_made_up_qid"])
    with pytest.raises(Phase2PreflightError) as exc_info:
        validate_hc3_group_cardinality(None, spec, df)
    assert exc_info.value.code == "HC3_UNCLASSIFIED_QUERY"
    assert exc_info.value.details["unclassified_queries"] == ["totally_made_up_qid"]


def test_hc3_unclassified_qid_at_or_under_50_groups_does_not_block():
    df = _cardinality_df(50)
    spec = _single_view_spec(c_queries=["totally_made_up_qid"])
    validate_hc3_group_cardinality(None, spec, df)  # no raise


# ============================================================================
#  HC3 does not mutate DataFrame or spec
# ============================================================================
def test_hc3_does_not_mutate_spec():
    df = _cardinality_df(60)
    spec = _single_view_spec(c_queries=[RESTRICTED_V3_QID])
    before = copy.deepcopy(spec)
    with pytest.raises(Phase2PreflightError):
        validate_hc3_group_cardinality(None, spec, df)
    assert spec == before


# ============================================================================
#  HC4 boundary: k = min_len-1 rejects, k = min_len passes, k = min_len+1 passes
# ============================================================================
def test_hc4_k_equals_min_len_minus_1_rejects():
    df = _monthly_df(11)
    spec = _single_view_spec(min_len=12)
    with pytest.raises(Phase2PreflightError) as exc_info:
        validate_hc4_time_bins(None, spec, df)
    err = exc_info.value
    assert err.code == "HC4_INSUFFICIENT_TIME_BINS"
    assert err.details == {"view": None, "bin_count": 11, "min_len": 12}


def test_hc4_k_equals_min_len_passes():
    df = _monthly_df(12)
    spec = _single_view_spec(min_len=12)
    validate_hc4_time_bins(None, spec, df)  # no raise


def test_hc4_k_equals_min_len_plus_1_passes():
    df = _monthly_df(13)
    spec = _single_view_spec(min_len=12)
    validate_hc4_time_bins(None, spec, df)  # no raise


# ============================================================================
#  HC4 monthly vs weekly window units
# ============================================================================
def test_hc4_weekly_window_counts_distinct_weeks():
    dates = pd.date_range("2020-01-01", periods=20, freq="W")
    df = pd.DataFrame({"DATE": dates, "LATITUDE": 1})
    spec = _single_view_spec(min_len=20, window={"unit": "week"})
    validate_hc4_time_bins(None, spec, df)  # no raise (exactly 20 weeks)

    spec_too_strict = _single_view_spec(min_len=21, window={"unit": "week"})
    with pytest.raises(Phase2PreflightError):
        validate_hc4_time_bins(None, spec_too_strict, df)


# ============================================================================
#  HC4 real+synthetic union
# ============================================================================
def test_hc4_real_synthetic_union_of_bins():
    # real: Jan/Feb/Mar; synth: Mar/Apr/May -> union k=5 (Jan-May)
    real_df = pd.DataFrame({
        "DATE": pd.to_datetime(["2020-01-15", "2020-02-15", "2020-03-15"]),
        "LATITUDE": 1,
    })
    synth_df = pd.DataFrame({
        "DATE": pd.to_datetime(["2020-03-15", "2020-04-15", "2020-05-15"]),
        "LATITUDE": 1,
    })
    spec = _single_view_spec(min_len=5, window={"unit": "month"})
    validate_hc4_time_bins(None, spec, real_df, synth_df)  # no raise (k=5)

    spec_too_strict = _single_view_spec(min_len=6, window={"unit": "month"})
    with pytest.raises(Phase2PreflightError) as exc_info:
        validate_hc4_time_bins(None, spec_too_strict, real_df, synth_df)
    assert exc_info.value.details["bin_count"] == 5


def test_hc4_real_synthetic_uses_union_not_real_alone():
    # real alone only has 3 bins (would fail min_len=5), but union with
    # synth reaches 5 - must pass, proving real_df alone is not used.
    real_df = pd.DataFrame({
        "DATE": pd.to_datetime(["2020-01-15", "2020-02-15", "2020-03-15"]),
        "LATITUDE": 1,
    })
    synth_df = pd.DataFrame({
        "DATE": pd.to_datetime(["2020-04-15", "2020-05-15"]),
        "LATITUDE": 1,
    })
    spec = _single_view_spec(min_len=5, window={"unit": "month"})
    validate_hc4_time_bins(None, spec, real_df, synth_df)  # no raise


# ============================================================================
#  HC4 multi-view independence
# ============================================================================
def test_hc4_multi_view_independent_only_violating_view_reported():
    good_view = _single_view_spec(min_len=3)
    bad_view = _single_view_spec(min_len=100)
    spec = _multi_view_spec([("good", good_view), ("bad", bad_view)])
    df = _monthly_df(12)
    with pytest.raises(Phase2PreflightError) as exc_info:
        run_data_preflight(spec, df)
    assert exc_info.value.code == "HC4_INSUFFICIENT_TIME_BINS"
    assert exc_info.value.details["view"] == "bad"


# ============================================================================
#  HC4 arbitrary time-column name
# ============================================================================
def test_hc4_arbitrary_time_column_name():
    df = _monthly_df(5, time_col="observed_at")
    spec = _single_view_spec(min_len=6, time_col="observed_at")
    with pytest.raises(Phase2PreflightError) as exc_info:
        validate_hc4_time_bins(None, spec, df)
    assert exc_info.value.details["bin_count"] == 5


# ============================================================================
#  HC3-before-HC4 ordering within a view, per run_data_preflight
# ============================================================================
def test_run_data_preflight_hc3_checked_before_hc4_within_view():
    # A view that violates BOTH HC3 and HC4 - HC3 error must surface first
    # (validate_hc3_group_cardinality runs before validate_hc4_time_bins in
    # run_data_preflight).
    df = _cardinality_df(60, rows_per_group=1)  # 60 groups, only 1 month -> also HC4-thin
    spec = _single_view_spec(c_queries=[RESTRICTED_V3_QID], min_len=99)
    with pytest.raises(Phase2PreflightError) as exc_info:
        run_data_preflight(spec, df)
    assert exc_info.value.code == "HC3_GROUP_CARDINALITY_EXCEEDED"


# ============================================================================
#  run_data_preflight passes clean spec/data through untouched
# ============================================================================
def test_run_data_preflight_passes_for_valid_view():
    df = _monthly_df(12)
    spec = _single_view_spec(min_len=12, c_queries=[SAFE_V3_QID])
    run_data_preflight(spec, df)  # no raise


def test_run_data_preflight_real_synthetic_passes_for_valid_views():
    real_df = _monthly_df(12)
    synth_df = _monthly_df(12)
    spec = _single_view_spec(min_len=12, c_queries=[SAFE_V3_QID])
    run_data_preflight(spec, real_df, synth_df)  # no raise


# ============================================================================
#  view with no groupby keys is a no-op for HC3 (defensive)
# ============================================================================
def test_hc3_no_groupby_keys_is_noop():
    spec = _single_view_spec()
    spec["groupby"]["keys"] = []
    df = _cardinality_df(60)
    validate_hc3_group_cardinality(None, spec, df)  # no raise, nothing to key on


# ============================================================================
#  integration: run_data_preflight wired into evaluation_service, before any
#  querylib execution (run_real / run_pair never invoked after rejection;
#  the rejection surfaces as a structured error_details via the status API)
# ============================================================================
def _write_csv(path, columns, n_rows=60):
    """Write a minimal CSV satisfying `required_columns(spec)` with enough
    distinct STATION_ID values to trigger HC3 (>50 groups)."""
    dates = pd.date_range("2020-01-01", periods=3, freq="MS")
    rows = []
    for g in range(n_rows):
        for d in dates:
            row = {c: 0 for c in columns}
            row["STATION_ID"] = f"S{g}"
            row["DATE"] = d.strftime("%Y-%m-%d")
            row["LATITUDE"] = g
            rows.append(row)
    pd.DataFrame(rows)[list(columns)].to_csv(path, index=False)


def _hc3_violating_spec():
    return _single_view_spec(groupby_attr="LATITUDE", c_queries=[RESTRICTED_V3_QID], min_len=1)


def test_evaluation_service_real_only_rejects_via_data_preflight_before_run_real(
    tmp_path, monkeypatch
):
    from app.services.evaluation2 import evaluation_service
    from app.services.evaluation2 import handout_adapter as adapter

    spec = _hc3_violating_spec()
    columns = {"STATION_ID", "DATE", "LATITUDE", "PRCP", "TMAX", "TMIN"}
    real_csv = tmp_path / "real.csv"
    _write_csv(real_csv, columns, n_rows=60)

    monkeypatch.setattr(adapter, "load_spec", lambda path: spec)
    monkeypatch.setattr(adapter, "enumerate_instances", lambda spec_, *a, **k: list(range(5)))

    def fake_load_panel(path):
        df = pd.read_csv(real_csv, parse_dates=["DATE"])
        return df, None

    monkeypatch.setattr(adapter, "load_panel", fake_load_panel)

    def boom_run_real(*a, **k):
        raise AssertionError("run_real must never be called after an HC3/HC4 rejection")

    monkeypatch.setattr(adapter, "run_real", boom_run_real)

    with pytest.raises(Phase2PreflightError) as exc_info:
        evaluation_service.run_real_only(real_csv, tmp_path / "spec.yaml")
    assert exc_info.value.code == "HC3_GROUP_CARDINALITY_EXCEEDED"


def test_evaluation_service_real_synthetic_rejects_via_data_preflight_before_run_pair(
    tmp_path, monkeypatch
):
    from app.services.evaluation2 import evaluation_service
    from app.services.evaluation2 import handout_adapter as adapter
    from app.services.evaluation2 import input_validator as validator

    spec = _hc3_violating_spec()
    columns = {"STATION_ID", "DATE", "LATITUDE", "PRCP", "TMAX", "TMIN"}
    real_csv = tmp_path / "real.csv"
    synth_csv = tmp_path / "synth.csv"
    _write_csv(real_csv, columns, n_rows=60)
    _write_csv(synth_csv, columns, n_rows=60)

    monkeypatch.setattr(adapter, "load_spec", lambda path: spec)
    monkeypatch.setattr(adapter, "enumerate_instances", lambda spec_, *a, **k: list(range(5)))

    def fake_load_panel(path):
        source = real_csv if str(path) == str(real_csv) else synth_csv
        df = pd.read_csv(source, parse_dates=["DATE"])
        return df, None

    monkeypatch.setattr(adapter, "load_panel", fake_load_panel)
    monkeypatch.setattr(validator, "validate_real_synthetic_schema", lambda *a, **k: None)

    def boom_run_pair(*a, **k):
        raise AssertionError("run_pair must never be called after an HC3/HC4 rejection")

    monkeypatch.setattr(adapter, "run_pair", boom_run_pair)

    with pytest.raises(Phase2PreflightError) as exc_info:
        evaluation_service.run_real_synthetic(real_csv, synth_csv, tmp_path / "spec.yaml")
    assert exc_info.value.code == "HC3_GROUP_CARDINALITY_EXCEEDED"


def test_evaluation_service_real_only_valid_job_proceeds_past_data_preflight(
    tmp_path, monkeypatch
):
    """A valid (HC3/HC4-passing) spec+data must still reach `run_real` -
    proves `run_data_preflight` does not over-reject."""
    from app.services.evaluation2 import evaluation_service
    from app.services.evaluation2 import handout_adapter as adapter

    spec = _single_view_spec(groupby_attr="LATITUDE", c_queries=[SAFE_V3_QID], min_len=1)
    columns = {"STATION_ID", "DATE", "LATITUDE", "PRCP", "TMAX", "TMIN"}
    real_csv = tmp_path / "real.csv"
    _write_csv(real_csv, columns, n_rows=5)  # well under the HC3 threshold

    monkeypatch.setattr(adapter, "load_spec", lambda path: spec)
    monkeypatch.setattr(adapter, "enumerate_instances", lambda spec_, *a, **k: list(range(5)))

    def fake_load_panel(path):
        df = pd.read_csv(real_csv, parse_dates=["DATE"])
        return df, None

    monkeypatch.setattr(adapter, "load_panel", fake_load_panel)

    run_real_calls = []

    def fake_run_real(spec_, df_):
        run_real_calls.append(1)
        return pd.DataFrame()

    monkeypatch.setattr(adapter, "run_real", fake_run_real)
    monkeypatch.setattr(adapter, "group_series", lambda *a, **k: pd.DataFrame())

    result = evaluation_service.run_real_only(real_csv, tmp_path / "spec.yaml")
    assert run_real_calls == [1]
    assert result["result"]["instances"] == []


# ============================================================================
#  Phase F.1/F.3/F.4 regression: HC1/HC2 still short-circuit before HC3/HC4
#  ever run - run_data_preflight is a strictly later stage.
# ============================================================================
def test_run_backend_preflight_and_run_data_preflight_are_independent_stages():
    from app.services.evaluation2.preflight import run_backend_preflight

    # A spec that fails HC1 must be rejected by run_backend_preflight alone -
    # run_data_preflight is never reached in the real evaluation_service
    # sequence when this happens (see evaluation_service.py's ordering).
    spec = _single_view_spec(groupby_attr="STATION_ID")
    spec["dataset"]["id"] = "STATION_ID"
    with pytest.raises(Phase2PreflightError) as exc_info:
        run_backend_preflight(spec)
    assert exc_info.value.code == "HC1_GROUPING_CONSTRAINT"


# ============================================================================
#  Phase F.6.1 - taxonomy-version guard verification (read-only + regression)
# ============================================================================
# Source-verified (querylib/spec.py::validate, lines ~74-79):
#     version = spec.get("taxonomy_version", "v2")
#     if version not in TAXONOMY_VERSIONS:      # TAXONOMY_VERSIONS = ("v2", "v3")
#         raise SpecError(...)
# and confirmed live through the exact public path this backend uses
# (`handout_adapter.load_spec`, which delegates unchanged to
# `handout_lib.load_spec` -> `querylib.spec.load` -> `validate`):
#   - a missing `taxonomy_version` key legitimately defaults to "v2"
#   - explicit "v2"/"v3" are accepted
#   - explicit "v99" (and, additionally verified, "" and null) are REJECTED
#     with `querylib.spec.SpecError` before `load_spec` ever returns a dict
#
# Consequence: `evaluation_service.run_real_only`/`run_real_synthetic` call
# `adapter.load_spec(spec_path)` as their very first step (before
# `run_backend_preflight`, before `run_data_preflight`, before this module's
# `classify_hc3_c_qid`). A `SpecError` there propagates immediately - no
# production spec carrying an explicitly-unsupported `taxonomy_version` can
# ever reach `classify_hc3_c_qid`'s v2 fallback. That fallback exists purely
# as defensive code (e.g. for direct unit-level calls to preflight helpers,
# as in `test_hc3_unknown_taxonomy_version_falls_back_to_v2` above) and is
# unreachable via the real evaluation_service entry points.
#
# CASE A applies (per the Phase F.6.1 task's decision tree) - no production
# code correction was made. These tests exist only to pin the CASE A
# determination itself, so a future querylib upgrade that loosens this
# validation would be caught by CI rather than silently reopening the gap.
_HANDOUT_DIR_ENV = "BENCHMARK_PHASE2_HANDOUT_DIR"


def _handout_dir():
    from pathlib import Path
    raw = os.environ.get(_HANDOUT_DIR_ENV)
    return Path(raw) if raw else None


def _minimal_spec_dict(taxonomy_version=...):
    """A hand-built spec valid under BOTH v2 and v3 (uses only the
    universally-valid `mean` query id) so these tests isolate
    taxonomy_version handling from any v2/v3 query-catalog differences."""
    d = {
        "dataset": {"name": "noaa", "id": "ID", "time": "DATE",
                    "measurements": ["PRCP", "TMAX", "TMIN"]},
        "groupby": {"keys": [{"attr": "LATITUDE", "bin_edges": [0, 40, 90]}],
                    "window": {"unit": "month"}, "agg": {"default": "avg"},
                    "fill": "interp", "min_len": 12},
        "focus": {"A": [{"group": "largest", "measurement": "TMAX"}], "B": [], "C": []},
        "queries": {"A": ["mean"], "B": [], "C": []},
    }
    if taxonomy_version is not ...:  # Ellipsis sentinel = omit the key entirely
        d["taxonomy_version"] = taxonomy_version
    return d


def _write_scratch_spec(tmp_path, taxonomy_version=...):
    spec_dict = _minimal_spec_dict(taxonomy_version)
    path = tmp_path / "scratch_spec.yaml"
    with open(path, "w") as f:
        yaml.safe_dump(spec_dict, f)
    return path


_needs_real_handout = pytest.mark.skipif(
    _handout_dir() is None,
    reason=f"{_HANDOUT_DIR_ENV} is not set - skipping real querylib taxonomy checks.",
)


@pytest.fixture
def handout_configured(monkeypatch):
    from app.core.config import settings
    original = settings.phase2_handout_dir
    monkeypatch.setattr(settings, "phase2_handout_dir", _handout_dir())
    yield
    monkeypatch.setattr(settings, "phase2_handout_dir", original)


@_needs_real_handout
def test_taxonomy_missing_key_follows_real_querylib_default(tmp_path, handout_configured):
    from app.services.evaluation2 import handout_adapter as adapter

    path = _write_scratch_spec(tmp_path, taxonomy_version=...)
    spec = adapter.load_spec(path)
    assert spec["taxonomy_version"] == "v2"


@_needs_real_handout
def test_taxonomy_explicit_v2_accepted_via_load_spec(tmp_path, handout_configured):
    from app.services.evaluation2 import handout_adapter as adapter

    path = _write_scratch_spec(tmp_path, taxonomy_version="v2")
    spec = adapter.load_spec(path)
    assert spec["taxonomy_version"] == "v2"


@_needs_real_handout
def test_taxonomy_explicit_v3_accepted_via_load_spec(tmp_path, handout_configured):
    from app.services.evaluation2 import handout_adapter as adapter

    path = _write_scratch_spec(tmp_path, taxonomy_version="v3")
    spec = adapter.load_spec(path)
    assert spec["taxonomy_version"] == "v3"


@_needs_real_handout
def test_taxonomy_explicit_unknown_version_rejected_before_reaching_hc3_classifier(
    tmp_path, handout_configured
):
    """The critical CASE A regression: an explicitly unsupported
    taxonomy_version ("v99") must be rejected by the SAME public path the
    backend uses (`handout_adapter.load_spec`) - i.e. by querylib's own
    `SpecError` - and must NEVER reach this backend's HC3 classifier, which
    would otherwise silently treat it as v2."""
    from app.services.evaluation2 import handout_adapter as adapter

    path = _write_scratch_spec(tmp_path, taxonomy_version="v99")
    with pytest.raises(Exception) as exc_info:
        adapter.load_spec(path)

    # `querylib` only lands on sys.path as a side effect of `load_handout()`
    # (triggered by the `adapter.load_spec` call above) - importing
    # `querylib.spec.SpecError` beforehand would fail. Import it now, after
    # the handout has been bootstrapped, purely to check the exception type.
    from querylib.spec import SpecError

    assert isinstance(exc_info.value, SpecError)
    assert "taxonomy_version" in str(exc_info.value)
    assert "v99" in str(exc_info.value)
    # Explicitly NOT a Phase2PreflightError: this rejection happens entirely
    # inside querylib's own spec validation, upstream of any backend-owned
    # preflight (HC1/HC2/HC3/HC4) ever running.
    assert not isinstance(exc_info.value, Phase2PreflightError)


@_needs_real_handout
@pytest.mark.parametrize("bad_version", ["v99", "", "V2", "v2.0", "v4"])
def test_taxonomy_various_unsupported_values_all_rejected(tmp_path, handout_configured, bad_version):
    from app.services.evaluation2 import handout_adapter as adapter

    path = _write_scratch_spec(tmp_path, taxonomy_version=bad_version)
    with pytest.raises(Exception) as exc_info:
        adapter.load_spec(path)
    from querylib.spec import SpecError
    assert isinstance(exc_info.value, SpecError)


def test_taxonomy_classifier_fallback_is_v2_for_none_or_unknown_string():
    # Unit-level pin of the EXISTING (unchanged) defensive fallback in
    # classify_hc3_c_qid - proven above to be unreachable from a real spec
    # via evaluation_service, but still correct in isolation for any direct
    # caller (e.g. future diagnostics code).
    assert classify_hc3_c_qid(SAFE_V2_QID, None) == "safe"
    assert classify_hc3_c_qid(SAFE_V2_QID, "v99") == "safe"
    assert classify_hc3_c_qid(RESTRICTED_V2_QID, "v99") == "restricted"
