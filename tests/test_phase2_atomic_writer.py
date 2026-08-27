"""Phase F.1 tests: services/evaluation2/result_writer.py's atomic
temp-file + os.replace write behavior for outputs/result.json and
outputs/curves.json.

Covers: successful writes, replacing an existing destination file only after
the new temp file is fully written, a failure before os.replace leaving the
final path completely untouched (previous file survives unmodified, no stale
temp file left behind), and that allow_nan=False strictness is unchanged.
"""
from __future__ import annotations

import json
import math

import pytest

from app.services.evaluation2 import result_writer


# ============================================================================
#  A / B. successful result / curves writes
# ============================================================================
def test_write_result_creates_valid_strict_json(tmp_path):
    path = tmp_path / "outputs" / "result.json"
    result_writer.write_result(path, {"mode": "real_only", "instances": [], "metadata": {"instance_count": 0}})

    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["mode"] == "real_only"


def test_write_curves_creates_valid_strict_json(tmp_path):
    path = tmp_path / "outputs" / "curves.json"
    result_writer.write_curves(path, [{"view": "A", "real": 1.0, "synth": None}])

    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == [{"view": "A", "real": 1.0, "synth": None}]


def test_write_creates_parent_directory(tmp_path):
    path = tmp_path / "does" / "not" / "exist" / "result.json"
    result_writer.write_result(path, {"mode": "real_only"})
    assert path.exists()


# ============================================================================
#  E / 16. existing-file replacement: destination replaced only after temp
#  file is fully written; the old file's content is never visible merged
#  with the new one, and no earlier partial state is exposed.
# ============================================================================
def test_successful_write_replaces_existing_destination(tmp_path):
    path = tmp_path / "result.json"
    result_writer.write_result(path, {"mode": "real_only", "version": 1})
    assert json.loads(path.read_text())["version"] == 1

    result_writer.write_result(path, {"mode": "real_only", "version": 2})
    assert json.loads(path.read_text())["version"] == 2


def test_no_temp_file_left_behind_after_successful_write(tmp_path):
    path = tmp_path / "result.json"
    result_writer.write_result(path, {"mode": "real_only"})

    remaining = list(tmp_path.iterdir())
    assert remaining == [path], f"unexpected leftover files: {remaining}"


# ============================================================================
#  C / D / F. failure before os.replace: final path untouched, temp file
#  cleaned up, original exception not masked
# ============================================================================
def test_json_dump_failure_leaves_final_path_absent_when_no_prior_file(tmp_path, monkeypatch):
    path = tmp_path / "result.json"
    assert not path.exists()

    def boom(*args, **kwargs):
        raise TypeError("simulated unsupported type during json.dump")

    monkeypatch.setattr(json, "dump", boom)

    with pytest.raises(TypeError, match="simulated unsupported type"):
        result_writer.write_result(path, {"mode": "real_only"})

    assert not path.exists()
    # no stale temp file left in the directory either
    assert list(tmp_path.iterdir()) == []


def test_write_failure_leaves_existing_valid_destination_unchanged(tmp_path, monkeypatch):
    """D: existing valid destination + a replacement write that fails before
    os.replace must leave the previous file completely intact."""
    path = tmp_path / "result.json"
    result_writer.write_result(path, {"mode": "real_only", "version": "original"})
    original_bytes = path.read_bytes()

    def boom(*args, **kwargs):
        raise TypeError("simulated failure during replacement write")

    monkeypatch.setattr(json, "dump", boom)

    with pytest.raises(TypeError, match="simulated failure during replacement write"):
        result_writer.write_result(path, {"mode": "real_only", "version": "corrupted-attempt"})

    # previous file is byte-for-byte unchanged
    assert path.read_bytes() == original_bytes
    assert json.loads(path.read_text())["version"] == "original"

    # F: no stale temp file left behind after the handled failure
    remaining = [p for p in tmp_path.iterdir() if p != path]
    assert remaining == [], f"stale temp file(s) left behind: {remaining}"


def test_os_replace_failure_does_not_mask_original_write_error(tmp_path, monkeypatch):
    """If temp-file cleanup itself fails after a write error, the original
    exception must still propagate, not the cleanup error."""
    path = tmp_path / "result.json"

    def boom_dump(*args, **kwargs):
        raise ValueError("original write failure")

    monkeypatch.setattr(json, "dump", boom_dump)

    import pathlib

    original_unlink = pathlib.Path.unlink

    def boom_unlink(self, *args, **kwargs):
        if self.name.startswith(".result.json."):
            raise OSError("simulated cleanup failure")
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "unlink", boom_unlink)

    with pytest.raises(ValueError, match="original write failure"):
        result_writer.write_result(path, {"mode": "real_only"})


# ============================================================================
#  strict JSON preservation (allow_nan=False, no default=str)
# ============================================================================
def test_atomic_write_still_enforces_allow_nan_false(tmp_path):
    path = tmp_path / "result.json"
    with pytest.raises(ValueError):
        result_writer.write_result(path, {"value": math.nan})

    # a rejected NaN write must not leave any file (nothing was ever valid
    # to replace the destination with)
    assert not path.exists()


def test_atomic_write_does_not_stringify_unsupported_types(tmp_path):
    """No default=str fallback - an object json.dump can't natively handle
    must still raise, not silently become a string."""
    path = tmp_path / "result.json"

    class Unsupported:
        pass

    with pytest.raises(TypeError):
        result_writer.write_result(path, {"value": Unsupported()})

    assert not path.exists()


# ============================================================================
#  temp file uses the same directory/volume as the destination
# ============================================================================
def test_temp_file_is_created_in_same_directory_as_destination(tmp_path, monkeypatch):
    path = tmp_path / "result.json"
    seen_dirs = []

    import tempfile as tempfile_module

    original_mkstemp = tempfile_module.mkstemp

    def spy_mkstemp(*args, **kwargs):
        seen_dirs.append(kwargs.get("dir"))
        return original_mkstemp(*args, **kwargs)

    monkeypatch.setattr(result_writer.tempfile, "mkstemp", spy_mkstemp)

    result_writer.write_result(path, {"mode": "real_only"})

    assert seen_dirs == [str(tmp_path)]


# ============================================================================
#  19. JobExecutor regression: an output-write failure must still surface as
#  STATUS_FAILED through the existing exception lifecycle, not a new status.
# ============================================================================
def test_curves_write_failure_marks_job_failed_via_job_executor(tmp_path, monkeypatch):
    from app.core.config import settings
    from app.database import job_store
    from app.services.job import job_executor
    from app.services.job.job_executor import JobExecutor
    from app.services.job.job_manager import JobManager

    monkeypatch.setattr(settings, "job_db_path", tmp_path / "jobs.db")
    monkeypatch.setattr(settings, "storage_base_dir", tmp_path / "jobs")
    job_store.init_db()

    job_id = JobManager.create_job(mode="real_only")
    JobManager.get_upload_dir(job_id).mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        job_executor.evaluation_service,
        "run_real_only",
        lambda *a, **k: {
            "result": {"mode": "real_only", "overview": {}, "instances": [], "metadata": {"instance_count": 0}},
            "curves": [],
        },
    )
    monkeypatch.setattr(job_executor.result_writer, "write_result", lambda *a, **k: None)

    def boom_write_curves(*a, **k):
        raise OSError("simulated disk failure writing curves.json")

    monkeypatch.setattr(job_executor.result_writer, "write_curves", boom_write_curves)

    with pytest.raises(OSError, match="simulated disk failure"):
        JobExecutor.run_real_only(job_id)

    record = job_store.get_job(job_id)
    assert record.status == job_store.STATUS_FAILED
    assert "simulated disk failure" in record.error
    # no new status was introduced for this failure mode
    assert record.status in (job_store.STATUS_DONE, job_store.STATUS_FAILED)
