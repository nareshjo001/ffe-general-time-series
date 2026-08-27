"""Input/schema validation that must happen BEFORE calling into
`handout_adapter.run_real` / `handout_adapter.run_pair`.

Why this module exists (see the Phase 2 handout audit): `handout_lib.load_panel
-> run_real/run_pair` does not validate columns at all - a missing column
surfaces as a raw, unwrapped pandas `KeyError` deep inside querylib. Worse, a
real/synthetic dtype mismatch on a group-by attribute is NOT rejected by
querylib - it silently produces wrong group labels and corrupted distances
(verified: a LATITUDE column cast to string on the synthetic side pushed
`self_check`-equivalent scoring from 0.0 to ~1.0 with zero exception raised).
This module exists to catch both failure modes before any data reaches
`handout_adapter`.

This module does NOT duplicate anything `handout_adapter.load_spec` /
querylib's own `spec.validate` already do: no query-id validation, no
taxonomy validation, no bin-edge validation, no focus-structure validation,
no query-selection resolution, no Stage-1 grouping rules. It only reads the
already-validated spec dict to figure out which dataset columns are
referenced, and checks that those specific columns exist (and, for the
real+synthetic case, are dtype-compatible) - nothing else.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

import pandas as pd


class InputValidationError(ValueError):
    """Raised when uploaded/loaded data does not satisfy what a validated
    spec requires. Deliberately a small, local exception - not a project-wide
    hierarchy. Safe to surface directly as a 4xx response or a failed-job
    message: messages are deterministic and never expose raw pandas/numpy
    internals.
    """


# ============================================================================
#  required-column extraction (reads an already-validated spec dict only)
# ============================================================================
def required_columns(spec: dict) -> set[str]:
    """Every dataset column a validated spec (as returned by
    ``handout_adapter.load_spec``) references.

    Always includes ``dataset.id``, ``dataset.time``, and every entry of
    ``dataset.measurements``. Also includes every ``attr`` referenced by a
    grouping key, across either a single ``groupby`` block or every view in
    ``groupbys`` (multi-view specs). Never hard-codes column names - this
    works for any valid spec, on any dataset.

    Returns a plain ``set`` (deterministic membership, order does not
    matter for the checks this module performs; callers that need a stable
    display order should ``sorted()`` the result themselves, as the error
    messages in this module do).
    """
    dataset = spec.get("dataset") or {}
    cols: set[str] = set()

    id_col = dataset.get("id")
    if id_col:
        cols.add(id_col)

    time_col = dataset.get("time")
    if time_col:
        cols.add(time_col)

    for measurement in dataset.get("measurements") or []:
        cols.add(measurement)

    # Single-view specs are their own "view"; multi-view specs list their
    # views under `groupbys`, each a fully-validated sub-spec with its own
    # `groupby` block (see querylib/spec.py::validate).
    views = spec["groupbys"] if spec.get("groupbys") else [spec]
    for view in views:
        groupby = view.get("groupby") or {}
        for key in groupby.get("keys") or []:
            attr = key.get("attr")
            if attr:
                cols.add(attr)

    return cols


def _missing(required: Iterable[str], present: Iterable[str]) -> list[str]:
    return sorted(set(required) - set(present))


# ============================================================================
#  cheap, header-only CSV validation (no full CSV load)
# ============================================================================
def validate_csv_header(
    csv_path: str | Path, required: Iterable[str], *, label: str = "dataset"
) -> None:
    """Open ``csv_path``, read only its header row, and confirm every column
    in ``required`` is present. Raises :class:`InputValidationError` with a
    friendly message (never a raw pandas ``KeyError``) if anything is
    missing. Does not load or parse any data rows.
    """
    path = Path(csv_path)
    with path.open(newline="", encoding="utf-8") as f:
        try:
            header = next(csv.reader(f))
        except StopIteration:
            raise InputValidationError(
                f"{label} CSV has no header row (file is empty): {path}"
            ) from None

    missing = _missing(required, header)
    if missing:
        raise InputValidationError(
            f"Missing required columns in {label}: {', '.join(missing)}"
        )


# ============================================================================
#  already-loaded DataFrame validation
# ============================================================================
def validate_dataframe(
    df: pd.DataFrame, required: Iterable[str], *, label: str = "dataset"
) -> None:
    """Confirm every column in ``required`` exists in ``df``. Does not
    mutate ``df``. Extra columns not in ``required`` are ignored - this
    validates the spec-relevant schema, not full CSV equality.
    """
    missing = _missing(required, df.columns)
    if missing:
        raise InputValidationError(
            f"Missing required columns in {label}: {', '.join(missing)}"
        )


# ============================================================================
#  dtype categories (a small internal classification, not raw dtype strings)
# ============================================================================
NUMERIC = "numeric"
DATETIME = "datetime"
BOOLEAN = "boolean"
CATEGORICAL = "categorical"
STRING = "string/object"
OTHER = "other"


def classify_dtype(dtype) -> str:
    """Classify a pandas/numpy dtype into a small semantic category so
    e.g. int32 vs int64, or float32 vs float64, compare as compatible,
    while numeric vs string/object never does.

    Order matters: boolean and categorical dtypes would otherwise also
    satisfy pandas's own ``is_numeric_dtype``/``is_object_dtype`` checks, so
    they are classified first.
    """
    if isinstance(dtype, pd.CategoricalDtype):
        return CATEGORICAL
    if pd.api.types.is_bool_dtype(dtype):
        return BOOLEAN
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return DATETIME
    if pd.api.types.is_numeric_dtype(dtype):
        return NUMERIC
    if pd.api.types.is_object_dtype(dtype) or pd.api.types.is_string_dtype(dtype):
        return STRING
    return OTHER


def _dtype_categories_compatible(a: str, b: str) -> bool:
    """Conservative on purpose: only an exact category match is considered
    compatible. This is deliberately stricter than "could probably be
    coerced" - a numeric grouping attribute silently becoming a string on
    one side is exactly the corruption scenario this module exists to
    reject (verified in the Phase 2 handout audit), so ambiguous cases are
    treated as incompatible rather than guessed at.
    """
    return a == b


# ============================================================================
#  real + synthetic schema/dtype validation (comparison mode only)
# ============================================================================
def validate_real_synthetic_schema(
    spec: dict, real_df: pd.DataFrame, synth_df: pd.DataFrame
) -> None:
    """Validate that ``real_df`` and ``synth_df`` are safe to pass to
    ``handout_adapter.run_pair`` together, for this spec.

    Checks ONLY the columns the spec actually references (via
    :func:`required_columns`) - unrelated extra columns on either side never
    cause a failure. For each required column:

      A. it must exist on both sides (delegates to :func:`validate_dataframe`)
      B. its dtype category (see :func:`classify_dtype`) must match on both
         sides

    Deliberately does NOT require matching entity IDs, matching row counts,
    or the same number of entities - querylib itself does not require this
    (real/synthetic alignment happens inside querylib at the group-label +
    time-bin level, not the entity/row level), so this validator does not
    invent a stricter rule than the engine it is protecting.

    Raises :class:`InputValidationError` (with one line per offending
    column) on the first class of problem found: missing columns first, then
    dtype mismatches. Never mutates either DataFrame.
    """
    required = required_columns(spec)
    validate_dataframe(real_df, required, label="real dataset")
    validate_dataframe(synth_df, required, label="synthetic dataset")

    mismatches = []
    for col in sorted(required):
        real_cat = classify_dtype(real_df[col].dtype)
        synth_cat = classify_dtype(synth_df[col].dtype)
        if not _dtype_categories_compatible(real_cat, synth_cat):
            mismatches.append(
                f"Incompatible dtype for column '{col}':\n"
                f"real={real_cat}, synthetic={synth_cat}"
            )

    if mismatches:
        raise InputValidationError("\n".join(mismatches))


__all__ = [
    "InputValidationError",
    "required_columns",
    "validate_csv_header",
    "validate_dataframe",
    "classify_dtype",
    "validate_real_synthetic_schema",
    "NUMERIC",
    "DATETIME",
    "BOOLEAN",
    "CATEGORICAL",
    "STRING",
    "OTHER",
]
