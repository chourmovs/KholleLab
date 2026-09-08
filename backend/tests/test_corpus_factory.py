from fractions import Fraction
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from corpus_factory.engine import build_corpus, generate  # noqa: E402
from corpus_factory.families import FAMILIES  # noqa: E402
from app.domain.problem import Problem  # noqa: E402


def family(identifier):
    return next(item for item in FAMILIES if item.family_id == identifier)


def test_same_coordinate_is_reproducible_and_id_is_stable():
    first = generate(family("3e-equation-direct"), 3)
    assert first == generate(family("3e-equation-direct"), 3)
    assert first["id"] == "3e-equation-direct-g1-v003"


def test_variants_are_distinct_and_validate_through_domain_schema():
    records = [generate(family("4e-fraction-sum"), index) for index in range(1, 9)]
    assert len({item["statement"] for item in records}) == 8
    assert all(Problem.model_validate(item).generation for item in records)


def test_exact_fraction_solver_is_independently_checkable():
    item = generate(family("tle-integral-polynomial"), 2)
    # Rebuild the exact result from the committed parameter identity's source values.
    from corpus_factory.engine import stable_random
    random = stable_random(family("tle-integral-polynomial"), 2)
    a, b, c = random.randint(2, 9), random.randint(1, 12), random.randint(2, 10)
    expected = Fraction(a, 3) + Fraction(b, 2) + c
    rendered = str(expected.numerator) if expected.denominator == 1 else f"{expected.numerator}/{expected.denominator}"
    assert f"vaut ${rendered}$" in item["reference_solution"]


def test_invalid_variant_is_rejected_loudly():
    with pytest.raises(ValueError, match="declared range"):
        generate(family("4e-pythagoras-length"), 0)


def test_committed_build_matches_factory():
    assert len(build_corpus()) >= 25
    result = subprocess.run([sys.executable, "scripts/build_problem_corpus.py", "--check"],
                            cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
