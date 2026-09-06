"""Add durable remote-provider retry scheduling.

Revision ID: 20260906_08
Revises: 20260906_07
"""
from alembic import op
import sqlalchemy as sa

revision = "20260906_08"
down_revision = "20260906_07"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("evaluations", sa.Column("provider_retry_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("evaluations", sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_evaluations_retry_queue", "evaluations", ["status", "stage", "next_retry_at"])


def downgrade():
    op.drop_index("ix_evaluations_retry_queue", table_name="evaluations")
    op.drop_column("evaluations", "next_retry_at")
    op.drop_column("evaluations", "provider_retry_count")
