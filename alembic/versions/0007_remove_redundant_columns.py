"""remove redundant QA_Automation and DevSecOps columns

Revision ID: 0007_remove_redundant_columns
Revises: 0006_add_app_table_and_app_id_fks
Create Date: 2026-09-01
"""
from alembic import op
import sqlalchemy as sa


revision = "0007_remove_redundant_columns"
down_revision = "0006_add_app_table_and_app_id_fks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("qa_automation") as batch_op:
        batch_op.drop_column("app_name")

    with op.batch_alter_table("devsecops") as batch_op:
        batch_op.drop_index(op.f("ix_devsecops_qa_automation_id"))
        batch_op.drop_column("qa_automation_id")


def downgrade() -> None:
    with op.batch_alter_table("devsecops") as batch_op:
        batch_op.add_column(sa.Column("qa_automation_id", sa.Integer(), nullable=True))
        batch_op.create_index(op.f("ix_devsecops_qa_automation_id"), ["qa_automation_id"], unique=True)

    with op.batch_alter_table("qa_automation") as batch_op:
        batch_op.add_column(sa.Column("app_name", sa.String(length=255), nullable=True))
