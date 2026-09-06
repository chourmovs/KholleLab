from app.domain.problem import Problem
from app.services.problem_selector import ProblemSelector

def problem(identifier, level, difficulty, topic="algebra"):
    return Problem.model_validate({"id":identifier,"title":"Test","statement":"Test","curriculum":{"level":level,"difficulty":difficulty},"topics":[topic],"source":{"type":"internal","name":"Tests"},"reference_solution":"Solution"})

def test_exact_topic_exclusion_and_fallback():
    problems=[problem("test-one", "terminale", 2),problem("test-two", "terminale", 4),problem("test-geometry", "terminale", 3, "geometry")]
    selector=ProblemSelector(problems)
    assert selector.select(level="terminale",difficulty=3,topics=["geometry"]).id == "test-geometry"
    assert selector.select(level="terminale",difficulty=3,exclude_ids={"test-geometry"}).curriculum.difficulty == 2
    assert selector.select(level="maths-spe",difficulty=2) is None

def test_large_in_memory_corpus():
    selector=ProblemSelector([problem(f"fixture-{i:04d}","seconde",i%5+1) for i in range(1000)])
    assert selector.select(level="seconde",difficulty=3) is not None

def test_recent_history_cannot_fabricate_an_empty_corpus():
    one=problem("only-problem","seconde",2)
    assert ProblemSelector([one]).select(level="seconde",exclude_ids={one.id}) == one
    two=problem("other-problem","seconde",2)
    assert ProblemSelector([one,two]).select(level="seconde",exclude_ids={one.id,two.id}) is not None
    assert ProblemSelector([one,two,problem("geometry-only","seconde",2,"geometry")]).select(
        level="seconde",topics=["geometry"],exclude_ids={"geometry-only"}
    ).id == "geometry-only"
