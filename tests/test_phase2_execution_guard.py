"""Phase F.1 tests: the per-process Phase 2 execution lock
(app/services/evaluation2/execution_guard.py) actually serializes
`evaluation_service.run_real_only`/`run_real_synthetic` calls made through
`JobExecutor.run_real_only`/`run_real_synthetic`, for every mode
combination, releases correctly on failure (no lock leak), and is never
acquired by the legacy Phase 1 (`mode=None`) path.

These are pure concurrency/timing tests - no real querylib execution is
needed or used here. `evaluation_service.run_real_only`/`run_real_synthetic`
are monkeypatched with controlled, deterministically-synchronized fakes
(threading.Event-based, never sleep-only) so the tests are fast and not
timing-flaky.
"""
from __future__ import annotations

import threading
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


def _make_job(mode, isolated_job_store):
    from app.services.job.job_manager import JobManager

    job_id = JobManager.create_job(mode=mode)
    JobManager.get_upload_dir(job_id).mkdir(parents=True, exist_ok=True)
    return job_id


class _BlockingFake:
    """A controlled stand-in for evaluation_service.run_real_only/
    run_real_synthetic: signals `entered` the instant it starts executing
    (i.e. the instant it's inside the critical section), then blocks on
    `release` until the test lets it proceed. Records entry/exit order in a
    shared list so tests can assert non-overlap without relying on sleep
    timing.
    """

    def __init__(self, name, order, release: threading.Event | None = None):
        self.name = name
        self.order = order
        self.entered = threading.Event()
        self.release = release or threading.Event()

    def __call__(self, *args, **kwargs):
        self.order.append(("enter", self.name))
        self.entered.set()
        self.release.wait(timeout=5)
        self.order.append(("exit", self.name))
        return {
            "result": {"mode": "real_only", "overview": {}, "instances": [], "metadata": {"instance_count": 0}},
            "curves": [],
        }


def _run_in_thread(target, *args):
    t = threading.Thread(target=target, args=args)
    t.start()
    return t


def _patch_no_op_result_writer(monkeypatch):
    """The concurrency tests care only about the evaluation_service call
    site, not disk I/O - patch result_writer to a no-op so these tests don't
    depend on Phase F.1's atomic-writer behavior (covered separately in
    test_phase2_atomic_writer.py)."""
    from app.services.job import job_executor

    monkeypatch.setattr(job_executor.result_writer, "write_result", lambda *a, **k: None)
    monkeypatch.setattr(job_executor.result_writer, "write_curves", lambda *a, **k: None)


# ============================================================================
#  A/B/C. real_only+real_only, real_only+real_synthetic, real_synthetic+real_synthetic
#  cannot execute inside the Phase 2 critical section simultaneously
# ============================================================================
@pytest.mark.parametrize(
    "mode_a,mode_b",
    [
        ("real_only", "real_only"),
        ("real_only", "real_synthetic"),
        ("real_synthetic", "real_synthetic"),
    ],
)
def test_two_phase2_jobs_never_overlap_in_critical_section(
    isolated_job_store, monkeypatch, mode_a, mode_b
):
    from app.services.job import job_executor
    from app.services.job.job_executor import JobExecutor

    order: list[tuple[str, str]] = []
    fake_a = _BlockingFake("A", order)
    fake_b = _BlockingFake("B", order)

    # Both evaluation_service entry points are patched to a single dispatcher
    # that hands out fake_a to the first call and fake_b to the second,
    # regardless of which of the two modes (possibly the same mode twice)
    # each call came through.
    call_index = {"n": 0}
    fakes_in_order = [fake_a, fake_b]

    def dispatch(*args, **kwargs):
        fake = fakes_in_order[call_index["n"]]
        call_index["n"] += 1
        return fake(*args, **kwargs)

    monkeypatch.setattr(job_executor.evaluation_service, "run_real_only", dispatch)
    monkeypatch.setattr(job_executor.evaluation_service, "run_real_synthetic", dispatch)

    _patch_no_op_result_writer(monkeypatch)

    job_a = _make_job(mode_a, isolated_job_store)
    job_b = _make_job(mode_b, isolated_job_store)

    runner_a = JobExecutor.run_real_only if mode_a == "real_only" else JobExecutor.run_real_synthetic
    runner_b = JobExecutor.run_real_only if mode_b == "real_only" else JobExecutor.run_real_synthetic

    thread_a = _run_in_thread(runner_a, job_a)
    # Wait until job A is actually inside the critical section before
    # starting job B - this is what makes the assertion meaningful (rather
    # than a race on which thread happens to acquire the lock first).
    assert fake_a.entered.wait(timeout=5), "job A never entered the critical section"

    thread_b = _run_in_thread(runner_b, job_b)
    # Job B must NOT be able to enter while A is still holding the lock.
    entered_while_a_blocked = fake_b.entered.wait(timeout=0.3)
    assert not entered_while_a_blocked, (
        "job B entered the Phase 2 critical section while job A was still "
        "inside it - the execution lock did not serialize them"
    )

    # Release A; B must now be able to proceed.
    fake_a.release.set()
    thread_a.join(timeout=5)
    assert fake_b.entered.wait(timeout=5), "job B never entered after job A released the lock"
    fake_b.release.set()
    thread_b.join(timeout=5)

    assert order == [("enter", "A"), ("exit", "A"), ("enter", "B"), ("exit", "B")]

    record_a = isolated_job_store.get_job(job_a)
    record_b = isolated_job_store.get_job(job_b)
    assert record_a.status == isolated_job_store.STATUS_DONE
    assert record_b.status == isolated_job_store.STATUS_DONE


# ============================================================================
#  8. failure-release test: a failed Phase 2 evaluation must not leak the lock
# ============================================================================
def test_lock_releases_after_failure_and_does_not_block_later_jobs(
    isolated_job_store, monkeypatch
):
    from app.services.job import job_executor
    from app.services.job.job_executor import JobExecutor

    def boom(*args, **kwargs):
        raise RuntimeError("simulated evaluation_service failure")

    monkeypatch.setattr(job_executor.evaluation_service, "run_real_only", boom)
    _patch_no_op_result_writer(monkeypatch)

    job_1 = _make_job("real_only", isolated_job_store)
    with pytest.raises(RuntimeError):
        JobExecutor.run_real_only(job_1)

    record_1 = isolated_job_store.get_job(job_1)
    assert record_1.status == isolated_job_store.STATUS_FAILED

    # The lock must be free now - a second, successful Phase 2 job must be
    # able to acquire it without ever blocking.
    order: list[tuple[str, str]] = []
    fake_2 = _BlockingFake("second", order, release=threading.Event())
    fake_2.release.set()  # never actually blocks - proves no contention, not throughput
    monkeypatch.setattr(job_executor.evaluation_service, "run_real_only", fake_2)

    job_2 = _make_job("real_only", isolated_job_store)
    acquired = threading.Event()

    def run_and_signal():
        JobExecutor.run_real_only(job_2)
        acquired.set()

    t = _run_in_thread(run_and_signal)
    t.join(timeout=5)
    assert acquired.is_set(), "second job never completed - lock may have leaked"

    record_2 = isolated_job_store.get_job(job_2)
    assert record_2.status == isolated_job_store.STATUS_DONE


def test_lock_releases_after_self_check_style_failure_in_real_synthetic(
    isolated_job_store, monkeypatch
):
    """Same failure-release guarantee, but through the run_real_synthetic
    path specifically (e.g. representative of a SelfCheckFailedError)."""
    from app.services.evaluation2.evaluation_service import SelfCheckFailedError
    from app.services.job import job_executor
    from app.services.job.job_executor import JobExecutor

    def boom(*args, **kwargs):
        raise SelfCheckFailedError("simulated self-check failure")

    monkeypatch.setattr(job_executor.evaluation_service, "run_real_synthetic", boom)
    _patch_no_op_result_writer(monkeypatch)

    job_1 = _make_job("real_synthetic", isolated_job_store)
    with pytest.raises(SelfCheckFailedError):
        JobExecutor.run_real_synthetic(job_1)
    assert isolated_job_store.get_job(job_1).status == isolated_job_store.STATUS_FAILED

    # Lock must still be free for a subsequent job.
    monkeypatch.setattr(
        job_executor.evaluation_service,
        "run_real_synthetic",
        lambda *a, **k: {
            "result": {"mode": "real_synthetic", "overview": {}, "instances": [], "self_check": {}, "metadata": {}},
            "curves": [],
        },
    )
    job_2 = _make_job("real_synthetic", isolated_job_store)
    JobExecutor.run_real_synthetic(job_2)
    assert isolated_job_store.get_job(job_2).status == isolated_job_store.STATUS_DONE


# ============================================================================
#  9. legacy Phase 1 regression: mode=None must never touch the Phase 2 lock
# ============================================================================
def test_legacy_run_does_not_acquire_phase2_lock(isolated_job_store, monkeypatch):
    from app.services.evaluation2.execution_guard import phase2_execution_lock
    from app.services.job.job_executor import JobExecutor
    from app.services.job.job_manager import JobManager

    # Hold the Phase 2 lock for the whole test - if JobExecutor.run ever
    # tried to acquire it, this would deadlock/hang instead of completing.
    acquired_by_test = phase2_execution_lock.acquire(timeout=5)
    assert acquired_by_test, "test setup failed to acquire the lock"
    try:
        job_id = JobManager.create_job(mode=None)
        JobManager.get_upload_dir(job_id).mkdir(parents=True, exist_ok=True)
        JobManager.get_real_csv(job_id).write_text("a,b\n1,2\n")
        JobManager.get_synthetic_csv(job_id).write_text("a,b\n1,2\n")

        # JobExecutor.run will fail early (no DuckDB/real ingestion set up in
        # this unit test), but that's fine - the only thing under test is
        # that it does not block/deadlock trying to acquire a lock this test
        # thread is already holding. A quick failure proves it never touched
        # the lock at all.
        done = threading.Event()

        def run_and_signal():
            try:
                JobExecutor.run(job_id)
            except Exception:
                pass
            finally:
                done.set()

        t = _run_in_thread(run_and_signal)
        completed = done.wait(timeout=5)
        t.join(timeout=1)
        assert completed, (
            "JobExecutor.run did not complete while the Phase 2 lock was "
            "held by another thread - it may be incorrectly acquiring the "
            "Phase 2 execution lock"
        )
    finally:
        phase2_execution_lock.release()

    record = isolated_job_store.get_job(job_id)
    # Whatever the exact legacy failure mode is (missing DuckDB setup in this
    # unit test), it must have actually run and reached a terminal status,
    # not be stuck.
    assert record.status in (isolated_job_store.STATUS_FAILED, isolated_job_store.STATUS_DONE)


# ============================================================================
#  Status semantics while waiting for the lock
# ============================================================================
def test_status_stays_queued_while_blocked_on_lock_then_becomes_running(
    isolated_job_store, monkeypatch
):
    from app.services.job import job_executor
    from app.services.job.job_executor import JobExecutor

    order: list[tuple[str, str]] = []
    fake_a = _BlockingFake("A", order)
    fake_b = _BlockingFake("B", order)
    monkeypatch.setattr(job_executor.evaluation_service, "run_real_only", fake_a)
    _patch_no_op_result_writer(monkeypatch)

    job_a = _make_job("real_only", isolated_job_store)
    job_b = _make_job("real_only", isolated_job_store)
    isolated_job_store.set_status(job_b, isolated_job_store.STATUS_QUEUED)

    thread_a = _run_in_thread(JobExecutor.run_real_only, job_a)
    assert fake_a.entered.wait(timeout=5)
    assert isolated_job_store.get_job(job_a).status == isolated_job_store.STATUS_RUNNING

    monkeypatch.setattr(job_executor.evaluation_service, "run_real_only", fake_b)
    thread_b = _run_in_thread(JobExecutor.run_real_only, job_b)

    # While A still holds the lock, B must not have transitioned to RUNNING -
    # it should still read as QUEUED (the status it was left at), since it
    # hasn't acquired the lock yet.
    time.sleep(0.2)
    assert not fake_b.entered.is_set()
    assert isolated_job_store.get_job(job_b).status == isolated_job_store.STATUS_QUEUED

    fake_a.release.set()
    thread_a.join(timeout=5)
    assert fake_b.entered.wait(timeout=5)
    assert isolated_job_store.get_job(job_b).status == isolated_job_store.STATUS_RUNNING
    fake_b.release.set()
    thread_b.join(timeout=5)
    assert isolated_job_store.get_job(job_b).status == isolated_job_store.STATUS_DONE
