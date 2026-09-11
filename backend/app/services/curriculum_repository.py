from __future__ import annotations

from datetime import date
from pathlib import Path
import re

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain.problem import CurriculumLevel


class CurriculumCorpusError(RuntimeError):
    """The version-controlled curriculum catalogue is structurally invalid."""


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Level(Model):
    id: CurriculumLevel
    label: str = Field(min_length=1)
    short_label: str = Field(min_length=1)
    stage: str = Field(pattern="^(college|lycee|cpge)$")


class Difficulty(Model):
    id: int = Field(ge=1, le=5)
    label: str = Field(min_length=1)


class Applicability(Model):
    level: CurriculumLevel
    academic_year_from: str
    academic_year_until: str | None = None


class Programme(Model):
    id: str
    label: str
    authority: str
    publication_date: date
    source_reference: str
    source_url: str
    applicability: tuple[Applicability, ...] = Field(min_length=1)


class KnowledgeNode(Model):
    id: str
    label: str
    kind: str
    parent: str | None = None
    prerequisites: tuple[str, ...] = ()


class CurriculumExpectation(Model):
    id: str
    programme_id: str
    level: CurriculumLevel
    domain: str
    theme: str | None = None
    theme_label: str | None = None
    order: int = Field(default=0, ge=0)
    historical: bool = False
    label: str
    description: str
    knowledge_ids: tuple[str, ...] = Field(min_length=1)
    source_reference: str


YEAR_RE = re.compile(r"^(\d{4})-(\d{4})$")


def academic_year_for(day: date) -> str:
    """Return the French school year; September starts the next school year."""
    start = day.year if day.month >= 9 else day.year - 1
    return f"{start}-{start + 1}"


def _year_start(value: str) -> int:
    match = YEAR_RE.fullmatch(value)
    if not match or int(match.group(2)) != int(match.group(1)) + 1:
        raise CurriculumCorpusError(f"invalid academic year: {value!r} (expected YYYY-YYYY with consecutive years)")
    return int(match.group(1))


class CurriculumRepository:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.levels: tuple[Level, ...] = ()
        self.difficulties: tuple[Difficulty, ...] = ()
        self.programmes: dict[str, Programme] = {}
        self.expectations: dict[str, CurriculumExpectation] = {}
        self.knowledge_nodes: dict[str, KnowledgeNode] = {}
        self.expectations_by_level_domain: dict[tuple[CurriculumLevel, str], tuple[CurriculumExpectation, ...]] = {}

    def _read(self, relative: str) -> dict:
        path = self.root / relative
        try:
            value = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise CurriculumCorpusError(f"curriculum catalogue invalid: {path}: {exc}") from exc
        if not isinstance(value, dict) or value.get("schema_version") != 1:
            raise CurriculumCorpusError(f"curriculum catalogue invalid: {path}: schema_version must be 1")
        return value

    @staticmethod
    def _index(items, kind: str):
        result = {}
        for item in items:
            if item.id in result:
                raise CurriculumCorpusError(f"duplicate {kind} ID: {item.id}")
            result[item.id] = item
        return result

    def load(self) -> None:
        try:
            levels = self._read("levels.yaml")
            self.levels = tuple(Level.model_validate(x) for x in levels.get("levels", ()))
            self.difficulties = tuple(Difficulty.model_validate(x) for x in levels.get("difficulties", ()))
            self.programmes = self._index((Programme.model_validate(x) for x in self._read("programmes/programmes.yaml").get("programmes", ())), "programme")
            self.knowledge_nodes = self._index((KnowledgeNode.model_validate(x) for x in self._read("knowledge/nodes.yaml").get("knowledge", ())), "knowledge")
            self.expectations = self._index((CurriculumExpectation.model_validate(x) for x in self._read("expectations/expectations.yaml").get("expectations", ())), "expectation")
        except ValidationError as exc:
            raise CurriculumCorpusError(f"curriculum catalogue invalid: {exc}") from exc
        expected_order = tuple(CurriculumLevel)
        if tuple(level.id for level in self.levels) != expected_order:
            raise CurriculumCorpusError("levels.yaml order must match the complete CurriculumLevel compatibility enum")
        if len({x.id for x in self.levels}) != len(self.levels) or tuple(x.id for x in self.difficulties) != (1, 2, 3, 4, 5):
            raise CurriculumCorpusError("level IDs must be unique and difficulties must be ordered 1 through 5")
        known_levels = {x.id for x in self.levels}
        for programme in self.programmes.values():
            for applicability in programme.applicability:
                if applicability.level not in known_levels:
                    raise CurriculumCorpusError(f"programme {programme.id} references unknown level {applicability.level}")
                start = _year_start(applicability.academic_year_from)
                if applicability.academic_year_until and _year_start(applicability.academic_year_until) < start:
                    raise CurriculumCorpusError(f"programme {programme.id} has an inverted applicability interval")
        self._validate_no_overlaps()
        self._validate_knowledge_graph()
        grouped: dict[tuple[CurriculumLevel, str], list[CurriculumExpectation]] = {}
        for expectation in self.expectations.values():
            programme = self.programmes.get(expectation.programme_id)
            if programme is None:
                raise CurriculumCorpusError(f"expectation {expectation.id} references unknown programme {expectation.programme_id}")
            if not any(a.level == expectation.level for a in programme.applicability):
                raise CurriculumCorpusError(f"expectation {expectation.id} uses a level outside programme {programme.id}")
            unknown = [x for x in expectation.knowledge_ids if x not in self.knowledge_nodes]
            if unknown:
                raise CurriculumCorpusError(f"expectation {expectation.id} references unknown knowledge {unknown[0]}")
            if len(set(expectation.knowledge_ids)) != len(expectation.knowledge_ids):
                raise CurriculumCorpusError(f"expectation {expectation.id} contains duplicate knowledge references")
            if expectation.domain not in domain_labels():
                raise CurriculumCorpusError(f"expectation {expectation.id} uses unknown domain {expectation.domain}")
            grouped.setdefault((expectation.level, expectation.domain), []).append(expectation)
        ordered_groups: dict[tuple[str, CurriculumLevel, str], list[int]] = {}
        for expectation in self.expectations.values():
            if not expectation.historical and expectation.order:
                ordered_groups.setdefault(
                    (expectation.programme_id, expectation.level, expectation.domain), []
                ).append(expectation.order)
        for key, orders in ordered_groups.items():
            if len(orders) != len(set(orders)):
                raise CurriculumCorpusError(f"duplicate pedagogical order in {key[0]}/{key[1].value}/{key[2]}")
        self.expectations_by_level_domain = {
            key: tuple(sorted(value, key=lambda x: (x.historical, x.order, x.id))) for key, value in grouped.items()
        }

    def _validate_no_overlaps(self) -> None:
        by_level: dict[CurriculumLevel, list[tuple[int, int, str]]] = {}
        for programme in self.programmes.values():
            for item in programme.applicability:
                by_level.setdefault(item.level, []).append((_year_start(item.academic_year_from), _year_start(item.academic_year_until) if item.academic_year_until else 9999, programme.id))
        for level, spans in by_level.items():
            for index, left in enumerate(spans):
                for right in spans[index + 1:]:
                    if max(left[0], right[0]) <= min(left[1], right[1]):
                        raise CurriculumCorpusError(f"overlapping programme applicability for {level.value}: {left[2]} and {right[2]}")

    def _validate_knowledge_graph(self) -> None:
        edges: dict[str, tuple[str, ...]] = {}
        for node in self.knowledge_nodes.values():
            refs = tuple(x for x in (node.parent, *node.prerequisites) if x)
            for ref in refs:
                if ref == node.id:
                    raise CurriculumCorpusError(f"knowledge {node.id} cannot reference itself")
                if ref not in self.knowledge_nodes:
                    raise CurriculumCorpusError(f"knowledge {node.id} references unknown knowledge {ref}")
            edges[node.id] = refs
        visiting: list[str] = []
        visited: set[str] = set()
        def visit(identifier: str) -> None:
            if identifier in visiting:
                raise CurriculumCorpusError(f"knowledge prerequisite cycle: {' -> '.join(visiting[visiting.index(identifier):] + [identifier])}")
            if identifier in visited:
                return
            visiting.append(identifier)
            for target in edges[identifier]:
                visit(target)
            visiting.pop()
            visited.add(identifier)
        for identifier in edges:
            visit(identifier)

    def resolve_programme(self, level: CurriculumLevel | str, academic_year: str) -> Programme:
        level = CurriculumLevel(level)
        year = _year_start(academic_year)
        matches = [p for p in self.programmes.values() for a in p.applicability
                   if a.level == level and _year_start(a.academic_year_from) <= year
                   and (a.academic_year_until is None or year <= _year_start(a.academic_year_until))]
        if len(matches) != 1:
            raise CurriculumCorpusError(f"expected exactly one programme for {level.value} in {academic_year}; found {len(matches)}")
        return matches[0]

    def level_metadata(self, academic_year: str) -> list[dict]:
        result = []
        for level in self.levels:
            programme = self.resolve_programme(level.id, academic_year)
            domains = []
            for (item_level, domain), expectations in self.expectations_by_level_domain.items():
                active = [x for x in expectations if x.programme_id == programme.id and not x.historical]
                if item_level == level.id and active:
                    domains.append({"id": domain, "label": domain_labels()[domain], "expectations": [
                        {"id": x.id, "label": x.label, "theme": x.theme_label} for x in active
                    ]})
            result.append({"id": level.id.value, "label": level.label, "short_label": level.short_label, "stage": level.stage,
                           "programme": {"id": programme.id, "label": programme.label}, "domains": sorted(domains, key=lambda x: x["label"])})
        return result


def domain_labels() -> dict[str, str]:
    return {"numbers": "Nombres et calculs", "algebra": "Algèbre", "geometry": "Géométrie", "data": "Données et statistiques", "functions": "Fonctions", "analysis": "Analyse", "probability": "Probabilités", "logic": "Logique et raisonnement", "algorithmics": "Algorithmique et programmation", "automatismes": "Automatismes"}
