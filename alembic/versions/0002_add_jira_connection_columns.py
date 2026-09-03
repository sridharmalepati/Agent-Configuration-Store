"""add jira connection columns

Revision ID: 0002_add_jira_connection_columns
Revises: 0001_create_repo_details
Create Date: 2026-09-01
"""
from alembic import op
import sqlalchemy as sa


revision = "0002_add_jira_connection_columns"
down_revision = "0001_create_repo_details"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("repo_details") as batch_op:
        batch_op.add_column(sa.Column("jira_connection_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("jira_base_url", sa.String(length=1024), nullable=True))
        batch_op.add_column(sa.Column("jira_auth_type", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("jira_credential_ref", sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column("jira_api_version", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("jira_project_key", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("jira_board_id", sa.Integer(), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE repo_details
            SET
                jira_connection_id = id,
                jira_base_url = 'https://example.atlassian.net',
                jira_auth_type = 'API_TOKEN',
                jira_credential_ref = 'secret/jira/default',
                jira_api_version = 3,
                jira_project_key = 'DEFAULT'
            WHERE jira_connection_id IS NULL
            """
        )
    )

    with op.batch_alter_table("repo_details") as batch_op:
        batch_op.alter_column("jira_connection_id", nullable=False)
        batch_op.alter_column("jira_base_url", nullable=False)
        batch_op.alter_column("jira_auth_type", nullable=False)
        batch_op.alter_column("jira_credential_ref", nullable=False)
        batch_op.alter_column("jira_api_version", nullable=False)
        batch_op.alter_column("jira_project_key", nullable=False)
        batch_op.create_index("ix_repo_details_jira_connection_id", ["jira_connection_id"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("repo_details") as batch_op:
        batch_op.drop_index("ix_repo_details_jira_connection_id")
        batch_op.drop_column("jira_board_id")
        batch_op.drop_column("jira_project_key")
        batch_op.drop_column("jira_api_version")
        batch_op.drop_column("jira_credential_ref")
        batch_op.drop_column("jira_auth_type")
        batch_op.drop_column("jira_base_url")
        batch_op.drop_column("jira_connection_id")
