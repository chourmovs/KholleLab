"""create evaluations
Revision ID: 20260904_02
Revises: 20260903_01
"""
from alembic import op
import sqlalchemy as sa
revision="20260904_02"; down_revision="20260903_01"; branch_labels=None; depends_on=None
def upgrade():
    status=sa.Enum("running","completed","failed",name="evaluation_status")
    op.create_table("evaluations",sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("attempt_id",sa.Uuid(),sa.ForeignKey("attempts.id",ondelete="CASCADE"),nullable=False,unique=True),sa.Column("status",status,nullable=False),sa.Column("provider",sa.String(64),nullable=False),sa.Column("model",sa.String(255),nullable=False),sa.Column("prompt_version",sa.String(64),nullable=False),sa.Column("score",sa.Float()),sa.Column("verdict",sa.String(32)),sa.Column("confidence",sa.Float()),sa.Column("audit_json",sa.JSON()),sa.Column("result_json",sa.JSON()),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("started_at",sa.DateTime(timezone=True),nullable=False),sa.Column("completed_at",sa.DateTime(timezone=True)),sa.Column("error_code",sa.String(64)))
def downgrade():
    op.drop_table("evaluations"); sa.Enum(name="evaluation_status").drop(op.get_bind(),checkfirst=True)
