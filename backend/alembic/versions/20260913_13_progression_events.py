"""add durable progression event ledger and backfill eligible sessions"""
from datetime import timezone
import uuid
from zoneinfo import ZoneInfo

from alembic import op
import sqlalchemy as sa

revision = "20260913_13"
down_revision = "20260912_12"
branch_labels = None
depends_on = None

PARIS = ZoneInfo("Europe/Paris")


def upgrade():
    op.create_table(
        "progression_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("learning_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.Enum("session_completed", name="progression_event_type"), nullable=False),
        sa.Column("xp", sa.Integer(), nullable=False),
        sa.Column("policy_version", sa.String(32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activity_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", "event_type", name="uq_progression_events_session_type"),
    )
    op.create_index("ix_progression_events_session_id", "progression_events", ["session_id"])
    op.create_index("ix_progression_events_activity_date", "progression_events", ["activity_date"])
    op.create_index("ix_progression_events_event_type", "progression_events", ["event_type"])

    connection = op.get_bind()
    sessions = sa.table("learning_sessions", sa.column("id", sa.Uuid()), sa.column("status", sa.String()),
                        sa.column("completed_at", sa.DateTime(timezone=True)),
                        sa.column("updated_at", sa.DateTime(timezone=True)))
    attempts = sa.table("attempts", sa.column("session_id", sa.Uuid()), sa.column("status", sa.String()),
                        sa.column("solution_markdown", sa.Text()))
    events = sa.table("progression_events", sa.column("id", sa.Uuid()), sa.column("session_id", sa.Uuid()),
                      sa.column("event_type", sa.String()), sa.column("xp", sa.Integer()),
                      sa.column("policy_version", sa.String()),
                      sa.column("occurred_at", sa.DateTime(timezone=True)),
                      sa.column("activity_date", sa.Date()),
                      sa.column("created_at", sa.DateTime(timezone=True)))
    rows = connection.execute(sa.select(sessions.c.id, sessions.c.completed_at, sessions.c.updated_at).where(
        sessions.c.status == "completed",
        sa.exists(sa.select(attempts.c.session_id).where(
            attempts.c.session_id == sessions.c.id,
            attempts.c.status == "submitted",
            sa.func.length(sa.func.trim(attempts.c.solution_markdown)) > 0,
        )),
    )).all()
    for session_id, completed_at, updated_at in rows:
        occurred_at = completed_at or updated_at
        aware = occurred_at.replace(tzinfo=timezone.utc) if occurred_at.tzinfo is None else occurred_at
        connection.execute(events.insert().values(
            id=uuid.uuid4(), session_id=session_id, event_type="session_completed", xp=10,
            policy_version="xp-v1", occurred_at=occurred_at,
            activity_date=aware.astimezone(PARIS).date(), created_at=occurred_at,
        ))


def downgrade():
    op.drop_table("progression_events")
