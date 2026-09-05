from app.domain.problem import CurriculumLevel, Skill, StrictModel, Topic
from app.domain.resource import PedagogicalResource, ResourceId, Slug
from app.services.resource_repository import ResourceRepository


class ResourceContext(StrictModel):
    curriculum_level: CurriculumLevel
    topics: tuple[Topic, ...] = ()
    prerequisites: tuple[Slug, ...] = ()
    skills: tuple[Skill, ...] = ()
    tags: tuple[Slug, ...] = ()
    problem_id: str | None = None
    explicit_resource_refs: tuple[ResourceId, ...] = ()


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
                score += 1000
                reasons.append(f"explicit:{resource.id}")
            for value in sorted(set(context.prerequisites) & set(resource.prerequisites)):
                score += 120
                reasons.append(f"prerequisite:{value}")
            for value in sorted(set(context.topics) & set(resource.topics), key=str):
                score += 60
                reasons.append(f"topic:{value.value}")
            score += 40
            reasons.append(f"level:{context.curriculum_level.value}")
            for value in sorted(set(context.skills) & set(resource.skills), key=str):
                score += 20
                reasons.append(f"skill:{value.value}")
            for value in sorted(set(context.tags) & set(resource.tags)):
                score += 10
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
