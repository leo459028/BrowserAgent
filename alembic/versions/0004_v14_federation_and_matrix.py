"""Add v1.4 federation cluster_nodes table and task matrix/dlp/engine columns."""

from alembic import op


revision = "0004_v14_federation_and_matrix"
down_revision = "0003_v12_scheduled_tasks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS cluster_nodes (
            id TEXT PRIMARY KEY,
            region TEXT NOT NULL DEFAULT 'default',
            is_leader BOOLEAN NOT NULL DEFAULT FALSE,
            status TEXT NOT NULL DEFAULT 'healthy',
            last_heartbeat_at TIMESTAMPTZ NOT NULL,
            active_schedules_count INT NOT NULL DEFAULT 0,
            metadata JSON NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_cluster_nodes_region ON cluster_nodes(region, is_leader);

        ALTER TABLE tasks ADD COLUMN IF NOT EXISTS browser_engine TEXT NOT NULL DEFAULT 'chromium';
        ALTER TABLE tasks ADD COLUMN IF NOT EXISTS matrix_id TEXT;
        ALTER TABLE tasks ADD COLUMN IF NOT EXISTS human_intervened BOOLEAN NOT NULL DEFAULT FALSE;
        ALTER TABLE tasks ADD COLUMN IF NOT EXISTS dlp_masked BOOLEAN NOT NULL DEFAULT FALSE;
        CREATE INDEX IF NOT EXISTS idx_tasks_matrix_id ON tasks(matrix_id) WHERE matrix_id IS NOT NULL;
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS idx_tasks_matrix_id;
        ALTER TABLE tasks DROP COLUMN IF EXISTS dlp_masked;
        ALTER TABLE tasks DROP COLUMN IF EXISTS human_intervened;
        ALTER TABLE tasks DROP COLUMN IF EXISTS matrix_id;
        ALTER TABLE tasks DROP COLUMN IF EXISTS browser_engine;
        DROP TABLE IF EXISTS cluster_nodes;
    """)
