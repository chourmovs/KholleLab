"""add global generated problem catalogue

Revision ID: 20260911_09
Revises: 20260906_08
"""
from alembic import op
import sqlalchemy as sa

revision = "20260911_09"
down_revision = "20260906_08"
branch_labels = None
depends_on = None


def upgrade():
    status = sa.Enum("accepted", "retired", name="generated_problem_status")
    op.create_table("generated_problems",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("status", status, nullable=False), sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("level", sa.String(32), nullable=False), sa.Column("programme_id", sa.String(128), nullable=False),
        sa.Column("expectation_id", sa.String(128), nullable=False), sa.Column("domain", sa.String(64), nullable=False),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generator_family", sa.String(64), nullable=False), sa.Column("generator_model", sa.String(255), nullable=False),
        sa.Column("generator_prompt_version", sa.String(64), nullable=False), sa.Column("critic_family", sa.String(64), nullable=False),
        sa.Column("critic_model", sa.String(255), nullable=False), sa.Column("critic_prompt_version", sa.String(64), nullable=False),
        sa.Column("validation_version", sa.String(64), nullable=False), sa.Column("validation_json", sa.JSON(), nullable=False),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("last_served_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("content_hash", name="uq_generated_problems_content_hash"))
    op.create_index("ix_generated_problems_bucket", "generated_problems", ["programme_id", "level", "expectation_id", "difficulty", "status"])


def downgrade():
    op.drop_index("ix_generated_problems_bucket", table_name="generated_problems")
    op.drop_table("generated_problems")
    sa.Enum(name="generated_problem_status").drop(op.get_bind(), checkfirst=True)
