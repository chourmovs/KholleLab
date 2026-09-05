#!/usr/bin/env python3
"""Report current resolver coverage without enforcing a threshold."""
from collections import defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.domain.problem import CURRICULUM_ORDER
from app.services.problem_repository import ProblemRepository
from app.services.resource_repository import ResourceRepository, validate_problem_resource_refs
from app.services.resource_resolver import ResourceContext, ResourceResolver

LABELS = {"seconde": "Seconde", "premiere": "Première", "terminale": "Terminale", "maths-sup": "Maths Sup", "maths-spe": "Maths Spé"}


def main() -> None:
    problems, resources = ProblemRepository(ROOT / "problems"), ResourceRepository(ROOT / "resources")
    problems.load(); resources.load(); validate_problem_resource_refs(problems, resources)
    resolver = ResourceResolver(resources)
    rows = defaultdict(lambda: [0, 0, 0])
    all_topics, covered_topics, prerequisites = set(), set(), set()
    resource_prerequisites = {slug for r in resources.list() for slug in r.prerequisites}
    for problem in problems.list():
        matches = resolver.resolve(ResourceContext(curriculum_level=problem.curriculum.level, topics=problem.topics,
            prerequisites=problem.prerequisites, skills=problem.skills, tags=problem.tags,
            problem_id=problem.id, explicit_resource_refs=problem.resource_refs))
        row = rows[problem.curriculum.level.value]; row[0] += 1
        row[1] += bool(problem.resource_refs); row[2] += bool(matches)
        all_topics.update(problem.topics); prerequisites.update(problem.prerequisites)
        if matches: covered_topics.update(problem.topics)
    print("RESOURCE COVERAGE\n")
    print(f"{'':12} {'problems':>8} {'explicit':>9} {'matched':>8} {'coverage':>9}")
    for level in CURRICULUM_ORDER:
        total, explicit, matched = rows[level]
        coverage = 100 * matched / total if total else 0
        print(f"{LABELS[level]:12} {total:8} {explicit:9} {matched:8} {coverage:8.1f}%")
    print(f"\nunique topics: {len(all_topics)}")
    print(f"topics with resource coverage: {len(covered_topics)}")
    print(f"prerequisite slugs: {len(prerequisites)}")
    print(f"unmatched prerequisite slugs: {len(prerequisites - resource_prerequisites)}")


if __name__ == "__main__":
    main()
