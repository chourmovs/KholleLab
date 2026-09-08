#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.curriculum_repository import CurriculumCorpusError, CurriculumRepository  # noqa: E402
from app.services.problem_repository import ProblemCorpusError, ProblemRepository  # noqa: E402

curriculum = CurriculumRepository(ROOT / "curriculum")
try:
    curriculum.load()
    repository = ProblemRepository(ROOT / "problems", curriculum)
    repository.load()
except (CurriculumCorpusError, ProblemCorpusError) as exc:
    print(exc, file=sys.stderr)
    raise SystemExit(1)
print("Khollelab curriculum and problem corpus valid.")
print(f"Corpus: {repository.count}")
for level in curriculum.levels:
    problems = [problem for problem in repository.list() if problem.curriculum.level == level.id]
    minimum = 10 if level.id.value in {"quatrieme", "troisieme"} else 5
    if len(problems) < minimum:
        print(f"Required curriculum {level.id.value} has {len(problems)} problems; minimum is {minimum}.", file=sys.stderr)
        raise SystemExit(1)
    counts = " ".join(f"D{difficulty} {sum(p.curriculum.difficulty == difficulty for p in problems)}" for difficulty in range(1, 6))
    print(f"{level.label:<12} {len(problems):>3}  {counts}")
