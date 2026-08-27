import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.upload import router as upload_router
from app.api.evaluate import router as evaluate_router
from app.api.jobs import router as jobs_router
from app.core.config import settings
from app.core.logging_config import configure_logging
from app.core.scheduler import start_scheduler, stop_scheduler
from app.database import job_store

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    job_store.init_db()
    # Phase F.4: startup reconciliation for a single-backend-process
    # deployment. Must run AFTER init_db() (the `jobs` table has to exist)
    # and BEFORE start_scheduler() (stale QUEUED/RUNNING rows left over
    # from a previous process instance must be repaired to FAILED before
    # the periodic cleanup scan ever runs against them). See
    # job_store.reconcile_interrupted_jobs's docstring for exactly why this
    # is safe only because there is a single backend process.
    counts = job_store.reconcile_interrupted_jobs()
    logger.info(
        "startup reconciliation marked %s queued and %s running jobs as failed",
        counts["queued_recovered"],
        counts["running_recovered"],
    )
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(evaluate_router)
app.include_router(jobs_router)


@app.get("/")
def home():
    return {
        "message": "Synthetic Data Benchmark Backend Running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }