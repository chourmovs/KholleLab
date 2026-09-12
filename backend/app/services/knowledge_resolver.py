"""Canonical, curriculum-backed mapping from a problem to direct knowledge nodes."""
from dataclasses import dataclass

from app.services.curriculum_repository import CurriculumRepository, KnowledgeNode


@dataclass(frozen=True)
class ProblemKnowledge:
    expectation_ids: tuple[str, ...]
    knowledge_ids: tuple[str, ...]
    nodes: tuple[KnowledgeNode, ...]
    metadata_issues: tuple[str, ...] = ()


def knowledge_for_problem(problem, curriculum: CurriculumRepository) -> ProblemKnowledge:
    """Resolve only explicitly mapped, non-domain nodes; never traverse graph edges."""
    expectation_ids = tuple(dict.fromkeys(problem.curriculum.expectations))
    identifiers: list[str] = []
    issues: list[str] = []
    for expectation_id in expectation_ids:
        expectation = curriculum.expectations.get(expectation_id)
        if expectation is None:
            issues.append(f"unknown_expectation:{expectation_id}")
            continue
        concrete = [identifier for identifier in expectation.knowledge_ids
                    if curriculum.knowledge_nodes[identifier].kind != "domain"]
        if not concrete:
            issues.append(f"domain_only_expectation:{expectation_id}")
        for identifier in concrete:
            if identifier not in identifiers:
                identifiers.append(identifier)
    return ProblemKnowledge(expectation_ids, tuple(identifiers),
                            tuple(curriculum.knowledge_nodes[x] for x in identifiers), tuple(issues))


def curriculum_snapshot_for_problem(problem, curriculum: CurriculumRepository) -> dict:
    mapping = knowledge_for_problem(problem, curriculum)
    return {"version": 1, "expectation_ids": list(mapping.expectation_ids),
            "knowledge_ids": list(mapping.knowledge_ids),
            "difficulty": problem.curriculum.difficulty}
