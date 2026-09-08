from app.domain.problem import CurriculumLevel, Skill, StrictModel, Topic
from app.domain.resource import PedagogicalResource, ResourceId, Slug
from app.services.resource_repository import ResourceRepository
from app.services.curriculum_repository import CurriculumRepository

EXPLICIT_REF_WEIGHT = 10_000
EXPECTATION_WEIGHT = 1_000
KNOWLEDGE_WEIGHT = 500
PREREQUISITE_WEIGHT = 120
TOPIC_WEIGHT = 60
SKILL_WEIGHT = 20
TAG_WEIGHT = 10
LEVEL_WEIGHT = 1


class ResourceContext(StrictModel):
    curriculum_level: CurriculumLevel
    topics: tuple[Topic, ...] = ()
    prerequisites: tuple[Slug, ...] = ()
    skills: tuple[Skill, ...] = ()
    tags: tuple[Slug, ...] = ()
    problem_id: str | None = None
    explicit_resource_refs: tuple[ResourceId, ...] = ()
    knowledge_ids: tuple[Slug, ...] = ()
    curriculum_expectations: tuple[Slug, ...] = ()


def context_for_problem(problem, curriculum: CurriculumRepository) -> ResourceContext:
    """Build resolver context without duplicating curriculum knowledge in problem YAML."""
    expectation_ids = tuple(problem.curriculum.expectations)
    knowledge_ids = tuple(dict.fromkeys(
        knowledge_id
        for expectation_id in expectation_ids
        for knowledge_id in curriculum.expectations[expectation_id].knowledge_ids
    ))
    return ResourceContext(
        curriculum_level=problem.curriculum.level, topics=problem.topics,
        prerequisites=problem.prerequisites, skills=problem.skills, tags=problem.tags,
        problem_id=problem.id, explicit_resource_refs=problem.resource_refs,
        knowledge_ids=knowledge_ids, curriculum_expectations=expectation_ids,
    )


class ResolvedResource(StrictModel):
    resource: PedagogicalResource
    score: int
    reasons: tuple[str, ...]


class ResourceResolver:
    def __init__(self, repository: ResourceRepository) -> None:
        self.repository = repository

    def resolve(self, context: ResourceContext, limit: int = 3) -> list[ResolvedResource]:
        if limit < 1:
            return []
        explicit = set(context.explicit_resource_refs)
        scored: list[ResolvedResource] = []
        for resource in self.repository.list():
            # Empty level lists are forbidden by the model: generic resources must be explicit later.
            if context.curriculum_level not in resource.curriculum_levels:
                continue
            reasons: list[str] = []
            score = resource.priority
            if resource.id in explicit:
                score += EXPLICIT_REF_WEIGHT
                reasons.append(f"explicit:{resource.id}")
            expectation_matches = sorted(set(context.curriculum_expectations) & set(resource.curriculum_expectations))
            if expectation_matches:
                score += EXPECTATION_WEIGHT
            for value in expectation_matches:
                reasons.append(f"expectation:{value}")
            knowledge_matches = sorted(set(context.knowledge_ids) & set(resource.knowledge_ids))
            if knowledge_matches:
                score += KNOWLEDGE_WEIGHT
            for value in knowledge_matches:
                reasons.append(f"knowledge:{value}")
            for value in sorted(set(context.prerequisites) & set(resource.prerequisites)):
                score += PREREQUISITE_WEIGHT
                reasons.append(f"prerequisite:{value}")
            for value in sorted(set(context.topics) & set(resource.topics), key=str):
                score += TOPIC_WEIGHT
                reasons.append(f"topic:{value.value}")
            score += LEVEL_WEIGHT
            reasons.append(f"level:{context.curriculum_level.value}")
            for value in sorted(set(context.skills) & set(resource.skills), key=str):
                score += SKILL_WEIGHT
                reasons.append(f"skill:{value.value}")
            for value in sorted(set(context.tags) & set(resource.tags)):
                score += TAG_WEIGHT
                reasons.append(f"tag:{value}")
            # Level alone is eligibility, not meaningful semantic overlap.
            if len(reasons) == 1:
                continue
            scored.append(ResolvedResource(resource=resource, score=score, reasons=tuple(reasons)))

        scored.sort(key=lambda item: (-item.score, item.resource.id))
        # Keep the strongest candidate of each canonical type, then preserve rank.
        selected: list[ResolvedResource] = []
        seen_types: set[str] = set()
        for item in scored:
            if item.resource.type not in seen_types:
                selected.append(item)
                seen_types.add(item.resource.type)
        selected.sort(key=lambda item: (-item.score, item.resource.id))
        return selected[:limit]
