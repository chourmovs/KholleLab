#!/usr/bin/env python3
"""Report modelled official-objective and knowledge coverage for an academic year."""
from collections import Counter
from datetime import date
from pathlib import Path
import os
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
from app.services.curriculum_repository import CurriculumRepository, academic_year_for  # noqa: E402
from app.services.problem_repository import ProblemRepository  # noqa: E402
from corpus_factory.families import FAMILIES  # noqa: E402

curriculum = CurriculumRepository(ROOT / "curriculum"); curriculum.load()
year = os.getenv("CURRICULUM_ACADEMIC_YEAR") or academic_year_for(date.today())
repository = ProblemRepository(ROOT / "problems", curriculum, academic_year=year); repository.load()
school = [p for p in repository.list() if p.curriculum.level.value not in {"maths-sup", "maths-spe"}]
active = []
print(f"MODELLED OFFICIAL OBJECTIVE COVERAGE — academic year {year}")
print("Warning: modelled-objective coverage is not a claim of complete French-programme coverage.")
for level in curriculum.levels:
    if level.stage == "cpge": continue
    programme = curriculum.resolve_programme(level.id, year)
    expectations = sorted((x for x in curriculum.expectations.values() if x.level == level.id and x.programme_id == programme.id and not x.historical), key=lambda x: (x.order, x.id))
    active.extend(expectations); covered = 0
    print(f"\n{level.label} — {programme.label} — expectations={len(expectations)}")
    print("  objective | problems | families | D1 D2 D3 D4 D5")
    for expectation in expectations:
        items = [p for p in school if expectation.id in p.curriculum.expectations]
        families = {p.generation.family_id for p in items if p.generation}
        dist = Counter(p.curriculum.difficulty for p in items); covered += bool(items)
        print(f"  {expectation.id} | {len(items)} | {len(families)} | {' '.join(str(dist[d]) for d in range(1, 6))}")
    uncovered = [x.id for x in expectations if not any(x.id in p.curriculum.expectations for p in school)]
    print(f"  covered={covered}/{len(expectations)} ({covered / len(expectations):.1%}); uncovered={len(uncovered)}")
    for identifier in uncovered: print(f"    - {identifier}")
active_ids = {x.id for x in active}; active_nodes = {kid for x in active for kid in x.knowledge_ids}
problem_nodes = {kid for p in school for eid in p.curriculum.expectations if eid in curriculum.expectations for kid in curriculum.expectations[eid].knowledge_ids}
course_nodes=set()
for path in (ROOT / "resources").glob("**/*.yaml"):
    raw=yaml.safe_load(path.read_text())
    records=raw.get("resources",[]) if isinstance(raw,dict) and "resources" in raw else [raw]
    for item in records:
        if isinstance(item,dict) and item.get("type")=="course": course_nodes.update(item.get("knowledge_ids",[]))
covered=sum(any(x.id in p.curriculum.expectations for p in school) for x in active)
print(f"\nTOTAL: expectations={len(active)} covered={covered} uncovered={len(active)-covered} objective_coverage={covered/len(active):.1%}")
print(f"Families: valid_current={sum(f.expectation in active_ids for f in FAMILIES)}/{len(FAMILIES)}")
print(f"Knowledge: active={len(active_nodes)} with_problems={len(active_nodes & problem_nodes)} with_course_resources={len(active_nodes & course_nodes)} neither={len(active_nodes - problem_nodes - course_nodes)}")
for identifier in sorted(active_nodes - problem_nodes - course_nodes): print(f"  - {identifier}")
