"""Persist compact tutor resource recommendations."""
from alembic import op
import sqlalchemy as sa

revision="20260905_05"
down_revision="20260905_04"
branch_labels=None
depends_on=None

def upgrade():
    op.add_column("tutor_assessments",sa.Column("recommended_resource_id",sa.String(64),nullable=True))
    op.add_column("tutor_assessments",sa.Column("resource_need",sa.String(32),nullable=True))

def downgrade():
    op.drop_column("tutor_assessments","resource_need")
    op.drop_column("tutor_assessments","recommended_resource_id")
