from collections.abc import Collection

from app.domain.problem import CurriculumLevel, Problem, Topic


class ProblemSelector:
    """Selects from an already-loaded corpus without crossing curricula."""

    def __init__(self, problems: list[Problem]) -> None:
        self._problems = tuple(problems)

    def select(self, *, level: CurriculumLevel, difficulty: int | None = None,
               topics: list[Topic] | None = None, exclude_ids: Collection[str] | None = None) -> Problem | None:
        compatible = [p for p in self._problems if p.curriculum.level == level]
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
        if difficulty is not None:
            candidates.sort(key=lambda p: (abs(p.curriculum.difficulty - difficulty), p.curriculum.difficulty > difficulty,
                                           p.curriculum.difficulty, p.id))
        else:
            candidates.sort(key=lambda p: p.id)
        return candidates[0]

    def compatible_candidates(self, *, level: CurriculumLevel,
                              topics: list[Topic] | None = None) -> list[Problem]:
        """Return only hard-compatible problems in a stable order.

        Difficulty deliberately remains a ranking/fallback preference, matching
        ``select``; curriculum and an explicitly requested topic are hard rules.
        """
        required = set(topics or ())
        return sorted(
            (problem for problem in self._problems
             if problem.curriculum.level == level
             and (not required or bool(required.intersection(problem.topics)))),
            key=lambda problem: problem.id,
        )
