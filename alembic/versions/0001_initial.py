"""Initial schema."""

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    with open("sql/schema.sql", "r", encoding="utf-8") as f:
        sql = f.read()
    for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
        op.execute(stmt)

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS approvals CASCADE")
    op.execute("DROP TABLE IF EXISTS evaluations CASCADE")
    op.execute("DROP TABLE IF EXISTS task_artifacts CASCADE")
    op.execute("DROP TABLE IF EXISTS task_steps CASCADE")
    op.execute("DROP TABLE IF EXISTS tasks CASCADE")
    op.execute("DROP TABLE IF EXISTS skills CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
    op.execute("DROP TABLE IF EXISTS tenants CASCADE")
