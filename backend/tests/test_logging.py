from pathlib import Path

from loguru import logger

from app.core.logging import configure_logging


def test_unwritable_runtime_log_directory_does_not_block_startup(monkeypatch):
    def permission_denied(*args, **kwargs):
        raise PermissionError("read-only filesystem")

    monkeypatch.setattr(Path, "mkdir", permission_denied)

    configure_logging()

    # A usable STDERR handler remains configured even though the persistent sink
    # could not be created. This assertion intentionally avoids Loguru internals.
    logger.bind(component="api").info("API can still start")
