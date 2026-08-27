"""Phase B tests for `app.services.evaluation2.input_validator`.

Most tests here need no handout/querylib at all - `input_validator` only
depends on pandas, and hand-crafted spec dicts that mirror the *shape*
`handout_adapter.load_spec` returns (documented in querylib/spec.py) are
enough to test required-column extraction and dtype-compatibility rules in
isolation.

A second block of tests (marked and skipped like the Phase A suite when
`BENCHMARK_PHASE2_HANDOUT_DIR` is unset) cross-checks `required_columns`
against the REAL validated spec shape `handout_adapter.load_spec` produces,
for both a single-view spec (demo_small.yaml) and a multi-view spec
(noaa_winner.yaml) - so the hand-crafted assumptions above are not the only
thing being tested.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest

from app.services.evaluation2.input_validator import (
    InputValidationError,
    classify_dtype,
    required_columns,
    validate_csv_header,
    validate_dataframe,
    validate_real_synthetic_schema,
)

_HANDOUT_DIR_ENV = "BENCHMARK_PHASE2_HANDOUT_DIR"


# ============================================================================
#  hand-crafted spec fixtures (shape mirrors querylib/spec.py::validate)
# ============================================================================
def _single_view_spec(measurements=("PRCP", "TMAX", "TMIN"), attrs=("LATITUDE",)):
    return {
        "taxonomy_version": "v3",
        "dataset": {"name": "noaa", "id": "ID", "time": "DATE",
                    "measurements": list(measurements)},
        "groupby": {
            "keys": [{"attr": a, "bin_edges": [0, 40, 90]} for a in attrs],
            "window": {"unit": "month"},
            "agg": {"default": "avg"},
            "fill": "interp",
            "min_len": 12,
        },
        "focus": {"A": [{"group": "largest", "measurement": "TMAX"}], "B": [], "C": []},
        "queries": {"A": ["mean"], "B": [], "C": []},
    }


def _multi_view_spec():
    dataset = {"name": "noaa", "id": "ID", "time": "DATE",
               "measurements": ["PRCP", "TMAX", "TMIN"]}

    def _view(name, attr):
        return {
            "__name": name,
            "dataset": dict(dataset),
            "groupby": {
                "keys": [{"attr": attr, "bin_edges": [0, 40, 90]}],
                "window": {"unit": "month"},
                "agg": {"default": "avg"},
                "fill": "interp",
                "min_len": 12,
            },
            "focus": {"A": [], "B": [], "C": []},
            "queries": {"A": [], "B": [], "C": []},
        }

    return {
        "taxonomy_version": "v3",
        "dataset": dataset,
        "groupbys": [
            _view("latzone", "LATITUDE"),
            _view("elevband", "ELEVATION"),
            _view("latlon_grid", "LATITUDE"),  # duplicate attr across views on purpose
        ],
    }


# ============================================================================
#  4. required-column extraction
# ============================================================================
def test_required_columns_single_view():
    spec = _single_view_spec()
    assert required_columns(spec) == {"ID", "DATE", "PRCP", "TMAX", "TMIN", "LATITUDE"}


def test_required_columns_multi_view():
    spec = _multi_view_spec()
    cols = required_columns(spec)
    # dataset columns (shared across views) + every attr referenced anywhere
    assert cols == {"ID", "DATE", "PRCP", "TMAX", "TMIN", "LATITUDE", "ELEVATION"}


def test_required_columns_duplicate_attr_collapses_to_one_entry():
    # LATITUDE is used by two of the three views in _multi_view_spec(); the
    # result is a set, so it must not appear "twice" in any meaningful sense.
    spec = _multi_view_spec()
    cols = required_columns(spec)
    assert "LATITUDE" in cols
    assert isinstance(cols, set)


def test_required_columns_multiple_measurements():
    spec = _single_view_spec(measurements=("A", "B", "C", "D"))
    cols = required_columns(spec)
    assert {"A", "B", "C", "D"}.issubset(cols)


def test_required_columns_does_not_hardcode_noaa_names():
    spec = _single_view_spec(measurements=("humidity", "windspeed"), attrs=("region",))
    spec["dataset"]["id"] = "sensor_id"
    spec["dataset"]["time"] = "ts"
    cols = required_columns(spec)
    assert cols == {"sensor_id", "ts", "humidity", "windspeed", "region"}


# ============================================================================
#  header-level (cheap) validation
# ============================================================================
def test_validate_csv_header_passes_with_extra_columns(tmp_path):
    csv_path = tmp_path / "real.csv"
    csv_path.write_text("ID,DATE,LATITUDE,TMAX,PRCP,TMIN,EXTRA_METADATA\n1,2020-01-01,10,200,5,100,foo\n")
    validate_csv_header(csv_path, required_columns(_single_view_spec()))


def test_validate_csv_header_missing_columns_raises_friendly_error(tmp_path):
    csv_path = tmp_path / "real.csv"
    # missing LATITUDE and TMAX on purpose
    csv_path.write_text("ID,DATE,PRCP,TMIN\n1,2020-01-01,5,100\n")
    with pytest.raises(InputValidationError) as exc_info:
        validate_csv_header(csv_path, required_columns(_single_view_spec()), label="real dataset")
    msg = str(exc_info.value)
    assert "Missing required columns in real dataset" in msg
    assert "LATITUDE" in msg
    assert "TMAX" in msg
    # never a raw pandas/csv exception type
    assert exc_info.type is InputValidationError


def test_validate_csv_header_empty_file_raises(tmp_path):
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("")
    with pytest.raises(InputValidationError):
        validate_csv_header(csv_path, {"ID"})


# ============================================================================
#  DataFrame-level validation
# ============================================================================
def test_validate_dataframe_passes():
    df = pd.DataFrame({"ID": [1], "DATE": ["2020-01-01"], "LATITUDE": [10.0],
                        "TMAX": [200], "PRCP": [5], "TMIN": [100]})
    validate_dataframe(df, required_columns(_single_view_spec()))  # no raise


def test_validate_dataframe_missing_measurement_raises():
    df = pd.DataFrame({"ID": [1], "DATE": ["2020-01-01"], "LATITUDE": [10.0],
                        "PRCP": [5], "TMIN": [100]})  # TMAX missing
    with pytest.raises(InputValidationError, match="TMAX"):
        validate_dataframe(df, required_columns(_single_view_spec()), label="real dataset")


def test_validate_dataframe_missing_grouping_attribute_raises():
    df = pd.DataFrame({"ID": [1], "DATE": ["2020-01-01"],
                        "TMAX": [200], "PRCP": [5], "TMIN": [100]})  # LATITUDE missing
    with pytest.raises(InputValidationError, match="LATITUDE"):
        validate_dataframe(df, required_columns(_single_view_spec()), label="real dataset")


def test_validate_dataframe_does_not_mutate_input():
    df = pd.DataFrame({"ID": [1], "DATE": ["2020-01-01"], "LATITUDE": [10.0],
                        "TMAX": [200], "PRCP": [5], "TMIN": [100]})
    before = df.copy(deep=True)
    validate_dataframe(df, required_columns(_single_view_spec()))
    pd.testing.assert_frame_equal(df, before)


# ============================================================================
#  dtype classification
# ============================================================================
@pytest.mark.parametrize("dtype", ["int32", "int64", "float32", "float64"])
def test_classify_dtype_numeric_variants(dtype):
    s = pd.Series([1, 2, 3], dtype=dtype)
    assert classify_dtype(s.dtype) == "numeric"


def test_classify_dtype_boolean():
    s = pd.Series([True, False])
    assert classify_dtype(s.dtype) == "boolean"


def test_classify_dtype_datetime():
    s = pd.to_datetime(pd.Series(["2020-01-01", "2020-01-02"]))
    assert classify_dtype(s.dtype) == "datetime"


def test_classify_dtype_string_object():
    s = pd.Series(["a", "b", "c"])
    assert classify_dtype(s.dtype) == "string/object"


def test_classify_dtype_categorical():
    s = pd.Series(["a", "b"]).astype("category")
    assert classify_dtype(s.dtype) == "categorical"


# ============================================================================
#  15. real + synthetic schema validation
# ============================================================================
def test_valid_real_only_dataset_style_columns_present():
    df = pd.DataFrame({"ID": [1, 2], "DATE": ["2020-01-01", "2020-01-02"],
                        "LATITUDE": [10.0, 20.0], "TMAX": [200, 210],
                        "PRCP": [5, 6], "TMIN": [100, 110]})
    validate_dataframe(df, required_columns(_single_view_spec()))


def test_compatible_numeric_dtypes_pass():
    spec = _single_view_spec()
    real = pd.DataFrame({"ID": [1, 2], "DATE": ["a", "b"], "LATITUDE": pd.array([10.0, 20.0], dtype="float64"),
                          "TMAX": [200, 210], "PRCP": [5, 6], "TMIN": [100, 110]})
    synth = pd.DataFrame({"ID": [9, 8], "DATE": ["a", "b"], "LATITUDE": pd.array([10, 20], dtype="int64"),
                           "TMAX": [200, 210], "PRCP": [5, 6], "TMIN": [100, 110]})
    validate_real_synthetic_schema(spec, real, synth)  # float64 vs int64 -> both numeric, OK


def test_incompatible_grouping_dtype_rejected():
    """Reproduces the exact querylib corruption scenario from the handout audit:
    a numeric grouping attribute (LATITUDE) becoming a string on the synthetic
    side must be rejected here, before run_pair() ever sees it."""
    spec = _single_view_spec()
    real = pd.DataFrame({"ID": [1, 2], "DATE": ["a", "b"], "LATITUDE": [10.0, 20.0],
                          "TMAX": [200, 210], "PRCP": [5, 6], "TMIN": [100, 110]})
    synth = pd.DataFrame({"ID": [9, 8], "DATE": ["a", "b"], "LATITUDE": ["10.0", "20.0"],
                           "TMAX": [200, 210], "PRCP": [5, 6], "TMIN": [100, 110]})
    with pytest.raises(InputValidationError) as exc_info:
        validate_real_synthetic_schema(spec, real, synth)
    msg = str(exc_info.value)
    assert "LATITUDE" in msg
    assert "real=numeric" in msg
    assert "synthetic=string/object" in msg


def test_different_entity_ids_pass():
    spec = _single_view_spec()
    real = pd.DataFrame({"ID": [1, 2], "DATE": ["a", "b"], "LATITUDE": [10.0, 20.0],
                          "TMAX": [200, 210], "PRCP": [5, 6], "TMIN": [100, 110]})
    synth = pd.DataFrame({"ID": [101, 102, 103], "DATE": ["a", "b", "c"],
                           "LATITUDE": [11.0, 21.0, 31.0],
                           "TMAX": [201, 211, 221], "PRCP": [5, 6, 7], "TMIN": [101, 111, 121]})
    validate_real_synthetic_schema(spec, real, synth)  # disjoint IDs -> still OK


def test_different_row_counts_pass():
    spec = _single_view_spec()
    real = pd.DataFrame({"ID": [1, 2, 3], "DATE": ["a", "b", "c"], "LATITUDE": [10.0, 20.0, 30.0],
                          "TMAX": [200, 210, 220], "PRCP": [5, 6, 7], "TMIN": [100, 110, 120]})
    synth = pd.DataFrame({"ID": [9], "DATE": ["a"], "LATITUDE": [10.0],
                           "TMAX": [200], "PRCP": [5], "TMIN": [100]})
    validate_real_synthetic_schema(spec, real, synth)  # 3 rows vs 1 row -> still OK


def test_extra_unreferenced_columns_pass():
    spec = _single_view_spec()
    real = pd.DataFrame({"ID": [1], "DATE": ["a"], "LATITUDE": [10.0],
                          "TMAX": [200], "PRCP": [5], "TMIN": [100], "EXTRA_METADATA": ["x"]})
    synth = pd.DataFrame({"ID": [9], "DATE": ["a"], "LATITUDE": [10.0],
                           "TMAX": [200], "PRCP": [5], "TMIN": [100], "SOME_OTHER_COLUMN": [1]})
    validate_real_synthetic_schema(spec, real, synth)


def test_missing_column_on_synthetic_side_reported():
    spec = _single_view_spec()
    real = pd.DataFrame({"ID": [1], "DATE": ["a"], "LATITUDE": [10.0],
                          "TMAX": [200], "PRCP": [5], "TMIN": [100]})
    synth = pd.DataFrame({"ID": [9], "DATE": ["a"], "LATITUDE": [10.0],
                           "TMAX": [200], "PRCP": [5]})  # TMIN missing
    with pytest.raises(InputValidationError, match="synthetic dataset"):
        validate_real_synthetic_schema(spec, real, synth)


# ============================================================================
#  cross-check against the REAL validated spec shape (skipped if handout unset)
# ============================================================================
def _handout_dir() -> Path | None:
    raw = os.environ.get(_HANDOUT_DIR_ENV)
    return Path(raw) if raw else None


@pytest.mark.skipif(
    _handout_dir() is None,
    reason=f"{_HANDOUT_DIR_ENV} is not set - skipping real-spec cross-check.",
)
class TestAgainstRealHandoutSpecs:
    def test_required_columns_matches_real_demo_small_spec(self):
        from app.core.config import settings
        from app.services.evaluation2 import handout_adapter as A

        original = settings.phase2_handout_dir
        settings.phase2_handout_dir = _handout_dir()
        try:
            spec = A.load_spec(_handout_dir() / "specs" / "demo_small.yaml")
        finally:
            settings.phase2_handout_dir = original

        assert required_columns(spec) == {"ID", "DATE", "PRCP", "TMAX", "TMIN", "LATITUDE"}

    def test_required_columns_matches_real_noaa_winner_spec(self):
        from app.core.config import settings
        from app.services.evaluation2 import handout_adapter as A

        original = settings.phase2_handout_dir
        settings.phase2_handout_dir = _handout_dir()
        try:
            spec = A.load_spec(_handout_dir() / "specs" / "noaa_winner.yaml")
        finally:
            settings.phase2_handout_dir = original

        cols = required_columns(spec)
        assert {"ID", "DATE", "PRCP", "TMAX", "TMIN"}.issubset(cols)
        assert {"LATITUDE", "LONGITUDE", "ELEVATION"}.issubset(cols)

    def test_corrupted_synthetic_dtype_is_rejected_before_run_pair(self):
        """18. Critical correctness test: reproduce the exact corruption
        scenario from the Phase 2 handout audit using the REAL bundled
        real/synthetic sample and the REAL validated spec, and confirm
        `validate_real_synthetic_schema` rejects it BEFORE `run_pair` is ever
        called - not after. Steven's files on disk are never touched; only an
        in-memory copy of the loaded synthetic DataFrame is corrupted.
        """
        from app.core.config import settings
        from app.services.evaluation2 import handout_adapter as A

        handout_dir = _handout_dir()
        original = settings.phase2_handout_dir
        settings.phase2_handout_dir = handout_dir
        try:
            spec = A.load_spec(handout_dir / "specs" / "demo_small.yaml")
            real_df, cfg = A.load_panel(handout_dir / "examples" / "data" / "noaa_sample")
            real_df = A.subsample_panel(real_df, cfg["id"], n=40)
            synth_df, _ = A.load_panel(
                handout_dir / "examples" / "data" / "synthetic_wavestitch_sample.csv"
            )

            # in-memory corruption only - never written back to disk
            corrupted_synth = synth_df.copy(deep=True)
            corrupted_synth["LATITUDE"] = corrupted_synth["LATITUDE"].astype(str)

            with pytest.raises(InputValidationError) as exc_info:
                validate_real_synthetic_schema(spec, real_df, corrupted_synth)
            msg = str(exc_info.value)
            assert "LATITUDE" in msg
            assert "real=numeric" in msg
            assert "synthetic=string/object" in msg

            # sanity: the ORIGINAL (uncorrupted) synthetic sample passes,
            # proving the rejection above is specifically about the
            # corruption, not a false positive on this dataset/spec pair.
            validate_real_synthetic_schema(spec, real_df, synth_df)
        finally:
            settings.phase2_handout_dir = original
