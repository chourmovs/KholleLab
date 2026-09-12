from pathlib import Path

from app.domain.problem import Problem
from app.services.curriculum_repository import CurriculumRepository
from app.services.knowledge_resolver import curriculum_snapshot_for_problem, knowledge_for_problem

ROOT = Path(__file__).resolve().parents[2]


def test_direct_knowledge_resolution_and_snapshot_do_not_propagate_graph():
    curriculum = CurriculumRepository(ROOT / "curriculum"); curriculum.load()
    expectation = next(item for item in curriculum.expectations.values() if "factorisation" in item.knowledge_ids)
    problem = Problem.model_validate({"id":"resolver-test","title":"Factoriser","statement":"Factoriser x²-1.",
        "curriculum":{"level":expectation.level.value,"difficulty":2,"expectations":[expectation.id]},
        "topics":["algebra"],"skills":["calculation"],"source":{"type":"internal","name":"test"},
        "reference_solution":"(x-1)(x+1)"})
    result = knowledge_for_problem(problem, curriculum)
    assert "factorisation" in result.knowledge_ids
    assert "algebra" not in result.knowledge_ids
    assert not set(curriculum.knowledge_nodes["factorisation"].prerequisites) & set(result.knowledge_ids)
    assert curriculum_snapshot_for_problem(problem, curriculum) == {"version":1,
        "expectation_ids":[expectation.id],"knowledge_ids":list(result.knowledge_ids),"difficulty":2}
