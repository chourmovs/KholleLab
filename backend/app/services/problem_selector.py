from app.domain.problem import CurriculumLevel, Problem, Topic


class ProblemSelector:
    """Selects from an already-loaded corpus without crossing curricula."""

    def __init__(self, problems: list[Problem]) -> None:
        self._problems = tuple(problems)

    def select(self, *, level: CurriculumLevel, difficulty: int | None = None,
               topics: list[Topic] | None = None, exclude_ids: set[str] | None = None) -> Problem | None:
        excluded = exclude_ids or set()
        candidates = [p for p in self._problems if p.curriculum.level == level and p.id not in excluded]
        if topics:
            required = set(topics)
            candidates = [p for p in candidates if required.intersection(p.topics)]
        if not candidates:
            return None
        if difficulty is not None:
            candidates.sort(key=lambda p: (abs(p.curriculum.difficulty - difficulty), p.curriculum.difficulty > difficulty,
                                           p.curriculum.difficulty, p.id))
        else:
            candidates.sort(key=lambda p: p.id)
        return candidates[0]
