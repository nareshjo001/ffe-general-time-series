"""Phase C tests: upload workflows for both Phase 2 job modes.

Route functions (`create_job`, `upload_real`, `upload_synthetic`,
`upload_spec`) are called directly as plain Python/async functions - no
FastAPI TestClient/ASGI server, no new test-only HTTP-client dependency
(`httpx` is not part of the current environment) - `asyncio.run()` drives the
`async def` routes exactly the way FastAPI would, minus the HTTP layer
itself, which none of this logic depends on.

Covers:
    - real-only workflow: real.csv + spec.yaml, no synthetic required
    - real+synthetic workflow: all three artifacts saved correctly
    - synthetic upload to a real_only job is rejected clearly
    - invalid spec file extension is rejected
    - the spec upload path goes through FileManager.save_upload (not a
      second, separate whole-file upload mechanism)
"""
from __future__ import annotations

import asyncio
import io

import pytest
from fastapi import HTTPException, UploadFile


@pytest.fixture
def isolated_job_store(tmp_path, monkeypatch):
    from app.core.config import settings
    from app.database import job_store

    monkeypatch.setattr(settings, "job_db_path", tmp_path / "jobs.db")
    monkeypatch.setattr(settings, "storage_base_dir", tmp_path / "jobs")
    job_store.init_db()
    return job_store


def _upload_file(filename: str, content: bytes = b"a,b,c\n1,2,3\n") -> UploadFile:
    return UploadFile(io.BytesIO(content), filename=filename)


def _run(coro):
    return asyncio.run(coro)


# ============================================================================
#  9 / 18. real-only upload workflow
# ============================================================================
def test_real_only_workflow_saves_real_and_spec_no_synthetic_required(isolated_job_store):
    from app.api.upload import CreateJobRequest, create_job, upload_real, upload_spec
    from app.services.job.job_manager import JobManager

    response = create_job(body=CreateJobRequest(mode="real_only"))
    job_id = response["job_id"]

    _run(upload_real(job_id, _upload_file("real.csv")))
    _run(upload_spec(job_id, _upload_file("spec.yaml", b"dataset:\n  id: ID\n")))

    assert JobManager.get_real_csv(job_id).exists()
    assert JobManager.get_spec_path(job_id).exists()
    assert JobManager.get_real_csv(job_id).read_bytes() == b"a,b,c\n1,2,3\n"
    assert JobManager.get_spec_path(job_id).read_bytes() == b"dataset:\n  id: ID\n"
    # no synthetic upload happened, and none is required for this mode
    assert not JobManager.get_synthetic_csv(job_id).exists()


# ============================================================================
#  10 / 18. real + synthetic upload workflow
# ============================================================================
def test_real_synthetic_workflow_saves_all_three_artifacts(isolated_job_store):
    from app.api.upload import (
        CreateJobRequest,
        create_job,
        upload_real,
        upload_spec,
        upload_synthetic,
    )
    from app.services.job.job_manager import JobManager

    response = create_job(body=CreateJobRequest(mode="real_synthetic"))
    job_id = response["job_id"]

    _run(upload_real(job_id, _upload_file("real.csv", b"real-data\n")))
    _run(upload_synthetic(job_id, _upload_file("synthetic.csv", b"synth-data\n")))
    _run(upload_spec(job_id, _upload_file("spec.yaml", b"dataset: {}\n")))

    assert JobManager.get_real_csv(job_id).read_bytes() == b"real-data\n"
    assert JobManager.get_synthetic_csv(job_id).read_bytes() == b"synth-data\n"
    assert JobManager.get_spec_path(job_id).read_bytes() == b"dataset: {}\n"


# ============================================================================
#  12 / 18. mode enforcement: synthetic upload rejected for real_only
# ============================================================================
def test_synthetic_upload_to_real_only_job_is_rejected(isolated_job_store):
    from app.api.upload import CreateJobRequest, create_job, upload_synthetic
    from app.services.job.job_manager import JobManager

    response = create_job(body=CreateJobRequest(mode="real_only"))
    job_id = response["job_id"]

    with pytest.raises(HTTPException) as exc_info:
        _run(upload_synthetic(job_id, _upload_file("synthetic.csv")))

    assert exc_info.value.status_code == 400
    assert "real_only" in exc_info.value.detail
    # and, critically, nothing was written to disk
    assert not JobManager.get_synthetic_csv(job_id).exists()


def test_synthetic_upload_to_real_synthetic_job_is_allowed(isolated_job_store):
    from app.api.upload import CreateJobRequest, create_job, upload_synthetic
    from app.services.job.job_manager import JobManager

    response = create_job(body=CreateJobRequest(mode="real_synthetic"))
    job_id = response["job_id"]

    _run(upload_synthetic(job_id, _upload_file("synthetic.csv")))
    assert JobManager.get_synthetic_csv(job_id).exists()


def test_synthetic_upload_to_legacy_modeless_job_is_allowed(isolated_job_store):
    """A job created the old way (no mode at all) must behave exactly like
    Phase 1 always did - synthetic upload is never blocked for it."""
    from app.api.upload import create_job, upload_synthetic
    from app.services.job.job_manager import JobManager

    response = create_job(body=None)
    job_id = response["job_id"]

    _run(upload_synthetic(job_id, _upload_file("synthetic.csv")))
    assert JobManager.get_synthetic_csv(job_id).exists()


# ============================================================================
#  18. invalid spec extension rejected
# ============================================================================
def test_spec_upload_rejects_invalid_extension(isolated_job_store):
    from app.api.upload import CreateJobRequest, create_job, upload_spec
    from app.services.job.job_manager import JobManager

    response = create_job(body=CreateJobRequest(mode="real_only"))
    job_id = response["job_id"]

    with pytest.raises(HTTPException) as exc_info:
        _run(upload_spec(job_id, _upload_file("spec.exe", b"not a spec")))

    assert exc_info.value.status_code == 400
    assert not JobManager.get_spec_path(job_id).exists()


def test_spec_upload_accepts_yml_extension_too(isolated_job_store):
    from app.api.upload import CreateJobRequest, create_job, upload_spec
    from app.services.job.job_manager import JobManager

    response = create_job(body=CreateJobRequest(mode="real_only"))
    job_id = response["job_id"]

    _run(upload_spec(job_id, _upload_file("spec.yml", b"dataset: {}\n")))
    assert JobManager.get_spec_path(job_id).exists()


def test_spec_upload_requires_existing_job(isolated_job_store):
    from app.api.upload import upload_spec

    with pytest.raises(HTTPException) as exc_info:
        _run(upload_spec("does-not-exist", _upload_file("spec.yaml")))
    assert exc_info.value.status_code == 404


# ============================================================================
#  19. streaming preservation: spec upload goes through FileManager.save_upload
# ============================================================================
def test_spec_upload_uses_file_manager_save_upload(isolated_job_store, monkeypatch):
    from app.api.upload import CreateJobRequest, create_job, upload_spec
    from app.services.job import file_manager

    calls = []
    original_save_upload = file_manager.FileManager.save_upload

    def _spy_save_upload(file, destination):
        calls.append((file, destination))
        return original_save_upload(file, destination)

    monkeypatch.setattr(file_manager.FileManager, "save_upload", staticmethod(_spy_save_upload))

    response = create_job(body=CreateJobRequest(mode="real_only"))
    job_id = response["job_id"]
    _run(upload_spec(job_id, _upload_file("spec.yaml", b"dataset: {}\n")))

    assert len(calls) == 1
    _, destination = calls[0]
    from app.services.job.job_manager import JobManager
    assert destination == JobManager.get_spec_path(job_id)


# ============================================================================
#  status lifecycle: spec upload follows the existing upload-status pattern
# ============================================================================
def test_spec_upload_sets_status_uploading(isolated_job_store):
    from app.api.upload import CreateJobRequest, create_job, upload_spec
    from app.database import job_store

    response = create_job(body=CreateJobRequest(mode="real_only"))
    job_id = response["job_id"]

    _run(upload_spec(job_id, _upload_file("spec.yaml", b"dataset: {}\n")))

    record = job_store.get_job(job_id)
    assert record.status == job_store.STATUS_UPLOADING
