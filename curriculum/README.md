# Catalogue curriculaire versionné

Ce répertoire est la source de vérité lisible et versionnée du moteur curriculaire. Chaque fichier porte `schema_version: 1`; le chargeur déterministe refuse les identifiants dupliqués, les références pendantes, les cycles du graphe de connaissances, les années mal formées et les périodes d'application qui se chevauchent.

## Modèle

- `levels.yaml` définit l'ordre, les libellés français, les étapes et les intensités présentés par l'API.
- `programmes/programmes.yaml` décrit une publication et ses périodes d'application **par niveau**. Une même publication peut donc être déployée à des rentrées différentes. Une année scolaire s'écrit `YYYY-YYYY` avec deux années consécutives.
- `knowledge/nodes.yaml` contient les `KnowledgeNode`, notions mathématiques stables et indépendantes des révisions officielles. `parent` structure la taxonomie et `prerequisites` forme un graphe acyclique.
- `expectations/expectations.yaml` contient les `CurriculumExpectation`, objectifs concis propres à un programme et un niveau, reliés à un ou plusieurs nœuds stables.

`CURRICULUM_ACADEMIC_YEAR` peut figer l'année active. Sans cette variable, septembre ouvre la nouvelle année scolaire française. Pour ajouter un programme, créer une entrée et fermer explicitement la période précédente pour chaque niveau concerné. Pour ajouter un objectif, choisir un ID versionné, référencer un programme applicable au niveau et uniquement des connaissances existantes. Ne jamais inclure l'année ou la version du programme dans un ID de connaissance.

Les lacunes de couverture sont informatives (`python scripts/report_curriculum_coverage.py`); les incohérences structurelles bloquent le démarrage.

## Granularité et stabilité

Pour l'année active 2026-2027, une expectation désigne un objectif enseignable et évaluable cohérent. `order` conserve l'ordre pédagogique officiel dans l'API, `theme` est un identifiant éditorial interne et `theme_label` son libellé apprenant. Les anciens objectifs agrégés nécessaires à la résolution historique portent `historical: true` et ne sont pas proposés par l'API active.

Les `KnowledgeNode` sont indépendants des classes et des millésimes. Leurs liens `parent` et `prerequisites` forment un graphe acyclique de compétences mathématiques réutilisable; ils ne codent pas artificiellement l'ordre des années scolaires.
