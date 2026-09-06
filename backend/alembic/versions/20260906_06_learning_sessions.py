"""Add durable learning sessions without modifying legacy attempts."""
from alembic import op
import sqlalchemy as sa

revision = "20260906_06"
down_revision = "20260905_05"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "learning_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("problem_id", sa.String(255), nullable=False),
        sa.Column("active_problem_key", sa.String(255), nullable=True),
        sa.Column("status", sa.Enum("active", "completed", "abandoned", name="learning_session_status"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_attempt_id", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("active_problem_key"),
    )
    op.create_index("ix_learning_sessions_updated_at", "learning_sessions", ["updated_at"])
    op.create_index("ix_learning_sessions_problem_id", "learning_sessions", ["problem_id"])
    op.create_index("ix_learning_sessions_status", "learning_sessions", ["status"])
    op.add_column("attempts", sa.Column("session_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_attempts_session_id", "attempts", "learning_sessions", ["session_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_attempts_session_id", "attempts", ["session_id"])


def downgrade():
    op.drop_index("ix_attempts_session_id", table_name="attempts")
    op.drop_constraint("fk_attempts_session_id", "attempts", type_="foreignkey")
    op.drop_column("attempts", "session_id")
    op.drop_table("learning_sessions")
    op.execute("DROP TYPE IF EXISTS learning_session_status")
