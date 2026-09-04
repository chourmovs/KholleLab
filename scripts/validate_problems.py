#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.problem_repository import ProblemCorpusError, ProblemRepository  # noqa: E402
from app.domain.problem import CURRICULUM_ORDER  # noqa: E402

repository = ProblemRepository(ROOT / "problems")
try:
    repository.load()
except ProblemCorpusError as exc:
    print(exc, file=sys.stderr)
    raise SystemExit(1)
print("Khollelab problem corpus valid.")
print(f"{repository.count} problems loaded.")
print("Corpus distribution:")
labels = {"seconde":"Seconde", "premiere":"Première", "terminale":"Terminale", "maths-sup":"Maths Sup", "maths-spe":"Maths Spé"}
for level in CURRICULUM_ORDER:
    problems = [problem for problem in repository.list() if problem.curriculum.level == level]
    if not problems:
        print(f"No problems for required curriculum {level}.", file=sys.stderr)
        raise SystemExit(1)
    counts = " ".join(f"D{difficulty} {sum(p.curriculum.difficulty == difficulty for p in problems)}" for difficulty in range(1, 6))
    print(f"{labels[level]:<12} {len(problems):>3}  {counts}")
