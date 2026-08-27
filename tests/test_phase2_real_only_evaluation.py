"""Phase D tests: mode="real_only" end-to-end through the existing Phase 1
job lifecycle (POST /evaluate -> BackgroundTasks -> JobExecutor -> Phase 2
evaluation_service -> handout_adapter -> querylib -> serialize/aggregate ->
outputs/result.json + outputs/curves.json -> DONE).

Every test uses an isolated, per-test SQLite file + job storage directory
(tmp_path + monkeypatched app.core.config.settings), exactly like the Phase C
tests. Route functions and JobExecutor methods are called directly (no ASGI
server / no httpx dependency), and background-task execution is simulated by
calling `JobExecutor.run_real_only` directly after `evaluate()` queues the
job - equivalent to what FastAPI's BackgroundTasks would do post-response,
without needing a running event loop/server.

Tests requiring the real bundled handout (end-to-end, invalid-dataset,
invalid-spec, JSON-strictness) are skipped, like every other Phase A/B/C
integration test, when BENCHMARK_PHASE2_HANDOUT_DIR is unset.
"""
from __future__ import annotations

import asyncio
import io
import json
import os
from pathlib import Path

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
    """Point Settings at the real bundled handout for this test."""
    from app.core.config import settings

    original = settings.phase2_handout_dir
    monkeypatch.setattr(settings, "phase2_handout_dir", _handout_dir())
    yield
    monkeypatch.setattr(settings, "phase2_handout_dir", original)


def _upload_file(filename: str, content: bytes) -> UploadFile:
    return UploadFile(io.BytesIO(content), filename=filename)


def _run(coro):
    return asyncio.run(coro)


def _create_real_only_job():
    from app.api.upload import CreateJobRequest, create_job
    response = create_job(body=CreateJobRequest(mode="real_only"))
    return response["job_id"]


# ============================================================================
#  22. real_only branch must never enter DuckDB/packet-flow execution
# ============================================================================
def test_real_only_never_touches_duckdb_or_packet_flow_pipeline(
    isolated_job_store, handout_configured, monkeypatch
):
    from app.services.job.job_executor import JobExecutor

    calls = {"get_connection": 0, "load_csv_to_table": 0}

    from app.database import db as db_module
    from app.services.ingestion.csv_loader import CSVLoader
    from app.services.evaluation.evaluation_controller import EvaluationController
    from app.services.evaluation.evaluation_controller_parallel import (
        ParallelEvaluationController,
    )

    def _boom_get_connection(*a, **k):
        calls["get_connection"] += 1
        raise AssertionError("real_only path must never call get_connection()")

    def _boom_load_csv_to_table(*a, **k):
        calls["load_csv_to_table"] += 1
        raise AssertionError("real_only path must never call CSVLoader.load_csv_to_table()")

    def _boom_run_all(*a, **k):
        raise AssertionError("real_only path must never call EvaluationController.run_all()")

    def _boom_parallel_run_all(*a, **k):
        raise AssertionError("real_only path must never call ParallelEvaluationController.run_all()")

    monkeypatch.setattr(db_module, "get_connection", _boom_get_connection)
    monkeypatch.setattr(CSVLoader, "load_csv_to_table", staticmethod(_boom_load_csv_to_table))
    monkeypatch.setattr(EvaluationController, "run_all", staticmethod(_boom_run_all))
    monkeypatch.setattr(ParallelEvaluationController, "run_all", staticmethod(_boom_parallel_run_all))

    job_id = _create_real_only_job()
    _upload_demo_real_and_spec(job_id)

    # If run_real_only touched any of the spied-on functions, they would
    # raise AssertionError, which JobExecutor's except-block would catch and
    # turn into STATUS_FAILED - so a DONE status here is itself proof the old
    # pipeline was never entered, in addition to the explicit call counts.
    JobExecutor.run_real_only(job_id)

    record = isolated_job_store.get_job(job_id)
    assert record.status == isolated_job_store.STATUS_DONE, record.error
    assert calls == {"get_connection": 0, "load_csv_to_table": 0}


def _upload_demo_real_and_spec(job_id, *, spec_bytes: bytes | None = None, real_bytes: bytes | None = None):
    from app.api.upload import upload_real, upload_spec

    handout_dir = _handout_dir()
    if real_bytes is None:
        real_bytes = (handout_dir / "examples" / "data" / "noaa_sample" / "data.csv").read_bytes()
    if spec_bytes is None:
        spec_bytes = (handout_dir / "specs" / "demo_small.yaml").read_bytes()

    _run(upload_real(job_id, _upload_file("real.csv", real_bytes)))
    _run(upload_spec(job_id, _upload_file("spec.yaml", spec_bytes)))


# ============================================================================
#  23. legacy Phase 1 (mode=None) dispatch still works
# ============================================================================
def test_legacy_mode_none_still_dispatches_to_existing_job_executor_run(
    isolated_job_store, monkeypatch
):
    """Prove /evaluate/{job_id} still routes a legacy job through
    JobExecutor.run (the unchanged Phase 1 sequential path) - without
    actually running the (expensive, DuckDB-dependent) Phase 1 pipeline."""
    from app.api.evaluate import evaluate
    from app.api.upload import create_job
    from app.services.job.job_executor import JobExecutor
    from app.services.job.job_manager import JobManager

    calls = []
    monkeypatch.setattr(JobExecutor, "run", staticmethod(lambda job_id: calls.append(("run", job_id))))
    monkeypatch.setattr(
        JobExecutor, "run_parallel", staticmethod(lambda job_id: calls.append(("run_parallel", job_id)))
    )
    monkeypatch.setattr(
        JobExecutor, "run_real_only", staticmethod(lambda job_id: calls.append(("run_real_only", job_id)))
    )

    response = create_job(body=None)  # legacy: no mode
    job_id = response["job_id"]

    # legacy readiness still requires both CSVs - satisfy it without touching
    # the executor itself.
    JobManager.get_upload_dir(job_id).mkdir(parents=True, exist_ok=True)
    JobManager.get_real_csv(job_id).write_text("a,b\n1,2\n")
    JobManager.get_synthetic_csv(job_id).write_text("a,b\n1,2\n")

    bg = BackgroundTasks()
    response = evaluate(job_id, bg)
    assert response["status"] == isolated_job_store.STATUS_QUEUED

    # simulate FastAPI actually running the queued background task
    _run(bg())

    assert calls == [("run", job_id)]


def test_evaluate_route_dispatches_real_only_to_run_real_only(isolated_job_store, monkeypatch):
    from app.api.evaluate import evaluate
    from app.services.job.job_executor import JobExecutor
    from app.services.job.job_manager import JobManager

    calls = []
    monkeypatch.setattr(
        JobExecutor, "run_real_only", staticmethod(lambda job_id: calls.append(("run_real_only", job_id)))
    )
    monkeypatch.setattr(JobExecutor, "run", staticmethod(lambda job_id: calls.append(("run", job_id))))

    job_id = _create_real_only_job()
    JobManager.get_upload_dir(job_id).mkdir(parents=True, exist_ok=True)
    JobManager.get_real_csv(job_id).write_text("a,b\n1,2\n")
    JobManager.get_spec_path(job_id).write_text("dataset: {}\n")

    bg = BackgroundTasks()
    evaluate(job_id, bg)
    _run(bg())

    assert calls == [("run_real_only", job_id)]


# ============================================================================
#  4. duplicate-run protection retained
# ============================================================================
def test_evaluate_rejects_already_queued_real_only_job(isolated_job_store):
    from app.api.evaluate import evaluate
    from app.services.job.job_manager import JobManager

    job_id = _create_real_only_job()
    JobManager.get_upload_dir(job_id).mkdir(parents=True, exist_ok=True)
    JobManager.get_real_csv(job_id).write_text("a,b\n1,2\n")
    JobManager.get_spec_path(job_id).write_text("dataset: {}\n")

    evaluate(job_id, BackgroundTasks())  # first call queues it
    with pytest.raises(HTTPException) as exc_info:
        evaluate(job_id, BackgroundTasks())  # second call must be rejected
    assert exc_info.value.status_code == 409


# ============================================================================
#  3. real-only readiness validation
# ============================================================================
def test_evaluate_real_only_requires_real_csv(isolated_job_store):
    from app.api.evaluate import evaluate
    from app.services.job.job_manager import JobManager

    job_id = _create_real_only_job()
    JobManager.get_upload_dir(job_id).mkdir(parents=True, exist_ok=True)
    JobManager.get_spec_path(job_id).write_text("dataset: {}\n")  # spec only

    with pytest.raises(HTTPException) as exc_info:
        evaluate(job_id, BackgroundTasks())
    assert exc_info.value.status_code == 400
    assert "Real CSV" in exc_info.value.detail


def test_evaluate_real_only_requires_spec(isolated_job_store):
    from app.api.evaluate import evaluate
    from app.services.job.job_manager import JobManager

    job_id = _create_real_only_job()
    JobManager.get_upload_dir(job_id).mkdir(parents=True, exist_ok=True)
    JobManager.get_real_csv(job_id).write_text("a,b\n1,2\n")  # real csv only

    with pytest.raises(HTTPException) as exc_info:
        evaluate(job_id, BackgroundTasks())
    assert exc_info.value.status_code == 400
    assert "Spec" in exc_info.value.detail


def test_evaluate_real_only_does_not_require_synthetic_csv(isolated_job_store):
    """Confirms real_only readiness never checks synthetic.csv at all."""
    from app.api.evaluate import evaluate
    from app.services.job.job_manager import JobManager

    job_id = _create_real_only_job()
    JobManager.get_upload_dir(job_id).mkdir(parents=True, exist_ok=True)
    JobManager.get_real_csv(job_id).write_text("a,b\n1,2\n")
    JobManager.get_spec_path(job_id).write_text("dataset: {}\n")
    assert not JobManager.get_synthetic_csv(job_id).exists()

    response = evaluate(job_id, BackgroundTasks())  # must not raise
    assert response["status"] == isolated_job_store.STATUS_QUEUED


# ============================================================================
#  15 / 2. real_synthetic dispatch; parallel endpoint rejected
#
#  As of Phase E, real_synthetic is implemented (see
#  test_phase2_real_synthetic_evaluation.py for full readiness/dispatch/
#  end-to-end coverage of this mode). This file keeps only a minimal dispatch
#  smoke test so Phase D's file continues to document that a real_synthetic
#  job dispatches through the same POST /evaluate/{job_id} endpoint used by
#  every other mode - it no longer asserts the Phase D-era temporary
#  rejection, which Phase E removed.
# ============================================================================
def test_evaluate_dispatches_real_synthetic_to_run_real_synthetic(
    isolated_job_store, monkeypatch
):
    from app.api.evaluate import evaluate
    from app.api.upload import CreateJobRequest, create_job
    from app.services.job.job_executor import JobExecutor
    from app.services.job.job_manager import JobManager

    calls = []
    monkeypatch.setattr(
        JobExecutor,
        "run_real_synthetic",
        staticmethod(lambda job_id: calls.append(("run_real_synthetic", job_id))),
    )

    response = create_job(body=CreateJobRequest(mode="real_synthetic"))
    job_id = response["job_id"]
    JobManager.get_upload_dir(job_id).mkdir(parents=True, exist_ok=True)
    JobManager.get_real_csv(job_id).write_text("a,b\n1,2\n")
    JobManager.get_synthetic_csv(job_id).write_text("a,b\n1,2\n")
    JobManager.get_spec_path(job_id).write_text("dataset: {}\n")

    bg = BackgroundTasks()
    response = evaluate(job_id, bg)
    assert response["status"] == isolated_job_store.STATUS_QUEUED
    _run(bg())
    assert calls == [("run_real_synthetic", job_id)]


def test_parallel_endpoint_rejects_real_only_job(isolated_job_store):
    from app.api.evaluate import evaluate_parallel
    from app.services.job.job_manager import JobManager

    job_id = _create_real_only_job()
    JobManager.get_upload_dir(job_id).mkdir(parents=True, exist_ok=True)
    JobManager.get_real_csv(job_id).write_text("a,b\n1,2\n")
    JobManager.get_spec_path(job_id).write_text("dataset: {}\n")

    with pytest.raises(HTTPException) as exc_info:
        evaluate_parallel(job_id, BackgroundTasks())
    assert exc_info.value.status_code == 400
    assert "Phase 1 only" in exc_info.value.detail


def test_parallel_endpoint_still_works_for_legacy_job(isolated_job_store, monkeypatch):
    from app.api.evaluate import evaluate_parallel
    from app.api.upload import create_job
    from app.services.job.job_executor import JobExecutor
    from app.services.job.job_manager import JobManager

    calls = []
    monkeypatch.setattr(
        JobExecutor, "run_parallel", staticmethod(lambda job_id: calls.append(job_id))
    )

    response = create_job(body=None)
    job_id = response["job_id"]
    JobManager.get_upload_dir(job_id).mkdir(parents=True, exist_ok=True)
    JobManager.get_real_csv(job_id).write_text("a,b\n1,2\n")
    JobManager.get_synthetic_csv(job_id).write_text("a,b\n1,2\n")

    bg = BackgroundTasks()
    response = evaluate_parallel(job_id, bg)
    assert response["status"] == isolated_job_store.STATUS_QUEUED
    _run(bg())
    assert calls == [job_id]


# ============================================================================
#  24. end-to-end real-only test (real bundled handout, skipped otherwise)
# ============================================================================
@pytest.mark.skipif(
    _handout_dir() is None,
    reason=f"{_HANDOUT_DIR_ENV} is not set - skipping end-to-end real-only evaluation.",
)
class TestRealOnlyEndToEnd:
    def test_full_lifecycle_produces_expected_result_and_curves(
        self, isolated_job_store, handout_configured
    ):
        from app.api.evaluate import evaluate
        from app.api.jobs import get_curves, get_result, get_status
        from app.services.job.job_executor import JobExecutor
        from app.services.job.job_manager import JobManager

        job_id = _create_real_only_job()
        _upload_demo_real_and_spec(job_id)

        bg = BackgroundTasks()
        response = evaluate(job_id, bg)
        assert response["status"] == "queued"

        # simulate FastAPI running the queued background task post-response
        JobExecutor.run_real_only(job_id)

        status_response = get_status(job_id)
        assert status_response["status"] == "done", status_response.get("error")
        assert status_response["mode"] == "real_only"

        result_response = get_result(job_id)
        result = json.loads(result_response.body)
        assert result["mode"] == "real_only"
        assert len(result["instances"]) == 25
        assert result["metadata"]["instance_count"] == 25
        assert "overview" in result
        assert result["overview"]["total_instances"] == 25

        curves_response = get_curves(job_id)
        curves = json.loads(curves_response.body)
        assert len(curves) == 540
        for row in curves[:3]:
            for col in ("view", "group", "measurement", "bin", "time_label", "real", "synth"):
                assert col in row
            assert row["synth"] is None  # real-only: no synthetic side

        # files actually exist on disk
        assert JobManager.get_result_path(job_id).exists()
        assert JobManager.get_curves_path(job_id).exists()


# ============================================================================
#  25. invalid dataset (missing required column) fails cleanly
# ============================================================================
@pytest.mark.skipif(
    _handout_dir() is None,
    reason=f"{_HANDOUT_DIR_ENV} is not set - skipping invalid-dataset test.",
)
def test_invalid_dataset_missing_column_fails_with_friendly_error(
    isolated_job_store, handout_configured
):
    import pandas as pd

    from app.api.evaluate import evaluate
    from app.services.job.job_executor import JobExecutor

    handout_dir = _handout_dir()
    real_df = pd.read_csv(handout_dir / "examples" / "data" / "noaa_sample" / "data.csv")
    assert "LATITUDE" in real_df.columns
    corrupted = real_df.drop(columns=["LATITUDE"])  # demo_small.yaml groups by LATITUDE

    job_id = _create_real_only_job()
    _upload_demo_real_and_spec(job_id, real_bytes=corrupted.to_csv(index=False).encode())

    bg = BackgroundTasks()
    response = evaluate(job_id, bg)
    assert response["status"] == "queued"  # route only checks artifact presence

    # run_real_only mirrors JobExecutor.run/run_parallel: it sets the job to
    # FAILED *and* re-raises, exactly like a real BackgroundTasks-driven
    # invocation would (Starlette logs, does not swallow, the exception).
    from app.services.evaluation2.input_validator import InputValidationError

    with pytest.raises(InputValidationError):
        JobExecutor.run_real_only(job_id)  # background job runs, must fail

    record = isolated_job_store.get_job(job_id)
    assert record.status == isolated_job_store.STATUS_FAILED
    assert "LATITUDE" in record.error
    assert "KeyError" not in record.error
    assert "InputValidationError" in record.error


# ============================================================================
#  26. invalid spec fails cleanly with querylib's own error message
# ============================================================================
@pytest.mark.skipif(
    _handout_dir() is None,
    reason=f"{_HANDOUT_DIR_ENV} is not set - skipping invalid-spec test.",
)
def test_invalid_spec_fails_with_spec_error_message(isolated_job_store, handout_configured):
    from app.api.evaluate import evaluate
    from app.services.job.job_executor import JobExecutor

    # missing dataset.measurements -> querylib.spec.SpecError,
    # "dataset.measurements is required and non-empty"
    malformed_spec = b"dataset:\n  id: ID\n  time: DATE\ngroupby:\n  keys: []\n"

    job_id = _create_real_only_job()
    _upload_demo_real_and_spec(job_id, spec_bytes=malformed_spec)

    # Deliberately not importing querylib.spec.SpecError here - this test
    # package must stay on the handout_lib boundary just like application
    # code; asserting on the persisted job error is enough.
    bg = BackgroundTasks()
    evaluate(job_id, bg)
    with pytest.raises(Exception):
        JobExecutor.run_real_only(job_id)

    record = isolated_job_store.get_job(job_id)
    assert record.status == isolated_job_store.STATUS_FAILED
    assert "measurements" in record.error.lower()


# ============================================================================
#  27. JSON strictness: persisted files parse and contain no NaN/Infinity tokens
# ============================================================================
@pytest.mark.skipif(
    _handout_dir() is None,
    reason=f"{_HANDOUT_DIR_ENV} is not set - skipping JSON strictness test.",
)
def test_persisted_result_and_curves_are_strict_json(isolated_job_store, handout_configured):
    from app.api.evaluate import evaluate
    from app.services.job.job_executor import JobExecutor
    from app.services.job.job_manager import JobManager

    job_id = _create_real_only_job()
    _upload_demo_real_and_spec(job_id)

    evaluate(job_id, BackgroundTasks())
    JobExecutor.run_real_only(job_id)

    result_text = JobManager.get_result_path(job_id).read_text(encoding="utf-8")
    curves_text = JobManager.get_curves_path(job_id).read_text(encoding="utf-8")

    for token in ("NaN", "Infinity", "-Infinity"):
        assert token not in result_text, f"{token!r} found in result.json"
        assert token not in curves_text, f"{token!r} found in curves.json"

    # both parse with the standard library's default (strict-enough) loader
    json.loads(result_text)
    json.loads(curves_text)
