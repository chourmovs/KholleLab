import sys
from pathlib import Path

from loguru import logger

from app.core.config import settings

FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level: <5} | {extra[component]: <10} | {message}"


def configure_logging() -> None:
    """Configure logging, keeping STDERR available if the file sink is unwritable.

    The runtime volume is writable in Compose, but local development and CI may run
    as an unprivileged user without a ``/runtime-logs`` mount. Logging must never
    prevent the API from starting in that case.
    """
    logger.remove()
    logger.configure(extra={"component": "application"})
    logger.add(sys.stderr, level=settings.log_level, format=FORMAT, backtrace=False, diagnose=False)
    directory = Path(settings.runtime_logs_dir)
    try:
        directory.mkdir(parents=True, exist_ok=True)
        logger.add(
            directory / "khollelab.log",
            level=settings.log_level,
            format=FORMAT,
            rotation=settings.log_rotation,
            retention=settings.log_retention,
            backtrace=False,
            diagnose=False,
        )
    except OSError as exc:
        logger.bind(component="application").warning(
            "Runtime file logging unavailable path={} error_type={}; continuing with STDERR",
            directory,
            type(exc).__name__,
        )


def component_logger(component: str):
    return logger.bind(component=component)
