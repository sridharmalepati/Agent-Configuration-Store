"""Pydantic request and response schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl


class QA_AutomationCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "description": (
                "Create payload for QA_Automation. github_url must be a valid reachable URL. "
                "If the GitHub repo does not exist, validation returns: "
                "github_url repo not found (HTTP 404), Please add a valid github url. "
                "is_deleted is managed by the service and defaults to N."
            ),
            "examples": [
                {
                    "app_id": 1,
                    "github_url": "https://github.com/example/acme-service",
                    "access_token": "secret-token-1234",
                    "jira_connection_id": 1001,
                    "jira_base_url": "https://mycompany.atlassian.net",
                    "jira_auth_type": "API_TOKEN",
                    "jira_credential_ref": "secret/jira/prod",
                    "jira_api_version": 3,
                    "jira_project_key": "PAY",
                    "jira_board_id": 77,
                    "jira_active": "Y",
                }
            ],
        },
    )

    app_id: int
    github_url: HttpUrl
    access_token: str
    jira_connection_id: int
    jira_base_url: HttpUrl
    jira_auth_type: str
    jira_credential_ref: str
    jira_api_version: int
    jira_project_key: str
    jira_board_id: int | None = None
    jira_active: str = "Y"


class QA_AutomationUpdate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "new_github_url": "https://github.com/example/acme-service-renamed",
                    "jira_project_key": "PAYX",
                    "jira_board_id": 88,
                    "access_token": "new-token-5678",
                    "jira_connection_id": 1001,
                    "jira_base_url": "https://mycompany.atlassian.net",
                    "jira_auth_type": "API_TOKEN",
                    "jira_credential_ref": "secret/jira/prod",
                    "jira_api_version": 3,
                    "jira_active": "Y",
                }
            ],
            "description": (
                "Partial update payload. Only include fields you want to change. "
                "github_url query parameter selects the row and must be valid/reachable. "
                "If the GitHub repo does not exist, validation returns: "
                "github_url repo not found (HTTP 404), Please add a valid github url. "
                "Use new_github_url to rename the repository URL; it must also be valid/reachable. "
                "app_id is immutable after create."
            ),
        },
    )

    new_github_url: HttpUrl | None = None
    access_token: str | None = None
    jira_connection_id: int | None = None
    jira_base_url: HttpUrl | None = None
    jira_auth_type: str | None = None
    jira_credential_ref: str | None = None
    jira_api_version: int | None = None
    jira_project_key: str | None = None
    jira_board_id: int | None = None
    jira_active: str | None = None


class QA_AutomationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    app_id: int
    github_url: str
    jira_connection_id: int
    jira_base_url: str
    jira_auth_type: str
    jira_credential_ref: str
    jira_api_version: int
    jira_project_key: str
    jira_board_id: int | None = None
    jira_active: str
    is_deleted: str
    delete_date: datetime | None = None
    access_token_masked: str


class DevSecOpsCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "description": (
                "Create payload for DevSecOps. git_repository_url must be a valid reachable URL. "
                "is_deleted is managed by the service and defaults to N."
            ),
            "examples": [
                {
                    "app_id": 1,
                    "git_repository_url": "https://github.com/example/acme-service",
                    "github_token": "ghp_example_token",
                    "ci_runner": "GitHub Actions",
                    "pr_branch": "main",
                    "code_coverage_tool": "Codecov",
                    "code_coverage_org": "acme",
                    "code_coverage_token": "codecov_token",
                    "sast_tool": "SonarQube",
                    "sca_tool": "Snyk",
                    "dast_tool": "OWASP ZAP",
                    "container_image_scan_tool": "Trivy",
                    "artifact_repository": "JFrog Artifactory",
                    "container_registry": "ghcr.io",
                    "container_registry_owner": "acme",
                    "container_registry_pat": "ghcr_pat",
                }
            ],
        },
    )

    app_id: int
    git_repository_url: str
    github_token: str | None = None
    ci_runner: str | None = None
    pr_branch: str | None = None
    code_coverage_tool: str | None = None
    code_coverage_org: str | None = None
    code_coverage_token: str | None = None
    sast_tool: str | None = None
    sca_tool: str | None = None
    dast_tool: str | None = None
    container_image_scan_tool: str | None = None
    artifact_repository: str | None = None
    container_registry: str | None = None
    container_registry_owner: str | None = None
    container_registry_pat: str | None = None


class DevSecOpsUpdate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "ci_runner": "Azure Pipelines",
                    "dast_tool": "Aqua",
                    "sast_tool": "SonarCloud",
                    "container_image_scan_tool": "Trivy",
                    "artifact_repository": "Azure Artifacts",
                    "git_repository_url": "https://github.com/example/acme-service-renamed",
                }
            ],
            "description": (
                "Partial update payload. app_id is immutable after create and is_deleted is delete-only. "
                "git_repository_url must be valid and reachable if changed."
            ),
        },
    )

    git_repository_url: str | None = None
    github_token: str | None = None
    ci_runner: str | None = None
    pr_branch: str | None = None
    code_coverage_tool: str | None = None
    code_coverage_org: str | None = None
    code_coverage_token: str | None = None
    sast_tool: str | None = None
    sca_tool: str | None = None
    dast_tool: str | None = None
    container_image_scan_tool: str | None = None
    artifact_repository: str | None = None
    container_registry: str | None = None
    container_registry_owner: str | None = None
    container_registry_pat: str | None = None


class DevSecOpsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    app_id: int
    git_repository_url: str
    github_token: str | None = None
    ci_runner: str | None = None
    pr_branch: str | None = None
    code_coverage_tool: str | None = None
    code_coverage_org: str | None = None
    code_coverage_token: str | None = None
    sast_tool: str | None = None
    sca_tool: str | None = None
    dast_tool: str | None = None
    container_image_scan_tool: str | None = None
    artifact_repository: str | None = None
    container_registry: str | None = None
    container_registry_owner: str | None = None
    container_registry_pat: str | None = None
    is_deleted: str
    delete_date: datetime | None = None


class HealthResponse(BaseModel):
    status: str
    service: str
