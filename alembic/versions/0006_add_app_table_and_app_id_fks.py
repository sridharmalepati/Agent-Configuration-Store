"""add app table and app_id foreign keys

Revision ID: 0006_add_app_table_and_app_id_fks
Revises: 0005_create_devsecops_table
Create Date: 2026-09-01
"""
from alembic import op
import sqlalchemy as sa


revision = "0006_add_app_table_and_app_id_fks"
down_revision = "0005_create_devsecops_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app",
        sa.Column("app_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("app_name", sa.String(length=255), nullable=False),
        sa.Column("app_description", sa.String(length=2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("app_id"),
    )
    op.create_index(op.f("ix_app_app_name"), "app", ["app_name"], unique=True)

    op.add_column("repo_details", sa.Column("app_id", sa.Integer(), nullable=True))
    op.execute(sa.text("INSERT INTO app (app_name, app_description) VALUES ('default-app', 'Default application')"))
    op.execute(sa.text("UPDATE repo_details SET app_id = 1 WHERE app_id IS NULL"))
    with op.batch_alter_table("repo_details") as batch_op:
        batch_op.create_foreign_key("fk_repo_details_app_id", "app", ["app_id"], ["app_id"])
        batch_op.alter_column("app_id", nullable=False)
        batch_op.create_index(op.f("ix_repo_details_app_id"), ["app_id"], unique=False)

    op.add_column("devsecops", sa.Column("app_id", sa.Integer(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE devsecops SET app_id = (SELECT app_id FROM repo_details WHERE repo_details.id = devsecops.repo_details_id) WHERE app_id IS NULL"
        )
    )
    with op.batch_alter_table("devsecops") as batch_op:
        batch_op.create_foreign_key("fk_devsecops_app_id", "app", ["app_id"], ["app_id"])
        batch_op.alter_column("app_id", nullable=False)
        batch_op.create_index(op.f("ix_devsecops_app_id"), ["app_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("devsecops") as batch_op:
        batch_op.drop_index(op.f("ix_devsecops_app_id"))
        batch_op.drop_constraint("fk_devsecops_app_id", type_="foreignkey")
        batch_op.drop_column("app_id")

    with op.batch_alter_table("repo_details") as batch_op:
        batch_op.drop_index(op.f("ix_repo_details_app_id"))
        batch_op.drop_constraint("fk_repo_details_app_id", type_="foreignkey")
        batch_op.drop_column("app_id")

    op.drop_index(op.f("ix_app_app_name"), table_name="app")
    op.drop_table("app")
