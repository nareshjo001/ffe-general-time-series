"""Phase E tests: mode="real_synthetic" end-to-end through the existing
Phase 1 job lifecycle (POST /evaluate -> BackgroundTasks -> JobExecutor ->
Phase 2 evaluation_service.run_real_synthetic -> handout_adapter ->
querylib's self_check + run_pair + group_series -> serialize/aggregate ->
outputs/result.json + outputs/curves.json -> DONE).

Same isolation/test-calling conventions as test_phase2_real_only_evaluation.py:
per-test tmp_path job store/storage, route/executor functions called
directly (no ASGI server, no httpx), handout-dependent tests skipped when
BENCHMARK_PHASE2_HANDOUT_DIR is unset.
"""
from __future__ import annotations

import asyncio
import io
import json
import os
from pathlib import Path

import pandas as pd
import pytest
from fastapi import BackgroundTasks, HTTPException, UploadFile

_HANDOUT_DIR_ENV = "BENCHMARK_PHASE2_HANDOUT_DIR"


def _handout_dir() -> Path | None:
    raw = os.environ.get(_HANDOUT_DIR_ENV)
    return Path(raw) if raw else None


@pytest.fixture
def isolated_job_store(tmp_path, monkeypatch):
    from app.core.config import settings
    from app.database import job_store

    monkeypatch.setattr(settings, "job_db_path", tmp_path / "jobs.db")
    monkeypatch.setattr(settings, "storage_base_dir", tmp_path / "jobs")
    job_store.init_db()
    return job_store


@pytest.fixture
def handout_configured(monkeypatch):
    from app.core.config import settings

    original = settings.phase2_handout_dir
    monkeypatch.setattr(settings, "phase2_handout_dir", _handout_dir())
    yield
    monkeypatch.setattr(settings, "phase2_handout_dir", original)


def _upload_file(filename: str, content: bytes) -> UploadFile:
    return UploadFile(io.BytesIO(content), filename=filename)


def _run(coro):
    return asyncio.run(coro)


def _create_real_synthetic_job():
    from app.api.upload import CreateJobRequest, create_job
    response = create_job(body=CreateJobRequest(mode="real_synthetic"))
    return response["job_id"]


def _upload_demo_real_synthetic_and_spec(
    job_id,
    *,
    spec_bytes: bytes | None = None,
    real_bytes: bytes | None = None,
    synth_bytes: bytes | None = None,
):
    from app.api.upload import upload_real, upload_spec, upload_synthetic

    handout_dir = _handout_dir()
    if real_bytes is None:
        real_bytes = (handout_dir / "examples" / "data" / "noaa_sample" / "data.csv").read_bytes()
    if synth_bytes is None:
        synth_bytes = (handout_dir / "examples" / "data" / "synthetic_wavestitch_sample.csv").read_bytes()
    if spec_bytes is None:
        spec_bytes = (handout_dir / "specs" / "demo_small.yaml").read_bytes()

    _run(upload_real(job_id, _upload_file("real.csv", real_bytes)))
    _run(upload_synthetic(job_id, _upload_file("synthetic.csv", synth_bytes)))
    _run(upload_spec(job_id, _upload_file("spec.yaml", spec_bytes)))


# ============================================================================
#  4. real+synthetic readiness validation
# ============================================================================
def test_evaluate_real_synthetic_requires_real_csv(isolated_job_store):
    from app.api.evaluate import evaluate
    from app.services.job.job_manager import JobManager

    job_id = _create_real_synthetic_job()
    JobManager.get_upload_dir(job_id).mkdir(parents=True, exist_ok=True)
    JobManager.get_synthetic_csv(job_id).write_text("a,b\n1,2\n")
    JobManager.get_spec_path(job_id).write_text("dataset: {}\n")

    with pytest.raises(HTTPException) as exc_info:
        evaluate(job_id, BackgroundTasks())
    assert exc_info.value.status_code == 400
    assert "Real CSV" in exc_info.value.detail


def test_evaluate_real_synthetic_requires_synthetic_csv(isolated_job_store):
    """25. Missing synthetic -> synchronous failure before queueing."""
    from app.api.evaluate import evaluate
    from app.database import job_store as js
    from app.services.job.job_manager import JobManager

    job_id = _create_real_synthetic_job()
    JobManager.get_upload_dir(job_id).mkdir(parents=True, exist_ok=True)
    JobManager.get_real_csv(job_id).write_text("a,b\n1,2\n")
    JobManager.get_spec_path(job_id).write_text("dataset: {}\n")

    with pytest.raises(HTTPException) as exc_info:
        evaluate(job_id, BackgroundTasks())
    assert exc_info.value.status_code == 400
    assert "Synthetic CSV" in exc_info.value.detail

    record = js.get_job(job_id)
    assert record.status != js.STATUS_QUEUED


def test_evaluate_real_synthetic_requires_spec(isolated_job_store):
    from app.api.evaluate import evaluate
    from app.services.job.job_manager import JobManager

    job_id = _create_real_synthetic_job()
    JobManager.get_upload_dir(job_id).mkdir(parents=True, exist_ok=True)
    JobManager.get_real_csv(job_id).write_text("a,b\n1,2\n")
    JobManager.get_synthetic_csv(job_id).write_text("a,b\n1,2\n")

    with pytest.raises(HTTPException) as exc_info:
        evaluate(job_id, BackgroundTasks())
    assert exc_info.value.status_code == 400
    assert "Spec" in exc_info.value.detail


def test_evaluate_real_synthetic_dispatches_to_run_real_synthetic(
    isolated_job_store, monkeypatch
):
    from app.api.evaluate import evaluate
    from app.services.job.job_executor import JobExecutor
    from app.services.job.job_manager import JobManager

    calls = []
    monkeypatch.setattr(
        JobExecutor,
        "run_real_synthetic",
        staticmethod(lambda job_id: calls.append(("run_real_synthetic", job_id))),
    )
    monkeypatch.setattr(
        JobExecutor, "run_real_only", staticmethod(lambda job_id: calls.append(("run_real_only", job_id)))
    )

    job_id = _create_real_synthetic_job()
    JobManager.get_upload_dir(job_id).mkdir(parents=True, exist_ok=True)
    JobManager.get_real_csv(job_id).write_text("a,b\n1,2\n")
    JobManager.get_synthetic_csv(job_id).write_text("a,b\n1,2\n")
    JobManager.get_spec_path(job_id).write_text("dataset: {}\n")

    bg = BackgroundTasks()
    evaluate(job_id, bg)
    _run(bg())

    assert calls == [("run_real_synthetic", job_id)]


def test_evaluate_rejects_already_queued_real_synthetic_job(isolated_job_store):
    from app.api.evaluate import evaluate
    from app.services.job.job_manager import JobManager

    job_id = _create_real_synthetic_job()
    JobManager.get_upload_dir(job_id).mkdir(parents=True, exist_ok=True)
    JobManager.get_real_csv(job_id).write_text("a,b\n1,2\n")
    JobManager.get_synthetic_csv(job_id).write_text("a,b\n1,2\n")
    JobManager.get_spec_path(job_id).write_text("dataset: {}\n")

    evaluate(job_id, BackgroundTasks())
    with pytest.raises(HTTPException) as exc_info:
        evaluate(job_id, BackgroundTasks())
    assert exc_info.value.status_code == 409


# ============================================================================
#  3. parallel endpoint rejects real_synthetic
# ============================================================================
def test_parallel_endpoint_rejects_real_synthetic_job(isolated_job_store):
    from app.api.evaluate import evaluate_parallel
    from app.services.job.job_manager import JobManager

    job_id = _create_real_synthetic_job()
    JobManager.get_upload_dir(job_id).mkdir(parents=True, exist_ok=True)
    JobManager.get_real_csv(job_id).write_text("a,b\n1,2\n")
    JobManager.get_synthetic_csv(job_id).write_text("a,b\n1,2\n")
    JobManager.get_spec_path(job_id).write_text("dataset: {}\n")

    with pytest.raises(HTTPException) as exc_info:
        evaluate_parallel(job_id, BackgroundTasks())
    assert exc_info.value.status_code == 400
    assert "Phase 1 only" in exc_info.value.detail


# ============================================================================
#  26 / 27 / 28. regression: real_only, legacy, DuckDB isolation
# ============================================================================
@pytest.mark.skipif(_handout_dir() is None, reason=f"{_HANDOUT_DIR_ENV} is not set")
def test_real_only_still_calls_run_real_and_never_run_pair(
    isolated_job_store, handout_configured, monkeypatch
):
    """26. real_only must still invoke run_real, never run_pair."""
    from app.services.evaluation2 import handout_adapter as adapter
    from app.services.job.job_executor import JobExecutor

    calls = []
    orig_run_real = adapter.run_real
    orig_group_series = adapter.group_series

    def spy_run_real(*a, **k):
        calls.append("run_real")
        return orig_run_real(*a, **k)

    def spy_group_series(*a, **k):
        calls.append("group_series")
        return orig_group_series(*a, **k)

    def boom_run_pair(*a, **k):
        raise AssertionError("real_only must never call run_pair")

    monkeypatch.setattr(adapter, "run_real", spy_run_real)
    monkeypatch.setattr(adapter, "group_series", spy_group_series)
    monkeypatch.setattr(adapter, "run_pair", boom_run_pair)
    # evaluation_service imported adapter functions by module reference
    # (`handout_adapter as adapter`), so patching the module attribute above
    # is visible to evaluation_service.run_real_only as well.

    from app.api.upload import CreateJobRequest, create_job
    from app.services.job.job_manager import JobManager

    response = create_job(body=CreateJobRequest(mode="real_only"))
    job_id = response["job_id"]
    handout_dir = _handout_dir()
    real_bytes = (handout_dir / "examples" / "data" / "noaa_sample" / "data.csv").read_bytes()
    spec_bytes = (handout_dir / "specs" / "demo_small.yaml").read_bytes()
    JobManager.get_upload_dir(job_id).mkdir(parents=True, exist_ok=True)
    JobManager.get_real_csv(job_id).write_bytes(real_bytes)
    JobManager.get_spec_path(job_id).write_bytes(spec_bytes)

    JobExecutor.run_real_only(job_id)

    record = isolated_job_store.get_job(job_id)
    assert record.status == isolated_job_store.STATUS_DONE, record.error
    assert "run_real" in calls
    assert "group_series" in calls


def test_legacy_mode_none_still_dispatches_to_run(isolated_job_store, monkeypatch):
    """27. Legacy Phase 1 dispatch must be unaffected by Phase E."""
    from app.api.evaluate import evaluate
    from app.api.upload import create_job
    from app.services.job.job_executor import JobExecutor
    from app.services.job.job_manager import JobManager

    calls = []
    monkeypatch.setattr(JobExecutor, "run", staticmethod(lambda job_id: calls.append(job_id)))

    response = create_job(body=None)
    job_id = response["job_id"]
    JobManager.get_upload_dir(job_id).mkdir(parents=True, exist_ok=True)
    JobManager.get_real_csv(job_id).write_text("a,b\n1,2\n")
    JobManager.get_synthetic_csv(job_id).write_text("a,b\n1,2\n")

    bg = BackgroundTasks()
    evaluate(job_id, bg)
    _run(bg())

    assert calls == [job_id]


def test_real_synthetic_never_touches_duckdb_or_packet_flow_pipeline(
    isolated_job_store, handout_configured, monkeypatch
):
    """28. Comparison engine must be handout_lib/querylib only."""
    from app.database import db as db_module
    from app.services.evaluation.evaluation_controller import EvaluationController
    from app.services.evaluation.evaluation_controller_parallel import (
        ParallelEvaluationController,
    )
    from app.services.ingestion.csv_loader import CSVLoader
    from app.services.job.job_executor import JobExecutor

    calls = {"get_connection": 0, "load_csv_to_table": 0}

    def _boom_get_connection(*a, **k):
        calls["get_connection"] += 1
        raise AssertionError("real_synthetic path must never call get_connection()")

    def _boom_load_csv_to_table(*a, **k):
        calls["load_csv_to_table"] += 1
        raise AssertionError("real_synthetic path must never call CSVLoader.load_csv_to_table()")

    def _boom_run_all(*a, **k):
        raise AssertionError("real_synthetic path must never call EvaluationController.run_all()")

    def _boom_parallel_run_all(*a, **k):
        raise AssertionError("real_synthetic path must never call ParallelEvaluationController.run_all()")

    monkeypatch.setattr(db_module, "get_connection", _boom_get_connection)
    monkeypatch.setattr(CSVLoader, "load_csv_to_table", staticmethod(_boom_load_csv_to_table))
    monkeypatch.setattr(EvaluationController, "run_all", staticmethod(_boom_run_all))
    monkeypatch.setattr(ParallelEvaluationController, "run_all", staticmethod(_boom_parallel_run_all))

    job_id = _create_real_synthetic_job()
    _upload_demo_real_synthetic_and_spec(job_id)

    JobExecutor.run_real_synthetic(job_id)

    record = isolated_job_store.get_job(job_id)
    assert record.status == isolated_job_store.STATUS_DONE, record.error
    assert calls == {"get_connection": 0, "load_csv_to_table": 0}


# ============================================================================
#  21. end-to-end comparison test (real bundled handout, skipped otherwise)
# ============================================================================
@pytest.mark.skipif(
    _handout_dir() is None,
    reason=f"{_HANDOUT_DIR_ENV} is not set - skipping end-to-end real+synthetic evaluation.",
)
class TestRealSyntheticEndToEnd:
    def test_full_lifecycle_produces_expected_result_and_curves(
        self, isolated_job_store, handout_configured
    ):
        from app.api.evaluate import evaluate
        from app.api.jobs import get_curves, get_result, get_status
        from app.services.job.job_executor import JobExecutor
        from app.services.job.job_manager import JobManager

        job_id = _create_real_synthetic_job()
        _upload_demo_real_synthetic_and_spec(job_id)

        bg = BackgroundTasks()
        response = evaluate(job_id, bg)
        assert response["status"] == "queued"

        JobExecutor.run_real_synthetic(job_id)  # simulate BackgroundTasks execution

        status_response = get_status(job_id)
        assert status_response["status"] == "done", status_response.get("error")
        assert status_response["mode"] == "real_synthetic"

        result_response = get_result(job_id)
        result = json.loads(result_response.body)
        assert result["mode"] == "real_synthetic"
        assert len(result["instances"]) == 25
        assert result["metadata"]["instance_count"] == 25

        # Phase F.3: self_check no longer runs automatically in production -
        # the field is present (contract-preserving) but always None/not-run,
        # never a fabricated "passed" value for a check that never executed.
        assert result["self_check"] is None

        for inst in result["instances"]:
            distance = inst["distance"]
            assert distance is None or 0.0 <= distance <= 1.0

        assert "overview" in result
        assert "grid" in result["overview"]
        assert "worst_instances" in result["overview"]
        assert len(result["overview"]["worst_instances"]) <= 5

        curves_response = get_curves(job_id)
        curves = json.loads(curves_response.body)
        assert len(curves) == 540
        for row in curves[:3]:
            for col in ("view", "group", "measurement", "bin", "time_label", "real", "synth"):
                assert col in row

        assert JobManager.get_result_path(job_id).exists()
        assert JobManager.get_curves_path(job_id).exists()

        # strict JSON persistence, no NaN/Infinity tokens
        result_text = JobManager.get_result_path(job_id).read_text(encoding="utf-8")
        curves_text = JobManager.get_curves_path(job_id).read_text(encoding="utf-8")
        for token in ("NaN", "Infinity", "-Infinity"):
            assert token not in result_text
            assert token not in curves_text


# ============================================================================
#  22. dtype corruption integration test
# ============================================================================
@pytest.mark.skipif(
    _handout_dir() is None,
    reason=f"{_HANDOUT_DIR_ENV} is not set - skipping dtype-corruption test.",
)
def test_synthetic_latitude_dtype_corruption_fails_before_run_pair(
    isolated_job_store, handout_configured, monkeypatch
):
    from app.services.evaluation2 import handout_adapter as adapter
    from app.services.job.job_executor import JobExecutor

    handout_dir = _handout_dir()
    synth_df = pd.read_csv(handout_dir / "examples" / "data" / "synthetic_wavestitch_sample.csv")
    assert pd.api.types.is_numeric_dtype(synth_df["LATITUDE"])
    corrupted_synth = synth_df.copy()
    # A plain str(53.3639) round-trips through CSV -> pd.read_csv and gets
    # re-inferred as float64 again, silently "fixing" the corruption before
    # it ever reaches the validator. Prefix with a non-numeric character so
    # the object/string dtype actually survives the CSV round-trip - this is
    # what a genuine upstream dtype corruption (e.g. a categorical encoder
    # applied to a numeric column) would produce.
    corrupted_synth["LATITUDE"] = "lat_" + corrupted_synth["LATITUDE"].astype(str)

    run_pair_calls = []
    orig_run_pair = adapter.run_pair

    def spy_run_pair(*a, **k):
        run_pair_calls.append(1)
        return orig_run_pair(*a, **k)

    monkeypatch.setattr(adapter, "run_pair", spy_run_pair)

    job_id = _create_real_synthetic_job()
    _upload_demo_real_synthetic_and_spec(
        job_id, synth_bytes=corrupted_synth.to_csv(index=False).encode()
    )

    from app.api.evaluate import evaluate

    response = evaluate(job_id, BackgroundTasks())
    assert response["status"] == "queued"

    with pytest.raises(Exception):
        JobExecutor.run_real_synthetic(job_id)

    record = isolated_job_store.get_job(job_id)
    assert record.status == isolated_job_store.STATUS_FAILED
    assert "LATITUDE" in record.error
    assert "real=numeric" in record.error
    assert "synthetic=string/object" in record.error
    assert "KeyError" not in record.error
    assert run_pair_calls == []  # run_pair must never have been invoked


# ============================================================================
#  23. different entity population test
# ============================================================================
@pytest.mark.skipif(
    _handout_dir() is None,
    reason=f"{_HANDOUT_DIR_ENV} is not set - skipping different-entity-population test.",
)
def test_different_entity_ids_and_row_counts_are_valid(isolated_job_store, handout_configured):
    """Validation (and the actual comparison) must permit real/synthetic
    datasets with completely different entity IDs and row counts - querylib
    aligns at the group-label + time-bin level, not the entity level."""
    from app.services.evaluation2 import evaluation_service
    from app.services.job.job_manager import JobManager

    handout_dir = _handout_dir()
    real_df = pd.read_csv(handout_dir / "examples" / "data" / "noaa_sample" / "data.csv")
    synth_df = pd.read_csv(handout_dir / "examples" / "data" / "synthetic_wavestitch_sample.csv")

    # Keep only half the synthetic stations (different IDs, different row
    # count, but same columns/dtypes) - a strictly smaller, different entity
    # population than the real side.
    synth_ids = sorted(synth_df["ID"].unique())
    real_ids = sorted(real_df["ID"].unique())
    assert set(synth_ids) == set(real_ids), "bundled sample is expected to share IDs by default"
    keep_ids = synth_ids[: len(synth_ids) // 2]
    reduced_synth = synth_df[synth_df["ID"].isin(keep_ids)].reset_index(drop=True)

    assert set(reduced_synth["ID"].unique()) != set(real_df["ID"].unique())
    assert len(reduced_synth) != len(real_df)

    job_id = _create_real_synthetic_job()
    _upload_demo_real_synthetic_and_spec(
        job_id, synth_bytes=reduced_synth.to_csv(index=False).encode()
    )

    from app.services.job.job_executor import JobExecutor

    JobExecutor.run_real_synthetic(job_id)

    record = isolated_job_store.get_job(job_id)
    assert record.status == isolated_job_store.STATUS_DONE, record.error

    result = json.loads(JobManager.get_result_path(job_id).read_text(encoding="utf-8"))
    assert result["metadata"]["instance_count"] > 0


# ============================================================================
#  Phase F.3: production real_synthetic evaluation must NOT call self_check
# ============================================================================
@pytest.mark.skipif(_handout_dir() is None, reason=f"{_HANDOUT_DIR_ENV} is not set")
def test_production_real_synthetic_never_calls_self_check(
    isolated_job_store, handout_configured, monkeypatch
):
    """14/15. self_check must not run automatically in production; run_pair
    must still execute normally on a valid comparison. Uses a spy that
    raises if self_check is invoked at all, rather than merely asserting a
    call-count afterward, so a regression fails loudly and immediately."""
    from app.services.evaluation2 import handout_adapter as adapter
    from app.services.job.job_executor import JobExecutor
    from app.services.job.job_manager import JobManager

    def boom_self_check(*a, **k):
        raise AssertionError(
            "production run_real_synthetic must never call adapter.self_check"
        )

    run_pair_calls = []
    orig_run_pair = adapter.run_pair

    def spy_run_pair(*a, **k):
        run_pair_calls.append(1)
        return orig_run_pair(*a, **k)

    monkeypatch.setattr(adapter, "self_check", boom_self_check)
    monkeypatch.setattr(adapter, "run_pair", spy_run_pair)

    job_id = _create_real_synthetic_job()
    _upload_demo_real_synthetic_and_spec(job_id)

    JobExecutor.run_real_synthetic(job_id)  # must not raise

    record = isolated_job_store.get_job(job_id)
    assert record.status == isolated_job_store.STATUS_DONE, record.error
    assert run_pair_calls == [1]

    result = json.loads(JobManager.get_result_path(job_id).read_text(encoding="utf-8"))
    # 16. self_check is null/not-run in the persisted result contract.
    assert result["self_check"] is None


def test_handout_adapter_self_check_remains_directly_callable(handout_configured):
    """17. handout_adapter.self_check itself is completely untouched and
    remains callable for tests/diagnostics/manual validation, even though
    production evaluation_service.run_real_synthetic no longer calls it."""
    if _handout_dir() is None:
        pytest.skip(f"{_HANDOUT_DIR_ENV} is not set")

    from app.services.evaluation2 import handout_adapter as adapter

    handout_dir = _handout_dir()
    spec = adapter.load_spec(handout_dir / "specs" / "demo_small.yaml")
    real_df, _cfg = adapter.load_panel(handout_dir / "examples" / "data" / "noaa_sample")

    score = adapter.self_check(spec, real_df)
    assert isinstance(score, float)
    assert abs(score) <= 1e-9
