import sys
from pathlib import Path

from loguru import logger

from app.core.config import settings

FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level: <5} | {extra[component]: <10} | {message}"


def configure_logging() -> None:
    """Configure the two application sinks without ever serialising environment data."""
    directory = Path(settings.runtime_logs_dir)
    directory.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.configure(extra={"component": "application"})
    logger.add(sys.stderr, level=settings.log_level, format=FORMAT, backtrace=False, diagnose=False)
    logger.add(
        directory / "khollelab.log",
        level=settings.log_level,
        format=FORMAT,
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        backtrace=False,
        diagnose=False,
    )


def component_logger(component: str):
    return logger.bind(component=component)
