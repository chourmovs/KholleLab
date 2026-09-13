"""add learner curriculum state keyed by anonymous-capable learner identity"""
from alembic import op
import sqlalchemy as sa

revision = "20260913_14"
down_revision = "20260913_13"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "learner_curriculum_states",
        sa.Column("learner_id", sa.Uuid(), primary_key=True),
        sa.Column("initial_level", sa.String(32), nullable=False),
        sa.Column("current_level", sa.String(32), nullable=False),
        sa.Column("highest_unlocked_level", sa.String(32), nullable=False),
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("learner_curriculum_states")
