from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from app.domain.resource import PedagogicalResource, RESOURCE_ADAPTER, ResourceType


class ResourceCorpusError(RuntimeError):
    """The version-controlled pedagogical catalogue is invalid."""


class ResourceRepository:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self._resources: tuple[PedagogicalResource, ...] = ()
        self._by_id: dict[str, PedagogicalResource] = {}

    def load(self) -> None:
        loaded: dict[str, PedagogicalResource] = {}
        origins: dict[str, Path] = {}
        for path in sorted(self.root.glob("**/*.yaml")):
            try:
                raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError) as exc:
                raise ResourceCorpusError(f"Resource catalogue validation failed:\nfile: {path}\n{exc}") from exc
            resource_id = raw.get("id") if isinstance(raw, dict) else None
            try:
                resource = RESOURCE_ADAPTER.validate_python(raw)
            except ValidationError as exc:
                identity = f"\nresource ID: {resource_id}" if resource_id else ""
                raise ResourceCorpusError(
                    f"Resource catalogue validation failed:\nfile: {path}{identity}\n{exc}"
                ) from exc
            if resource.id in loaded:
                raise ResourceCorpusError(
                    f"Resource catalogue validation failed:\nfile: {path}\nresource ID: {resource.id}\n"
                    f"duplicate ID (already defined in {origins[resource.id]})"
                )
            loaded[resource.id] = resource
            origins[resource.id] = path
        self._resources = tuple(loaded[key] for key in sorted(loaded))
        self._by_id = loaded

    def list(self) -> list[PedagogicalResource]:
        return list(self._resources)

    def get(self, resource_id: str) -> PedagogicalResource | None:
        return self._by_id.get(resource_id)

    def list_by_type(self, resource_type: ResourceType | str) -> list[PedagogicalResource]:
        return [resource for resource in self._resources if resource.type == resource_type]

    @property
    def count(self) -> int:
        return len(self._resources)


def validate_problem_resource_refs(problems, resources: ResourceRepository) -> None:
    for problem in problems.list():
        for resource_id in problem.resource_refs:
            if resources.get(resource_id) is None:
                raise ResourceCorpusError(
                    f"Problem {problem.id} references unknown resource {resource_id}"
                )
