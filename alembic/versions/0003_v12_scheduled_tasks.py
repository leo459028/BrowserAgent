"""Add v1.2 scheduled_tasks table and tasks foreign key."""

from alembic import op


revision = "0003_v12_scheduled_tasks"
down_revision = "0002_v06_reliability_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_tasks (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(id),
            name TEXT NOT NULL,
            cron_expression TEXT NOT NULL,
            concurrency_policy TEXT NOT NULL DEFAULT 'skip',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            task_template JSON NOT NULL,
            last_run_at TIMESTAMPTZ,
            next_run_at TIMESTAMPTZ,
            created_by UUID REFERENCES users(id),
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_tenant_active ON scheduled_tasks(tenant_id, is_active);
        CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_next_run ON scheduled_tasks(next_run_at) WHERE is_active = TRUE;
        ALTER TABLE tasks ADD COLUMN IF NOT EXISTS scheduled_task_id UUID REFERENCES scheduled_tasks(id) ON DELETE SET NULL;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE tasks DROP COLUMN IF EXISTS scheduled_task_id;
        DROP TABLE IF EXISTS scheduled_tasks;
    """)
