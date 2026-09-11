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


def test_active_2026_curriculum_is_granular_sourced_and_mapped():
    repo = repository()
    metadata = repo.level_metadata("2026-2027")[:5]
    counts = {level["id"]: sum(len(domain["expectations"]) for domain in level["domains"]) for level in metadata}
    assert counts == {"quatrieme": 15, "troisieme": 15, "seconde": 15, "premiere": 15, "terminale": 15}
    active_ids = {item["id"] for level in metadata for domain in level["domains"] for item in domain["expectations"]}
    assert len(active_ids) == 75
    assert all(repo.expectations[item].source_reference for item in active_ids)
    assert all(repo.expectations[item].knowledge_ids for item in active_ids)
    assert len(repo.knowledge_nodes) >= 50


def test_current_corpus_and_families_only_reference_active_expectations():
    from corpus_factory.families import FAMILIES
    repo = repository()
    active_ids = {item["id"] for level in repo.level_metadata("2026-2027")[:5]
                  for domain in level["domains"] for item in domain["expectations"]}
    problems = ProblemRepository(ROOT / "problems", repo, academic_year="2026-2027")
    problems.load()
    school = [p for p in problems.list() if p.curriculum.level.value not in {"maths-sup", "maths-spe"}]
    assert all(set(problem.curriculum.expectations) <= active_ids for problem in school)
    assert all(family.expectation in active_ids for family in FAMILIES)
