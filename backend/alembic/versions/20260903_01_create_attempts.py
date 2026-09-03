"""create attempts

Revision ID: 20260903_01
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "20260903_01"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    status = sa.Enum("draft", "submitted", name="attempt_status")
    op.create_table("attempts", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("problem_id", sa.String(255), nullable=False), sa.Column("status", status, nullable=False), sa.Column("solution_markdown", sa.Text(), nullable=False), sa.Column("started_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("submitted_at", sa.DateTime(timezone=True)), sa.Column("elapsed_seconds", sa.Integer(), nullable=False), sa.Column("revision", sa.Integer(), nullable=False), sa.CheckConstraint("elapsed_seconds >= 0", name="ck_attempt_elapsed_nonnegative"), sa.CheckConstraint("revision >= 0", name="ck_attempt_revision_nonnegative"))
    op.create_index("ix_attempts_problem_id", "attempts", ["problem_id"]); op.create_index("ix_attempts_updated_at", "attempts", ["updated_at"]); op.create_index("ix_attempts_status", "attempts", ["status"])

def downgrade():
    op.drop_index("ix_attempts_status", table_name="attempts"); op.drop_index("ix_attempts_updated_at", table_name="attempts"); op.drop_index("ix_attempts_problem_id", table_name="attempts"); op.drop_table("attempts")
    sa.Enum(name="attempt_status").drop(op.get_bind(), checkfirst=True)
