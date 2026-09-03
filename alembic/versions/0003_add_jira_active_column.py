"""add jira active column

Revision ID: 0003_add_jira_active_column
Revises: 0002_add_jira_connection_columns
Create Date: 2026-09-01
"""
from alembic import op
import sqlalchemy as sa


revision = "0003_add_jira_active_column"
down_revision = "0002_add_jira_connection_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("repo_details") as batch_op:
        batch_op.add_column(sa.Column("jira_active", sa.String(length=1), nullable=True, server_default="Y"))

    op.execute(sa.text("UPDATE repo_details SET jira_active = 'Y' WHERE jira_active IS NULL"))

    with op.batch_alter_table("repo_details") as batch_op:
        batch_op.alter_column("jira_active", nullable=False, server_default="Y")


def downgrade() -> None:
    with op.batch_alter_table("repo_details") as batch_op:
        batch_op.drop_column("jira_active")
