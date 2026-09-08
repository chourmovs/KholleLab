"""Declarative family catalogue.

Each row is an independently versioned pedagogical archetype.  Mathematical
construction lives in :mod:`corpus_factory.engine`, not in the build script.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Family:
    family_id: str
    level: str
    expectation: str
    kind: str
    topics: tuple[str, ...]
    skills: tuple[str, ...]
    difficulties: tuple[int, ...] = (2, 3)
    variant_count: int = 8
    version: int = 1


FAMILIES = (
    Family("4e-fraction-sum", "quatrieme", "c4-2020-4e-fractions", "fraction", ("arithmetic",), ("calculation",), (1, 2)),
    Family("4e-fraction-context", "quatrieme", "c4-2020-4e-fractions", "fraction_context", ("arithmetic",), ("modeling",), (2, 3)),
    Family("4e-proportionality-table", "quatrieme", "c4-2020-4e-proportionality", "proportion", ("arithmetic",), ("calculation",), (1, 2)),
    Family("4e-proportionality-context", "quatrieme", "c4-2020-4e-proportionality", "proportion_context", ("arithmetic",), ("modeling",), (2, 3)),
    Family("4e-expand-expression", "quatrieme", "c4-2020-4e-algebra", "expand", ("algebra",), ("calculation",), (1, 2)),
    Family("4e-algebra-justify", "quatrieme", "c4-2020-4e-algebra", "identity", ("algebra",), ("proof",), (2, 3)),
    Family("4e-pythagoras-length", "quatrieme", "c4-2020-4e-pythagoras", "pythagoras", ("geometry",), ("reasoning",), (2, 3)),
    Family("4e-statistics-mean", "quatrieme", "c4-2020-4e-statistics", "mean", ("arithmetic",), ("calculation",), (1, 2)),
    Family("4e-statistics-missing", "quatrieme", "c4-2020-4e-statistics", "mean_reverse", ("arithmetic",), ("reasoning",), (2, 3)),
    Family("3e-equation-direct", "troisieme", "c4-2020-3e-equations", "equation", ("equations",), ("equation-solving",), (1, 2)),
    Family("3e-equation-context", "troisieme", "c4-2020-3e-equations", "equation_context", ("equations",), ("modeling",), (2, 3)),
    Family("3e-powers-product", "troisieme", "c4-2020-3e-powers", "powers", ("arithmetic",), ("calculation",), (1, 2)),
    Family("3e-thales-length", "troisieme", "c4-2020-3e-thales", "thales", ("geometry",), ("reasoning",), (2, 3)),
    Family("3e-trigonometry-length", "troisieme", "c4-2020-3e-trigonometry", "trigonometry", ("trigonometry",), ("reasoning",), (2, 3)),
    Family("3e-function-image", "troisieme", "c4-2020-3e-functions", "function_image", ("functions",), ("calculation",), (1, 2)),
    Family("3e-function-antecedent", "troisieme", "c4-2020-3e-functions", "function_antecedent", ("functions",), ("equation-solving",), (2, 3)),
    Family("2de-algebra-factor", "seconde", "lycee-2019-2de-algebra", "factor", ("algebra",), ("calculation",), (2, 3)),
    Family("2de-algebra-inequality", "seconde", "lycee-2019-2de-algebra", "inequality", ("inequalities",), ("inequality-solving",), (2, 3)),
    Family("2de-function-image", "seconde", "lycee-2019-2de-functions", "quadratic_image", ("functions",), ("calculation",), (1, 3)),
    Family("2de-function-variation", "seconde", "lycee-2019-2de-functions", "vertex", ("functions",), ("reasoning",), (2, 4)),
    Family("2de-vector-midpoint", "seconde", "lycee-2019-2de-geometry", "midpoint", ("geometry",), ("calculation",), (1, 3)),
    Family("2de-probability-complement", "seconde", "lycee-2019-2de-data", "probability", ("probability",), ("reasoning",), (1, 3)),
    Family("1re-algebra-sequence", "premiere", "lycee-2019-1re-algebra", "arithmetic_sequence", ("sequences",), ("reasoning",), (2, 3)),
    Family("1re-derivative-polynomial", "premiere", "lycee-2019-1re-analysis", "derivative", ("derivatives",), ("calculation",), (2, 3)),
    Family("1re-derivative-extremum", "premiere", "lycee-2019-1re-analysis", "derivative_extremum", ("derivatives",), ("optimization",), (3, 4)),
    Family("1re-vector-collinearity", "premiere", "lycee-2019-1re-geometry", "collinearity", ("geometry",), ("proof",), (2, 3)),
    Family("1re-probability-tree", "premiere", "lycee-2019-1re-probability", "conditional", ("probability",), ("reasoning",), (2, 4)),
    Family("tle-sequence-limit", "terminale", "lycee-2019-tle-analysis", "geometric_limit", ("limits", "sequences"), ("reasoning",), (2, 3)),
    Family("tle-integral-polynomial", "terminale", "lycee-2019-tle-integrals", "integral", ("integrals",), ("calculation",), (2, 3)),
    Family("tle-algebra-induction", "terminale", "lycee-2019-tle-algebra", "induction", ("algebra",), ("induction",), (3, 4)),
    Family("tle-binomial-probability", "terminale", "lycee-2019-tle-probability", "binomial", ("probability",), ("modeling",), (2, 4)),
)
