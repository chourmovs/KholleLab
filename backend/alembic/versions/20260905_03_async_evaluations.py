"""persist asynchronous evaluation queue state

Revision ID: 20260905_03
Revises: 20260904_02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260905_03"
down_revision = "20260904_02"
branch_labels = None
depends_on = None

def upgrade():
    values = ("queued", "candidate_audit", "adjudication", "finalizing", "completed", "failed")
    postgresql.ENUM(*values, name="evaluation_stage").create(op.get_bind(), checkfirst=True)
    # The type was created explicitly above so ALTER TABLE must only reference
    # it.  Without create_type=False Alembic tries CREATE TYPE a second time.
    stage = postgresql.ENUM(*values, name="evaluation_stage", create_type=False)
    op.add_column("evaluations", sa.Column("stage", stage, nullable=False, server_default="queued"))
    op.add_column("evaluations", sa.Column("progress", sa.Integer(), nullable=False, server_default="5"))
    op.add_column("evaluations", sa.Column("heartbeat_at", sa.DateTime(timezone=True)))
    op.add_column("evaluations", sa.Column("recovery_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("evaluations", sa.Column("elapsed_ms", sa.Float()))
    op.alter_column("evaluations", "started_at", nullable=True)
    op.execute("UPDATE evaluations SET stage = CASE status WHEN 'completed' THEN 'completed'::evaluation_stage WHEN 'failed' THEN 'failed'::evaluation_stage ELSE 'queued'::evaluation_stage END")

def downgrade():
    op.alter_column("evaluations", "started_at", nullable=False)
    for column in ("elapsed_ms", "recovery_count", "heartbeat_at", "progress", "stage"):
        op.drop_column("evaluations", column)
    postgresql.ENUM(name="evaluation_stage").drop(op.get_bind(), checkfirst=True)
