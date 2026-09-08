#!/usr/bin/env python3
"""Validate resource schema plus all problem and curriculum references."""
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.curriculum_repository import CurriculumRepository
from app.services.problem_repository import ProblemRepository
from app.services.resource_repository import (ResourceRepository, validate_problem_resource_refs,
                                               validate_resource_curriculum_refs)


def main() -> None:
    curriculum = CurriculumRepository(ROOT / "curriculum"); curriculum.load()
    problems = ProblemRepository(ROOT / "problems", curriculum); problems.load()
    resources = ResourceRepository(ROOT / "resources"); resources.load()
    validate_resource_curriculum_refs(resources, curriculum)
    validate_problem_resource_refs(problems, resources)
    uses = Counter(slug for problem in problems.list() for slug in problem.prerequisites)
    matched = {slug for resource in resources.list() for slug in resource.prerequisites}
    print("RESOURCE VALIDATION\n")
    print(f"files: {resources.count}\n")
    for kind in ("course", "example", "video"):
        print(f"{kind}: {len(resources.list_by_type(kind))}")
    print("\nduplicate ids: 0\ninvalid resources: 0\ndangling problem refs: 0")
    print("unknown knowledge refs: 0\nunknown expectation refs: 0\nincompatible expectation levels: 0")
    print(f"unmatched prerequisite slugs: {len(set(uses) - matched)}\n")
    print("PREREQUISITE AUDIT")
    for slug in sorted(uses):
        resource_ids = [r.id for r in resources.list() if slug in r.prerequisites]
        print(f"{slug}: uses={uses[slug]}, resources={','.join(resource_ids) or '-'}")

if __name__ == "__main__": main()
