"""Phase F.4 tests: single-process startup reconciliation
(`job_store.reconcile_interrupted_jobs`), the cleanup-policy change that
excludes QUEUED/RUNNING from the abandoned-job branch
(`job_store.find_cleanup_candidates`), and the app lifespan's startup
ordering (`app/main.py`).

Same isolation convention as the rest of the Phase 2 test suite: a
per-test tmp_path SQLite DB/storage dir via the `isolated_job_store`
fixture, no ASGI server needed for the job-store/cleanup tests. The
lifespan-ordering test drives `app.main.lifespan` directly as an async
context manager with every side-effecting dependency monkeypatched, so it
never starts a real APScheduler or touches real logging config.
"""
from __future__ import annotations

import asyncio
import json
import time

import pytest


@pytest.fixture
def isolated_job_store(tmp_path, monkeypatch):
    from app.core.config import settings
    from app.database import job_store

    monkeypatch.setattr(settings, "job_db_path", tmp_path / "jobs.db")
    monkeypatch.setattr(settings, "storage_base_dir", tmp_path / "jobs")
    job_store.init_db()
    return job_store


def _make_job(job_store_module, status, *, mode="real_only", error=None):
    job_id = job_store_module.create_job(mode=mode)
    if status != job_store_module.STATUS_CREATED:
        job_store_module.set_status(job_id, status, error=error)
    return job_id


# ============================================================================
#  1/2. RUNNING and QUEUED become FAILED
# ============================================================================
def test_running_job_becomes_failed(isolated_job_store):
    job_id = _make_job(isolated_job_store, isolated_job_store.STATUS_RUNNING)

    counts = isolated_job_store.reconcile_interrupted_jobs()

    record = isolated_job_store.get_job(job_id)
    assert record.status == isolated_job_store.STATUS_FAILED
    assert counts == {"queued_recovered": 0, "running_recovered": 1}


def test_queued_job_becomes_failed(isolated_job_store):
    job_id = _make_job(isolated_job_store, isolated_job_store.STATUS_QUEUED)

    counts = isolated_job_store.reconcile_interrupted_jobs()

    record = isolated_job_store.get_job(job_id)
    assert record.status == isolated_job_store.STATUS_FAILED
    assert counts == {"queued_recovered": 1, "running_recovered": 0}


# ============================================================================
#  3/4. structured interruption errors - stable code/details
# ============================================================================
def test_running_interruption_error_is_structured(isolated_job_store):
    job_id = _make_job(isolated_job_store, isolated_job_store.STATUS_RUNNING)
    isolated_job_store.reconcile_interrupted_jobs()

    record = isolated_job_store.get_job(job_id)
    parsed = json.loads(record.error)
    assert parsed == {
        "code": "JOB_INTERRUPTED",
        "message": "Evaluation was interrupted by a backend restart.",
        "details": {"previous_status": "running"},
    }


def test_queued_interruption_error_is_structured(isolated_job_store):
    job_id = _make_job(isolated_job_store, isolated_job_store.STATUS_QUEUED)
    isolated_job_store.reconcile_interrupted_jobs()

    record = isolated_job_store.get_job(job_id)
    parsed = json.loads(record.error)
    assert parsed == {
        "code": "QUEUED_JOB_INTERRUPTED",
        "message": "Queued evaluation was interrupted before execution by a backend restart.",
        "details": {"previous_status": "queued"},
    }


# ============================================================================
#  5/6/7/8. transition field semantics
# ============================================================================
def test_completed_at_set_on_recovery(isolated_job_store):
    job_id = _make_job(isolated_job_store, isolated_job_store.STATUS_RUNNING)
    before = isolated_job_store.get_job(job_id)
    assert before.completed_at is None

    isolated_job_store.reconcile_interrupted_jobs()

    after = isolated_job_store.get_job(job_id)
    assert after.completed_at is not None


def test_updated_at_advances_on_recovery(isolated_job_store):
    job_id = _make_job(isolated_job_store, isolated_job_store.STATUS_RUNNING)
    before = isolated_job_store.get_job(job_id)

    time.sleep(0.01)
    isolated_job_store.reconcile_interrupted_jobs()

    after = isolated_job_store.get_job(job_id)
    assert after.updated_at > before.updated_at


def test_created_at_preserved_on_recovery(isolated_job_store):
    job_id = _make_job(isolated_job_store, isolated_job_store.STATUS_QUEUED)
    before = isolated_job_store.get_job(job_id)

    isolated_job_store.reconcile_interrupted_jobs()

    after = isolated_job_store.get_job(job_id)
    assert after.created_at == before.created_at
    assert after.job_id == job_id


def test_mode_preserved_on_recovery(isolated_job_store):
    job_id = _make_job(isolated_job_store, isolated_job_store.STATUS_RUNNING, mode="real_synthetic")

    isolated_job_store.reconcile_interrupted_jobs()

    after = isolated_job_store.get_job(job_id)
    assert after.mode == "real_synthetic"


# ============================================================================
#  9/10/11/12. untouched statuses
# ============================================================================
def test_created_job_untouched(isolated_job_store):
    job_id = _make_job(isolated_job_store, isolated_job_store.STATUS_CREATED)
    before = isolated_job_store.get_job(job_id)

    counts = isolated_job_store.reconcile_interrupted_jobs()

    after = isolated_job_store.get_job(job_id)
    assert after.status == isolated_job_store.STATUS_CREATED
    assert after.error == before.error
    assert after.completed_at == before.completed_at
    assert counts == {"queued_recovered": 0, "running_recovered": 0}


def test_uploading_job_untouched(isolated_job_store):
    job_id = _make_job(isolated_job_store, isolated_job_store.STATUS_UPLOADING)
    before = isolated_job_store.get_job(job_id)

    isolated_job_store.reconcile_interrupted_jobs()

    after = isolated_job_store.get_job(job_id)
    assert after.status == isolated_job_store.STATUS_UPLOADING
    assert after.error == before.error
    assert after.completed_at == before.completed_at


def test_done_job_untouched(isolated_job_store):
    job_id = _make_job(isolated_job_store, isolated_job_store.STATUS_DONE)
    before = isolated_job_store.get_job(job_id)

    isolated_job_store.reconcile_interrupted_jobs()

    after = isolated_job_store.get_job(job_id)
    assert after.status == isolated_job_store.STATUS_DONE
    assert after.error == before.error
    assert after.completed_at == before.completed_at
    assert after.updated_at == before.updated_at


def test_existing_failed_job_untouched(isolated_job_store):
    job_id = _make_job(
        isolated_job_store, isolated_job_store.STATUS_FAILED, error="RuntimeError: something else"
    )
    before = isolated_job_store.get_job(job_id)

    isolated_job_store.reconcile_interrupted_jobs()

    after = isolated_job_store.get_job(job_id)
    assert after.status == isolated_job_store.STATUS_FAILED
    assert after.error == "RuntimeError: something else"
    assert after.error == before.error
    assert after.completed_at == before.completed_at
    assert after.updated_at == before.updated_at


# ============================================================================
#  13. idempotence
# ============================================================================
def test_reconciliation_is_idempotent(isolated_job_store):
    running_id = _make_job(isolated_job_store, isolated_job_store.STATUS_RUNNING)
    queued_id = _make_job(isolated_job_store, isolated_job_store.STATUS_QUEUED)

    first_counts = isolated_job_store.reconcile_interrupted_jobs()
    assert first_counts == {"queued_recovered": 1, "running_recovered": 1}

    running_after_first = isolated_job_store.get_job(running_id)
    queued_after_first = isolated_job_store.get_job(queued_id)

    time.sleep(0.01)
    second_counts = isolated_job_store.reconcile_interrupted_jobs()
    assert second_counts == {"queued_recovered": 0, "running_recovered": 0}

    running_after_second = isolated_job_store.get_job(running_id)
    queued_after_second = isolated_job_store.get_job(queued_id)

    # Already-terminal (FAILED) jobs must not be touched again - same
    # status, same original interruption error, same completed/updated_at.
    assert running_after_second.status == isolated_job_store.STATUS_FAILED
    assert running_after_second.error == running_after_first.error
    assert running_after_second.completed_at == running_after_first.completed_at
    assert running_after_second.updated_at == running_after_first.updated_at

    assert queued_after_second.status == isolated_job_store.STATUS_FAILED
    assert queued_after_second.error == queued_after_first.error
    assert queued_after_second.completed_at == queued_after_first.completed_at
    assert queued_after_second.updated_at == queued_after_first.updated_at


# ============================================================================
#  14. counts returned correctly for a mix of jobs
# ============================================================================
def test_reconciliation_returns_correct_mixed_counts(isolated_job_store):
    for _ in range(2):
        _make_job(isolated_job_store, isolated_job_store.STATUS_QUEUED)
    for _ in range(3):
        _make_job(isolated_job_store, isolated_job_store.STATUS_RUNNING)
    _make_job(isolated_job_store, isolated_job_store.STATUS_CREATED)
    _make_job(isolated_job_store, isolated_job_store.STATUS_DONE)

    counts = isolated_job_store.reconcile_interrupted_jobs()
    assert counts == {"queued_recovered": 2, "running_recovered": 3}


# ============================================================================
#  Part 15 - status API surfaces the structured interruption error via the
#  existing Phase F.3 error_details parser, with no changes needed there
# ============================================================================
def test_recovered_running_job_status_api_shows_structured_error(isolated_job_store):
    from app.api.jobs import get_status

    job_id = _make_job(isolated_job_store, isolated_job_store.STATUS_RUNNING)
    isolated_job_store.reconcile_interrupted_jobs()

    status = get_status(job_id)
    assert status["status"] == "failed"
    assert isinstance(status["error"], str)
    assert json.loads(status["error"])["code"] == "JOB_INTERRUPTED"
    assert status["error_details"] == {
        "code": "JOB_INTERRUPTED",
        "message": "Evaluation was interrupted by a backend restart.",
        "details": {"previous_status": "running"},
    }


def test_recovered_queued_job_status_api_shows_structured_error(isolated_job_store):
    from app.api.jobs import get_status

    job_id = _make_job(isolated_job_store, isolated_job_store.STATUS_QUEUED)
    isolated_job_store.reconcile_interrupted_jobs()

    status = get_status(job_id)
    assert status["status"] == "failed"
    assert status["error_details"]["code"] == "QUEUED_JOB_INTERRUPTED"


# ============================================================================
#  Part 16/17 - cleanup-candidate selection after F.4
# ============================================================================
def _set_updated_at(job_store_module, job_id, seconds_ago):
    """Directly backdate `updated_at` (and `completed_at` where relevant)
    past a candidate cleanup threshold - bypassing `set_status`'s own
    `time.time()` stamping, which always uses "now"."""
    with job_store_module._cursor() as cur:
        cur.execute(
            "UPDATE jobs SET updated_at = ? WHERE job_id = ?",
            (time.time() - seconds_ago, job_id),
        )


def _set_completed_at(job_store_module, job_id, seconds_ago):
    with job_store_module._cursor() as cur:
        cur.execute(
            "UPDATE jobs SET completed_at = ? WHERE job_id = ?",
            (time.time() - seconds_ago, job_id),
        )


_ABANDONED_THRESHOLD = 3600.0  # 1 hour, arbitrary for these tests
_FAILED_THRESHOLD = 3600.0
_DONE_THRESHOLD = 86400.0


def _find_candidates(job_store_module):
    return job_store_module.find_cleanup_candidates(
        failed_after_seconds=_FAILED_THRESHOLD,
        done_after_seconds=_DONE_THRESHOLD,
        abandoned_after_seconds=_ABANDONED_THRESHOLD,
    )


def test_stale_created_job_is_cleanup_candidate(isolated_job_store):
    job_id = _make_job(isolated_job_store, isolated_job_store.STATUS_CREATED)
    _set_updated_at(isolated_job_store, job_id, _ABANDONED_THRESHOLD + 60)

    candidates = {r.job_id for r in _find_candidates(isolated_job_store)}
    assert job_id in candidates


def test_stale_uploading_job_is_cleanup_candidate(isolated_job_store):
    job_id = _make_job(isolated_job_store, isolated_job_store.STATUS_UPLOADING)
    _set_updated_at(isolated_job_store, job_id, _ABANDONED_THRESHOLD + 60)

    candidates = {r.job_id for r in _find_candidates(isolated_job_store)}
    assert job_id in candidates


def test_stale_queued_job_is_not_cleanup_candidate(isolated_job_store):
    """17. A QUEUED job may legitimately be waiting behind another job for
    the Phase F.1 execution lock - a stale `updated_at` alone must never
    make it a deletion candidate."""
    job_id = _make_job(isolated_job_store, isolated_job_store.STATUS_QUEUED)
    _set_updated_at(isolated_job_store, job_id, _ABANDONED_THRESHOLD + 60)

    candidates = {r.job_id for r in _find_candidates(isolated_job_store)}
    assert job_id not in candidates


def test_stale_running_job_is_not_cleanup_candidate(isolated_job_store):
    """17. A live RUNNING job has no heartbeat and may legitimately take a
    long time - a stale `updated_at` alone must never make it a deletion
    candidate (regression guard for the Phase F.0 risk finding)."""
    job_id = _make_job(isolated_job_store, isolated_job_store.STATUS_RUNNING)
    _set_updated_at(isolated_job_store, job_id, _ABANDONED_THRESHOLD + 60)

    candidates = {r.job_id for r in _find_candidates(isolated_job_store)}
    assert job_id not in candidates


def test_old_failed_job_is_cleanup_candidate(isolated_job_store):
    job_id = _make_job(isolated_job_store, isolated_job_store.STATUS_FAILED, error="boom")
    _set_completed_at(isolated_job_store, job_id, _FAILED_THRESHOLD + 60)

    candidates = {r.job_id for r in _find_candidates(isolated_job_store)}
    assert job_id in candidates


def test_old_done_job_is_cleanup_candidate(isolated_job_store):
    job_id = _make_job(isolated_job_store, isolated_job_store.STATUS_DONE)
    _set_completed_at(isolated_job_store, job_id, _DONE_THRESHOLD + 60)

    candidates = {r.job_id for r in _find_candidates(isolated_job_store)}
    assert job_id in candidates


def test_recovered_job_becomes_ordinary_failed_cleanup_candidate_after_retention(
    isolated_job_store,
):
    """Part 9/13: a startup-recovered job is not special-cased - once it is
    FAILED, it follows the exact same failed-retention rule as any other
    failure."""
    job_id = _make_job(isolated_job_store, isolated_job_store.STATUS_RUNNING)
    isolated_job_store.reconcile_interrupted_jobs()

    # Not yet old enough to be a candidate.
    candidates = {r.job_id for r in _find_candidates(isolated_job_store)}
    assert job_id not in candidates

    _set_completed_at(isolated_job_store, job_id, _FAILED_THRESHOLD + 60)
    candidates = {r.job_id for r in _find_candidates(isolated_job_store)}
    assert job_id in candidates


# ============================================================================
#  Part 18 - lifespan startup order: configure_logging -> init_db ->
#  reconcile -> start_scheduler -> (yield) -> stop_scheduler
# ============================================================================
def test_lifespan_calls_init_db_then_reconcile_then_start_scheduler(monkeypatch):
    from app import main as main_module

    order: list[str] = []

    monkeypatch.setattr(main_module, "configure_logging", lambda: order.append("configure_logging"))
    monkeypatch.setattr(main_module.job_store, "init_db", lambda: order.append("init_db"))

    def fake_reconcile():
        order.append("reconcile")
        return {"queued_recovered": 0, "running_recovered": 0}

    monkeypatch.setattr(main_module.job_store, "reconcile_interrupted_jobs", fake_reconcile)
    monkeypatch.setattr(main_module, "start_scheduler", lambda: order.append("start_scheduler"))
    monkeypatch.setattr(main_module, "stop_scheduler", lambda: order.append("stop_scheduler"))

    async def _run():
        async with main_module.lifespan(main_module.app):
            order.append("yielded")

    asyncio.run(_run())

    assert order == [
        "configure_logging",
        "init_db",
        "reconcile",
        "start_scheduler",
        "yielded",
        "stop_scheduler",
    ]
