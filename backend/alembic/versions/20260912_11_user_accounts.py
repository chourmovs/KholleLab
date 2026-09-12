"""add persistent user accounts and hashed auth sessions"""
from alembic import op
import sqlalchemy as sa

revision = "20260912_11"
down_revision = "20260911_10"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("user_accounts",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("learner_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(320), nullable=False), sa.Column("email_normalized", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(512), nullable=False), sa.Column("display_name", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("disabled_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("learner_id"), sa.UniqueConstraint("email"), sa.UniqueConstraint("email_normalized"))
    op.create_table("auth_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)))
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])

def downgrade():
    op.drop_table("auth_sessions")
    op.drop_table("user_accounts")
