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
from app.services.problem_catalog import ProblemCatalog
from app.services.curriculum_repository import CurriculumRepository, academic_year_for
from datetime import date

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
    curriculum = CurriculumRepository(settings.curriculum_dir); curriculum.load()
    academic_year = settings.curriculum_academic_year or academic_year_for(date.today())
    static = ProblemRepository(settings.problems_dir, curriculum, academic_year); static.load()
    problems = ProblemCatalog(static, SessionLocal)
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
