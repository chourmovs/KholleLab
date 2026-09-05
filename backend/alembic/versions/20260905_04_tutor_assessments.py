"""persist tutor assessments

Revision ID: 20260905_04
Revises: 20260905_03
"""
from alembic import op
import sqlalchemy as sa
revision="20260905_04"; down_revision="20260905_03"; branch_labels=None; depends_on=None
def upgrade():
    op.create_table("tutor_assessments",sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("attempt_id",sa.Uuid(),sa.ForeignKey("attempts.id",ondelete="CASCADE"),nullable=False),sa.Column("revision",sa.Integer(),nullable=False),sa.Column("trigger",sa.String(32),nullable=False),sa.Column("requested_help_level",sa.Integer(),nullable=False),sa.Column("effective_help_level",sa.Integer(),nullable=False),sa.Column("student_state",sa.String(32),nullable=False),sa.Column("intervention_needed",sa.Boolean(),nullable=False),sa.Column("intervention_type",sa.String(32),nullable=False),sa.Column("intervention",sa.Text()),sa.Column("confidence",sa.Float(),nullable=False),sa.Column("error_category",sa.String(32),nullable=False),sa.Column("reveals_answer",sa.Boolean(),nullable=False),sa.Column("provider",sa.String(64),nullable=False),sa.Column("model",sa.String(255),nullable=False),sa.Column("backend",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("client_request_id",sa.String(100),nullable=False),sa.UniqueConstraint("attempt_id","client_request_id",name="uq_tutor_attempt_request"))
    op.create_index("ix_tutor_assessments_attempt_id","tutor_assessments",["attempt_id"]);op.create_index("ix_tutor_assessments_created_at","tutor_assessments",["created_at"])
def downgrade():op.drop_table("tutor_assessments")
