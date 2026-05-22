"""Add v0.6 reliability indexes."""

from alembic import op


revision = "0002_v06_reliability_indexes"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_tenant_idempotency_key
        ON tasks(tenant_id, idempotency_key)
        WHERE idempotency_key IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_tasks_tenant_idempotency_key")
