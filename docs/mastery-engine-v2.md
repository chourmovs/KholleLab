# KnowledgeNode mastery engine v2

## Canonical unit and mapping

Mastery is derived for the 72 stable `KnowledgeNode` identifiers in the curriculum graph. Only concrete nodes (`concept`, `procedure`, and similar non-domain kinds) are assessable. Domain nodes group the UI and may aggregate counts; evidence on a child never establishes its domain, parent, prerequisite, descendant, or sibling.

Every curated, parametric, or accepted generated problem uses the same `knowledge_for_problem(problem, curriculum)` resolver. It follows the problem's curriculum expectation IDs to each expectation's explicit `knowledge_ids`. An expectation that maps only to domains is a curriculum metadata issue, not permission to invent concrete mastery.

## Evidence semantics

A terminal session produces one of five explicit outcomes:

* `POSITIVE`: completed evaluation, confidence at least 0.65, verdict `correct` or `mostly_correct`;
* `PARTIAL`: completed, sufficiently confident `partial` verdict;
* `NEGATIVE`: completed, sufficiently confident `incorrect` or `non_answer` verdict;
* `UNASSESSED`: missing, failed, unknown-verdict, or low-confidence evaluation;
* `INCOMPLETE`: abandoned session.

Only the first three are assessed correctness evidence. **FAILED OR LOW-CONFIDENCE INFERENCE IS NOT LEARNER EVIDENCE.** An abandoned session alone is not proof of mathematical failure. Genuine non-fallback tutor signals can prioritize support or explanation but cannot alter correctness.

## Deterministic categorical transitions

At most the eight latest assessed observations per node are considered, drawn from at most 50 recent terminal sessions. Fewer than two assessed outcomes gives `not_enough_data`. `established` requires at least four assessed outcomes, at least three positive outcomes, at least two positives among the latest three, and no pair of latest negative outcomes. `practicing` requires at least three assessed outcomes, at least two positive-or-partial outcomes, and no pair of latest negative outcomes. Other sufficiently observed nodes are `emerging`.

KnowledgeNode mastery is categorical, not a percentage. There is no numeric score and no mutable mastery table.

## Historical mapping

New sessions capture an immutable versioned `curriculum_snapshot` containing expectation IDs, direct knowledge IDs, and difficulty. Historical mastery therefore uses the pedagogical mapping captured at session time even if the current catalogue changes. A legacy `NULL` snapshot falls back conservatively to the current unified problem catalogue and curriculum repository; history is never rewritten.

## Profile and prerequisites

The profile's canonical `knowledge` list reports node identity and hierarchy, categorical state, separate assessed/positive/partial/negative/incomplete/unassessed counts, difficulty range, highest positive difficulty, latest practice, and support signals. Deprecated `topics` and `skills` projections remain temporarily for compatibility.

Strengths and consolidation use concrete nodes. Consolidation can explain repeated negatives, partial work, course or method gaps, incomplete work, inconsistent results, and a useful immediate prerequisite gap. It does not recursively mark ancestors weak.

## Adaptive targeting

Adaptive context derives KnowledgeNode targets only from assessed weakness, genuine tutor support, and immediate prerequisite gaps. Missing/failed evaluations and fallback tutor records create no remediation target. Ranking rewards candidates that directly map to target nodes or an unmet immediate prerequisite, while preserving difficulty, same-problem avoidance, family diversity, and all upstream level/domain/expectation hard filters.
