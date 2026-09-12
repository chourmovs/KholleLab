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
exhausted it, the bucket grows one validated problem at a time until
`LLM_PROBLEM_POOL_TARGET`, then recycles the learner's least-recently-seen problem;
only thinner inventory may synchronously add one problem. Thus the target is a hard
behavioural boundary for learner-driven growth, not a background refill setting.

Generation uses strict `GeneratedProblemDraft` output, deterministic URL, answer-leak,
length, exact-duplicate, and conservative near-duplicate checks, followed by a separate
structured critic pass. Only a draft passing every critical critic field is persisted.
Content-addressed IDs remain derived from the trusted curriculum target, normalized
statement, and normalized reference solution. A second SHA-256 fingerprint of only the
normalized statement has a partial unique index over accepted rows, preventing exact
duplicates across all buckets. Near-duplicate comparison includes the static corpus
and a bounded cross-bucket window of accepted generated material.

PostgreSQL transaction advisory locks, keyed deterministically by bucket, prevent
duplicate generation spending across replicas. SQLite tests use an in-process
per-bucket async lock. Both paths recheck unseen inventory and the target after waiting.
Serving increments usage atomically in SQL and records all timestamps in the same
statement.

Generator prompts receive bounded title, statement, and archetype diversity examples.
They never receive learner history, work, profile, identity, or reference solutions.
Provider/model and critic diagnostics are private database metadata; public problem
serialization is allow-listed and excludes the reference solution and validation data.
