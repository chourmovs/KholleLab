"""Container health probe for the evaluation worker (no provider calls)."""
import sys
import time
from pathlib import Path

from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal


def check() -> bool:
    path = Path(settings.evaluation_worker_heartbeat_path)
    try:
        if not path.is_file() or time.time() - path.stat().st_mtime > settings.evaluation_worker_health_max_age_seconds:
            return False
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def main() -> int:
    return 0 if check() else 1


if __name__ == "__main__":
    sys.exit(main())
