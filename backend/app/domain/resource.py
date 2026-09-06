from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, HttpUrl, StringConstraints, Tag, TypeAdapter, model_validator

from app.domain.problem import CurriculumLevel, NonEmpty, Skill, Slug, StrictModel, Topic

ResourceId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")]


class ResourceType(StrEnum):
    COURSE = "course"
    EXAMPLE = "example"
    VIDEO = "video"


class ResourceMetadata(StrictModel):
    id: ResourceId
    title: NonEmpty
    curriculum_levels: tuple[CurriculumLevel, ...] = Field(min_length=1)
    topics: tuple[Topic, ...] = ()
    prerequisites: tuple[Slug, ...] = ()
    skills: tuple[Skill, ...] = ()
    tags: tuple[Slug, ...] = ()
    priority: int = 0

    @model_validator(mode="after")
    def reject_duplicate_classification(self) -> "ResourceMetadata":
        for name in ("curriculum_levels", "topics", "prerequisites", "skills", "tags"):
            values = getattr(self, name)
            if len(values) != len(set(values)):
                raise ValueError(f"{name} must not contain duplicates")
        return self


class CourseResource(ResourceMetadata):
    type: Literal["course"]
    summary: NonEmpty
    content: NonEmpty


class ExampleResource(ResourceMetadata):
    type: Literal["example"]
    statement: NonEmpty
    solution: NonEmpty


class VideoResource(ResourceMetadata):
    type: Literal["video"]
    provider: Literal["youtube"]
    url: HttpUrl
    author: NonEmpty
    duration_minutes: int = Field(gt=0)

    @model_validator(mode="after")
    def require_youtube_url(self) -> "VideoResource":
        if self.url.host not in {"youtube.com", "www.youtube.com", "youtu.be"}:
            raise ValueError("youtube resources must use a YouTube URL")
        return self


PedagogicalResource = Annotated[
    Annotated[CourseResource, Tag("course")]
    | Annotated[ExampleResource, Tag("example")]
    | Annotated[VideoResource, Tag("video")],
    Field(discriminator="type"),
]
RESOURCE_ADAPTER = TypeAdapter(PedagogicalResource)
