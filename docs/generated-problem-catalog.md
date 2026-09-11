# Global generated-problem catalogue

`ProblemCatalog` is the single resolver used by the API, tutor, examiner, history,
resources, profile, and evaluation worker. It first resolves immutable YAML material
(curated and parametric), then `llm-*` identifiers from PostgreSQL. Retired database
rows remain directly resolvable but are excluded from selection.

The generated inventory is global and bucketed by programme, level, granular
expectation, and difficulty. No learner or session identifier is stored on a generated
problem. The anonymous learner cookie is used only to query normal session history and
prefer a globally accepted problem that learner has not seen. Accepted inventory is
ordered deterministically by usage count, creation time, and ID.

The request path reuses unseen inventory without any inference. When the learner has
exhausted it, a bucket at or above `LLM_PROBLEM_POOL_MIN_AVAILABLE` is still reused;
only thinner inventory may synchronously add one problem. `LLM_PROBLEM_POOL_TARGET`
describes the desired future stock rather than forcing an expensive refill.

Generation uses strict `GeneratedProblemDraft` output, deterministic URL, answer-leak,
length, exact-duplicate, and conservative near-duplicate checks, followed by a separate
structured critic pass. Only a draft passing every critical critic field is persisted.
IDs and the unique database hash are derived from the trusted curriculum target,
normalized statement, and normalized reference solution. An insertion race resolves
to the canonical existing row.

An in-process per-bucket async lock prevents duplicate generation storms and rechecks
the catalogue after waiting. The database uniqueness constraint protects identical
content across replicas. A distributed per-bucket lock is intentionally deferred: two
replicas can generate different valid problems for the same thin bucket, enriching it
by two rows rather than failing or duplicating content.

Generator prompts receive bounded title, statement, and archetype diversity examples.
They never receive learner history, work, profile, identity, or reference solutions.
Provider/model and critic diagnostics are private database metadata; public problem
serialization is allow-listed and excludes the reference solution and validation data.
