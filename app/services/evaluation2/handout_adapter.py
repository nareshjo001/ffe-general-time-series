"""Thin wrappers over Steven's `handout_lib` public API.

Every function here does nothing but delegate to the corresponding
`handout_lib` function via `handout_bootstrap.load_handout()`. There is
deliberately:
    - no business logic
    - no schema/dtype validation
    - no real/synthetic entity alignment
    - no serialization of results
    - no aggregation
    - no DataFrame caching
    - no job/HTTP concerns
    - no `import querylib` anywhere

Those concerns belong to later phases. This module's only job is to be the
one place the rest of the application calls into `handout_lib` through, so
that `querylib` is never imported directly from application code.

Return values are passed through exactly as `handout_lib` produces them
(pandas DataFrames, plain dicts, floats) - nothing is reshaped, renamed, or
summarized here.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.services.evaluation2.handout_bootstrap import load_handout


def load_spec(path: str | Path) -> dict:
    """Load + validate a YAML query spec.

    Delegates to ``handout_lib.load_spec(path)``.

    Raises:
        querylib.spec.SpecError (a ValueError subclass) if the spec is
        malformed - propagated unchanged, not caught or reinterpreted here.
    """
    return load_handout().load_spec(str(path))


def load_panel(dataset_dir: str | Path) -> tuple[pd.DataFrame, dict | None]:
    """Load a dataset directory (data.csv + config.json) or a bare CSV path.

    Delegates to ``handout_lib.load_panel(dataset_dir)``.

    Returns:
        (DataFrame, config dict) for a dataset directory, or
        (DataFrame, None) for a bare CSV path.
    """
    return load_handout().load_panel(str(dataset_dir))


def subsample_panel(df: pd.DataFrame, id_col: str, n: int = 40) -> pd.DataFrame:
    """Deterministic representative subset of ``n`` entities.

    Delegates to ``handout_lib.subsample_panel(df, id_col, n=n)``.
    """
    return load_handout().subsample_panel(df, id_col, n=n)


def enumerate_instances(spec: dict, real_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per query instance (the panel list).

    Delegates to ``handout_lib.enumerate_instances(spec, real_df)``.

    Without ``real_df``: a fast, data-free layout preview (focus tokens
    unresolved, ``return_type`` is ``""``).
    With ``real_df``: runs the full battery to resolve exact focus labels and
    ``return_type`` - not a cheap call.
    """
    return load_handout().enumerate_instances(spec, real_df)


def run_real(spec: dict, real_df: pd.DataFrame) -> pd.DataFrame:
    """Function 1: raw query value on real data, per instance.

    Delegates to ``handout_lib.run_real(spec, real_df)``.
    """
    return load_handout().run_real(spec, real_df)


def run_pair(spec: dict, real_df: pd.DataFrame, synth_df: pd.DataFrame) -> pd.DataFrame:
    """Function 2: real value, synthetic value, and [0,1] distance per instance.

    Delegates to ``handout_lib.run_pair(spec, real_df, synth_df)``.

    No entity alignment is performed here or by ``handout_lib`` - real and
    synthetic may contain different entity IDs. Alignment happens inside
    querylib at the group-label + time-bin level only.
    """
    return load_handout().run_pair(spec, real_df, synth_df)


def group_series(
    spec: dict,
    real_df: pd.DataFrame,
    synth_df: pd.DataFrame | None = None,
    view: str | None = None,
) -> pd.DataFrame:
    """The Stage-1 grouped curves (the raw material behind every panel).

    Delegates to ``handout_lib.group_series(spec, real_df, synth_df, view)``.
    """
    return load_handout().group_series(spec, real_df, synth_df, view)


def self_check(spec: dict, real_df: pd.DataFrame) -> float:
    """Score real data against itself; must be ~0.0 (<=1e-9).

    Delegates to ``handout_lib.self_check(spec, real_df)``.

    This validates only the engine's real-vs-real correctness invariant. It
    does NOT validate real/synthetic dtype or schema compatibility - that is
    a separate concern for a later phase's input validator, not something
    this function (or ``handout_lib``) checks.
    """
    return load_handout().self_check(spec, real_df)


__all__: list[str] = [
    "load_spec",
    "load_panel",
    "subsample_panel",
    "enumerate_instances",
    "run_real",
    "run_pair",
    "group_series",
    "self_check",
]
