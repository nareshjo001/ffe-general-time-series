"""The ONLY place in this application that locates and imports Steven's
`handout_lib` (and, transitively, the `querylib` package it wraps).

Steven's corrected handout is never copied into this repository (its
redistribution/license status is unresolved - see the Phase 2 handout audit).
Instead, the directory containing `handout_lib.py` and `querylib/` is located
via the `phase2_handout_dir` application setting (env var
`BENCHMARK_PHASE2_HANDOUT_DIR`), which a developer/operator points at wherever
the delivered handout actually lives on disk.

Nothing outside this module should touch `sys.path` for this purpose, and
nothing in this application should ever `import querylib` directly - only
`import handout_lib` (done here, once) is allowed. `handout_lib.py` imports
`querylib` internally; that is expected and is Steven's concern, not ours.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

from app.core.config import settings


class HandoutUnavailableError(RuntimeError):
    """Raised when Steven's handout cannot be located or imported.

    This is the one application-level error this module produces; it always
    preserves the underlying cause (missing path / missing file / missing
    dependency) so the real reason is never hidden from logs or callers.
    """


_handout_lib: ModuleType | None = None


def _resolve_handout_dir() -> Path:
    handout_dir = settings.phase2_handout_dir
    if handout_dir is None:
        raise HandoutUnavailableError(
            "phase2_handout_dir is not configured. Set the "
            "BENCHMARK_PHASE2_HANDOUT_DIR environment variable (or the "
            ".env equivalent) to the directory containing handout_lib.py "
            "and querylib/."
        )
    if not handout_dir.exists():
        raise HandoutUnavailableError(
            f"Configured phase2_handout_dir does not exist: {handout_dir}"
        )
    if not handout_dir.is_dir():
        raise HandoutUnavailableError(
            f"Configured phase2_handout_dir is not a directory: {handout_dir}"
        )

    handout_lib_path = handout_dir / "handout_lib.py"
    if not handout_lib_path.is_file():
        raise HandoutUnavailableError(
            f"handout_lib.py was not found in phase2_handout_dir: {handout_dir}"
        )

    querylib_dir = handout_dir / "querylib"
    if not querylib_dir.is_dir() or not any(querylib_dir.glob("*.py")):
        raise HandoutUnavailableError(
            f"querylib/ was not found (or is empty) alongside handout_lib.py "
            f"in phase2_handout_dir: {handout_dir}"
        )

    return handout_dir


def load_handout() -> ModuleType:
    """Import and cache Steven's `handout_lib` module.

    Safe to call repeatedly - after the first successful call, the cached
    module is returned without re-running path resolution or re-importing.

    Raises:
        HandoutUnavailableError: if the configured directory, handout_lib.py,
            or querylib/ cannot be found, or if importing handout_lib fails
            (e.g. because a dependency such as pandas/numpy/pyyaml is
            missing). The original exception is always chained via
            ``raise ... from exc`` so the underlying cause is preserved.
    """
    global _handout_lib
    if _handout_lib is not None:
        return _handout_lib

    handout_dir = _resolve_handout_dir()

    handout_dir_str = str(handout_dir)
    if handout_dir_str not in sys.path:
        # handout_lib.py itself adds its parent directory to sys.path (that is
        # where the bundled querylib/ package lives, per its own docstring) -
        # we only need to make handout_lib.py itself importable by name.
        sys.path.insert(0, handout_dir_str)

    try:
        import handout_lib  # noqa: E402  (import must follow sys.path setup)
    except ImportError as exc:
        raise HandoutUnavailableError(
            "Failed to import handout_lib - a required dependency is likely "
            f"missing from this environment (see requirements-dashboard.txt "
            f"in {handout_dir}). Underlying error: {exc}"
        ) from exc

    _handout_lib = handout_lib
    return _handout_lib


def is_loaded() -> bool:
    """True once `load_handout()` has succeeded at least once in this process."""
    return _handout_lib is not None
