from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, update

from app.domain.problem import Problem
from app.models.generated_problem import GeneratedProblem, GeneratedProblemStatus


class ProblemCatalog:
    """Unified durable resolution for static and globally generated problems."""

    def __init__(self, static_repository, session_factory):
        self.static = static_repository
        self.session_factory = session_factory

    @property
    def curriculum_repository(self):
        return self.static.curriculum_repository

    @property
    def academic_year(self):
        return self.static.academic_year

    def list_static(self) -> list[Problem]:
        return self.static.list()

    def list(self) -> list[Problem]:
        # Public corpus browsing remains stable; generation selection is explicit.
        return self.list_static()

    def get(self, problem_id: str) -> Problem | None:
        problem = self.static.get(problem_id)
        if problem is not None:
            return problem
        if not problem_id.startswith("llm-"):
            return None
        with self.session_factory() as db:
            row = db.get(GeneratedProblem, problem_id)
            return Problem.model_validate(row.payload_json) if row else None

    resolve = get

    def get_many(self, problem_ids, db=None) -> dict[str, Problem]:
        """Resolve static and generated IDs, including retired rows, with one DB query."""
        identifiers = tuple(dict.fromkeys(problem_ids))
        resolved = {identifier: problem for identifier in identifiers
                    if (problem := self.static.get(identifier)) is not None}
        generated_ids = [identifier for identifier in identifiers
                         if identifier not in resolved and identifier.startswith("llm-")]
        if not generated_ids:
            return resolved
        owns = db is None
        db = db or self.session_factory()
        try:
            rows = db.scalars(select(GeneratedProblem).where(GeneratedProblem.id.in_(generated_ids)))
            resolved.update({row.id: Problem.model_validate(row.payload_json) for row in rows})
            return resolved
        finally:
            if owns:
                db.close()

    @property
    def count(self) -> int:
        return self.static.count

    @property
    def _problems(self):
        return self.static._problems

    @_problems.setter
    def _problems(self, value):
        self.static._problems = value

    def find_generated(self, *, programme_id: str, level: str, expectation_id: str,
                       difficulty: int, domain: str | None = None,
                       include_retired: bool = False, db=None) -> list[GeneratedProblem]:
        owns = db is None
        db = db or self.session_factory()
        try:
            query = select(GeneratedProblem).where(
                GeneratedProblem.programme_id == programme_id,
                GeneratedProblem.level == level,
                GeneratedProblem.expectation_id == expectation_id,
                GeneratedProblem.difficulty == difficulty,
            )
            if domain:
                query = query.where(GeneratedProblem.domain == domain)
            if not include_retired:
                query = query.where(GeneratedProblem.status == GeneratedProblemStatus.ACCEPTED)
            return list(db.scalars(query.order_by(GeneratedProblem.usage_count, GeneratedProblem.created_at, GeneratedProblem.id)))
        finally:
            if owns:
                db.close()

    def generated_for_comparison(self, db, limit: int = 500) -> list[GeneratedProblem]:
        """Return a bounded cross-bucket sample for conservative textual comparison."""
        return list(db.scalars(select(GeneratedProblem).where(
            GeneratedProblem.status == GeneratedProblemStatus.ACCEPTED,
        ).order_by(GeneratedProblem.created_at.desc(), GeneratedProblem.id).limit(limit)))

    def mark_served(self, problem_id: str, db=None) -> None:
        owns = db is None
        db = db or self.session_factory()
        try:
            now = datetime.now(timezone.utc)
            db.execute(update(GeneratedProblem).where(GeneratedProblem.id == problem_id).values(
                usage_count=GeneratedProblem.usage_count + 1,
                last_served_at=now,
                updated_at=now,
            ))
            if owns:
                db.commit()
        finally:
            if owns:
                db.close()
