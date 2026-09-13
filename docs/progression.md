# Learner progression (XP v1)

Progression is a motivational record of regular practice. It is deliberately separate from the
pedagogical mastery profile: **XP measures practice, not mathematical mastery**. XP, grade, and
streaks never change KnowledgeNode evidence, adaptive targets, curriculum filters, problem
difficulty, or access to content. Established mastery does not award XP.

## Immutable event ledger

`progression_events` records one immutable `session_completed` event per eligible learning
session. The unique `(session_id, event_type)` constraint is the final idempotency and concurrency
guard. Events store no user, account, learner, or email identifier. Ownership is always resolved
through `ProgressionEvent -> LearningSession -> learner_id`.

This indirection is essential to account claims. Claiming anonymous history updates only
`LearningSession.learner_id`; its event remains attached to the same session and therefore becomes
visible to the account automatically. Claim code must neither copy nor rewrite progression events.

Migration `20260913_13` backfills one event for every historical completed session with at least
one submitted attempt whose trimmed solution is non-empty. `occurred_at` uses `completed_at`, or
`updated_at` as a fallback, and `activity_date` uses the timezone policy below. Re-running normal
award checks cannot duplicate a migrated event.

## XP policy `xp-v1`

- An eligible completed session earns exactly **10 XP**, once.
- Eligibility requires `LearningSession.status == completed` and at least one submitted attempt
  with a non-empty solution.
- Opening, autosaving, abandoning, empty completion, evaluation retries, and tutor interactions do
  not award XP.
- Correctness, difficulty, problem source (static, parametric, or generated), hints, authentication,
  and LLM evaluation results do not change XP.
- A genuine submitted attempt earns the same practice XP if its evaluation is incorrect or fails.

The server alone computes awards and summaries. The frontend never submits XP, grade, or streak.

## Grade

Grade is derived at read time from lifetime XP and is not persisted. The threshold for grade `g`
is `25 * g * (g - 1)`: Grade 1 starts at 0 XP, Grade 2 at 50, Grade 3 at 150, Grade 4 at 300, and
Grade 5 at 500. Grade is motivational only; it does not unlock or gate curriculum content.

## Streaks and timezone

XP v1 uses the IANA timezone **Europe/Paris**. Each event records the Paris calendar
`activity_date` corresponding to its occurrence. Streaks use distinct activity dates, so multiple
sessions increase XP but count as a single active day.

- Current streak: consecutive active dates ending today, or ending yesterday while today remains
  available.
- If the latest activity is older than yesterday, current streak is zero.
- Longest streak is the largest historical run of consecutive distinct dates.
- `active_today` and `last_active_date` expose the remaining calendar context.
- There is no streak freeze in XP v1.

The progression summary endpoint is `GET /api/progression`. It is scoped by the same resolved
learner identity as sessions, so anonymous browsers, claimed accounts, and all authenticated
devices see the appropriate shared history while unrelated anonymous identities cannot see it.
