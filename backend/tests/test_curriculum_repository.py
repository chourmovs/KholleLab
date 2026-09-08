from datetime import date
from pathlib import Path
import shutil

import pytest
import yaml

from app.domain.problem import CURRICULUM_ORDER
from app.services.curriculum_repository import CurriculumCorpusError, CurriculumRepository, academic_year_for
from app.services.problem_repository import ProblemCorpusError, ProblemRepository

ROOT = Path(__file__).resolve().parents[2]


def repository() -> CurriculumRepository:
    result = CurriculumRepository(ROOT / "curriculum"); result.load(); return result


def copy_catalogue(tmp_path: Path) -> Path:
    target = tmp_path / "curriculum"; shutil.copytree(ROOT / "curriculum", target); return target


def test_level_order_and_frozen_academic_year_resolution():
    assert CURRICULUM_ORDER == ["quatrieme", "troisieme", "seconde", "premiere", "terminale", "maths-sup", "maths-spe"]
    assert academic_year_for(date(2026, 8, 31)) == "2025-2026"
    assert academic_year_for(date(2026, 9, 1)) == "2026-2027"


def test_programme_transition_for_same_level(tmp_path: Path):
    root = copy_catalogue(tmp_path); path = root / "programmes/programmes.yaml"; data = yaml.safe_load(path.read_text())
    old = next(x for x in data["programmes"] if x["id"] == "lycee-seconde-mathematiques-2019")
    old["applicability"][0]["academic_year_until"] = "2025-2026"
    new = dict(old, id="lycee-seconde-mathematiques-2026", label="Programme test 2026", applicability=[{"level":"seconde", "academic_year_from":"2026-2027"}])
    data["programmes"].append(new); path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
    repo = CurriculumRepository(root); repo.load()
    assert repo.resolve_programme("seconde", "2025-2026").id.endswith("2019")
    assert repo.resolve_programme("seconde", "2026-2027").id.endswith("2026")


def test_overlapping_programmes_fail(tmp_path: Path):
    root = copy_catalogue(tmp_path); path = root / "programmes/programmes.yaml"; data = yaml.safe_load(path.read_text())
    duplicate = dict(data["programmes"][1], id="collision")
    data["programmes"].append(duplicate); path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
    with pytest.raises(CurriculumCorpusError, match="overlapping"):
        CurriculumRepository(root).load()


@pytest.mark.parametrize("mutation, message", [("unknown", "unknown knowledge"), ("cycle", "cycle")])
def test_unknown_knowledge_and_cycles_fail(tmp_path: Path, mutation: str, message: str):
    root = copy_catalogue(tmp_path)
    if mutation == "unknown":
        path=root/"expectations/expectations.yaml"; data=yaml.safe_load(path.read_text()); data["expectations"][0]["knowledge_ids"]=["missing"]
    else:
        path=root/"knowledge/nodes.yaml"; data=yaml.safe_load(path.read_text()); data["knowledge"][0]["prerequisites"]=["fraction-addition"]
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
    with pytest.raises(CurriculumCorpusError, match=message): CurriculumRepository(root).load()


def test_problem_expectation_must_match_level(tmp_path: Path):
    folder=tmp_path/"seconde"; folder.mkdir(); (folder/"bad.yaml").write_text("""id: bad-001\ntitle: Bad\nstatement: Unique\ncurriculum: {level: seconde, difficulty: 1, expectations: [c4-2020-4e-fractions]}\ntopics: [algebra]\nsource: {type: internal, name: Test}\nreference_solution: Test\n""")
    with pytest.raises(ProblemCorpusError, match="belongs to quatrieme"):
        ProblemRepository(tmp_path, repository()).load()
