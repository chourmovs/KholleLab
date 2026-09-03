from pathlib import Path
import pytest
from app.services.problem_repository import ProblemCorpusError, ProblemRepository

VALID='''id: demo-001\ntitle: Demo\nstatement: Test\nlevel: premiere\ndifficulty: 1\ntopics: [algebra]\nsource: {type: internal, name: Tests}\nreference_solution: Solution\n'''

def test_recursive_and_deterministic(tmp_path: Path):
    (tmp_path/'b/c').mkdir(parents=True); (tmp_path/'a').mkdir()
    (tmp_path/'b/c/two.yaml').write_text(VALID.replace('demo-001','demo-002'))
    (tmp_path/'a/one.yaml').write_text(VALID)
    repo=ProblemRepository(tmp_path); repo.load()
    assert [p.id for p in repo.list()] == ['demo-001','demo-002']
    assert repo.count == 2 and repo.get('unknown') is None

def test_duplicate_id(tmp_path: Path):
    (tmp_path/'a.yaml').write_text(VALID); (tmp_path/'b.yaml').write_text(VALID)
    with pytest.raises(ProblemCorpusError, match='duplicate ID'): ProblemRepository(tmp_path).load()
def test_invalid_yaml(tmp_path: Path):
    (tmp_path/'bad.yaml').write_text('x: [')
    with pytest.raises(ProblemCorpusError, match='bad.yaml'): ProblemRepository(tmp_path).load()
def test_invalid_domain(tmp_path: Path):
    (tmp_path/'bad.yaml').write_text(VALID.replace('difficulty: 1','difficulty: 9'))
    with pytest.raises(ProblemCorpusError, match='difficulty'): ProblemRepository(tmp_path).load()
