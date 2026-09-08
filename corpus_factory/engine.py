"""Pure generation and exact solvers for the family catalogue."""
from fractions import Fraction
import hashlib
import json
import random

from .families import FAMILIES, Family


def stable_random(family: Family, variant: int, attempt: int = 0) -> random.Random:
    material = f"{family.family_id}:{family.version}:{variant}:{attempt}".encode()
    return random.Random(int.from_bytes(hashlib.sha256(material).digest()))


def _fmt(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _content(kind: str, r: random.Random, variant: int) -> tuple[str, str, dict]:
    a, b, x = r.randint(2, 9), r.randint(1, 12), r.randint(2, 10)
    if kind in {"equation", "equation_context"}:
        c = a * x + b
        prefix = "Un nombre multiplié" if kind.endswith("context") else "Résoudre"
        return f"{prefix} : ${a}x+{b}={c}$. Justifier puis vérifier la réponse.", f"${a}x={c-b}$, donc $x={x}$. Vérification : ${a}\\times{x}+{b}={c}$.", {"a": a, "b": b, "c": c}
    if kind in {"fraction", "fraction_context"}:
        p, q = r.randint(1, 7), r.randint(2, 9)
        value = Fraction(p, q) + Fraction(a, q)
        wording = "Une recette utilise successivement" if kind.endswith("context") else "Calculer exactement"
        return f"{wording} ${p}/{q}$ puis ${a}/{q}$ d'une unité. Donner la somme irréductible.", f"La somme vaut $({p}+{a})/{q}={_fmt(value)}$ après simplification.", {"p": p, "q": q, "a": a}
    if kind in {"proportion", "proportion_context", "thales"}:
        k, n = r.randint(2, 7), r.randint(2, 9); result = k*n
        context = "Sur un plan à l'échelle, " if kind == "thales" else ("Pour une recette, " if kind.endswith("context") else "Dans un tableau proportionnel, ")
        return f"{context}{n} unités correspondent à {result} unités. À combien correspondent {n+1} unités ? Expliquer.", f"Le coefficient est ${k}$. Donc $({n}+1)\\times{k}={k*(n+1)}$ unités.", {"k": k, "n": n}
    if kind in {"expand", "identity", "factor"}:
        if kind == "factor":
            return f"Factoriser ${a}x^2+{a*b}x$ et contrôler en développant.", f"On met ${a}x$ en facteur : ${a}x(x+{b})$.", {"a": a, "b": b}
        return f"Développer et réduire ${a}(x+{b})-{b}x$. Détailler la distributivité.", f"${a}x+{a*b}-{b}x=({a-b})x+{a*b}$.", {"a": a, "b": b}
    if kind == "pythagoras":
        triples = [(3,4,5),(5,12,13),(8,15,17),(7,24,25)]; u,v,w = triples[variant % len(triples)]
        return f"Le triangle ABC est rectangle en A, avec $AB={u}$ cm et $AC={v}$ cm. Calculer BC et justifier.", f"Pythagore donne $BC^2={u}^2+{v}^2={w*w}$, donc $BC={w}$ cm.", {"u": u, "v": v, "w": w, "case": variant//len(triples)}
    if kind in {"mean", "mean_reverse"}:
        values = [a, b, x]; total=sum(values); mean=Fraction(total,3)
        if kind == "mean": return f"Calculer la moyenne exacte de la série ${a}; {b}; {x}$ et l'interpréter.", f"La somme est ${total}$, donc la moyenne est ${_fmt(mean)}$.", {"values": values}
        target=r.randint(5,12); missing=3*target-a-b
        return f"La moyenne de ${a}; {b}; y$ doit être ${target}$. Déterminer $y$ et vérifier.", f"${a}+{b}+y={3*target}$, donc $y={missing}$.", {"a":a,"b":b,"target":target}
    if kind == "powers":
        m,n=r.randint(2,6),r.randint(2,5)
        return f"Écrire $({a}^{m}\\times {a}^{n})/{a}^{2}$ sous la forme d'une puissance unique.", f"On additionne puis soustrait les exposants : ${a}^{{{m+n-2}}}$.", {"base":a,"m":m,"n":n}
    if kind == "trigonometry":
        triples=[(3,4,5),(5,12,13),(8,15,17),(7,24,25)]; u,v,w=triples[variant%4]
        return f"Dans un triangle rectangle, le côté adjacent à l'angle $\\alpha$ mesure {u} cm et l'hypoténuse {w} cm. Donner $\\cos(\\alpha)$ exactement.", f"Par définition, $\\cos(\\alpha)={u}/{w}$.", {"adjacent":u,"hypotenuse":w,"case":variant//4}
    if kind in {"function_image", "quadratic_image"}:
        if kind == "function_image": value=a*x+b; expr=f"{a}x+{b}"
        else: value=x*x+a*x+b; expr=f"x^2+{a}x+{b}"
        return f"On définit $f(x)={expr}$. Calculer $f({x})$ en montrant la substitution.", f"$f({x})={value}$.", {"a":a,"b":b,"x":x}
    if kind == "function_antecedent":
        y=a*x+b; return f"Pour $f(x)={a}x+{b}$, déterminer l'antécédent de ${y}$ et vérifier.", f"${a}x+{b}={y}$ donne $x={x}$.", {"a":a,"b":b,"y":y}
    if kind == "inequality":
        c=a*x+b; return f"Résoudre ${a}x+{b}\\leq {c}$ et représenter les solutions.", f"Comme ${a}>0$, $x\\leq {x}$, soit $]-\\infty;{x}]$.", {"a":a,"b":b,"c":c}
    if kind == "vertex":
        return f"Étudier le minimum de $f(x)=(x-{x})^2+{b}$ et préciser où il est atteint.", f"Un carré est positif : le minimum vaut ${b}$, atteint pour $x={x}$.", {"x":x,"b":b}
    if kind in {"midpoint", "collinearity"}:
        if kind == "midpoint":
            return f"Dans un repère, $A({a};{b})$ et $B({a+2*x};{b+2})$. Calculer les coordonnées du milieu I.", f"$I(({a}+{a+2*x})/2;({b}+{b+2})/2)=({a+x};{b+1})$.", {"a":a,"b":b,"x":x}
        return f"Montrer que les vecteurs $u=({a};{b})$ et $v=({a*x};{b*x})$ sont colinéaires et donner le coefficient.", f"$v={x}u$ ; les vecteurs sont donc colinéaires.", {"a":a,"b":b,"x":x}
    if kind == "probability":
        p=Fraction(r.randint(1,8),10); return f"Un événement A a pour probabilité ${_fmt(p)}$. Calculer exactement $P(\\overline{{A}})$.", f"$P(\\overline{{A}})=1-P(A)={_fmt(1-p)}$.", {"p":_fmt(p)}
    if kind == "arithmetic_sequence":
        n=r.randint(5,12); value=a+(n-1)*b
        return f"La suite arithmétique vérifie $u_1={a}$ et a pour raison ${b}$. Calculer $u_{n}$ et justifier.", f"$u_{n}=u_1+({n}-1)r={value}$.", {"a":a,"b":b,"n":n}
    if kind in {"derivative", "derivative_extremum"}:
        if kind == "derivative": return f"Déterminer la dérivée de $f(x)={a}x^3+{b}x^2-{x}x+1$.", f"$f'(x)={3*a}x^2+{2*b}x-{x}$.", {"a":a,"b":b,"c":x}
        return f"Étudier les variations de $f(x)=(x-{x})^2+{b}$ à l'aide de sa dérivée.", f"$f'(x)=2(x-{x})$ : f décroît jusqu'à ${x}$ puis croît ; son minimum est ${b}$.", {"x":x,"b":b}
    if kind == "conditional":
        p=Fraction(r.randint(2,8),10); q=Fraction(r.randint(2,8),10)
        return f"On sait $P(A)={_fmt(p)}$ et $P(B\\mid A)={_fmt(q)}$. Calculer $P(A\\cap B)$ avec un arbre.", f"$P(A\\cap B)=P(A)P(B\\mid A)={_fmt(p*q)}$.", {"p":_fmt(p),"q":_fmt(q)}
    if kind == "geometric_limit":
        q=Fraction(r.randint(1,8),10); return f"La suite vérifie $u_n={a}\\times({_fmt(q)})^n$. Déterminer sa limite et justifier.", f"Comme $|{_fmt(q)}|<1$, $({_fmt(q)})^n\\to0$, donc $u_n\\to0$.", {"a":a,"q":_fmt(q)}
    if kind == "integral":
        value=Fraction(a,3)+Fraction(b,2)+x
        return f"Calculer exactement $\\int_0^1 ({a}x^2+{b}x+{x})\\,dx$.", f"Une primitive est $({a}/3)x^3+({b}/2)x^2+{x}x$ ; l'intégrale vaut ${_fmt(value)}$.", {"a":a,"b":b,"c":x}
    if kind == "induction":
        return f"Démontrer par récurrence que, pour tout $n\\geq0$, $\\sum_{{k=0}}^n {a}k={a}n(n+1)/2$.", f"Initialisation immédiate. Si la formule est vraie au rang n, ajouter ${a}(n+1)$ donne ${a}(n+1)(n+2)/2$.", {"a":a,"variant":variant}
    if kind == "binomial":
        n=r.randint(3,7); p=Fraction(r.randint(1,4),5)
        return f"$X$ suit une loi binomiale $\\mathcal B({n},{_fmt(p)})$. Calculer exactement $P(X=0)$.", f"$P(X=0)=(1-{_fmt(p)})^{n}=({_fmt(1-p)})^{n}$.", {"n":n,"p":_fmt(p)}
    raise ValueError(f"unknown family kind: {kind}")


def generate(family: Family, variant: int) -> dict:
    if not 1 <= variant <= family.variant_count:
        raise ValueError("variant outside declared range")
    statement, solution, parameters = _content(family.kind, stable_random(family, variant), variant)
    statement = f"Variante {variant} — {statement}"
    if not statement or not solution or any(value is None for value in parameters.values()):
        raise ValueError(f"degenerate parameters for {family.family_id} variant {variant}")
    parameters["wording_slot"] = variant
    identity = hashlib.sha256(json.dumps(parameters, sort_keys=True).encode()).hexdigest()
    difficulty = family.difficulties[(variant - 1) % len(family.difficulties)]
    return {"id": f"{family.family_id}-g{family.version}-v{variant:03d}", "title": family.family_id.replace("-", " ").title(),
            "statement": statement, "curriculum": {"level": family.level, "difficulty": difficulty, "expectations": [family.expectation]},
            "topics": list(family.topics), "skills": list(family.skills), "estimated_minutes": 8 + 3*difficulty,
            "source": {"type": "internal", "name": "Khollelab deterministic corpus factory"}, "reference_solution": solution,
            "hints": [{"level": 1, "text": "Identifier les données utiles et écrire la propriété mobilisée."}],
            "tags": ["parametric", "reasoning" if "reasoning" in family.skills or "proof" in family.skills else "fluency"],
            "generation": {"kind": "parametric", "family_id": family.family_id, "version": family.version,
                           "variant": variant, "parameter_identity": identity}}


def build_corpus() -> dict[str, list[dict]]:
    output: dict[str, list[dict]] = {}
    for family in FAMILIES:
        records = [generate(family, index) for index in range(1, family.variant_count + 1)]
        identities = {record["generation"]["parameter_identity"] for record in records}
        if len(identities) != len(records):
            raise ValueError(f"duplicate parameters in {family.family_id}")
        output[f"{family.level}/generated/{family.family_id}.yaml"] = records
    return output
