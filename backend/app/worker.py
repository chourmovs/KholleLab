import asyncio
import contextlib
from pathlib import Path

from app.core.config import settings
from app.core.logging import component_logger, configure_logging
from app.db.session import SessionLocal
from app.providers.llm import provider_from_settings
from app.repositories.attempt_repository import AttemptRepository
from app.repositories.evaluation_repository import EvaluationRepository
from app.services.examiner import ExaminerService
from app.services.problem_repository import ProblemRepository

log = component_logger("evaluation-worker")

async def run_once(problems, provider=None):
    try:
        with SessionLocal() as db:
            evaluations = EvaluationRepository(db)
            evaluations.recover_stale(settings.evaluation_stale_seconds)
            value = evaluations.claim_next()
            if not value: return False
            service = ExaminerService(AttemptRepository(db), evaluations, problems, provider or provider_from_settings())
            await service.process(value)
            return True
    except Exception:
        log.exception("evaluation_worker_job_failed")
        return True

async def main():
    configure_logging()
    problems=ProblemRepository(settings.problems_dir); problems.load()
    provider=provider_from_settings()
    log.info("evaluation_worker_started concurrency=1")
    heartbeat=asyncio.create_task(worker_heartbeat())
    try:
        while True:
            try:
                if not await run_once(problems,provider):
                    await asyncio.sleep(settings.evaluation_worker_poll_seconds)
            except Exception:
                log.exception("evaluation_worker_loop_recovered")
                await asyncio.sleep(settings.evaluation_worker_poll_seconds)
    finally:
        heartbeat.cancel()
        with contextlib.suppress(asyncio.CancelledError): await heartbeat

async def worker_heartbeat():
    path=Path(settings.evaluation_worker_heartbeat_path)
    while True:
        try:
            await asyncio.to_thread(path.touch)
        except OSError as exc:
            log.warning("evaluation_worker_heartbeat_failure error_type={}",type(exc).__name__)
        await asyncio.sleep(settings.evaluation_worker_heartbeat_seconds)

if __name__ == "__main__":
    asyncio.run(main())
