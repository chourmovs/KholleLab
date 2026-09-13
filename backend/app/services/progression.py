import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import distinct, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.attempt import Attempt, AttemptStatus, utcnow
from app.models.learning_session import LearningSession, LearningSessionStatus
from app.models.progression_event import ProgressionEvent, ProgressionEventType

SESSION_COMPLETED_XP = 10
XP_POLICY_VERSION = "xp-v1"
PROGRESSION_TIMEZONE = "Europe/Paris"


def paris_activity_date(value: datetime) -> date:
    # SQLite may return a naive value for timezone-aware columns; stored values
    # are UTC throughout the application.
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(ZoneInfo(PROGRESSION_TIMEZONE)).date()


def grade_threshold(grade: int) -> int:
    return 25 * grade * (grade - 1)


def grade_for_xp(total_xp: int) -> int:
    grade = 1
    while grade_threshold(grade + 1) <= total_xp:
        grade += 1
    return grade


class ProgressionService:
    def __init__(self, db: Session):
        self.db = db

    def ensure_completion_award(self, session_id: uuid.UUID) -> ProgressionEvent | None:
        existing = self.db.scalar(select(ProgressionEvent).where(
            ProgressionEvent.session_id == session_id,
            ProgressionEvent.event_type == ProgressionEventType.SESSION_COMPLETED,
        ))
        if existing:
            return existing
        learning = self.db.get(LearningSession, session_id)
        if not learning or learning.status != LearningSessionStatus.COMPLETED:
            return None
        eligible = self.db.scalar(select(Attempt.id).where(
            Attempt.session_id == session_id,
            Attempt.status == AttemptStatus.SUBMITTED,
            func.length(func.trim(Attempt.solution_markdown)) > 0,
        ).limit(1))
        if not eligible:
            return None
        occurred_at = learning.completed_at or learning.updated_at or utcnow()
        event = ProgressionEvent(
            session_id=session_id,
            event_type=ProgressionEventType.SESSION_COMPLETED,
            xp=SESSION_COMPLETED_XP,
            policy_version=XP_POLICY_VERSION,
            occurred_at=occurred_at,
            activity_date=paris_activity_date(occurred_at),
        )
        try:
            # The savepoint contains only the ledger insert. A concurrent winner
            # must never roll back the submitted attempt in the outer transaction.
            with self.db.begin_nested():
                self.db.add(event)
                self.db.flush()
            return event
        except IntegrityError:
            return self.db.scalar(select(ProgressionEvent).where(
                ProgressionEvent.session_id == session_id,
                ProgressionEvent.event_type == ProgressionEventType.SESSION_COMPLETED,
            ))

    def summary(self, learner_id: uuid.UUID, today: date | None = None) -> dict:
        rows = self.db.execute(select(
            func.coalesce(func.sum(ProgressionEvent.xp), 0),
            func.count(ProgressionEvent.id),
        ).join(LearningSession, ProgressionEvent.session_id == LearningSession.id).where(
            LearningSession.learner_id == learner_id,
            ProgressionEvent.event_type == ProgressionEventType.SESSION_COMPLETED,
        )).one()
        dates = list(self.db.scalars(select(distinct(ProgressionEvent.activity_date)).join(
            LearningSession, ProgressionEvent.session_id == LearningSession.id
        ).where(
            LearningSession.learner_id == learner_id,
            ProgressionEvent.event_type == ProgressionEventType.SESSION_COMPLETED,
        ).order_by(ProgressionEvent.activity_date)))
        total_xp, completed_sessions = int(rows[0]), int(rows[1])
        current_day = today or datetime.now(ZoneInfo(PROGRESSION_TIMEZONE)).date()
        current, longest, run = 0, 0, 0
        previous = None
        for active_date in dates:
            run = run + 1 if previous and active_date == previous + timedelta(days=1) else 1
            longest = max(longest, run)
            previous = active_date
        last = dates[-1] if dates else None
        if last and last in {current_day, current_day - timedelta(days=1)}:
            cursor = last
            active_dates = set(dates)
            while cursor in active_dates:
                current += 1
                cursor -= timedelta(days=1)
        grade = grade_for_xp(total_xp)
        current_start = grade_threshold(grade)
        next_xp = grade_threshold(grade + 1)
        return {
            "total_xp": total_xp,
            "grade": grade,
            "current_grade_start_xp": current_start,
            "next_grade_xp": next_xp,
            "xp_to_next_grade": next_xp - total_xp,
            "current_streak_days": current,
            "longest_streak_days": longest,
            "active_today": current_day in set(dates),
            "last_active_date": last,
            "completed_sessions": completed_sessions,
            "timezone": PROGRESSION_TIMEZONE,
        }
