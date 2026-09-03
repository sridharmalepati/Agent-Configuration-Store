"""ORM models for the QA_Automation service."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class APP(Base):
    __tablename__ = "app"

    app_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    app_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    app_description: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class QA_Automation(Base):
    __tablename__ = "qa_automation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    app_id: Mapped[int] = mapped_column(Integer, ForeignKey("app.app_id"), nullable=False, index=True)
    github_url: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True, index=True)
    access_token: Mapped[str] = mapped_column(String(2048), nullable=False)
    jira_connection_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    jira_base_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    jira_auth_type: Mapped[str] = mapped_column(String(64), nullable=False)
    jira_credential_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    jira_api_version: Mapped[int] = mapped_column(Integer, nullable=False)
    jira_project_key: Mapped[str] = mapped_column(String(64), nullable=False)
    jira_board_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    jira_active: Mapped[str] = mapped_column(String(1), nullable=False, default="Y", server_default="Y")
    is_deleted: Mapped[str] = mapped_column(String(1), nullable=False, default="N", server_default="N", index=True)
    delete_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class DevSecOps(Base):
    __tablename__ = "devsecops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    app_id: Mapped[int] = mapped_column(Integer, ForeignKey("app.app_id"), nullable=False, unique=True, index=True)
    git_repository_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    github_token: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    ci_runner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pr_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    code_coverage_tool: Mapped[str | None] = mapped_column(String(128), nullable=True)
    code_coverage_org: Mapped[str | None] = mapped_column(String(255), nullable=True)
    code_coverage_token: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    sast_tool: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sca_tool: Mapped[str | None] = mapped_column(String(128), nullable=True)
    dast_tool: Mapped[str | None] = mapped_column(String(128), nullable=True)
    container_image_scan_tool: Mapped[str | None] = mapped_column(String(128), nullable=True)
    artifact_repository: Mapped[str | None] = mapped_column(String(128), nullable=True)
    container_registry: Mapped[str | None] = mapped_column(String(128), nullable=True)
    container_registry_owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    container_registry_pat: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    is_deleted: Mapped[str] = mapped_column(String(1), nullable=False, default="N", server_default="N", index=True)
    delete_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
