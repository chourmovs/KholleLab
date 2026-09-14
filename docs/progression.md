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

## Daily practice goal and milestones

The read model also derives a **20 XP daily practice goal** from events whose `activity_date` is the
current Europe/Paris date. Missing the goal has no penalty and does not alter streaks. Six compact,
deterministic milestones cover only completed-session counts, lifetime XP, and the historical
longest streak. They are computed from the existing ledger on every summary read and are never
persisted as achievements.

`today_xp` is computed in the same aggregate query as lifetime XP and completed sessions. Streaks
reuse one ordered query of distinct activity dates, so their processing cost scales with active
days rather than attempts, evaluations, or blackboard edits. No per-event or per-day query is used.
# Three separate progression concepts

KholleLab deliberately keeps three measurements independent:

* **Engagement progression** is XP, streaks, practice frequency, daily goals, and
  milestones. The historical public field `grade` is an engagement XP rank, not a
  school grade. It remains temporarily for frontend compatibility and should be
  renamed/removed with its consumers in PR17.
* **Pedagogical mastery** aggregates the shared evidence classifier by knowledge,
  topic, and skill. It may evolve after later work.
* **Curriculum progression** stores the learner's initial/current/highest unlocked
  school levels and counts unique successfully solved stable-corpus exercises.

For a level, `progress = solved_unique_problem_ids / eligible_static_problem_ids`
(and is zero for an empty corpus). Runtime LLM materializations do not enter the
denominator, so generated variants cannot dilute progress indefinitely. A problem
is successfully solved when a **completed learning session** has a **completed
evaluation**, confidence at least the mastery threshold (`0.65`), and verdict
`correct` or `mostly_correct`. The mastery engine and curriculum progression use
the same classifier.

At `progress >= 0.60`, the next entry in `CURRICULUM_ORDER` is permanently unlocked.
The stored high-water mark never decreases if the corpus later grows. Unlocking
does not change the current level; only an explicit learner operation does. The
highest curriculum level has no successor.

The transition lifecycle is deliberately explicit:

```text
practice the current curriculum -> reach 60% -> unlock the next curriculum permanently
-> remain on the current level -> choose "advance" between exercises
-> current_level changes -> the guided engine serves the new curriculum
```

`initial_level`, `current_level`, and `highest_unlocked_level` are independent concepts.
Choosing an initial level sets all three to that level; earlier levels are logically accessible,
so a Terminale learner is not required to unlock lower curricula first. The high-water mark is
an upward progression gate, while `PUT /api/curriculum-progress/current-level` permits review of
any earlier, already-accessible level. Unlock is not promotion: promotion occurs only through
`POST /api/curriculum-progress/advance`, and both operations reject changes while an active
learning session exists so drafts remain untouched.

The progress response exposes the current-level metrics, successor, unlock/advance flags, and
the exact additional successes required. That value is
`max(0, ceil(eligible * NEXT_LEVEL_UNLOCK_RATIO) - solved)` for a non-empty current corpus; it is
zero for an empty corpus, which can never unlock a successor. Refresh takes a row lock, advances
only sequentially through `CURRICULUM_ORDER`, and returns the previous/new high-water marks plus
the newly unlocked levels. It is deterministic, idempotent, permanent, and runs primarily in the
same transaction as completed evaluation persistence. No popup or notification state is stored.

The workspace keys `khollelab.preferences.curriculumLevel` and
`khollelab.preferences.difficulty` remain solely for the legacy manual selector. Guided APIs do
not consume them; they are scheduled for deletion with Focus Mode rather than in PR14.
