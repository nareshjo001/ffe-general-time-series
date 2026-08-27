"""
Evaluation API endpoints.
Start benchmark evaluation jobs in the background and provide an
immediate response to the client.

Dispatches based on the job's persisted mode (see database/job_store.py):
    mode is None                -> legacy Phase 1 packet/flow evaluation, unchanged
    mode == MODE_REAL_ONLY      -> Phase 2 real-only evaluation (Phase D)
    mode == MODE_REAL_SYNTHETIC -> Phase 2 real+synthetic comparison (Phase E)

The parallel endpoint (/evaluate/parallel/{job_id}) remains Phase-1-specific
and is not used for any Phase 2 job mode.
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.database import job_store
from app.services.job.job_executor import JobExecutor
from app.services.job.job_manager import JobManager

router = APIRouter()


def _require_job_record(job_id: str) -> job_store.JobRecord:
    if not JobManager.job_exists(job_id):
        raise HTTPException(status_code=404, detail="Invalid Job ID")
    return job_store.get_job(job_id)


def _check_not_already_running(record: job_store.JobRecord):
    # Prevent double-submission: if a job is already queued/running, a second
    # POST here must not start a second concurrent evaluation - for the
    # legacy path that would violate the single-writer assumption DuckDB
    # ingestion relies on; for the Phase 2 path it would risk two concurrent
    # querylib batteries for the same job (see the Phase 2 migration
    # architecture report: concurrent handout_lib call safety is unverified).
    if record.status in (job_store.STATUS_QUEUED, job_store.STATUS_RUNNING):
        raise HTTPException(
            status_code=409,
            detail=f"Job is already {record.status}",
        )


def _validate_ready_for_legacy_evaluation(job_id: str):
    if not JobManager.get_real_csv(job_id).exists():
        raise HTTPException(status_code=400, detail="Real CSV not uploaded")

    if not JobManager.get_synthetic_csv(job_id).exists():
        raise HTTPException(status_code=400, detail="Synthetic CSV not uploaded")


def _validate_ready_for_real_only_evaluation(job_id: str):
    # Lightweight, filesystem-only pre-flight - never loads the CSV or spec
    # here. Requires exactly real.csv + spec.yaml; synthetic.csv is
    # deliberately not checked (and not required) for this mode.
    if not JobManager.get_real_csv(job_id).exists():
        raise HTTPException(status_code=400, detail="Real CSV not uploaded")

    if not JobManager.get_spec_path(job_id).exists():
        raise HTTPException(status_code=400, detail="Spec not uploaded")


def _validate_ready_for_real_synthetic_evaluation(job_id: str):
    # Same lightweight, filesystem-only pre-flight as real-only, extended to
    # require synthetic.csv as well. Never loads any file's contents here -
    # schema/dtype validation happens inside the background job
    # (evaluation_service.run_real_synthetic), not in this route.
    if not JobManager.get_real_csv(job_id).exists():
        raise HTTPException(status_code=400, detail="Real CSV not uploaded")

    if not JobManager.get_synthetic_csv(job_id).exists():
        raise HTTPException(status_code=400, detail="Synthetic CSV not uploaded")

    if not JobManager.get_spec_path(job_id).exists():
        raise HTTPException(status_code=400, detail="Spec not uploaded")


@router.post("/evaluate/{job_id}")
def evaluate(job_id: str, background_tasks: BackgroundTasks):
    """Mode-dispatching evaluation trigger. Runs in the background."""
    record = _require_job_record(job_id)
    _check_not_already_running(record)

    if record.mode is None:
        # Legacy Phase 1 job - existing sequential packet/flow evaluation,
        # completely unchanged.
        _validate_ready_for_legacy_evaluation(job_id)
        job_store.set_status(job_id, job_store.STATUS_QUEUED)
        background_tasks.add_task(JobExecutor.run, job_id)
        return {"job_id": job_id, "status": job_store.STATUS_QUEUED}

    if record.mode == job_store.MODE_REAL_ONLY:
        _validate_ready_for_real_only_evaluation(job_id)
        job_store.set_status(job_id, job_store.STATUS_QUEUED)
        background_tasks.add_task(JobExecutor.run_real_only, job_id)
        return {"job_id": job_id, "status": job_store.STATUS_QUEUED}

    if record.mode == job_store.MODE_REAL_SYNTHETIC:
        _validate_ready_for_real_synthetic_evaluation(job_id)
        job_store.set_status(job_id, job_store.STATUS_QUEUED)
        background_tasks.add_task(JobExecutor.run_real_synthetic, job_id)
        return {"job_id": job_id, "status": job_store.STATUS_QUEUED}

    # Unreachable given job_store.VALID_MODES, but never silently queue an
    # unrecognized mode either.
    raise HTTPException(status_code=400, detail=f"Unsupported job mode: {record.mode!r}")


@router.post("/evaluate/parallel/{job_id}")
def evaluate_parallel(job_id: str, background_tasks: BackgroundTasks):
    """Parallel evaluation - Phase 1 legacy jobs only.

    Phase 2 jobs (any mode) must use POST /evaluate/{job_id} instead; this
    endpoint does not attempt to map Phase 1's three-worker model onto
    querylib's Settings A/B/C, and rejects Phase 2 jobs clearly rather than
    running the wrong pipeline against them.
    """
    record = _require_job_record(job_id)

    if record.mode is not None:
        raise HTTPException(
            status_code=400,
            detail=(
                "The parallel evaluation endpoint is Phase 1 only; "
                f"this job has mode {record.mode!r}. "
                "Use POST /evaluate/{job_id} instead."
            ),
        )

    _check_not_already_running(record)
    _validate_ready_for_legacy_evaluation(job_id)

    job_store.set_status(job_id, job_store.STATUS_QUEUED)
    background_tasks.add_task(JobExecutor.run_parallel, job_id)

    return {"job_id": job_id, "status": job_store.STATUS_QUEUED}
