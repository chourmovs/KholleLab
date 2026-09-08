#!/usr/bin/env python3
"""Report depth of the currently modelled curriculum (not official completeness)."""
from collections import Counter
from datetime import date
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.curriculum_repository import CurriculumRepository, academic_year_for  # noqa: E402
from app.services.problem_repository import ProblemRepository  # noqa: E402

curriculum = CurriculumRepository(ROOT / "curriculum"); curriculum.load()
repository = ProblemRepository(ROOT / "problems", curriculum); repository.load()
year = os.getenv("CURRICULUM_ACADEMIC_YEAR") or academic_year_for(date.today())
school = [problem for problem in repository.list() if problem.curriculum.level.value not in {"maths-sup", "maths-spe"}]
print(f"Modelled curriculum corpus depth — academic year {year}")
print("Warning: this audits modelled expectations; it does not assert complete official programme coverage.")
all_families = {p.generation.family_id for p in school if p.generation}
print(f"Summary: problems={len(school)} curated={sum(p.generation is None for p in school)} "
      f"parametric={sum(p.generation is not None for p in school)} families={len(all_families)}")
for level in curriculum.levels:
    if level.stage == "cpge": continue
    programme = curriculum.resolve_programme(level.id, year)
    expectations = [item for item in curriculum.expectations.values()
                    if item.level == level.id and item.programme_id == programme.id]
    print(f"\n{level.label} — {programme.label}")
    print("  expectation | problems | curated | parametric | families | D1 D2 D3 D4 D5 | depth")
    for expectation in expectations:
        items = [p for p in school if expectation.id in p.curriculum.expectations]
        distribution = Counter(p.curriculum.difficulty for p in items)
        count = len(items)
        depth = "uncovered" if count == 0 else "thin" if count <= 2 else "developing" if count <= 7 else "deep"
        families = {p.generation.family_id for p in items if p.generation}
        print(f"  {expectation.id} | {count} | {sum(p.generation is None for p in items)} | "
              f"{sum(p.generation is not None for p in items)} | {len(families)} | "
              f"{' '.join(str(distribution[d]) for d in range(1, 6))} | {depth}")
