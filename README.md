# QA Automation FastAPI Service

This folder is now a standalone repository for the QA Automation and DevSecOps FastAPI service.

## What this service provides

- CRUD APIs for `qa_automation`
- CRUD APIs for `devsecops` linked by `app_id`
- Soft delete behavior (`is_deleted` + `delete_date`)
- Health endpoints: `/healthz`, `/readyz`
- `/healthz` is liveness (service process is up), and `/readyz` is readiness (service is ready to accept traffic).
- Request logging to `logs/api_requests.log`
- In-process LRU caching for QA Automation read lookups

## Project layout

- `src/repo_service/`: FastAPI app, models, schemas, CRUD, config, security
- `alembic/`: migration scripts
- `tests/`: API and security tests
- `scripts/`: sample seed/cleanup helpers

## Prerequisites

- Python 3.11+
- A database (PostgreSQL for normal usage)

## Setup

1. Create and activate a virtual environment.
2. Install dependencies.
3. Configure environment variables.
4. Run migrations.
5. Start the API.

### Install dependencies

Use either requirements or pyproject-based install.

```powershell
pip install -r requirements.txt
```

For reproducible installs with pinned versions:

```powershell
pip install -r requirements-lock.txt
```

or

```powershell
pip install -e .
```

### Environment variables

Create a `.env` file in the repo root (or export variables in your shell):

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/repo_service
ACCESS_TOKEN_ENCRYPTION_KEY=<fernet-base64-key>
LOG_LEVEL=INFO
CACHE_MAXSIZE=128
SERVICE_NAME=qa_automation_service
STRICT_REPO_URL_VALIDATION=true
GITHUB_VALIDATION_TOKEN=
```

For private GitHub repositories, provide a token in the payload (`access_token` for QA Automation or `github_token` for DevSecOps), or set `GITHUB_VALIDATION_TOKEN` in environment for shared validation. Set `STRICT_REPO_URL_VALIDATION=false` to disable repository reachability checks.

Generate an encryption key:

```powershell
python setup_encryption_key.py
```

### Run migrations

```powershell
alembic -c alembic.ini upgrade head
```

### Start server

```powershell
uvicorn repo_service.main:app --host 0.0.0.0 --port 8090
```

## Running tests

```powershell
pytest -q
```

## Seed sample DevSecOps data

```powershell
python seed_devsecops.py
```

## QA Automation example payload

```json
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
  "jira_active": "Y"
}
```

## DevSecOps example payload

```json
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
  "container_registry_pat": "ghcr_pat"
}
```
