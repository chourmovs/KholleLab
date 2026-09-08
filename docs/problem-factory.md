# Deterministic problem factory

PR15 adds a build-time corpus factory. It does **not** generate exercises at
runtime and it does not call an LLM. Runtime continues to read ordinary YAML.

## Family contract and stable coordinates

A `Family` in `corpus_factory/families.py` declares a stable `family_id`, a
positive generator `version`, level, explicit curriculum expectation, topics,
skills, difficulty bands, and variant count. The engine owns parameter,
statement, exact-solution, and validity logic. Families use existing curriculum
expectation mappings rather than introducing a parallel knowledge taxonomy.

The coordinate `(family_id, version, variant)` is pure. A local `Random` is
seeded from its SHA-256 digest; Python `hash()`, global random state, clocks, and
dates are forbidden. IDs are `<family>-g<version>-v<variant>`. A material change
to parameters, meaning, or solver semantics requires a version bump and new IDs.

## Exactness and validation

Solvers derive their reference solution from the parameters used by the
statement. Rational results use `fractions.Fraction`; integers and symbolic
forms remain exact. Families reject zero denominators, non-unique equations,
invalid geometry, out-of-range probabilities, collapsed expressions, and other
degenerate inputs. Any retry must be deterministic, bounded, and fail loudly.

Every record passes through the frozen Pydantic `Problem` model. Curriculum
validation rejects unknown expectations and level/programme mismatches.
Provenance records family, version, variant, and SHA-256 parameter identity.
Public serializers remain allow-listed, excluding provenance and solutions.

## Materialization workflow

```bash
python scripts/build_problem_corpus.py --write
python scripts/build_problem_corpus.py --check
python scripts/validate_problems.py
python scripts/audit_problem_duplicates.py
```

`--write` creates one deterministic bundle per family under
`problems/<level>/generated/`. Bundles avoid hundreds of tiny files while every
enclosed problem is independently validated. YAML is committed for reviewable
statements/solutions, stable history, useful diffs, and drift detection.
`--check` regenerates in a temporary directory and byte-compares the exact file
set. The duplicate audit rejects duplicate IDs, normalized statements,
family/version/variant coordinates, and parameter identities; conservative
wording concentration is warning-only.

## Adding a family

1. Select an already verified active expectation.
2. Add a focused declaration with honest difficulty bands.
3. Add/reuse an exact constructor; include contextual, inverse, multi-step,
   interpretation, or proof variation where appropriate.
4. Derive the answer from the parameters and validate degeneracies.
5. Add independent solution and rejection tests.
6. Run `--write`, review YAML, then run all checks above.

Reports measure **modelled curriculum coverage**, not completeness of the whole
official French programme.
