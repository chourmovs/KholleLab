from pathlib import Path
import re
import unicodedata

import yaml
from pydantic import ValidationError

from app.domain.problem import CURRICULUM_ORDER, Problem


class ProblemCorpusError(RuntimeError):
    """The on-disk corpus is malformed or inconsistent."""


class ProblemRepository:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self._problems: tuple[Problem, ...] = ()
        self._by_id: dict[str, Problem] = {}

    def load(self) -> None:
        if not self.root.is_dir():
            raise ProblemCorpusError(
                f"Problem corpus validation failed:\ndirectory does not exist: {self.root}"
            )
        paths = sorted(self.root.glob("**/*.yaml"))
        if not paths:
            raise ProblemCorpusError(
                f"Problem corpus validation failed:\nno YAML files found under {self.root}"
            )
        loaded: dict[str, Problem] = {}
        origins: dict[str, Path] = {}
        statements: dict[str, Path] = {}
        for path in paths:
            try:
                raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError) as exc:
                raise ProblemCorpusError(f"Problem corpus validation failed:\n{path}\n{exc}") from exc
            problem_id = raw.get("id") if isinstance(raw, dict) else None
            try:
                problem = Problem.model_validate(raw)
            except ValidationError as exc:
                identity = f"\nproblem ID: {problem_id}" if problem_id else ""
                raise ProblemCorpusError(
                    f"Problem corpus validation failed:\n{path}{identity}\n{exc}"
                ) from exc
            if problem.id in loaded:
                raise ProblemCorpusError(
                    f"Problem corpus validation failed:\n{path}\nproblem ID: {problem.id}\n"
                    f"duplicate ID (already defined in {origins[problem.id]})"
                )
            normalized = re.sub(
                r"\s+", " ", unicodedata.normalize("NFKC", problem.statement).casefold()
            ).strip()
            if normalized in statements:
                raise ProblemCorpusError(
                    f"Problem corpus validation failed:\n{path}\nproblem ID: {problem.id}\n"
                    f"duplicate normalized statement (already defined in {statements[normalized]})"
                )
            loaded[problem.id] = problem
            origins[problem.id] = path
            statements[normalized] = path
        self._problems = tuple(loaded[key] for key in sorted(loaded))
        self._by_id = dict(loaded)
        self._validate_recommendations(origins)

    def _validate_recommendations(self, origins: dict[str, Path]) -> None:
        order = {level: index for index, level in enumerate(CURRICULUM_ORDER)}
        edges: dict[str, tuple[str, ...]] = {}
        for problem in self._problems:
            edges[problem.id] = problem.recommended_after
            for target_id in problem.recommended_after:
                target = self._by_id.get(target_id)
                if target is None:
                    raise ProblemCorpusError(f"Problem corpus validation failed:\n{origins[problem.id]}\nproblem ID: {problem.id}\nrecommended_after target does not exist: {target_id}")
                if target_id == problem.id:
                    raise ProblemCorpusError(f"Problem corpus validation failed:\n{origins[problem.id]}\nproblem ID: {problem.id}\nrecommended_after cannot reference itself")
                if order[target.curriculum.level.value] > order[problem.curriculum.level.value]:
                    raise ProblemCorpusError(f"Problem corpus validation failed:\n{origins[problem.id]}\nproblem ID: {problem.id}\nrecommended_after target {target_id} is in a later curriculum")
        visiting: list[str] = []; visited: set[str] = set()
        def visit(identifier: str) -> None:
            if identifier in visiting:
                cycle = visiting[visiting.index(identifier):] + [identifier]
                raise ProblemCorpusError(f"Problem corpus validation failed:\n{origins[identifier]}\nproblem ID: {identifier}\nrecommended_after cycle: {' -> '.join(cycle)}")
            if identifier in visited: return
            visiting.append(identifier)
            for target in edges[identifier]: visit(target)
            visiting.pop(); visited.add(identifier)
        for identifier in edges: visit(identifier)

    def list(self) -> list[Problem]:
        return list(self._problems)

    def get(self, problem_id: str) -> Problem | None:
        return self._by_id.get(problem_id)

    @property
    def count(self) -> int:
        return len(self._problems)
