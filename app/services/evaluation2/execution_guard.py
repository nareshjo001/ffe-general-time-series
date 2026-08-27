"""Per-process serialization for Phase 2 (`handout_lib`/querylib) execution.

WHY THIS EXISTS
----------------
FastAPI/Starlette runs the synchronous `JobExecutor` background callbacks
through AnyIO worker threads (confirmed against the installed Starlette
source during the Phase F.0 audit: `BackgroundTasks.__call__` awaits
`run_in_threadpool` for any non-async callable, and AnyIO's default thread
capacity limiter allows up to 40 such callbacks to run concurrently). Two
different `job_id`s can therefore have their background tasks executing at
the same time in the same process - the existing duplicate-run guard in
`api/evaluate.py` only protects a single job_id against being queued twice,
it says nothing about two different jobs.

querylib itself contains no internal synchronization (no `threading.Lock`,
`Semaphore`, or similar - verified during the Phase F.0 handout audit), and
its thread-safety under concurrent invocation from two different Python
threads in the same process is NOT ESTABLISHED (neither proven safe nor
proven unsafe). Given that, this module conservatively allows only ONE
Phase 2 evaluation (`evaluation_service.run_real_only` /
`run_real_synthetic`, and therefore the `handout_adapter` -> `handout_lib`
-> querylib calls inside them) to execute at a time within this process.

SCOPE - READ CAREFULLY
------------------------
This lock provides a PER-PROCESS guarantee ONLY. It serializes Phase 2
querylib calls within a single Python process/interpreter. It does NOT
coordinate across multiple uvicorn worker processes, multiple machines, or
any other process boundary - if this application is ever deployed with more
than one worker process, two Phase 2 evaluations can still run concurrently
across those processes, and this module does nothing to prevent that. Making
that multi-process guarantee (if it's ever needed) would require a different
mechanism entirely (e.g. a single-worker deployment constraint, or an
external lock) - explicitly out of scope for this module and for Phase F.1.

WHAT THIS LOCK DOES NOT COVER
-------------------------------
The legacy Phase 1 evaluator (`JobExecutor.run` / `run_parallel`, driving
`EvaluationController`/`ParallelEvaluationController` over DuckDB) never
imports or calls into `handout_adapter`/`handout_lib`/querylib at all, so it
has no reason to acquire this lock and does not.

`result_writer.write_result`/`write_curves` are also deliberately NOT
covered by this lock - the safety concern this module addresses is
concurrent querylib execution, not independent JSON writes to two different
jobs' own output directories, which have no shared state to race on.
"""
from __future__ import annotations

import threading

# One process-wide lock, shared by every Phase 2 (`real_only` /
# `real_synthetic`) job executed in this process. A plain `threading.Lock` -
# not `asyncio.Lock` - because the callers (`JobExecutor.run_real_only` /
# `run_real_synthetic`) are synchronous functions running in AnyIO worker
# threads, not coroutines on the event loop; an `asyncio.Lock` would not be
# safe to acquire/release from a plain thread without its own event loop.
# Not a multiprocessing lock, not Redis/database-backed, no external queue -
# see the module docstring for why a per-process threading.Lock is the right
# (and only justified) scope for Phase F.1.
phase2_execution_lock = threading.Lock()

__all__ = ["phase2_execution_lock"]
