#!/usr/bin/env python3
"""Validate both curated corpora and print a prerequisite audit."""
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.problem_repository import ProblemRepository
from app.services.resource_repository import ResourceRepository, validate_problem_resource_refs


def main() -> None:
    problems = ProblemRepository(ROOT / "problems")
    resources = ResourceRepository(ROOT / "resources")
    problems.load()
    resources.load()
    validate_problem_resource_refs(problems, resources)
    uses = Counter(slug for problem in problems.list() for slug in problem.prerequisites)
    matched = {slug for resource in resources.list() for slug in resource.prerequisites}
    unmatched = sorted(set(uses) - matched)
    print("RESOURCE VALIDATION\n")
    print(f"files: {resources.count}\n")
    for kind in ("course", "example", "video"):
        print(f"{kind}: {len(resources.list_by_type(kind))}")
    print("\nduplicate ids: 0\ninvalid resources: 0\ndangling problem refs: 0")
    print(f"unmatched prerequisite slugs: {len(unmatched)}\n")
    print("PREREQUISITE AUDIT")
    for slug in sorted(uses):
        resource_ids = [r.id for r in resources.list() if slug in r.prerequisites]
        print(f"{slug}: uses={uses[slug]}, resources={','.join(resource_ids) or '-'}")


if __name__ == "__main__":
    main()
