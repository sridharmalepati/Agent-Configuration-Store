"""create repo_details table

Revision ID: 0001_create_repo_details
Revises: 
Create Date: 2026-08-28
"""
from alembic import op
import sqlalchemy as sa


revision = "0001_create_repo_details"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "repo_details",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("app_name", sa.String(length=255), nullable=False),
        sa.Column("github_url", sa.String(length=1024), nullable=False),
        sa.Column("access_token", sa.String(length=2048), nullable=False),
        sa.Column("active", sa.String(length=1), server_default="Y", nullable=False),
        sa.Column("delete_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_repo_details_github_url", "repo_details", ["github_url"], unique=True)
    op.create_index("ix_repo_details_active", "repo_details", ["active"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_repo_details_active", table_name="repo_details")
    op.drop_index("ix_repo_details_github_url", table_name="repo_details")
    op.drop_table("repo_details")
