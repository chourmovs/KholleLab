# Corpus de problèmes

Les fichiers YAML sont la source de vérité versionnée de Khollelab. Ils sont validés au démarrage de l'API et par `python scripts/validate_problems.py`. Les identifiants publiés sont immuables; utilisez les taxonomies définies dans `backend/app/domain/problem.py`.

Chaque problème scolaire place dans `curriculum.expectations` au moins un identifiant défini dans `curriculum/expectations/`. Le chargeur refuse un objectif inconnu, dupliqué ou appartenant à un autre niveau. Les tags grossiers `topics` et `skills` restent obligatoires/compatibles avec la sélection adaptative et le profil existants. Les problèmes CPGE peuvent laisser `expectations` vide tant qu'un référentiel officiel fin n'est pas normalisé.

Pour ajouter un problème : choisir le répertoire du niveau, conserver exactement ce niveau dans `curriculum.level`, régler la difficulté de 1 à 5, référencer un objectif actif et fournir énoncé, solution de référence et source. Exécuter ensuite `python scripts/validate_problems.py` et `python scripts/report_curriculum_coverage.py`. L'ajout d'un nouvel objectif se fait d'abord dans le catalogue curriculaire, jamais directement dans le code ou le frontend.

Le corpus de démonstration est synthétique et distribué sous la licence du dépôt.
