# Guided exercise engine

`GET /api/problems/next` is the canonical read-only guided-selection path. It takes
no curriculum or difficulty filters. It requires completed onboarding and resumes
the deterministically latest active session before considering any new exercise;
it never creates a session, attempt, evaluation, or progression event.

Without active work, `LearnerCurriculumState.current_level` is authoritative. An
unlocked higher level does not promote or redirect the learner. The eligible set is
the validated static `ProblemCatalog.list_static()` corpus at exactly that level;
generated material is neither selected nor included in curriculum progress. The
engine ranks unsolved eligible IDs first, using the canonical positive-evidence
definition from curriculum progression. Once all are solved, every eligible item
becomes a deterministic review pool. Empty pools are explicit errors.

Adaptive ranking remains shared with legacy adaptive selection. It targets weak
knowledge and prerequisites, follows recommended sequences, rewards diversity,
penalizes recent problems/families, and breaks ties by stable problem ID.

## Difficulty v1

Only bounded, persisted, assessed history from the current level is considered.
The base is the latest assessed problem's difficulty, or 2 without history. Two
latest positive outcomes add one; two latest negative outcomes subtract one; mixed
or partial outcomes stabilize it. Unassessed and incomplete outcomes are ignored,
and the result is clamped to 1–5. Ranking may select a nearby difficulty when an
exact match does not exist.

PR13 chooses the next exercise. PR13 does not automatically promote the learner to
another school level. Mastery evidence influences adaptive ranking, while separate
curriculum progression controls solved counts and unlocks.
