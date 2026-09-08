#!/usr/bin/env python3
"""Strict exact-duplicate audit plus conservative near-duplicate warnings."""
from collections import defaultdict
from pathlib import Path
import re
import sys
import unicodedata
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.domain.problem import Problem  # noqa: E402

seen = {"id": {}, "statement": {}, "family_variant": {}, "parameter": {}}
errors: list[str] = []
families: defaultdict[str, list[str]] = defaultdict(list)
for path in sorted((ROOT / "problems").glob("**/*.yaml")):
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    records = raw.get("problems") if isinstance(raw, dict) and "problems" in raw else [raw]
    for value in records:
        problem = Problem.model_validate(value)
        statement = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", problem.statement).casefold()).strip()
        keys = {"id": problem.id, "statement": statement}
        if problem.generation:
            keys["family_variant"] = (problem.generation.family_id, problem.generation.version, problem.generation.variant)
            keys["parameter"] = (problem.generation.family_id, problem.generation.version, problem.generation.parameter_identity)
            families[problem.generation.family_id].append(statement)
        for category, key in keys.items():
            if key in seen[category]: errors.append(f"duplicate {category}: {key} ({seen[category][key]}, {path})")
            seen[category][key] = path
if errors:
    print("\n".join(errors), file=sys.stderr); raise SystemExit(1)
# Near-duplicate detection intentionally warns only when normalized word skeletons
# (numbers removed) collapse completely within a family; parameterized drills are valid.
warnings = 0
for family, statements in families.items():
    skeletons = defaultdict(int)
    for statement in statements: skeletons[re.sub(r"\d+(?:/\d+)?", "#", statement)] += 1
    if max(skeletons.values(), default=0) == len(statements):
        warnings += 1; print(f"WARNING near-duplicate wording concentration: {family}")
print(f"Duplicate audit passed: {len(seen['id'])} problems, {len(families)} parametric families; warnings={warnings}.")
