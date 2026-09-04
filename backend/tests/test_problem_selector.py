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
