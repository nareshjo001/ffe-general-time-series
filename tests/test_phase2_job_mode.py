"""Phase C tests: job mode persistence, SQLite migration, and job creation.

Every test runs against an isolated, per-test SQLite file and job storage
directory (via `tmp_path` + monkeypatching `app.core.config.settings`) so
nothing here touches the real project database or `storage/jobs/` tree, and
tests never interfere with each other.

Covers:
    - fresh-database schema includes `mode`
    - a pre-Phase-2 ("legacy") database migrates additively, with all
      existing rows/columns preserved
    - job creation with mode=None (exact legacy behavior), mode="real_only",
      mode="real_synthetic"
    - invalid mode strings are rejected
    - the /create-job route function's backward-compatible "no body" path
"""
from __future__ import annotations

import sqlite3
import time

import pytest


@pytest.fixture
def isolated_job_store(tmp_path, monkeypatch):
    """Point Settings + job_store at an isolated, empty SQLite file/dir for
    this test only, and initialize the (current, migrated) schema."""
    from app.core.config import settings
    from app.database import job_store

    monkeypatch.setattr(settings, "job_db_path", tmp_path / "jobs.db")
    monkeypatch.setattr(settings, "storage_base_dir", tmp_path / "jobs")
    job_store.init_db()
    return job_store


# ============================================================================
#  16. database migration tests
# ============================================================================
def test_fresh_database_has_mode_column(isolated_job_store):
    job_store = isolated_job_store
    from app.core.config import settings

    conn = sqlite3.connect(settings.job_db_path)
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(jobs)")}
    finally:
        conn.close()
    assert "mode" in cols


def test_legacy_database_migrates_additively_and_preserves_data(tmp_path, monkeypatch):
    """Construct the OLD (pre-Phase-2) jobs schema by hand - no `mode`
    column at all - insert a legacy row exactly the way Phase 1's
    `job_store.create_job()` used to, then run today's `init_db()` and
    confirm: the mode column is added, and the existing row's status/
    timestamps/error/etc. all survive unchanged."""
    from app.core.config import settings
    from app.database import job_store

    db_path = tmp_path / "legacy_jobs.db"
    monkeypatch.setattr(settings, "job_db_path", db_path)
    monkeypatch.setattr(settings, "storage_base_dir", tmp_path / "jobs")

    # 1) build the OLD schema directly (mirrors job_store.py before mode existed)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE jobs (
            job_id                 TEXT PRIMARY KEY,
            status                 TEXT NOT NULL,
            created_at             REAL NOT NULL,
            updated_at             REAL NOT NULL,
            completed_at           REAL,
            error                  TEXT,
            result_downloaded_at   REAL
        )
    """)
    created_at = time.time() - 1000
    updated_at = time.time() - 500
    conn.execute(
        "INSERT INTO jobs (job_id, status, created_at, updated_at, completed_at, "
        "error, result_downloaded_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("legacy-job-1", "done", created_at, updated_at, updated_at, None, None),
    )
    conn.commit()
    conn.close()

    # 2) run today's init_db() against that pre-existing file - this is the migration
    job_store.init_db()

    # 3) mode column now exists
    conn = sqlite3.connect(db_path)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(jobs)")}
    conn.close()
    assert "mode" in cols

    # 4) the pre-existing row survived with all its original data intact
    record = job_store.get_job("legacy-job-1")
    assert record is not None
    assert record.status == "done"
    assert record.created_at == created_at
    assert record.updated_at == updated_at
    assert record.completed_at == updated_at
    assert record.error is None
    # ... and its mode is None (SQLite default for a newly added column),
    # exactly the "legacy job, mode not set" value the rest of the app expects
    assert record.mode is None


def test_running_init_db_twice_is_a_no_op_migration(isolated_job_store):
    """Calling init_db() again (e.g. a second app startup against the same
    file) must not fail or duplicate the column."""
    job_store = isolated_job_store
    job_store.init_db()  # second call - must not raise
    job_id = job_store.create_job(mode=job_store.MODE_REAL_ONLY)
    assert job_store.get_job(job_id).mode == job_store.MODE_REAL_ONLY


# ============================================================================
#  17. job creation tests
# ============================================================================
def test_create_real_only_job_persists_mode(isolated_job_store):
    job_store = isolated_job_store
    job_id = job_store.create_job(mode=job_store.MODE_REAL_ONLY)
    record = job_store.get_job(job_id)
    assert record.mode == "real_only"


def test_create_real_synthetic_job_persists_mode(isolated_job_store):
    job_store = isolated_job_store
    job_id = job_store.create_job(mode=job_store.MODE_REAL_SYNTHETIC)
    record = job_store.get_job(job_id)
    assert record.mode == "real_synthetic"


def test_create_job_without_mode_preserves_legacy_behavior(isolated_job_store):
    job_store = isolated_job_store
    job_id = job_store.create_job()  # no mode - exact old Phase 1 call shape
    record = job_store.get_job(job_id)
    assert record.mode is None
    assert record.status == job_store.STATUS_CREATED


def test_create_job_invalid_mode_rejected(isolated_job_store):
    job_store = isolated_job_store
    with pytest.raises(ValueError, match="invalid mode"):
        job_store.create_job(mode="foobar")


def test_job_manager_create_job_with_mode(isolated_job_store):
    from app.services.job.job_manager import JobManager

    job_id = JobManager.create_job(mode="real_only")
    record = isolated_job_store.get_job(job_id)
    assert record.mode == "real_only"
    # directory layout is unchanged - Phase C does not redesign it
    job_dir = JobManager.get_job_dir(job_id)
    assert (job_dir / "uploads").is_dir()
    assert (job_dir / "database").is_dir()
    assert (job_dir / "outputs").is_dir()
    assert (job_dir / "logs").is_dir()


def test_job_manager_get_spec_path(isolated_job_store):
    from app.services.job.job_manager import JobManager

    job_id = JobManager.create_job(mode="real_only")
    spec_path = JobManager.get_spec_path(job_id)
    assert spec_path == JobManager.get_upload_dir(job_id) / "spec.yaml"


# ============================================================================
#  /create-job route: mode contract + backward-compatible "no body" path
# ============================================================================
def test_create_job_route_with_no_body_matches_legacy_frontend_call(isolated_job_store):
    """The existing frontend calls `POST /create-job` with NO body at all
    (see components/UploadForm.js). FastAPI passes `body=None` in that case -
    this must keep working exactly as before."""
    from app.api.upload import create_job

    response = create_job(body=None)
    assert response["mode"] is None
    record = isolated_job_store.get_job(response["job_id"])
    assert record.mode is None


def test_create_job_route_with_real_only_mode(isolated_job_store):
    from app.api.upload import CreateJobRequest, create_job

    response = create_job(body=CreateJobRequest(mode="real_only"))
    assert response["mode"] == "real_only"
    record = isolated_job_store.get_job(response["job_id"])
    assert record.mode == "real_only"


def test_create_job_route_with_real_synthetic_mode(isolated_job_store):
    from app.api.upload import CreateJobRequest, create_job

    response = create_job(body=CreateJobRequest(mode="real_synthetic"))
    assert response["mode"] == "real_synthetic"


def test_create_job_route_invalid_mode_returns_400(isolated_job_store):
    from fastapi import HTTPException

    from app.api.upload import CreateJobRequest, create_job

    with pytest.raises(HTTPException) as exc_info:
        create_job(body=CreateJobRequest(mode="foobar"))
    assert exc_info.value.status_code == 400


# ============================================================================
#  job metadata API surfaces mode
# ============================================================================
def test_job_status_route_includes_mode(isolated_job_store):
    from app.api.jobs import get_status
    from app.services.job.job_manager import JobManager

    job_id = JobManager.create_job(mode="real_synthetic")
    response = get_status(job_id)
    assert response["mode"] == "real_synthetic"


def test_list_jobs_route_includes_mode(isolated_job_store):
    from app.api.jobs import list_jobs
    from app.services.job.job_manager import JobManager

    JobManager.create_job(mode="real_only")
    response = list_jobs()
    assert len(response) >= 1
    assert all("mode" in r for r in response)
