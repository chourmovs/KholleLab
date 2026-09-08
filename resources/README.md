# Catalogue de ressources pédagogiques

Ce corpus versionné contient des rappels, exemples guidés et vidéos sélectionnées. Les fichiers YAML sont validés au démarrage. `course`, `example` et `video` sont les seuls types canoniques ; le catalogue vidéo peut rester vide tant qu’aucun lien réel n’a été vérifié.

## Modèle d’association

Une ressource s’attache en priorité à une connaissance mathématique du référentiel `curriculum/`, jamais à chaque variante générée :

- `knowledge_ids` référence un ou plusieurs `KnowledgeNode` réutilisables ; c’est le choix habituel pour un point de cours ;
- `curriculum_expectations` référence un objectif officiel précis lorsque la méthode dépend réellement du niveau ;
- `curriculum_levels` reste obligatoire et constitue une barrière d’éligibilité : un nœud commun ne permet jamais de recommander une ressource à un niveau non déclaré ;
- `topics`, `skills`, `prerequisites` et `tags` restent compatibles avec les ressources historiques. Les prérequis conservent notamment leur rôle pour recommander un rappel en amont.

Les références fines sont contrôlées contre le `CurriculumRepository`. Un identifiant inconnu, une référence répétée, ou une expectation dont le niveau n’est pas autorisé par la ressource fait échouer le démarrage et `scripts/validate_resources.py`. Les ressources anciennes sans référence fine continuent à être chargées et résolues par leurs métadonnées historiques.

## Résolution

Le problème fournit ses `curriculum.expectations`; le backend en déduit les `knowledge_ids` depuis le référentiel autoritatif. Aucun duplicata de ces nœuds n’est nécessaire dans les YAML de problèmes, y compris pour les variantes générées.

Après filtrage strict sur `curriculum_levels`, l’ordre de spécificité est : `resource_refs` explicite, expectation exacte, connaissance partagée, prérequis, thème, compétence, tag. Le niveau seul ne constitue jamais une correspondance sémantique. Une `resource_ref` reste utile pour un cas éditorial exceptionnel et doit viser l’identifiant exact d’une ressource compatible avec le niveau du problème.

## Exemple d’auteur

```yaml
id: equation-isolation-basics
type: course
title: Isoler l’inconnue dans une équation
summary: Transformer une équation sans changer ses solutions.
content: On effectue la même opération sur les deux membres…
curriculum_levels: [troisieme, seconde]
knowledge_ids: [first-degree-equation]
curriculum_expectations: []
topics: [equations]
prerequisites: [course-basics]
skills: [equation-solving]
tags: [rappel]
priority: 0
```

Le contenu d’un point de cours doit rester ciblé, correct et directement exploitable pendant un exercice. Il ne doit contenir ni corrigé propre à un problème ni contenu généré dynamiquement.
