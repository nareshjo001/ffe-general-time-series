"""
Job management API endpoints.

Provide endpoints for checking job status, retrieving completed results,
and listing benchmark jobs.
"""

import json
import math

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.database import job_store
from app.services.job.job_manager import JobManager

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _json_safe(value):
    """Recursively replace NaN/Infinity with None."""
    if isinstance(value, float):
        return None if (math.isnan(value) or math.isinf(value)) else value
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


def _try_parse_structured_error(error: str | None) -> dict | None:
    """Phase F.3: opportunistically parse `record.error` as a structured
    preflight error payload (see `preflight.Phase2PreflightError.to_json`/
    `job_executor.py`'s Phase2PreflightError-specific except block).

    Returns the parsed `{"code", "message", "details"}` dict only if
    `error` is valid JSON shaped like one - i.e. only for a Phase 2
    preflight rejection. For every other (legacy "ClassName: message"
    string, or no error at all) case, returns `None` without raising -
    this is purely additive parsing of an existing string field, never a
    schema change, and never breaks the plain `error` string field for
    any existing caller.
    """
    if not error:
        return None
    try:
        parsed = json.loads(error)
    except (ValueError, TypeError):
        return None
    if isinstance(parsed, dict) and {"code", "message"} <= parsed.keys():
        return parsed
    return None


@router.get("/{job_id}/status")
def get_status(job_id: str):
    record = job_store.get_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Invalid Job ID")

    return {
        "job_id": record.job_id,
        "status": record.status,
        "mode": record.mode,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "completed_at": record.completed_at,
        "error": record.error,
        # Phase F.3: structured form of `error` when it's a Phase 2
        # preflight rejection (code/message/details); `None` otherwise
        # (legacy string error, or no error). Purely additive - existing
        # callers that only read `error` are unaffected.
        "error_details": _try_parse_structured_error(record.error),
    }


@router.get("/{job_id}/result")
def get_result(job_id: str):
    record = job_store.get_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Invalid Job ID")

    if record.status == job_store.STATUS_FAILED:
        raise HTTPException(status_code=422, detail=f"Job failed: {record.error}")

    if record.status != job_store.STATUS_DONE:
        raise HTTPException(
            status_code=409,
            detail=f"Job is not finished yet (status: {record.status})",
        )

    result_path = JobManager.get_result_path(job_id)
    if not result_path.exists():
        # Job is marked as complete, but the result file is missing.
        # This indicates an inconsistent job state.
        raise HTTPException(status_code=500, detail="Result file missing for a completed job")

    job_store.mark_result_downloaded(job_id)

    with open(result_path) as f:
        result = json.load(f)

    return JSONResponse(content=_json_safe(result))


@router.get("/{job_id}/curves")
def get_curves(job_id: str):
    """Phase 2 curves.json for a completed job. Not produced by legacy
    Phase 1 (mode=None) jobs - those return 404 here, same as any other
    completed job with no curves file, rather than a separate error shape.
    """
    record = job_store.get_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Invalid Job ID")

    if record.status == job_store.STATUS_FAILED:
        raise HTTPException(status_code=422, detail=f"Job failed: {record.error}")

    if record.status != job_store.STATUS_DONE:
        raise HTTPException(
            status_code=409,
            detail=f"Job is not finished yet (status: {record.status})",
        )

    curves_path = JobManager.get_curves_path(job_id)
    if not curves_path.exists():
        raise HTTPException(status_code=404, detail="Curves not available for this job")

    with open(curves_path) as f:
        curves = json.load(f)

    return JSONResponse(content=_json_safe(curves))


@router.get("")
def list_jobs(status: str | None = None, limit: int = 100):
    """List benchmark jobs for the dashboard."""
    records = job_store.list_jobs(status=status, limit=limit)
    return [
        {
            "job_id": r.job_id,
            "status": r.status,
            "mode": r.mode,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        }
        for r in records
    ]
