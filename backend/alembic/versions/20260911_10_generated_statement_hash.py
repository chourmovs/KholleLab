"""add global generated statement fingerprint

Revision ID: 20260911_10
Revises: 20260911_09
"""
import hashlib
import re
import unicodedata

from alembic import op
import sqlalchemy as sa

revision = "20260911_10"
down_revision = "20260911_09"
branch_labels = None
depends_on = None


def _fingerprint(statement: str) -> str:
    normalized = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", statement).casefold()).strip()
    return hashlib.sha256(normalized.encode()).hexdigest()


def upgrade():
    op.add_column("generated_problems", sa.Column("statement_hash", sa.String(64), nullable=True))
    bind = op.get_bind()
    table = sa.table("generated_problems",
        sa.column("id", sa.String), sa.column("payload_json", sa.JSON),
        sa.column("statement_hash", sa.String), sa.column("status", sa.String))
    rows = bind.execute(sa.select(table.c.id, table.c.payload_json, table.c.status)
                        .order_by(table.c.id)).all()
    accepted_hashes: set[str] = set()
    for identifier, payload, status in rows:
        digest = _fingerprint((payload or {}).get("statement", ""))
        values = {"statement_hash": digest}
        status_value = getattr(status, "value", status)
        if status_value == "accepted" and digest in accepted_hashes:
            values["status"] = "retired"
        elif status_value == "accepted":
            accepted_hashes.add(digest)
        bind.execute(table.update().where(table.c.id == identifier).values(**values))
    with op.batch_alter_table("generated_problems") as batch:
        batch.alter_column("statement_hash", existing_type=sa.String(64), nullable=False)
    op.create_index("uq_generated_problems_accepted_statement_hash", "generated_problems",
                    ["statement_hash"], unique=True,
                    postgresql_where=sa.text("status = 'accepted'"),
                    sqlite_where=sa.text("status = 'accepted'"))


def downgrade():
    op.drop_index("uq_generated_problems_accepted_statement_hash", table_name="generated_problems")
    with op.batch_alter_table("generated_problems") as batch:
        batch.drop_column("statement_hash")
