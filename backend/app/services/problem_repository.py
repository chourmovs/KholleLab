from pathlib import Path

import yaml
from pydantic import ValidationError

from app.domain.problem import Problem


class ProblemCorpusError(RuntimeError):
    """The on-disk corpus is malformed or inconsistent."""


class ProblemRepository:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self._problems: tuple[Problem, ...] = ()
        self._by_id: dict[str, Problem] = {}

    def load(self) -> None:
        loaded: dict[str, Problem] = {}
        origins: dict[str, Path] = {}
        for path in sorted(self.root.glob("**/*.yaml")):
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
            loaded[problem.id] = problem
            origins[problem.id] = path
        self._problems = tuple(loaded[key] for key in sorted(loaded))
        self._by_id = dict(loaded)

    def list(self) -> list[Problem]:
        return list(self._problems)

    def get(self, problem_id: str) -> Problem | None:
        return self._by_id.get(problem_id)

    @property
    def count(self) -> int:
        return len(self._problems)
