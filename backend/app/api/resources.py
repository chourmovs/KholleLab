from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from app.domain.problem import CurriculumLevel, Skill, Topic
from app.domain.resource import PedagogicalResource, ResourceType
from app.services.resource_repository import ResourceRepository

router = APIRouter(prefix="/resources", tags=["resources"])


def repository(request: Request) -> ResourceRepository:
    return request.app.state.resource_repository


@router.get("", response_model=list[PedagogicalResource], response_model_exclude_none=True)
def list_resources(
    request: Request,
    resource_type: Annotated[ResourceType | None, Query(alias="type")] = None,
    level: CurriculumLevel | None = None,
    topic: Topic | None = None,
    prerequisite: str | None = None,
    skill: Skill | None = None,
) -> list[PedagogicalResource]:
    values = repository(request).list()
    return [resource for resource in values if
            (resource_type is None or resource.type == resource_type) and
            (level is None or level in resource.curriculum_levels) and
            (topic is None or topic in resource.topics) and
            (prerequisite is None or prerequisite in resource.prerequisites) and
            (skill is None or skill in resource.skills)]


@router.get("/{resource_id}", response_model=PedagogicalResource, response_model_exclude_none=True)
def get_resource(resource_id: str, request: Request) -> PedagogicalResource:
    resource = repository(request).get(resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource
