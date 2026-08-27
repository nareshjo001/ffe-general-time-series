"""
Upload API endpoints.
Handle file uploads for benchmark jobs and update the job status during
the upload process.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.database import job_store
from app.services.job.job_manager import JobManager
from app.services.job.file_manager import FileManager

router = APIRouter()

ALLOWED_EXTENSIONS = {".csv"}
ALLOWED_SPEC_EXTENSIONS = {".yaml", ".yml"}


def _validate_csv(file: UploadFile):
    name = (file.filename or "").lower()
    if not any(name.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail="Only .csv files are accepted"
        )


def _validate_spec_extension(file: UploadFile):
    name = (file.filename or "").lower()
    if not any(name.endswith(ext) for ext in ALLOWED_SPEC_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail="Only .yaml or .yml files are accepted"
        )


def _require_job(job_id: str):
    if not JobManager.job_exists(job_id):
        raise HTTPException(status_code=404, detail="Invalid Job ID")


class CreateJobRequest(BaseModel):
    """Optional Phase 2 job-mode selection.

    `mode` is optional: a request with no body at all (the existing Phase 1
    frontend's exact call pattern - `POST /create-job` with no body) still
    works unchanged and creates a mode-less (legacy) job. A Phase 2 caller
    passes `{"mode": "real_only"}` or `{"mode": "real_synthetic"}` to fix the
    job's mode at creation time, so required uploads are known up front
    rather than inferred later from whichever files happen to be uploaded.
    """
    mode: str | None = None


@router.post("/create-job")
def create_job(body: CreateJobRequest | None = None):
    mode = body.mode if body is not None else None
    try:
        job_id = JobManager.create_job(mode=mode)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"job_id": job_id, "mode": mode}


@router.post("/upload-real/{job_id}")
async def upload_real(job_id: str, file: UploadFile = File(...)):

    _require_job(job_id)

    _validate_csv(file)

    try:
        # save_upload does blocking disk I/O - run it off the event loop
        # so a large upload doesn't stall every other concurrent request.
        await run_in_threadpool(
            FileManager.save_upload, file, JobManager.get_real_csv(job_id)
        )
    except ValueError as e:
        raise HTTPException(status_code=413, detail=str(e))

    job_store.set_status(job_id, job_store.STATUS_UPLOADING)
    return {"message": "Real CSV uploaded"}


@router.post("/upload-synthetic/{job_id}")
async def upload_synthetic(job_id: str, file: UploadFile = File(...)):

    _require_job(job_id)

    # Mode enforcement: a job explicitly created with mode="real_only" has
    # no use for synthetic data - reject clearly rather than silently
    # accepting it (which would leave synthetic.csv on disk for a job whose
    # chosen mode never uses it) or silently switching the job's mode based
    # on file presence (which the mode field exists specifically to avoid).
    # A mode-less (legacy Phase 1, or real_synthetic) job is unaffected.
    record = job_store.get_job(job_id)
    if record is not None and record.mode == job_store.MODE_REAL_ONLY:
        raise HTTPException(
            status_code=400,
            detail=(
                "This job was created with mode 'real_only'; "
                "synthetic data is not accepted for it."
            ),
        )

    _validate_csv(file)

    try:
        await run_in_threadpool(
            FileManager.save_upload, file, JobManager.get_synthetic_csv(job_id)
        )
    except ValueError as e:
        raise HTTPException(status_code=413, detail=str(e))

    job_store.set_status(job_id, job_store.STATUS_UPLOADING)
    return {"message": "Synthetic CSV uploaded"}


@router.post("/upload-spec/{job_id}")
async def upload_spec(job_id: str, file: UploadFile = File(...)):
    """Store a Phase 2 query spec (YAML) for a job.

    This route only saves the file via the same streaming FileManager used
    by the CSV uploads - it does not parse or validate the spec with
    querylib. That happens later, at evaluation pre-flight time.
    """
    _require_job(job_id)

    _validate_spec_extension(file)

    try:
        await run_in_threadpool(
            FileManager.save_upload, file, JobManager.get_spec_path(job_id)
        )
    except ValueError as e:
        raise HTTPException(status_code=413, detail=str(e))

    job_store.set_status(job_id, job_store.STATUS_UPLOADING)
    return {"message": "Spec uploaded"}