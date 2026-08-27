"""Filesystem persistence for Phase 2 evaluation results.

Responsibility is deliberately narrow: write already-serialized (JSON-safe)
data to disk. Does not call `serialize`/`handout_adapter` itself, does not
know about job status, and does not decide *where* a job's files live
(callers pass an explicit path, resolved via `JobManager`).

Uses `json.dump(..., allow_nan=False)` - never `default=str` - so that if a
serialization bug somehow lets a NaN/Infinity/non-JSON-safe value through,
persistence fails loudly here instead of silently writing invalid JSON
tokens (`NaN`, `Infinity`, `-Infinity`) that a strict downstream JSON parser
would reject.

ATOMICITY (Phase F.1)
----------------------
Both writers go through ``_atomic_write_json``: the JSON payload is written
in full to a temporary file in the *same* output directory as the final
path, then ``os.replace(temp_path, final_path)`` swaps it into place.
``os.replace`` is atomic on both POSIX and Windows as long as the temp file
and the destination are on the same volume, which is guaranteed here since
the temp file is created directly inside ``final_path.parent``.

This guarantees a reader (or a subsequent writer) never observes a
truncated/partially-written file under the final name - the final path
either still holds the previous complete file, or already holds the new
complete file; there is no state in between visible under that name. This
protects against a Python-level exception or process crash happening while
the JSON is still being written. It intentionally does NOT add `fsync`/
directory-fsync durability against an OS or hardware crash losing
already-"written" data still sitting in the OS page cache - that is a
separate, lower-probability failure mode not in scope for Phase F.1 (see the
Phase F.0 audit's atomic-persistence recommendation).

If writing the temp file fails for any reason (a serialization error inside
`json.dump`, a disk-full condition, etc.), the temp file is removed on a
best-effort basis and the final path is left completely untouched - the
previous file (if any) survives unmodified. Temp-file cleanup failures are
swallowed rather than allowed to mask the original write error.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def _atomic_write_json(path: Path, data: Any) -> None:
    """Write ``data`` to ``path`` as strict JSON (``allow_nan=False``),
    atomically: a temp file in ``path.parent`` is fully written first, then
    swapped into place via ``os.replace``. See the module docstring for the
    exact guarantees and the fsync/durability scope decision.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, allow_nan=False)
        os.replace(tmp_path, path)
    except Exception:
        # Best-effort cleanup only - a failure here (e.g. the temp file was
        # already removed by something else) must never hide the original
        # write/serialization exception that got us into this branch.
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise


def write_result(result_path: Path, result: dict[str, Any]) -> None:
    """Write a Phase 2 result dict to ``result_path`` as strict JSON,
    atomically (see module docstring)."""
    _atomic_write_json(result_path, result)


def write_curves(curves_path: Path, curves: list[dict[str, Any]]) -> None:
    """Write a Phase 2 curves list to ``curves_path`` as strict JSON,
    atomically (see module docstring)."""
    _atomic_write_json(curves_path, curves)


__all__ = ["write_result", "write_curves"]
