from collections.abc import Collection

from app.domain.problem import CurriculumLevel, Problem, Topic
from app.services.curriculum_repository import CurriculumRepository


class ProblemSelector:
    """Selects from an already-loaded corpus without crossing curricula."""

    def __init__(self, problems: list[Problem], curriculum: CurriculumRepository | None = None,
                 programme_id: str | None = None) -> None:
        self._problems = tuple(problems)
        self._curriculum = curriculum
        self._programme_id = programme_id

    def _matches_domain(self, problem: Problem, domain: str | None) -> bool:
        if not domain:
            return True
        if self._curriculum is None:
            return False
        return any(
            (expectation := self._curriculum.expectations.get(identifier)) is not None
            and expectation.domain == domain
            and (self._programme_id is None or expectation.programme_id == self._programme_id)
            for identifier in problem.curriculum.expectations
        )

    def select(self, *, level: CurriculumLevel, difficulty: int | None = None,
               topics: list[Topic] | None = None, domain: str | None = None,
               expectation: str | None = None,
               exclude_ids: Collection[str] | None = None) -> Problem | None:
        compatible = [p for p in self._problems if p.curriculum.level == level]
        compatible = [p for p in compatible if self._matches_domain(p, domain)]
        if expectation:
            compatible = [p for p in compatible if expectation in p.curriculum.expectations]
        if topics:
            required = set(topics)
            compatible = [p for p in compatible if required.intersection(p.topics)]
        # Recent-history exclusions are preferences, not compatibility constraints.
        # If exhausted, retain the first exclusion (the current exercise) where possible,
        # and finally allow a repeat for a one-item corpus.
        exclusions = list(exclude_ids or ())
        excluded = set(exclusions)
        candidates = [p for p in compatible if p.id not in excluded]
        if not candidates and compatible:
            mandatory = next((identifier for identifier in exclusions if any(p.id == identifier for p in compatible)), None)
            candidates = [p for p in compatible if p.id != mandatory]
        if not candidates:
            candidates = compatible
        if not candidates:
            return None
        # An explicit exclusion usually means “another exercise”. Prefer another
        # parametric archetype before merely changing its coefficients.
        excluded_families = {
            problem.generation.family_id for problem in compatible
            if problem.id in excluded and problem.generation
        }
        diverse = [problem for problem in candidates
                   if not problem.generation or problem.generation.family_id not in excluded_families]
        if diverse:
            candidates = diverse
        if difficulty is not None:
            candidates.sort(key=lambda p: (abs(p.curriculum.difficulty - difficulty), p.curriculum.difficulty > difficulty,
                                           p.curriculum.difficulty, p.id))
        else:
            candidates.sort(key=lambda p: p.id)
        return candidates[0]

    def compatible_candidates(self, *, level: CurriculumLevel,
                              topics: list[Topic] | None = None, domain: str | None = None,
                              expectation: str | None = None) -> list[Problem]:
        """Return only hard-compatible problems in a stable order.

        Difficulty deliberately remains a ranking/fallback preference, matching
        ``select``; curriculum and an explicitly requested topic are hard rules.
        """
        required = set(topics or ())
        return sorted(
            (problem for problem in self._problems
             if problem.curriculum.level == level
             and self._matches_domain(problem, domain)
             and (not expectation or expectation in problem.curriculum.expectations)
             and (not required or bool(required.intersection(problem.topics)))),
            key=lambda problem: problem.id,
        )
