"""
JobExecutor runs ingestion and evaluation for a benchmark job.

It updates the job's status, logs execution progress, and coordinates the
ingestion and evaluation workflow.
"""

import json
import time
import traceback

from concurrent.futures import ThreadPoolExecutor

from app.core.logging_config import get_job_logger
from app.database import job_store
from app.database.db import get_connection
from app.services.ingestion.csv_loader import CSVLoader
from app.services.job.job_manager import JobManager
from app.services.evaluation.evaluation_controller import EvaluationController
from app.services.evaluation.evaluation_controller_parallel import ParallelEvaluationController
from app.services.evaluation2 import evaluation_service, result_writer
from app.services.evaluation2.execution_guard import phase2_execution_lock
from app.services.evaluation2.preflight import Phase2PreflightError

class JobExecutor:

    # Shared ingestion: validate uploads, load CSVs, build gap tables.
    # Used by both the sequential and parallel evaluation paths so the
    # two endpoints can never drift out of sync with each other.
    @staticmethod
    def _ingest(job_id: str, log) -> str:

        if not JobManager.job_exists(job_id):
            raise FileNotFoundError("Invalid Job ID")

        real_csv = JobManager.get_real_csv(job_id)
        synthetic_csv = JobManager.get_synthetic_csv(job_id)

        if not real_csv.exists():
            raise FileNotFoundError("Real CSV not uploaded")

        if not synthetic_csv.exists():
            raise FileNotFoundError("Synthetic CSV not uploaded")

        log.info(
            "ingestion inputs",
            extra={
                "real_csv_mb": round(real_csv.stat().st_size / (1024 * 1024), 2),
                "synthetic_csv_mb": round(synthetic_csv.stat().st_size / (1024 * 1024), 2),
            },
        )

        db_path = JobManager.get_database_path(job_id)
        conn = get_connection(db_path)

        try:
            start = time.perf_counter()
            CSVLoader.load_csv_to_table(str(real_csv), "real_packets", conn)
            CSVLoader.load_csv_to_table(str(synthetic_csv), "synthetic_packets", conn)
            log.info("datasets loaded", extra={"duration_sec": round(time.perf_counter() - start, 2)})

            # Build real and synthetic gap tables in parallel.
            # Use separate cursors on the same database connection instead of
            # multiple write connections, since DuckDB does not guarantee that
            # concurrent schema changes from different connections are safe.
            start = time.perf_counter()

            real_cursor = conn.cursor()
            synthetic_cursor = conn.cursor()

            try:
                with ThreadPoolExecutor(max_workers=2) as executor:
                    real_future = executor.submit(
                        CSVLoader.build_stateful_tables, "real_packets", real_cursor
                    )
                    synthetic_future = executor.submit(
                        CSVLoader.build_stateful_tables, "synthetic_packets", synthetic_cursor
                    )
                    real_future.result()
                    synthetic_future.result()
            finally:
                real_cursor.close()
                synthetic_cursor.close()

            log.info("stateful tables built", extra={"duration_sec": round(time.perf_counter() - start, 2)})

        finally:
            conn.close()

        return db_path

    @staticmethod
    def _save_result(job_id: str, result: dict):
        result_path = JobManager.get_result_path(job_id)
        with open(result_path, "w") as f:
            json.dump(result, f, indent=4, default=str)

    # Sequential path - safe fallback. POST /evaluate/{job_id}
    @classmethod
    def run(cls, job_id: str):

        log = get_job_logger(job_id)
        overall_start = time.perf_counter()
        job_store.set_status(job_id, job_store.STATUS_RUNNING)
        log.info("evaluation started", extra={"mode": "sequential"})

        try:
            db_path = cls._ingest(job_id, log)

            conn = get_connection(db_path)
            try:
                start = time.perf_counter()
                result = EvaluationController.run_all(conn)
                log.info("evaluation phase complete", extra={"duration_sec": round(time.perf_counter() - start, 2)})
            finally:
                conn.close()

            cls._save_result(job_id, result)
            job_store.set_status(job_id, job_store.STATUS_DONE)

            log.info("job complete", extra={"total_duration_sec": round(time.perf_counter() - overall_start, 2)})
            return result

        except Exception as e:
            log.error(
                "job failed",
                exc_info=True,
                extra={"error_type": type(e).__name__},
            )
            job_store.set_status(job_id, job_store.STATUS_FAILED, error=f"{type(e).__name__}: {e}")
            raise

    # Phase 2 real-only path. POST /evaluate/{job_id} when the job's
    # persisted mode is MODE_REAL_ONLY (see api/evaluate.py). Never touches
    # DuckDB/CSVLoader/gap tables/the packet-flow evaluation controllers -
    # all execution happens through services/evaluation2/evaluation_service.py
    # (handout_adapter -> handout_lib -> querylib only). This method owns the
    # same status/error lifecycle as `run`/`run_parallel` above; the
    # evaluation logic itself lives in evaluation_service, not here.
    #
    # Phase F.1: the call into evaluation_service is serialized against every
    # other Phase 2 job in this process via phase2_execution_lock (see
    # execution_guard.py - a per-process-only guarantee, querylib thread
    # safety is not established). RUNNING is deliberately set only after the
    # lock is acquired, not before: a job blocked waiting for another Phase 2
    # evaluation to finish has not started executing yet, so it should not
    # be reported as RUNNING while merely waiting. result_writer's disk
    # writes happen outside the lock - they touch only this job's own output
    # directory and have nothing to race on with another job's querylib call.
    @classmethod
    def run_real_only(cls, job_id: str):

        log = get_job_logger(job_id)
        overall_start = time.perf_counter()
        log.info("waiting for phase2 execution lock", extra={"mode": job_store.MODE_REAL_ONLY})

        try:
            real_csv = JobManager.get_real_csv(job_id)
            spec_path = JobManager.get_spec_path(job_id)

            start = time.perf_counter()
            with phase2_execution_lock:
                job_store.set_status(job_id, job_store.STATUS_RUNNING)
                log.info("evaluation started", extra={"mode": job_store.MODE_REAL_ONLY})
                outcome = evaluation_service.run_real_only(real_csv, spec_path)
            log.info("evaluation phase complete", extra={"duration_sec": round(time.perf_counter() - start, 2)})

            result_writer.write_result(JobManager.get_result_path(job_id), outcome["result"])
            result_writer.write_curves(JobManager.get_curves_path(job_id), outcome["curves"])

            job_store.set_status(job_id, job_store.STATUS_DONE)

            log.info("job complete", extra={"total_duration_sec": round(time.perf_counter() - overall_start, 2)})
            return outcome["result"]

        # Phase F.3: a backend-owned HC1/HC2 preflight rejection is
        # structured (code/message/details) - persist that structured JSON
        # payload (via `Phase2PreflightError.to_json()`/`__str__`) into the
        # job store's existing `error` TEXT column verbatim, instead of the
        # generic "ClassName: message" format used below. No database
        # schema change: `error` is still just a string, it is simply a
        # JSON-shaped one for this specific exception type. The status API
        # (app/api/jobs.py::get_status) opportunistically parses this back
        # into a structured `error_details` field for the frontend.
        except Phase2PreflightError as e:
            log.error(
                "job failed (preflight rejection)",
                exc_info=True,
                extra={"error_type": type(e).__name__, "code": e.code},
            )
            job_store.set_status(job_id, job_store.STATUS_FAILED, error=e.to_json())
            raise

        except Exception as e:
            log.error(
                "job failed",
                exc_info=True,
                extra={"error_type": type(e).__name__},
            )
            job_store.set_status(job_id, job_store.STATUS_FAILED, error=f"{type(e).__name__}: {e}")
            raise

    # Phase 2 real+synthetic comparison path. POST /evaluate/{job_id} when the
    # job's persisted mode is MODE_REAL_SYNTHETIC (see api/evaluate.py). Same
    # DuckDB/packet-flow isolation guarantee as run_real_only above - all
    # execution happens through services/evaluation2/evaluation_service.py
    # (handout_adapter -> handout_lib -> querylib only). Owns the same
    # status/error lifecycle as run/run_real_only/run_parallel; the
    # evaluation logic itself (Phase F.3: no longer includes an automatic
    # self_check gate before run_pair - see evaluation_service.py) lives in
    # evaluation_service, not here.
    #
    # Phase F.1: same phase2_execution_lock as run_real_only above - shared
    # process-wide, so a real_only and a real_synthetic job (or any
    # combination of the two) can never have their evaluation_service calls
    # overlap. See run_real_only's comment above for why RUNNING is set only
    # after lock acquisition and why the result writes stay outside the lock.
    @classmethod
    def run_real_synthetic(cls, job_id: str):

        log = get_job_logger(job_id)
        overall_start = time.perf_counter()
        log.info("waiting for phase2 execution lock", extra={"mode": job_store.MODE_REAL_SYNTHETIC})

        try:
            real_csv = JobManager.get_real_csv(job_id)
            synthetic_csv = JobManager.get_synthetic_csv(job_id)
            spec_path = JobManager.get_spec_path(job_id)

            start = time.perf_counter()
            with phase2_execution_lock:
                job_store.set_status(job_id, job_store.STATUS_RUNNING)
                log.info("evaluation started", extra={"mode": job_store.MODE_REAL_SYNTHETIC})
                outcome = evaluation_service.run_real_synthetic(real_csv, synthetic_csv, spec_path)
            log.info("evaluation phase complete", extra={"duration_sec": round(time.perf_counter() - start, 2)})

            result_writer.write_result(JobManager.get_result_path(job_id), outcome["result"])
            result_writer.write_curves(JobManager.get_curves_path(job_id), outcome["curves"])

            job_store.set_status(job_id, job_store.STATUS_DONE)

            log.info("job complete", extra={"total_duration_sec": round(time.perf_counter() - overall_start, 2)})
            return outcome["result"]

        # Phase F.3: see run_real_only's identical except-block comment above
        # for why this structured-error case is handled separately from the
        # generic Exception branch below.
        except Phase2PreflightError as e:
            log.error(
                "job failed (preflight rejection)",
                exc_info=True,
                extra={"error_type": type(e).__name__, "code": e.code},
            )
            job_store.set_status(job_id, job_store.STATUS_FAILED, error=e.to_json())
            raise

        except Exception as e:
            log.error(
                "job failed",
                exc_info=True,
                extra={"error_type": type(e).__name__},
            )
            job_store.set_status(job_id, job_store.STATUS_FAILED, error=f"{type(e).__name__}: {e}")
            raise

    # Parallel path - production default. POST /evaluate/parallel/{job_id}
    @classmethod
    def run_parallel(cls, job_id: str):

        log = get_job_logger(job_id)
        overall_start = time.perf_counter()
        job_store.set_status(job_id, job_store.STATUS_RUNNING)
        log.info("evaluation started", extra={"mode": "parallel"})

        try:
            db_path = cls._ingest(job_id, log)

            start = time.perf_counter()
            result = ParallelEvaluationController.run_all(db_path)
            log.info("evaluation phase complete", extra={"duration_sec": round(time.perf_counter() - start, 2)})

            cls._save_result(job_id, result)
            job_store.set_status(job_id, job_store.STATUS_DONE)

            log.info("job complete", extra={"total_duration_sec": round(time.perf_counter() - overall_start, 2)})
            return result

        except Exception as e:
            log.error(
                "job failed",
                exc_info=True,
                extra={"error_type": type(e).__name__},
            )
            job_store.set_status(job_id, job_store.STATUS_FAILED, error=f"{type(e).__name__}: {e}")
            raise
