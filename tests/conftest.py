"""Pytest bootstrap: make the `app` package importable exactly like `main.py`
does (i.e. by running with `backend/` on sys.path), without requiring the
project to be installed as a package or adding a pyproject.toml/pytest.ini.
"""
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))
