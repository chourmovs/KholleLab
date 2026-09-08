#!/usr/bin/env python3
from collections import Counter
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.domain.problem import CurriculumLevel  # noqa: E402
from app.services.curriculum_repository import CurriculumRepository, academic_year_for  # noqa: E402
from app.services.problem_repository import ProblemRepository  # noqa: E402
from datetime import date  # noqa: E402

curriculum = CurriculumRepository(ROOT / "curriculum"); curriculum.load()
problems = ProblemRepository(ROOT / "problems", curriculum); problems.load()
year = os.getenv("CURRICULUM_ACADEMIC_YEAR") or academic_year_for(date.today())
print(f"Curriculum coverage — academic year {year}")
for level in curriculum.levels:
    if level.stage == "cpge":
        continue
    programme = curriculum.resolve_programme(level.id, year)
    expected = [x for x in curriculum.expectations.values() if x.level == level.id and x.programme_id == programme.id]
    level_problems = [x for x in problems.list() if x.curriculum.level == level.id]
    covered = {identifier for problem in level_problems for identifier in problem.curriculum.expectations}
    uncovered = [x for x in expected if x.id not in covered]
    distribution = Counter(x.curriculum.difficulty for x in level_problems)
    print(f"\n{level.label} — {programme.label}")
    print(f"  expectations: {len(expected)}; covered: {len(expected)-len(uncovered)}; problems: {len(level_problems)}")
    print("  difficulty: " + " ".join(f"D{x}={distribution[x]}" for x in range(1, 6)))
    print("  uncovered: " + (", ".join(f"{x.id} ({x.label})" for x in uncovered) or "none"))
