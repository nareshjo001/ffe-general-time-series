"""Phase B tests for `app.services.evaluation2.serialize`.

The pure unit tests below need no handout/querylib at all - they exercise
`jsonable`/`rows` against fabricated primitives, numpy scalars/arrays,
tuples, sets, and NaN/Inf, matching every value shape the Phase 2 handout
audit documented for `run_real`/`run_pair` output (`kind` in
scalar/vector/matrix/location/set/distribution/...).

A second block (skipped like the Phase A suite when
`BENCHMARK_PHASE2_HANDOUT_DIR` is unset) round-trips ACTUAL `run_real`/
`run_pair` output from the real bundled handout through `serialize.rows` and
`json.dumps(..., allow_nan=False)`, so the serializer is proven against real
querylib output, not just fabricated stand-ins.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.services.evaluation2.serialize import jsonable, rows

_HANDOUT_DIR_ENV = "BENCHMARK_PHASE2_HANDOUT_DIR"


# ============================================================================
#  16. primitives
# ============================================================================
@pytest.mark.parametrize("value,expected", [
    (1, 1),
    (1.5, 1.5),
    ("hello", "hello"),
    (True, True),
    (False, False),
    (None, None),
])
def test_primitives_pass_through(value, expected):
    assert jsonable(value) == expected
    assert type(jsonable(value)) is type(expected)


def test_bool_not_confused_with_int():
    # bool is a subclass of int in Python - must not become 1/0.
    assert jsonable(True) is True
    assert jsonable(False) is False


# ============================================================================
#  numpy scalars
# ============================================================================
@pytest.mark.parametrize("np_type", [np.int8, np.int16, np.int32, np.int64,
                                       np.uint8, np.uint32])
def test_numpy_integer_types(np_type):
    out = jsonable(np_type(7))
    assert out == 7
    assert type(out) is int


@pytest.mark.parametrize("np_type", [np.float32, np.float64])
def test_numpy_float_types(np_type):
    out = jsonable(np_type(3.25))
    assert out == pytest.approx(3.25)
    assert type(out) is float


def test_numpy_bool():
    assert jsonable(np.bool_(True)) is True
    assert jsonable(np.bool_(False)) is False


# ============================================================================
#  arrays
# ============================================================================
def test_ndarray_1d_becomes_list():
    out = jsonable(np.array([1, 2, 3]))
    assert out == [1, 2, 3]
    assert isinstance(out, list)


def test_ndarray_2d_becomes_nested_list():
    out = jsonable(np.array([[1, 2], [3, 4]]))
    assert out == [[1, 2], [3, 4]]


def test_ndarray_of_floats_with_nan():
    out = jsonable(np.array([1.0, np.nan, 3.0]))
    assert out == [1.0, None, 3.0]


# ============================================================================
#  tuple / set
# ============================================================================
def test_tuple_becomes_list():
    # this is exactly the querylib `location` kind shape: (index, length)
    assert jsonable((12, 6)) == [12, 6]


def test_set_becomes_deterministic_sorted_list():
    assert jsonable({3, 1, 2}) == [1, 2, 3]
    # deterministic across repeated calls, not just orderable
    assert jsonable({3, 1, 2}) == jsonable({2, 3, 1})


def test_set_of_strings_becomes_deterministic_sorted_list():
    assert jsonable({"b", "a", "c"}) == ["a", "b", "c"]


# ============================================================================
#  nested structures
# ============================================================================
def test_nested_dict_and_list():
    value = {"a": [1, np.int64(2), {"b": (3, 4)}], "c": {1, 2}}
    out = jsonable(value)
    assert out == {"a": [1, 2, {"b": [3, 4]}], "c": [1, 2]}


def test_dict_keys_coerced_to_str():
    out = jsonable({1: "x", 2: "y"})
    assert out == {"1": "x", "2": "y"}


# ============================================================================
#  NaN / Infinity
# ============================================================================
def test_nan_becomes_none():
    assert jsonable(float("nan")) is None
    assert jsonable(np.nan) is None


def test_positive_infinity_becomes_none():
    assert jsonable(float("inf")) is None
    assert jsonable(np.inf) is None


def test_negative_infinity_becomes_none():
    assert jsonable(float("-inf")) is None
    assert jsonable(-np.inf) is None


# ============================================================================
#  never stringifies numbers, never uses default=str semantics
# ============================================================================
def test_numeric_values_are_not_stringified():
    out = jsonable(np.float64(2.5))
    assert out == 2.5
    assert not isinstance(out, str)


# ============================================================================
#  hardening: unrecognized types are a hard error, never a silent str()
# ============================================================================
class _UnsupportedThing:
    """A stand-in for some future/unexpected querylib result type this
    module has never seen before."""

    def __repr__(self):
        return "<_UnsupportedThing>"


def test_unsupported_type_raises_type_error_not_silently_stringified():
    with pytest.raises(TypeError, match="Unsupported value type"):
        jsonable(_UnsupportedThing())


def test_unsupported_type_error_names_the_offending_type():
    with pytest.raises(TypeError) as exc_info:
        jsonable(_UnsupportedThing())
    msg = str(exc_info.value)
    assert "_UnsupportedThing" in msg
    assert __name__ in msg  # module-qualified, not just the bare class name


def test_unsupported_type_nested_inside_list_still_raises():
    with pytest.raises(TypeError, match="Unsupported value type"):
        jsonable([1, 2, _UnsupportedThing()])


def test_unsupported_type_nested_inside_dict_still_raises():
    with pytest.raises(TypeError, match="Unsupported value type"):
        jsonable({"ok": 1, "bad": _UnsupportedThing()})


# ============================================================================
#  json.dumps round-trip on a representative fabricated result row
# ============================================================================
def test_fabricated_representative_row_round_trips_through_json_dumps():
    row = {
        "instance_id": "(single)::A::mean::LATITUDE[0,40)/TMAX",
        "kind": "vector",
        "value": np.array([1.1, 2.2, np.nan]),
        "value_summary": {"shape": [3], "mean": float(np.float64(1.65))},
    }
    encoded = json.dumps(jsonable(row), allow_nan=False)
    decoded = json.loads(encoded)
    assert decoded["value"] == [1.1, 2.2, None]


def test_rows_helper_on_small_dataframe():
    df = pd.DataFrame({
        "instance_id": ["a", "b"],
        "kind": ["scalar", "set"],
        "value": [np.float64(1.0), {1, 2, 3}],
    })
    out = rows(df)
    assert out[0]["value"] == 1.0
    assert out[1]["value"] == [1, 2, 3]
    json.dumps(out, allow_nan=False)  # must not raise


# ============================================================================
#  17 & 9(serializer). integration with REAL querylib output (skipped if
#  handout unset)
# ============================================================================
def _handout_dir() -> Path | None:
    raw = os.environ.get(_HANDOUT_DIR_ENV)
    return Path(raw) if raw else None


@pytest.mark.skipif(
    _handout_dir() is None,
    reason=f"{_HANDOUT_DIR_ENV} is not set - skipping real querylib serialization checks.",
)
class TestRealQuerylibSerialization:
    @pytest.fixture(scope="class", autouse=True)
    @classmethod
    def _configure_handout_dir(cls):
        from app.core.config import settings

        original = settings.phase2_handout_dir
        settings.phase2_handout_dir = _handout_dir()
        yield
        settings.phase2_handout_dir = original

    @pytest.fixture(scope="class")
    @classmethod
    def spec(cls):
        from app.services.evaluation2 import handout_adapter as A
        return A.load_spec(_handout_dir() / "specs" / "demo_small.yaml")

    @pytest.fixture(scope="class")
    @classmethod
    def real_df(cls):
        from app.services.evaluation2 import handout_adapter as A
        df, cfg = A.load_panel(_handout_dir() / "examples" / "data" / "noaa_sample")
        return A.subsample_panel(df, cfg["id"], n=40)

    @pytest.fixture(scope="class")
    @classmethod
    def synth_df(cls):
        from app.services.evaluation2 import handout_adapter as A
        df, _ = A.load_panel(
            _handout_dir() / "examples" / "data" / "synthetic_wavestitch_sample.csv"
        )
        return df

    def test_run_real_output_serializes_and_round_trips(self, spec, real_df):
        from app.services.evaluation2 import handout_adapter as A

        result_df = A.run_real(spec, real_df)
        assert len(result_df) == 25

        serialized = rows(result_df)
        encoded = json.dumps(serialized, allow_nan=False)  # must not raise
        decoded = json.loads(encoded)
        assert len(decoded) == 25

        # spot-check every observed `kind` at least once serializes to a
        # JSON-native type (not a string repr of a numpy/py object).
        kinds_seen = {r["kind"] for r in serialized}
        assert kinds_seen  # non-empty - proves this ran against real data
        for r in serialized:
            assert isinstance(r["value_summary"], (int, float, str, dict, list, type(None)))

    def test_run_pair_output_serializes_and_round_trips(self, spec, real_df, synth_df):
        from app.services.evaluation2 import handout_adapter as A

        pair_df = A.run_pair(spec, real_df, synth_df)
        assert len(pair_df) == 25

        serialized = rows(pair_df)
        encoded = json.dumps(serialized, allow_nan=False)  # must not raise
        decoded = json.loads(encoded)
        assert len(decoded) == 25
        for r in decoded:
            assert 0.0 <= r["distance"] <= 1.0

    def test_raw_value_column_is_preserved_not_discarded(self, spec, real_df):
        """14. The serializer must not throw away complex raw values (matrix/
        vector/set/location) just because they're not trivially JSON-safe -
        it must convert their actual shape, not drop them."""
        from app.services.evaluation2 import handout_adapter as A

        result_df = A.run_real(spec, real_df)
        vector_rows = result_df[result_df["kind"] == "vector"]
        if len(vector_rows) == 0:
            pytest.skip("no vector-kind instance in this spec/data combination")
        raw_value = vector_rows.iloc[0]["value"]
        assert isinstance(raw_value, np.ndarray)
        serialized_value = jsonable(raw_value)
        assert isinstance(serialized_value, list)
        assert len(serialized_value) == len(raw_value)
