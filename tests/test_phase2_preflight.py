"""Phase F.3 tests: backend-owned HC1/HC2 preflight
(app/services/evaluation2/preflight.py) and its structured-error
integration with JobExecutor / the status API.

HC1 and the "does not mutate spec" / "arbitrary schema names" tests need no
handout/querylib at all - hand-crafted spec dicts (same shape convention as
test_evaluation2_input_validator.py) are enough. HC2 tests monkeypatch
`handout_adapter.enumerate_instances` directly (a plain list stands in for
the DataFrame - only `len()` is used by preflight.py), so they too need no
real handout/querylib - the goal here is to test preflight.py's own logic
in isolation, not to re-verify handout_lib's behavior (that's the Phase F.2
audit's job).
"""
from __future__ import annotations

import copy
import json

import pytest

from app.services.evaluation2.preflight import (
    HC2_MAX_SUPPORTED_INSTANCES,
    Phase2PreflightError,
    run_backend_preflight,
    validate_backend_hc1,
    validate_hc2_instance_count,
)


# ============================================================================
#  spec fixtures (shape mirrors querylib/spec.py::validate, same convention
#  as test_evaluation2_input_validator.py)
# ============================================================================
def _single_view_spec(id_col="STATION_ID", time_col="DATE", groupby_attr="LATITUDE"):
    return {
        "taxonomy_version": "v3",
        "dataset": {"name": "noaa", "id": id_col, "time": time_col,
                    "measurements": ["PRCP", "TMAX", "TMIN"]},
        "groupby": {
            "keys": [{"attr": groupby_attr, "bin_edges": [0, 40, 90]}],
            "window": {"unit": "month"},
            "agg": {"default": "avg"},
            "fill": "interp",
            "min_len": 12,
        },
        "focus": {"A": [{"group": "largest", "measurement": "TMAX"}], "B": [], "C": []},
        "queries": {"A": ["mean"], "B": [], "C": []},
    }


def _multi_view_spec(id_col="STATION_ID", time_col="DATE", attrs=("LATITUDE", "ELEVATION")):
    dataset = {"name": "noaa", "id": id_col, "time": time_col,
               "measurements": ["PRCP", "TMAX", "TMIN"]}

    def _view(name, attr):
        return {
            "__name": name,
            "dataset": dict(dataset),
            "groupby": {
                "keys": [{"attr": attr, "bin_edges": [0, 40, 90]}],
                "window": {"unit": "month"},
                "agg": {"default": "avg"},
                "fill": "interp",
                "min_len": 12,
            },
            "focus": {"A": [], "B": [], "C": []},
            "queries": {"A": [], "B": [], "C": []},
        }

    return {
        "taxonomy_version": "v3",
        "dataset": dataset,
        "groupbys": [_view(f"view{i}", a) for i, a in enumerate(attrs)],
    }


# ============================================================================
#  HC1 - valid grouping
# ============================================================================
def test_hc1_valid_grouping_passes():
    spec = _single_view_spec(groupby_attr="LATITUDE")
    validate_backend_hc1(spec)  # no raise


# ============================================================================
#  HC1 - id/time rejection
# ============================================================================
def test_hc1_groupby_dataset_id_rejects():
    spec = _single_view_spec(id_col="STATION_ID", groupby_attr="STATION_ID")
    with pytest.raises(Phase2PreflightError) as exc_info:
        validate_backend_hc1(spec)
    err = exc_info.value
    assert err.code == "HC1_GROUPING_CONSTRAINT"
    assert err.details == {"attribute": "STATION_ID", "role": "dataset.id"}
    assert "STATION_ID" in err.message
    assert "dataset.id" in err.message


def test_hc1_groupby_dataset_time_rejects():
    spec = _single_view_spec(time_col="DATE", groupby_attr="DATE")
    with pytest.raises(Phase2PreflightError) as exc_info:
        validate_backend_hc1(spec)
    err = exc_info.value
    assert err.code == "HC1_GROUPING_CONSTRAINT"
    assert err.details == {"attribute": "DATE", "role": "dataset.time"}


# ============================================================================
#  HC1 - multi-view / groupbys path
# ============================================================================
def test_hc1_multi_view_valid_passes():
    spec = _multi_view_spec(attrs=("LATITUDE", "ELEVATION"))
    validate_backend_hc1(spec)  # no raise


def test_hc1_multi_view_rejects_when_any_view_groups_by_id():
    # second view groups by the dataset id column
    spec = _multi_view_spec(id_col="STATION_ID", attrs=("LATITUDE", "STATION_ID"))
    with pytest.raises(Phase2PreflightError) as exc_info:
        validate_backend_hc1(spec)
    assert exc_info.value.details["attribute"] == "STATION_ID"
    assert exc_info.value.details["role"] == "dataset.id"


def test_hc1_multi_view_duplicate_attr_reported_once():
    # LATITUDE (valid) repeated across two views must not raise or be
    # reported twice - only actual id/time violations matter.
    spec = _multi_view_spec(attrs=("LATITUDE", "LATITUDE"))
    validate_backend_hc1(spec)  # no raise


# ============================================================================
#  HC1 - arbitrary, non-NOAA schema names
# ============================================================================
def test_hc1_arbitrary_schema_names_valid_passes():
    spec = _single_view_spec(id_col="sensor_id", time_col="ts", groupby_attr="region")
    validate_backend_hc1(spec)  # no raise


def test_hc1_arbitrary_schema_names_id_rejects():
    spec = _single_view_spec(id_col="sensor_id", time_col="ts", groupby_attr="sensor_id")
    with pytest.raises(Phase2PreflightError) as exc_info:
        validate_backend_hc1(spec)
    assert exc_info.value.details == {"attribute": "sensor_id", "role": "dataset.id"}


# ============================================================================
#  HC1 - spec is never mutated
# ============================================================================
def test_hc1_does_not_mutate_spec_on_pass():
    spec = _single_view_spec()
    before = copy.deepcopy(spec)
    validate_backend_hc1(spec)
    assert spec == before


def test_hc1_does_not_mutate_spec_on_rejection():
    spec = _single_view_spec(groupby_attr="STATION_ID", id_col="STATION_ID")
    before = copy.deepcopy(spec)
    with pytest.raises(Phase2PreflightError):
        validate_backend_hc1(spec)
    assert spec == before


# ============================================================================
#  HC2 - static instance count precheck
# ============================================================================
class _FakeEnumerateResult(list):
    """Stands in for the DataFrame `handout_adapter.enumerate_instances`
    returns - only `len()` is used by preflight.py, so a plain list (of
    that length) is sufficient and keeps these tests handout/pandas-free."""


def _patch_enumerate(monkeypatch, count, *, capture=None):
    from app.services.evaluation2 import preflight

    def fake_enumerate_instances(spec, *args, **kwargs):
        if capture is not None:
            capture.append((args, kwargs))
        return _FakeEnumerateResult(range(count))

    monkeypatch.setattr(preflight.adapter, "enumerate_instances", fake_enumerate_instances)


def test_hc2_zero_count_passes(monkeypatch):
    _patch_enumerate(monkeypatch, 0)
    validate_hc2_instance_count({})  # no raise


def test_hc2_199_passes(monkeypatch):
    _patch_enumerate(monkeypatch, 199)
    validate_hc2_instance_count({})  # no raise


def test_hc2_200_rejects(monkeypatch):
    _patch_enumerate(monkeypatch, 200)
    with pytest.raises(Phase2PreflightError) as exc_info:
        validate_hc2_instance_count({})
    err = exc_info.value
    assert err.code == "INSTANCE_LIMIT_EXCEEDED"
    assert err.details == {
        "expected_instance_count": 200,
        "max_supported_instances": HC2_MAX_SUPPORTED_INSTANCES,
    }
    assert HC2_MAX_SUPPORTED_INSTANCES == 199


def test_hc2_201_rejects(monkeypatch):
    _patch_enumerate(monkeypatch, 201)
    with pytest.raises(Phase2PreflightError) as exc_info:
        validate_hc2_instance_count({})
    assert exc_info.value.details["expected_instance_count"] == 201


# ============================================================================
#  HC2 - enumerate_instances must be called WITHOUT real_df, and must be the
#  ONLY handout_adapter call made during this precheck (no query battery)
# ============================================================================
def test_hc2_calls_enumerate_instances_without_real_df(monkeypatch):
    calls = []
    _patch_enumerate(monkeypatch, 5, capture=calls)
    validate_hc2_instance_count({"dataset": {}})
    assert len(calls) == 1
    args, kwargs = calls[0]
    # Only `spec` was passed - no real_df positional or keyword argument.
    assert args == ()
    assert kwargs == {}


def test_hc2_preflight_never_invokes_run_real_or_run_pair(monkeypatch):
    from app.services.evaluation2 import preflight

    _patch_enumerate(monkeypatch, 5)

    def boom_run_real(*a, **k):
        raise AssertionError("HC2 preflight must never call run_real")

    def boom_run_pair(*a, **k):
        raise AssertionError("HC2 preflight must never call run_pair")

    monkeypatch.setattr(preflight.adapter, "run_real", boom_run_real)
    monkeypatch.setattr(preflight.adapter, "run_pair", boom_run_pair)

    validate_hc2_instance_count({"dataset": {}})  # must not raise AssertionError


# ============================================================================
#  combined entry point: HC1 runs before HC2, short-circuits on HC1 failure
# ============================================================================
def test_run_backend_preflight_hc1_failure_short_circuits_before_hc2(monkeypatch):
    from app.services.evaluation2 import preflight

    enumerate_calls = []

    def fake_enumerate_instances(spec, *args, **kwargs):
        enumerate_calls.append(1)
        return _FakeEnumerateResult(range(5))

    monkeypatch.setattr(preflight.adapter, "enumerate_instances", fake_enumerate_instances)

    spec = _single_view_spec(id_col="STATION_ID", groupby_attr="STATION_ID")
    with pytest.raises(Phase2PreflightError) as exc_info:
        run_backend_preflight(spec)
    assert exc_info.value.code == "HC1_GROUPING_CONSTRAINT"
    assert enumerate_calls == [], "HC2 (enumerate_instances) must not run after an HC1 failure"


def test_run_backend_preflight_passes_when_both_rules_satisfied(monkeypatch):
    _patch_enumerate(monkeypatch, 10)
    spec = _single_view_spec()
    run_backend_preflight(spec)  # no raise


def test_run_backend_preflight_hc2_failure_after_hc1_pass(monkeypatch):
    _patch_enumerate(monkeypatch, 200)
    spec = _single_view_spec()  # HC1-valid
    with pytest.raises(Phase2PreflightError) as exc_info:
        run_backend_preflight(spec)
    assert exc_info.value.code == "INSTANCE_LIMIT_EXCEEDED"


# ============================================================================
#  Phase2PreflightError structured representation
# ============================================================================
def test_phase2_preflight_error_to_dict_and_json_roundtrip():
    err = Phase2PreflightError(
        code="HC1_GROUPING_CONSTRAINT",
        message="HC1 violation: grouping attribute 'X' cannot use dataset.id",
        details={"attribute": "X", "role": "dataset.id"},
    )
    d = err.to_dict()
    assert d == {
        "code": "HC1_GROUPING_CONSTRAINT",
        "message": "HC1 violation: grouping attribute 'X' cannot use dataset.id",
        "details": {"attribute": "X", "role": "dataset.id"},
    }
    # str(err) / __str__ returns the same payload as deterministic JSON
    parsed = json.loads(str(err))
    assert parsed == d
    parsed_via_to_json = json.loads(err.to_json())
    assert parsed_via_to_json == d


# ============================================================================
#  Structured job-error persistence + status API surfacing (Part 12 item 13)
# ============================================================================
@pytest.fixture
def isolated_job_store(tmp_path, monkeypatch):
    from app.core.config import settings
    from app.database import job_store

    monkeypatch.setattr(settings, "job_db_path", tmp_path / "jobs.db")
    monkeypatch.setattr(settings, "storage_base_dir", tmp_path / "jobs")
    job_store.init_db()
    return job_store


def test_hc1_preflight_failure_surfaces_structured_error_via_job_status(
    isolated_job_store, monkeypatch
):
    from app.api.jobs import get_status
    from app.services.job.job_executor import JobExecutor
    from app.services.job.job_manager import JobManager

    job_id = JobManager.create_job(mode="real_only")
    JobManager.get_upload_dir(job_id).mkdir(parents=True, exist_ok=True)
    JobManager.get_real_csv(job_id).write_text("a,b\n1,2\n")
    JobManager.get_spec_path(job_id).write_text("dataset: {}\n")

    from app.services.evaluation2.preflight import Phase2PreflightError

    def boom_run_real_only(*a, **k):
        raise Phase2PreflightError(
            code="HC1_GROUPING_CONSTRAINT",
            message="HC1 violation: grouping attribute 'STATION_ID' cannot use dataset.id",
            details={"attribute": "STATION_ID", "role": "dataset.id"},
        )

    from app.services.job import job_executor

    monkeypatch.setattr(job_executor.evaluation_service, "run_real_only", boom_run_real_only)

    with pytest.raises(Phase2PreflightError):
        JobExecutor.run_real_only(job_id)

    record = isolated_job_store.get_job(job_id)
    assert record.status == isolated_job_store.STATUS_FAILED

    # The raw `error` string is valid JSON (structured), not the legacy
    # "ClassName: message" format.
    parsed = json.loads(record.error)
    assert parsed["code"] == "HC1_GROUPING_CONSTRAINT"
    assert parsed["details"] == {"attribute": "STATION_ID", "role": "dataset.id"}

    # The status API exposes the same structure via `error_details`, while
    # `error` remains the raw string (backward compatible for any existing
    # caller that only reads that field).
    status = get_status(job_id)
    assert status["error"] == record.error
    assert status["error_details"] == parsed


def test_legacy_error_string_leaves_error_details_none(isolated_job_store, monkeypatch):
    from app.api.jobs import get_status
    from app.services.job.job_executor import JobExecutor
    from app.services.job.job_manager import JobManager

    job_id = JobManager.create_job(mode="real_only")
    JobManager.get_upload_dir(job_id).mkdir(parents=True, exist_ok=True)
    JobManager.get_real_csv(job_id).write_text("a,b\n1,2\n")
    JobManager.get_spec_path(job_id).write_text("dataset: {}\n")

    from app.services.job import job_executor

    def boom(*a, **k):
        raise RuntimeError("some ordinary runtime failure")

    monkeypatch.setattr(job_executor.evaluation_service, "run_real_only", boom)

    with pytest.raises(RuntimeError):
        JobExecutor.run_real_only(job_id)

    record = isolated_job_store.get_job(job_id)
    assert record.error == "RuntimeError: some ordinary runtime failure"

    status = get_status(job_id)
    assert status["error"] == record.error
    assert status["error_details"] is None
