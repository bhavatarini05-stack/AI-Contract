"""In-process background job runner (no Redis/Celery needed for local use).

One worker so a CPU-only machine running a local LLM isn't overloaded.
"""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor

from app.db import SessionLocal
from app.models import Job

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="analysis")


def enqueue_analysis(contract_id: int) -> Job:
    from app.pipeline.orchestrator import run_analysis

    db = SessionLocal()
    try:
        job = Job(contract_id=contract_id)
        db.add(job)
        db.commit()
        db.refresh(job)
    finally:
        db.close()
    _executor.submit(run_analysis, contract_id, job.id)
    return job


def submit(fn, *args) -> Future:
    return _executor.submit(fn, *args)


def shutdown() -> None:
    _executor.shutdown(wait=False, cancel_futures=True)
