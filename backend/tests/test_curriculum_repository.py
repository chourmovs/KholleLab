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


def test_programme_transition_boundaries():
    repo = repository()
    transitions = (
        ("quatrieme", "2026-2027", "cycle4-mathematiques-2020"),
        ("quatrieme", "2027-2028", "cycle4-mathematiques-2026"),
        ("troisieme", "2027-2028", "cycle4-mathematiques-2020"),
        ("troisieme", "2028-2029", "cycle4-mathematiques-2026"),
        ("seconde", "2025-2026", "lycee-seconde-mathematiques-2019"),
        ("seconde", "2026-2027", "lycee-seconde-mathematiques-2026"),
        ("premiere", "2025-2026", "lycee-premiere-specialite-mathematiques-2019"),
        ("premiere", "2026-2027", "lycee-premiere-specialite-mathematiques-2026"),
        ("terminale", "2026-2027", "lycee-terminale-specialite-mathematiques-2019"),
        ("terminale", "2027-2028", "lycee-terminale-specialite-mathematiques-2026"),
    )
    for level, year, expected in transitions:
        assert repo.resolve_programme(level, year).id == expected


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
