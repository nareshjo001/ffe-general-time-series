"""
Job metadata store.

WHY SQLITE (not Postgres) 
-------------------------
Uses SQLite because it is lightweight, requires no extra setup, and
handles the application's current workload well. If the application
needs to support much higher concurrency in the future, this module
can be replaced with a Postgres implementation without affecting the
rest of the code.

CONCURRENCY NOTE
-----------------
Each function opens and closes its own short-lived connection rather than
holding one open for the app's lifetime. SQLite connections are not
guaranteed thread-safe when shared across threads without care, and job
writes here are infrequent (a handful of status transitions per job) - so
the overhead of open/close per call is negligible.
"""

import json
import logging
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Valid job lifecycle states used throughout the application.
STATUS_CREATED = "created"        # Job created, no files uploaded yet
STATUS_UPLOADING = "uploading"    # Upload in progress
STATUS_QUEUED = "queued"          # Waiting to be evaluated
STATUS_RUNNING = "running"        # Evaluation in progress
STATUS_DONE = "done"              # Evaluation completed successfully
STATUS_FAILED = "failed"          # Evaluation failed

# Phase 2 evaluation modes. A job's mode is fixed at creation time and
# determines which uploads are required before evaluation:
#   MODE_REAL_ONLY       -> real.csv + spec.yaml
#   MODE_REAL_SYNTHETIC  -> real.csv + synthetic.csv + spec.yaml
# `mode` is nullable: Phase 1 jobs created before Phase 2 existed (and any
# caller that still omits it) have `mode = NULL` and are unaffected by any
# Phase 2 mode-enforcement logic - only an explicit MODE_REAL_ONLY currently
# changes upload behavior (see api/upload.py::upload_synthetic).
MODE_REAL_ONLY = "real_only"
MODE_REAL_SYNTHETIC = "real_synthetic"
VALID_MODES = (MODE_REAL_ONLY, MODE_REAL_SYNTHETIC)


@dataclass
class JobRecord:
    job_id: str
    status: str
    created_at: float
    updated_at: float
    completed_at: Optional[float]
    error: Optional[str]
    result_downloaded_at: Optional[float]
    mode: Optional[str] = None


def _connect() -> sqlite3.Connection:
    settings.job_db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.job_db_path, timeout=30)
    # Enable WAL mode so reads and writes can happen at the same time.
    # This lets status checks continue while another thread updates a job.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


"""
Provide a database cursor and automatically handle
commit and connection cleanup.
"""
@contextmanager
def _cursor():
    conn = _connect()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    finally:
        conn.close()


def _ensure_mode_column(cur: sqlite3.Cursor) -> None:
    """Additive, idempotent migration: add the `mode` column to an existing
    `jobs` table if it isn't there yet.

    Safe to call every time `init_db()` runs (fresh database, already-
    migrated database, or a pre-Phase-2 database created before `mode`
    existed) - it only ever adds a nullable column, never touches any
    existing column, row, or index. Existing rows automatically get
    `mode = NULL` (SQLite's default for a newly added column with no
    explicit DEFAULT), which is exactly the "legacy Phase 1 job" value this
    module already treats as "mode not set" everywhere else.
    """
    cur.execute("PRAGMA table_info(jobs)")
    existing_columns = {row[1] for row in cur.fetchall()}  # row[1] = column name
    if "mode" not in existing_columns:
        cur.execute("ALTER TABLE jobs ADD COLUMN mode TEXT")


def init_db() -> None:
    """Create the jobs table if it doesn't exist, and migrate it forward if
    it already exists in an older shape. Call once at app startup."""
    with _cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id                 TEXT PRIMARY KEY,
                status                 TEXT NOT NULL,
                created_at             REAL NOT NULL,
                updated_at             REAL NOT NULL,
                completed_at           REAL,
                error                  TEXT,
                result_downloaded_at   REAL,
                mode                   TEXT
            )
        """)
        _ensure_mode_column(cur)
        # Speed up queries that filter or sort jobs by status and update time.
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_status_updated
            ON jobs (status, updated_at)
        """)


def create_job(mode: Optional[str] = None) -> str:
    """Create a new job, store it in the database, and return its ID.

    `mode` is optional and defaults to None (a legacy/mode-less job,
    preserving exact Phase 1 behavior for any caller that doesn't pass one).
    When given, it must be one of `VALID_MODES` - an unrecognized mode
    raises `ValueError` rather than silently being stored.
    """
    if mode is not None and mode not in VALID_MODES:
        raise ValueError(f"invalid mode {mode!r}; must be one of {VALID_MODES}")

    job_id = uuid.uuid4().hex
    now = time.time()
    with _cursor() as cur:
        cur.execute(
            """
            INSERT INTO jobs (job_id, status, created_at, updated_at, mode)
            VALUES (?, ?, ?, ?, ?)
            """,
            (job_id, STATUS_CREATED, now, now, mode),
        )
    return job_id


def job_exists(job_id: str) -> bool:
    with _cursor() as cur:
        cur.execute("SELECT 1 FROM jobs WHERE job_id = ?", (job_id,))
        return cur.fetchone() is not None


def get_job(job_id: str) -> Optional[JobRecord]:
    with _cursor() as cur:
        cur.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
        row = cur.fetchone()
        return _row_to_record(row) if row else None


def set_status(job_id: str, status: str, error: Optional[str] = None) -> None:
    """Update a job's status.

    Records the completion time automatically when a job finishes or
    fails, so completed jobs can be tracked and cleaned up later.
    """
    now = time.time()
    completed_at = now if status in (STATUS_DONE, STATUS_FAILED) else None

    with _cursor() as cur:
        if completed_at is not None:
            cur.execute(
                """
                UPDATE jobs
                SET status = ?, updated_at = ?, completed_at = ?, error = ?
                WHERE job_id = ?
                """,
                (status, now, completed_at, error, job_id),
            )
        else:
            cur.execute(
                "UPDATE jobs SET status = ?, updated_at = ? WHERE job_id = ?",
                (status, now, job_id),
            )


# ============================================================================
#  Phase F.4 - single-process startup reconciliation
# ============================================================================
# Deployment is explicitly a single backend Python process (confirmed
# product/architecture decision - see the Phase F.2/F.3 reports). That
# assumption is what makes the transitions below safe:
#   - FastAPI `BackgroundTasks` callbacks live only in this process's
#     memory. If the process restarts, any callback that was going to run a
#     QUEUED job is gone - it will never fire.
#   - Only this one process can ever hold the Phase 2 execution lock
#     (execution_guard.py) or be mid-`evaluation_service` call. If this
#     process is starting up, no other process is concurrently executing a
#     job this database still says is RUNNING.
# Under a future multi-process/multi-worker deployment, NEITHER of the two
# assumptions above would hold, and this function would need to be
# redesigned (e.g. a per-worker heartbeat) rather than reused as-is.
_INTERRUPTION_ERRORS = {
    STATUS_RUNNING: {
        "code": "JOB_INTERRUPTED",
        "message": "Evaluation was interrupted by a backend restart.",
        "details": {"previous_status": STATUS_RUNNING},
    },
    STATUS_QUEUED: {
        "code": "QUEUED_JOB_INTERRUPTED",
        "message": "Queued evaluation was interrupted before execution by a backend restart.",
        "details": {"previous_status": STATUS_QUEUED},
    },
}


def _interruption_error_json(previous_status: str) -> str:
    """Deterministic JSON encoding of the structured interruption error for
    ``previous_status`` (``STATUS_QUEUED`` or ``STATUS_RUNNING``). Same
    minimal ``{"code", "message", "details"}`` shape introduced by Phase
    F.3's `Phase2PreflightError.to_json()` - reused here directly rather
    than via a second error type, and persisted into the same `error` TEXT
    column, so the status API's existing structured-error parser
    (`app/api/jobs.py::_try_parse_structured_error`) picks it up with no
    changes required there.
    """
    payload = _INTERRUPTION_ERRORS[previous_status]
    return json.dumps(payload, sort_keys=True)


def reconcile_interrupted_jobs() -> dict:
    """Startup-only reconciliation for a single-backend-process deployment.

    Call once, at application startup, AFTER `init_db()` (the `jobs` table
    must exist) and BEFORE the cleanup scheduler starts (stale
    QUEUED/RUNNING rows should be repaired before cleanup's periodic scan
    ever runs against them).

    Any job persisted as QUEUED or RUNNING when this function runs must
    have belonged to a previous process instance that no longer exists (see
    the module-level comment above for why this is safe under a
    single-process deployment) - both are transitioned to FAILED with a
    structured, deterministic interruption error (see
    `_interruption_error_json`).

    Deliberately conservative:
        - never inspects `result.json`/`curves.json` on disk to infer a
          job actually finished - presence of output files proves nothing
          about correctness or completeness (could be partial, could be
          stale from an earlier attempt), so this never recovers a job as
          DONE.
        - never deletes anything (no job rows, no output files) - a
          recovered job becomes an ordinary FAILED job and is left to the
          existing failed-job retention/cleanup policy (see cleanup.py),
          exactly like any other failure.
        - never requeues, retries, or resumes - the interruption is made
          operator-visible as a terminal FAILED status; a new job must be
          created manually if the evaluation should be re-run.
        - CREATED and UPLOADING are never touched here - neither status
          implies an in-memory evaluation callback was lost, so there is
          nothing for this specific reconciliation to safely conclude about
          them. They remain governed by the existing abandoned-job cleanup
          threshold, unchanged.

    Idempotent: a job already in a terminal status (including one this
    function itself just marked FAILED) is not matched by the `WHERE
    status IN (...)` clause on any subsequent call, so calling this
    function multiple times (e.g. in a test, or across multiple startups
    with no new QUEUED/RUNNING rows in between) never re-transitions an
    already-recovered job or overwrites its original interruption error.

    Runs inside the same single transaction as every other write in this
    module (via `_cursor()`) - single-process startup, before the scheduler
    starts and before the server accepts requests, so there is no concurrent
    writer to race here; no additional locking is introduced.

    Returns:
        ``{"queued_recovered": <int>, "running_recovered": <int>}``
    """
    now = time.time()
    queued_recovered = 0
    running_recovered = 0

    with _cursor() as cur:
        cur.execute(
            "SELECT job_id, status FROM jobs WHERE status IN (?, ?)",
            (STATUS_QUEUED, STATUS_RUNNING),
        )
        rows = cur.fetchall()

        for row in rows:
            job_id = row["job_id"]
            previous_status = row["status"]
            error = _interruption_error_json(previous_status)

            cur.execute(
                """
                UPDATE jobs
                SET status = ?, updated_at = ?, completed_at = ?, error = ?
                WHERE job_id = ?
                """,
                (STATUS_FAILED, now, now, error, job_id),
            )

            if previous_status == STATUS_QUEUED:
                queued_recovered += 1
            else:
                running_recovered += 1

    logger.info(
        "startup reconciliation marked %s queued and %s running jobs as failed",
        queued_recovered,
        running_recovered,
    )

    return {"queued_recovered": queued_recovered, "running_recovered": running_recovered}


def mark_result_downloaded(job_id: str) -> None:
    """Record when a job's result is first downloaded.
    Used by the cleanup process to identify jobs whose results have already
    been retrieved.
    """
    with _cursor() as cur:
        cur.execute(
            """
            UPDATE jobs
            SET result_downloaded_at = COALESCE(result_downloaded_at, ?)
            WHERE job_id = ?
            """,
            (time.time(), job_id),
        )


def list_jobs(status: Optional[str] = None, limit: int = 200) -> list[JobRecord]:
    with _cursor() as cur:
        if status:
            cur.execute(
                "SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            )
        else:
            cur.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
            )
        return [_row_to_record(row) for row in cur.fetchall()]


def find_cleanup_candidates(
    failed_after_seconds: float,
    done_after_seconds: float,
    abandoned_after_seconds: float,
) -> list[JobRecord]:
    """Return jobs that are eligible for cleanup.
    Includes completed, failed, and abandoned jobs that have exceeded the
    configured cleanup time.

    Phase F.4: the "abandoned" branch covers ONLY `CREATED`/`UPLOADING` -
    incomplete user/upload flows with no evaluation callback ever
    scheduled. `QUEUED` and `RUNNING` are deliberately excluded here:

        - a `QUEUED` job may legitimately remain queued for a long time
          while waiting behind another job for the Phase F.1 Phase 2
          execution lock (see execution_guard.py) - `updated_at` going
          stale does not mean anything was lost, only that the job hasn't
          reached the front of the queue yet.
        - a `RUNNING` job may legitimately take a long time to evaluate and
          has no heartbeat that refreshes `updated_at` mid-run - deleting
          it merely because `updated_at` is old would delete a live,
          in-progress evaluation out from under its own process.

    Any `QUEUED`/`RUNNING` row that is genuinely stale (i.e. left over from
    a previous process that no longer exists) is instead repaired by
    `reconcile_interrupted_jobs()` at startup, which transitions it to
    `FAILED` - at which point it naturally becomes a cleanup candidate
    under the existing failed-job retention policy above, like any other
    failure. This function does not need its own special case for that
    scenario.
    """
    now = time.time()
    with _cursor() as cur:
        cur.execute(
            """
            SELECT * FROM jobs
            WHERE
                (status = ? AND completed_at IS NOT NULL AND ? - completed_at > ?)
                OR
                (status = ? AND completed_at IS NOT NULL AND ? - completed_at > ?)
                OR
                (status IN (?, ?) AND ? - updated_at > ?)
            """,
            (
                STATUS_FAILED, now, failed_after_seconds,
                STATUS_DONE, now, done_after_seconds,
                STATUS_CREATED, STATUS_UPLOADING,
                now, abandoned_after_seconds,
            ),
        )
        return [_row_to_record(row) for row in cur.fetchall()]


def delete_job(job_id: str) -> None:
    with _cursor() as cur:
        cur.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))


def _row_to_record(row: sqlite3.Row) -> JobRecord:
    # `mode` is read defensively via row.keys() so this keeps working even
    # against a connection/cursor that predates the migration in
    # _ensure_mode_column (init_db() always runs it first in practice, but
    # this avoids a KeyError if that invariant is ever violated).
    row_keys = row.keys()
    return JobRecord(
        job_id=row["job_id"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        completed_at=row["completed_at"],
        error=row["error"],
        result_downloaded_at=row["result_downloaded_at"],
        mode=row["mode"] if "mode" in row_keys else None,
    )