"""Declarative family catalogue.

Each row is an independently versioned pedagogical archetype.  Mathematical
construction lives in :mod:`corpus_factory.engine`, not in the build script.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Family:
    family_id: str
    title: str
    level: str
    expectation: str
    kind: str
    topics: tuple[str, ...]
    skills: tuple[str, ...]
    difficulties: tuple[int, ...] = (2, 3)
    variant_count: int = 8
    version: int = 1


FAMILIES = (
    Family("4e-fraction-sum", "Additionner des fractions", "quatrieme", "c4-2020-4e-fractions", "fraction", ("arithmetic",), ("calculation",), (1, 2)),
    Family("4e-fraction-context", "Résoudre un problème de fractions", "quatrieme", "c4-2020-4e-fractions", "fraction_context", ("arithmetic",), ("modeling",), (2, 3)),
    Family("4e-proportionality-table", "Compléter un tableau de proportionnalité", "quatrieme", "c4-2020-4e-proportionality", "proportion", ("arithmetic",), ("calculation",), (1, 2)),
    Family("4e-proportionality-context", "Résoudre un problème de proportionnalité", "quatrieme", "c4-2020-4e-proportionality", "proportion_context", ("arithmetic",), ("modeling",), (2, 3)),
    Family("4e-expand-expression", "Développer une expression", "quatrieme", "c4-2020-4e-algebra", "expand", ("algebra",), ("calculation",), (1, 2)),
    Family("4e-algebra-justify", "Justifier une identité algébrique", "quatrieme", "c4-2020-4e-algebra", "identity", ("algebra",), ("proof",), (2, 3)),
    Family("4e-pythagoras-length", "Calculer une longueur avec Pythagore", "quatrieme", "c4-2020-4e-pythagoras", "pythagoras", ("geometry",), ("reasoning",), (2, 3)),
    Family("4e-statistics-mean", "Calculer une moyenne", "quatrieme", "c4-2020-4e-statistics", "mean", ("arithmetic",), ("calculation",), (1, 2)),
    Family("4e-statistics-missing", "Retrouver une valeur à partir de la moyenne", "quatrieme", "c4-2020-4e-statistics", "mean_reverse", ("arithmetic",), ("reasoning",), (2, 3)),
    Family("3e-equation-direct", "Résoudre une équation", "troisieme", "c4-2020-3e-equations", "equation", ("equations",), ("equation-solving",), (1, 2)),
    Family("3e-equation-context", "Mettre un problème en équation", "troisieme", "c4-2020-3e-equations", "equation_context", ("equations",), ("modeling",), (2, 3)),
    Family("3e-powers-product", "Calculer avec des puissances", "troisieme", "c4-2020-3e-powers", "powers", ("arithmetic",), ("calculation",), (1, 2)),
    Family("3e-thales-length", "Calculer une longueur avec Thalès", "troisieme", "c4-2020-3e-thales", "thales", ("geometry",), ("reasoning",), (2, 3)),
    Family("3e-trigonometry-length", "Utiliser le cosinus dans un triangle rectangle", "troisieme", "c4-2020-3e-trigonometry", "trigonometry", ("trigonometry",), ("reasoning",), (2, 3)),
    Family("3e-function-image", "Calculer l’image par une fonction", "troisieme", "c4-2020-3e-functions", "function_image", ("functions",), ("calculation",), (1, 2)),
    Family("3e-function-antecedent", "Déterminer un antécédent", "troisieme", "c4-2020-3e-functions", "function_antecedent", ("functions",), ("equation-solving",), (2, 3)),
    Family("2de-algebra-factor", "Factoriser une expression", "seconde", "lycee-2026-2de-algebra", "factor", ("algebra",), ("calculation",), (2, 3)),
    Family("2de-algebra-inequality", "Résoudre une inéquation", "seconde", "lycee-2026-2de-algebra", "inequality", ("inequalities",), ("inequality-solving",), (2, 3)),
    Family("2de-function-image", "Calculer l’image par une fonction quadratique", "seconde", "lycee-2026-2de-functions", "quadratic_image", ("functions",), ("calculation",), (1, 3)),
    Family("2de-function-variation", "Étudier le minimum d’une fonction", "seconde", "lycee-2026-2de-functions", "vertex", ("functions",), ("reasoning",), (2, 4)),
    Family("2de-vector-midpoint", "Calculer les coordonnées d’un milieu", "seconde", "lycee-2026-2de-geometry", "midpoint", ("geometry",), ("calculation",), (1, 3)),
    Family("2de-probability-complement", "Calculer la probabilité d’un événement contraire", "seconde", "lycee-2026-2de-data", "probability", ("probability",), ("reasoning",), (1, 3)),
    Family("1re-algebra-sequence", "Calculer un terme d’une suite arithmétique", "premiere", "lycee-2026-1re-algebra", "arithmetic_sequence", ("sequences",), ("reasoning",), (2, 3)),
    Family("1re-derivative-polynomial", "Dériver une fonction polynomiale", "premiere", "lycee-2026-1re-analysis", "derivative", ("derivatives",), ("calculation",), (2, 3)),
    Family("1re-derivative-extremum", "Étudier un extremum par la dérivée", "premiere", "lycee-2026-1re-analysis", "derivative_extremum", ("derivatives",), ("optimization",), (3, 4)),
    Family("1re-vector-collinearity", "Démontrer la colinéarité de vecteurs", "premiere", "lycee-2026-1re-geometry", "collinearity", ("geometry",), ("proof",), (2, 3)),
    Family("1re-probability-tree", "Calculer une probabilité conditionnelle", "premiere", "lycee-2026-1re-probability", "conditional", ("probability",), ("reasoning",), (2, 4)),
    Family("tle-sequence-limit", "Déterminer la limite d’une suite géométrique", "terminale", "lycee-2019-tle-analysis", "geometric_limit", ("limits", "sequences"), ("reasoning",), (2, 3)),
    Family("tle-integral-polynomial", "Calculer une intégrale polynomiale", "terminale", "lycee-2019-tle-integrals", "integral", ("integrals",), ("calculation",), (2, 3)),
    Family("tle-algebra-induction", "Démontrer une propriété par récurrence", "terminale", "lycee-2019-tle-algebra", "induction", ("algebra",), ("induction",), (3, 4)),
    Family("tle-binomial-probability", "Calculer une probabilité binomiale", "terminale", "lycee-2019-tle-probability", "binomial", ("probability",), ("modeling",), (2, 4)),
)
