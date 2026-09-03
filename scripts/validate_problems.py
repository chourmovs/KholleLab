#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.problem_repository import ProblemCorpusError, ProblemRepository  # noqa: E402

repository = ProblemRepository(ROOT / "problems")
try:
    repository.load()
except ProblemCorpusError as exc:
    print(exc, file=sys.stderr)
    raise SystemExit(1)
print("Khollelab problem corpus valid.")
print(f"{repository.count} problems loaded.")
