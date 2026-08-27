"""Phase A boundary tests: prove that
    Phase 1 Python environment -> our adapter -> real handout_lib -> real querylib
actually works, end to end, against Steven's bundled NOAA demo sample.

These tests are deliberately isolated from the rest of the Phase 1 application:
no job creation, no DuckDB, no FastAPI endpoints, no SQLite job records, no
upload routes, no Phase 1 query runners, no Phase 2 stub. They only import
`app.core.config` (for the `phase2_handout_dir` setting) and
`app.services.evaluation2.*` (the new adapter/bootstrap modules).

Requires the `BENCHMARK_PHASE2_HANDOUT_DIR` environment variable to point at a
directory containing `handout_lib.py` and `querylib/` (Steven's corrected
handout), plus a bundled sample dataset under
`<handout_dir>/examples/data/noaa_sample/` (data.csv + config.json) and
`<handout_dir>/examples/data/synthetic_wavestitch_sample.csv`. If that env var
is not set, every test in this module is skipped rather than failed - this
module proves the boundary works when the handout is available, it does not
assert the handout must always be present.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from app.core.config import settings
from app.services.evaluation2 import handout_adapter as A
from app.services.evaluation2.handout_bootstrap import (
    HandoutUnavailableError,
    load_handout,
)

_HANDOUT_DIR_ENV = "BENCHMARK_PHASE2_HANDOUT_DIR"


def _handout_dir() -> Path | None:
    raw = os.environ.get(_HANDOUT_DIR_ENV)
    return Path(raw) if raw else None


pytestmark = pytest.mark.skipif(
    _handout_dir() is None,
    reason=(
        f"{_HANDOUT_DIR_ENV} is not set - point it at a directory containing "
        "handout_lib.py and querylib/ to run the Phase 2 boundary tests."
    ),
)


@pytest.fixture(scope="module", autouse=True)
def _configure_handout_dir():
    """Point Settings at the handout dir for this test module only."""
    original = settings.phase2_handout_dir
    settings.phase2_handout_dir = _handout_dir()
    yield
    settings.phase2_handout_dir = original


@pytest.fixture(scope="module")
def spec_path() -> Path:
    return _handout_dir() / "specs" / "demo_small.yaml"


@pytest.fixture(scope="module")
def real_dataset_dir() -> Path:
    return _handout_dir() / "examples" / "data" / "noaa_sample"


@pytest.fixture(scope="module")
def synth_csv_path() -> Path:
    return _handout_dir() / "examples" / "data" / "synthetic_wavestitch_sample.csv"


@pytest.fixture(scope="module")
def spec(spec_path) -> dict:
    return A.load_spec(spec_path)


@pytest.fixture(scope="module")
def real_df(real_dataset_dir):
    df, cfg = A.load_panel(real_dataset_dir)
    return A.subsample_panel(df, cfg["id"], n=40)


@pytest.fixture(scope="module")
def synth_df(real_df, synth_csv_path, real_dataset_dir):
    _, cfg = A.load_panel(real_dataset_dir)
    df, _ = A.load_panel(synth_csv_path)
    # NOTE: no entity-ID filtering/alignment here on purpose - run_pair does not
    # require matching entity IDs between real and synthetic (verified in the
    # Phase 2 handout audit). We deliberately do NOT reproduce the old
    # prototype's `synth[synth[id_col].isin(set(real[id_col]))]` filtering.
    return df


# --- A. engine load --------------------------------------------------------
def test_engine_loads_through_bootstrap():
    handout_lib = load_handout()
    assert hasattr(handout_lib, "load_spec")
    assert hasattr(handout_lib, "run_pair")
    # calling again must return the cached module, not re-import
    assert load_handout() is handout_lib


def test_bootstrap_raises_clear_error_when_unconfigured(monkeypatch):
    from app.services.evaluation2 import handout_bootstrap as boot

    monkeypatch.setattr(settings, "phase2_handout_dir", None)
    monkeypatch.setattr(boot, "_handout_lib", None)
    with pytest.raises(HandoutUnavailableError, match="not configured"):
        boot.load_handout()


# --- B. spec -----------------------------------------------------------
def test_load_spec_succeeds(spec):
    assert isinstance(spec, dict)
    assert "dataset" in spec
    assert "queries" in spec or "groupbys" in spec


# --- C. panel ------------------------------------------------------------
def test_load_panel_reads_real_dataset(real_dataset_dir):
    df, cfg = A.load_panel(real_dataset_dir)
    assert len(df) > 0
    assert cfg is not None
    assert cfg["id"] in df.columns


def test_load_panel_reads_bare_csv(synth_csv_path):
    df, cfg = A.load_panel(synth_csv_path)
    assert len(df) > 0
    assert cfg is None


# --- D. enumeration --------------------------------------------------------
def test_enumerate_instances_static_matches_25(spec):
    # cheapest correct path: no real_df -> data-free layout preview, no battery run.
    instances = A.enumerate_instances(spec)
    assert len(instances) == 25
    for col in ("instance_id", "view", "setting", "family", "qid", "focus"):
        assert col in instances.columns


# --- E. real-only ------------------------------------------------------
def test_run_real_produces_25_rows_with_expected_columns(spec, real_df):
    t0 = time.perf_counter()
    df = A.run_real(spec, real_df)
    elapsed_first = time.perf_counter() - t0

    assert len(df) == 25
    for col in ("instance_id", "setting", "family", "qid", "focus", "kind",
                "value", "value_summary"):
        assert col in df.columns
    assert df["kind"].notna().all()

    t1 = time.perf_counter()
    A.run_real(spec, real_df)
    elapsed_second = time.perf_counter() - t1

    print(f"\n[run_real timing] first call: {elapsed_first:.2f}s, "
          f"second call (same process): {elapsed_second:.2f}s")


# --- F. self-check -----------------------------------------------------
def test_self_check_is_zero_on_clean_real_data(spec, real_df):
    score = A.self_check(spec, real_df)
    assert score == 0.0


# --- G. real + synthetic -------------------------------------------------
def test_run_pair_scores_within_unit_interval(spec, real_df, synth_df):
    df = A.run_pair(spec, real_df, synth_df)
    assert len(df) == 25
    for col in ("instance_id", "setting", "family", "qid", "focus", "kind",
                "real_value", "synth_value", "real_summary", "synth_summary",
                "distance"):
        assert col in df.columns
    assert (df["distance"] >= 0.0).all()
    assert (df["distance"] <= 1.0).all()


# --- H. curves -----------------------------------------------------------
def test_group_series_produces_expected_columns(spec, real_df):
    curves = A.group_series(spec, real_df)
    for col in ("view", "group", "measurement", "bin", "time_label", "real", "synth"):
        assert col in curves.columns
    # the prior runtime audit observed 540 rows for demo_small.yaml + the
    # bundled 40-station sample; assert against actual execution, not just
    # the number restated from that audit.
    print(f"\n[group_series] {len(curves)} rows (prior audit observed 540)")
    assert len(curves) > 0
