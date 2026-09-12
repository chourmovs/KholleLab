"""capture immutable session curriculum mapping"""
from alembic import op
import sqlalchemy as sa

revision = "20260912_12"
down_revision = "20260912_11"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("learning_sessions", sa.Column("curriculum_snapshot", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("learning_sessions", "curriculum_snapshot")
