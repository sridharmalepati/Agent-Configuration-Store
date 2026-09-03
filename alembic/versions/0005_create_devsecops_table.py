"""create devsecops table

Revision ID: 0005_create_devsecops_table
Revises: 0004_rename_active_to_is_deleted
Create Date: 2026-09-01
"""
from alembic import op
import sqlalchemy as sa


revision = "0005_create_devsecops_table"
down_revision = "0004_rename_active_to_is_deleted"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "devsecops",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("repo_details_id", sa.Integer(), nullable=False),
        sa.Column("git_repository_url", sa.String(length=2048), nullable=False),
        sa.Column("github_token", sa.String(length=2048), nullable=True),
        sa.Column("ci_runner", sa.String(length=255), nullable=True),
        sa.Column("pr_branch", sa.String(length=255), nullable=True),
        sa.Column("code_coverage_tool", sa.String(length=128), nullable=True),
        sa.Column("code_coverage_org", sa.String(length=255), nullable=True),
        sa.Column("code_coverage_token", sa.String(length=2048), nullable=True),
        sa.Column("sast_tool", sa.String(length=128), nullable=True),
        sa.Column("sca_tool", sa.String(length=128), nullable=True),
        sa.Column("dast_tool", sa.String(length=128), nullable=True),
        sa.Column("container_image_scan_tool", sa.String(length=128), nullable=True),
        sa.Column("artifact_repository", sa.String(length=128), nullable=True),
        sa.Column("container_registry", sa.String(length=128), nullable=True),
        sa.Column("container_registry_owner", sa.String(length=255), nullable=True),
        sa.Column("container_registry_pat", sa.String(length=2048), nullable=True),
        sa.Column("is_deleted", sa.String(length=1), server_default="N", nullable=False),
        sa.Column("delete_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["repo_details_id"], ["repo_details.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_devsecops_repo_details_id"), "devsecops", ["repo_details_id"], unique=True)
    op.create_index(op.f("ix_devsecops_is_deleted"), "devsecops", ["is_deleted"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_devsecops_is_deleted"), table_name="devsecops")
    op.drop_index(op.f("ix_devsecops_repo_details_id"), table_name="devsecops")
    op.drop_table("devsecops")
