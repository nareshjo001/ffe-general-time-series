"""Phase D/E orchestration: execute one Phase 2 evaluation for a job's
already-uploaded files.

This module owns ONLY the execution sequence - load spec, validate, load
data, validate, run the query battery, generate curves, serialize, and
aggregate. It does not:
    - own job status/lifecycle (that remains `JobExecutor`'s responsibility -
      see services/job/job_executor.py::JobExecutor.run_real_only /
      run_real_synthetic)
    - write anything to disk (see result_writer.py)
    - import `querylib` directly (only `handout_adapter`)
    - perform any real/synthetic entity-ID alignment (`validate_real_synthetic
      _schema` never compares IDs or row counts, and neither does this
      module - real/synthetic alignment happens inside querylib at the
      group-label + time-bin level only, see `run_real_synthetic` below)
    - call `subsample_panel` (no universal default subsample size has been
      established by product/mentor - the uploaded dataset(s) are evaluated
      as-is)
    - call `enumerate_instances` for the actual query battery (verified to
      rerun the full Stage-1 + Stage-2 battery; `run_real`/`run_pair`'s own
      output already carries one row per executed instance with all the
      metadata this module needs). `enumerate_instances` IS used, but only
      indirectly, via `preflight.run_backend_preflight`'s HC2 check, and
      only in its dataset-free static form (`real_df=None`) - never the
      dataset-aware form, and never for anything other than the static
      instance-count precheck.

Phase F.3 additions:
    - `preflight.run_backend_preflight(spec)` runs immediately after
      `adapter.load_spec()`, before any CSV/DataFrame validation, in both
      `run_real_only` and `run_real_synthetic`. It enforces two
      backend-owned rules (HC1 grouping constraint, HC2 static instance
      count < 200) that are NOT enforced anywhere in Steven's delivered
      handout (see the Phase F.2 audit) - see preflight.py's module
      docstring for exactly what these rules are and are not.
    - `run_real_synthetic` no longer calls `adapter.self_check(...)`
      automatically (product decision - self_check must not run
      automatically in production). `handout_adapter.self_check` itself is
      completely untouched and remains fully callable for tests,
      diagnostics, and manual validation; this module simply no longer
      invokes it as part of the normal evaluation sequence. The result's
      `self_check` field is `None` for every production real_synthetic
      result, communicating "not run" rather than fabricating a `passed`
      value that was never actually checked.

Phase F.6 additions:
    - `preflight.run_data_preflight(spec, real_df, synth_df=None)` runs
      after the DataFrame(s) are loaded and column-validated (and, for
      real_synthetic, after `validate_real_synthetic_schema`'s dtype-
      compatibility check), and before any querylib execution
      (`run_real`/`run_pair`). It enforces a data-aware HC3 raw-group-
      cardinality safeguard and the HC4 whole-view time-bin-count
      safeguard ONLY - see preflight.py's module docstring for the exact
      scope and for the many other HC3/HC4-adjacent rules this
      deliberately does NOT implement (in particular: the real-vs-
      synthetic Stage-1 zero-fill asymmetry is NOT addressed here or
      anywhere in this module - see preflight.py).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.database.job_store import MODE_REAL_ONLY, MODE_REAL_SYNTHETIC
from app.services.evaluation2 import aggregate
from app.services.evaluation2 import handout_adapter as adapter
from app.services.evaluation2 import input_validator as validator
from app.services.evaluation2 import preflight
from app.services.evaluation2 import serialize

# Steven's documented/runtime self_check invariant: a real-vs-real
# self-comparison must score ~0.0. Retained for tests/diagnostics/manual
# validation (see `handout_adapter.self_check` and the boundary tests) -
# NOT used anywhere in this module's production execution path as of
# Phase F.3 (self_check no longer runs automatically in production; see
# this module's docstring above).
SELF_CHECK_TOLERANCE = 1e-9


def run_real_only(real_csv_path: Path, spec_path: Path) -> dict[str, Any]:
    """Run a full real-only Phase 2 evaluation and return persistence-ready
    result objects. Never touches DuckDB, `CSVLoader`, gap tables, or any of
    the Phase 1 packet/flow evaluation machinery - the only data source read
    here is ``real_csv_path``, and the only query engine involved is
    ``handout_adapter`` (-> ``handout_lib`` -> ``querylib``).

    Sequence (mirrors the verified minimal real-only call shape from the
    Phase 2 handout audit - no ``subsample_panel``):

        1. load + validate the spec (delegates entirely to
           ``handout_adapter.load_spec`` / querylib's own ``spec.validate``)
        2. Phase F.3 backend-owned HC1/HC2 preflight
           (``preflight.run_backend_preflight``) - the only place
           ``enumerate_instances`` is called in this module, and only in its
           dataset-free static form; see preflight.py
        3. derive required columns from the validated spec
           (``input_validator.required_columns``)
        4. cheap header-only validation of the real CSV, before loading it
           (``input_validator.validate_csv_header``)
        5. load the real CSV into a DataFrame (``handout_adapter.load_panel``)
        6. validate the loaded DataFrame's columns
           (``input_validator.validate_dataframe``)
        6.5. Phase F.6 backend-owned HC3/HC4 data preflight
           (``preflight.run_data_preflight``) - the DataFrame is now loaded
           and column-validated, so raw group cardinality (HC3) and the
           whole-view time-bin count (HC4) can finally be computed; must
           run before any querylib execution
        7. run the real-only query battery (``handout_adapter.run_real``)
        8. generate the Stage-1 grouped curves (``handout_adapter.group_series``)
        9. serialize both outputs to JSON-safe structures (``serialize.rows``)
        10. build a purely structural setting x family overview
           (``aggregate.real_only_overview``)

    Returns:
        A dict with two keys:
            "result": the persistence-ready result.json payload
                       ({"mode", "overview", "instances", "metadata"})
            "curves": the persistence-ready curves.json payload (a list of
                       serialized rows)

    Raises:
        querylib.spec.SpecError: if the spec is malformed (from
            ``handout_adapter.load_spec``) - propagated unchanged.
        preflight.Phase2PreflightError: if the spec fails this backend's
            HC1 (grouping-constraint) or HC2 (static instance-count) policy
            - raised before any CSV/DataFrame validation or querylib
            execution - OR if the loaded real DataFrame fails the Phase F.6
            HC3 (raw group cardinality) or HC4 (whole-view time-bin count)
            data preflight - raised after DataFrame validation, before
            ``handout_adapter.run_real``.
        input_validator.InputValidationError: if the real CSV is missing a
            spec-referenced column (caught here, before any data ever
            reaches ``handout_adapter.run_real``/``group_series``).
        Any other exception ``handout_adapter`` itself raises (e.g. a
            querylib runtime failure) - propagated unchanged; this function
            does not swallow or reinterpret errors, it is the caller's
            (``JobExecutor``) job to turn them into a failed-job status.
    """
    spec = adapter.load_spec(spec_path)
    preflight.run_backend_preflight(spec)

    required = validator.required_columns(spec)
    validator.validate_csv_header(real_csv_path, required, label="real dataset")

    real_df, _config = adapter.load_panel(real_csv_path)
    validator.validate_dataframe(real_df, required, label="real dataset")

    # Phase F.6: data-aware HC3 (raw group cardinality) + HC4 (whole-view
    # time-bin count) preflight - must run AFTER the DataFrame is loaded and
    # column-validated, and BEFORE any querylib execution (`run_real`).
    preflight.run_data_preflight(spec, real_df)

    result_df = adapter.run_real(spec, real_df)
    curves_df = adapter.group_series(spec, real_df)

    instances = serialize.rows(result_df)
    curves = serialize.rows(curves_df)

    overview = aggregate.real_only_overview(instances)

    result = {
        "mode": MODE_REAL_ONLY,
        "overview": overview,
        "instances": instances,
        "metadata": {"instance_count": len(instances)},
    }
    return {"result": result, "curves": curves}


class SelfCheckFailedError(RuntimeError):
    """Raised when a caller explicitly runs `handout_adapter.self_check` and
    finds a real-vs-real distance above `SELF_CHECK_TOLERANCE`. Deliberately
    separate from `input_validator.InputValidationError`: a self-check
    failure means the query engine itself is not internally consistent for
    this spec+dataset, not that the uploaded data failed a schema/dtype
    check.

    Phase F.3: this is no longer raised anywhere in `run_real_synthetic`'s
    production sequence, since self_check is no longer called automatically
    in production (see this module's docstring). The type is kept here -
    not deleted - because it is still a meaningful, importable exception for
    tests/diagnostics/manual validation code that explicitly calls
    `handout_adapter.self_check` and wants to raise a typed error on
    failure, and because existing tests import it from this module.
    """


def run_real_synthetic(
    real_csv_path: Path, synthetic_csv_path: Path, spec_path: Path
) -> dict[str, Any]:
    """Run a full real+synthetic Phase 2 comparison evaluation and return
    persistence-ready result objects. Never touches DuckDB, `CSVLoader`, gap
    tables, or any of the Phase 1 packet/flow evaluation machinery, and never
    computes a distance itself - `handout_adapter.run_pair` (-> `handout_lib`
    -> `querylib`) owns the [0, 1] distance calculation entirely.

    Sequence (Phase F.3 - self_check removed from the production path; see
    this module's docstring):

        1. load + validate the spec (``handout_adapter.load_spec``)
        2. Phase F.3 backend-owned HC1/HC2 preflight
           (``preflight.run_backend_preflight``)
        3. derive required columns from the validated spec
        4. cheap header-only validation of both CSVs, before loading either
           (``input_validator.validate_csv_header``)
        5. load both CSVs into DataFrames (``handout_adapter.load_panel``)
        6. validate each loaded DataFrame's columns
           (``input_validator.validate_dataframe``)
        7. validate real/synthetic schema+dtype compatibility
           (``input_validator.validate_real_synthetic_schema``) - this is the
           check that stands between a dtype mismatch (e.g. a numeric
           grouping column becoming a string on the synthetic side) and a
           silently corrupted distance score; it always runs before step 8
           below, never after
        7.5. Phase F.6 backend-owned HC3/HC4 data preflight
           (``preflight.run_data_preflight``), called with both DataFrames
           so HC3's group-cardinality and HC4's time-bin-count checks use
           the UNION of real+synthetic observed values (backend policy -
           see preflight.py); runs after step 7's dtype-compatibility
           check and before step 8's querylib execution
        8. run_pair(spec, real_df, synth_df) - the actual comparison; no
           entity-ID alignment is performed here or anywhere in this module,
           real and synthetic may have completely different entity
           populations and row counts (alignment happens inside querylib at
           the group-label + time-bin level only). NOTE: `adapter.self_check`
           is deliberately NOT called anywhere in this sequence - product
           decision, not an oversight (see this module's docstring).
        9. group_series(spec, real_df, synth_df) - Stage-1 curves with both
           real and synth columns populated
        10. serialize both outputs to JSON-safe structures
        11. build the comparison overview (setting x family grid with
            distance statistics, plus a worst-offenders list)

    Returns:
        A dict with two keys:
            "result": the persistence-ready result.json payload
                       ({"mode", "overview", "instances", "self_check",
                       "metadata"}). "self_check" is always `None` in this
                       production path - it communicates "not run", never a
                       fabricated `passed` value.
            "curves": the persistence-ready curves.json payload (a list of
                       serialized rows, each with both "real" and "synth")

    Raises:
        querylib.spec.SpecError: if the spec is malformed - propagated
            unchanged.
        preflight.Phase2PreflightError: if the spec fails this backend's
            HC1 (grouping-constraint) or HC2 (static instance-count) policy
            - raised before any CSV/DataFrame validation or querylib
            execution - OR if the loaded real+synthetic DataFrames fail the
            Phase F.6 HC3 (union raw group cardinality) or HC4 (union
            time-bin count) data preflight - raised after schema/dtype
            compatibility validation, before ``handout_adapter.run_pair``.
        input_validator.InputValidationError: if either CSV is missing a
            spec-referenced column, or if a spec-referenced column has an
            incompatible dtype category between real and synthetic - caught
            here, before any data reaches ``handout_adapter.run_pair``.
        Any other exception ``handout_adapter`` itself raises - propagated
            unchanged; this function does not swallow or reinterpret errors,
            it is the caller's (``JobExecutor``) job to turn them into a
            failed-job status.
    """
    spec = adapter.load_spec(spec_path)
    preflight.run_backend_preflight(spec)

    required = validator.required_columns(spec)
    validator.validate_csv_header(real_csv_path, required, label="real dataset")
    validator.validate_csv_header(synthetic_csv_path, required, label="synthetic dataset")

    real_df, _real_config = adapter.load_panel(real_csv_path)
    synth_df, _synth_config = adapter.load_panel(synthetic_csv_path)

    validator.validate_dataframe(real_df, required, label="real dataset")
    validator.validate_dataframe(synth_df, required, label="synthetic dataset")

    # Real/synthetic schema+dtype compatibility - must run before run_pair.
    # Deliberately does not check entity IDs, row counts, or entity
    # population (see this function's docstring, step 8).
    validator.validate_real_synthetic_schema(spec, real_df, synth_df)

    # Phase F.6: data-aware HC3/HC4 preflight - must run AFTER schema/dtype
    # compatibility has already been confirmed (so HC3's union-tuple
    # counting and HC4's union-time-bin counting never silently compare
    # incompatible values), and BEFORE any querylib execution (`run_pair`).
    preflight.run_data_preflight(spec, real_df, synth_df)

    # Phase F.3: self_check is deliberately NOT called here (product
    # decision - self_check must not run automatically in production).
    # `handout_adapter.self_check` remains fully available and untouched for
    # tests, diagnostics, and manual validation - it is simply not part of
    # this production sequence.
    result_df = adapter.run_pair(spec, real_df, synth_df)
    curves_df = adapter.group_series(spec, real_df, synth_df)

    instances = serialize.rows(result_df)
    curves = serialize.rows(curves_df)

    overview = aggregate.real_synthetic_overview(instances)
    distance_stats = aggregate.distance_stats(instances)

    result = {
        "mode": MODE_REAL_SYNTHETIC,
        "overview": overview,
        "instances": instances,
        # Not run in production (Phase F.3 product decision) - `None`
        # communicates "not run", never a fabricated `passed: true`.
        "self_check": None,
        "metadata": {
            "instance_count": len(instances),
            **distance_stats,
        },
    }
    return {"result": result, "curves": curves}


__all__ = ["run_real_only", "run_real_synthetic", "SelfCheckFailedError", "SELF_CHECK_TOLERANCE"]
