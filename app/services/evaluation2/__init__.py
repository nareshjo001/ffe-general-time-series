"""Phase 2 evaluation package.

This package hosts the boundary between the Phase 1 backend and Steven's
`handout_lib` / `querylib` query-evaluation engine (Steven's own code is never
vendored into this repository — see `handout_bootstrap.py` for how it is
located at runtime).

Phase A added:
    - handout_bootstrap.py   locate + import handout_lib safely, once
    - handout_adapter.py     thin 1:1 wrappers over handout_lib's 8 public functions

Phase B added:
    - input_validator.py     required-column + real/synthetic dtype-compatibility
                              checks that must run BEFORE handout_adapter.run_real/
                              run_pair (querylib does not safely validate these itself)
    - serialize.py           recursive JSON-safe conversion of handout_adapter's raw
                              output (numpy scalars/arrays, tuples, sets, NaN/Inf)

Phase C added mode ("real_only"/"real_synthetic") on job metadata and a
spec-upload endpoint (in database/job_store.py and api/upload.py, not this
package).

Phase D added, and wired into JobExecutor.run_real_only (see
services/job/job_executor.py):
    - evaluation_service.py  orchestrates one real-only evaluation: load spec
                              -> validate -> load real.csv -> validate ->
                              run_real -> group_series -> serialize -> aggregate
    - aggregate.py           purely structural setting x family (3x4) instance
                              counts - no distance score, no cross-kind comparison
    - result_writer.py       strict (allow_nan=False) JSON persistence of
                              result.json / curves.json

Phase E added, in evaluation_service.py alongside run_real_only:
    - run_real_synthetic     self_check gate -> run_pair -> group_series, with
                              validate_real_synthetic_schema run before either
    - aggregate.py           + real_synthetic_overview / distance_stats
                              (distance is querylib's own [0,1] output - never
                              recomputed here)

Phase F.1 added:
    - execution_guard.py     one process-wide threading.Lock serializing every
                              Phase 2 (real_only/real_synthetic) call into this
                              package within a single Python process - see its
                              module docstring for exact scope (per-process
                              only; does not coordinate multiple uvicorn
                              workers). Held only around the call into
                              evaluation_service, from services/job/
                              job_executor.py.
    - result_writer.py       writes are now atomic: a temp file in the same
                              output directory is fully written first, then
                              swapped into place via os.replace, so a crash or
                              exception mid-write can never leave a truncated
                              result.json/curves.json visible under its final
                              name. allow_nan=False unchanged.

Nothing in this package may import `querylib` directly.
"""
