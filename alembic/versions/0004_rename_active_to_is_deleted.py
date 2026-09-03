"""rename active soft-delete flag to is_deleted

Revision ID: 0004_rename_active_to_is_deleted
Revises: 0003_add_jira_active_column
Create Date: 2026-09-01
"""
from alembic import op
import sqlalchemy as sa


revision = "0004_rename_active_to_is_deleted"
down_revision = "0003_add_jira_active_column"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("repo_details") as batch_op:
        batch_op.alter_column("active", new_column_name="is_deleted")

    op.execute(sa.text("UPDATE repo_details SET is_deleted = 'N' WHERE is_deleted IS NULL"))

    with op.batch_alter_table("repo_details") as batch_op:
        batch_op.alter_column("is_deleted", existing_type=sa.String(length=1), nullable=False, server_default="N")

    # Recreate the index against the renamed column.
    op.execute(sa.text("DROP INDEX IF EXISTS ix_repo_details_active"))
    op.create_index("ix_repo_details_is_deleted", "repo_details", ["is_deleted"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_repo_details_is_deleted", table_name="repo_details")
    with op.batch_alter_table("repo_details") as batch_op:
        batch_op.alter_column("is_deleted", new_column_name="active")
    op.create_index("ix_repo_details_active", "repo_details", ["active"], unique=False)
