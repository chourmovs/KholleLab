"""Scope active learning sessions to an anonymous learner."""
from alembic import op
import sqlalchemy as sa

revision = "20260906_07"
down_revision = "20260906_06"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("learning_sessions", sa.Column("learner_id", sa.Uuid(), nullable=True))
    op.drop_constraint("learning_sessions_active_problem_key_key", "learning_sessions", type_="unique")
    op.create_index("ix_learning_sessions_learner_id", "learning_sessions", ["learner_id"])
    op.create_unique_constraint(
        "uq_learning_sessions_learner_active_problem", "learning_sessions", ["learner_id", "active_problem_key"]
    )


def downgrade():
    op.drop_constraint("uq_learning_sessions_learner_active_problem", "learning_sessions", type_="unique")
    op.drop_index("ix_learning_sessions_learner_id", table_name="learning_sessions")
    op.create_unique_constraint("learning_sessions_active_problem_key_key", "learning_sessions", ["active_problem_key"])
    op.drop_column("learning_sessions", "learner_id")
