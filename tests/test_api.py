import os
import tempfile
from pathlib import Path
from collections.abc import Generator
from unittest.mock import patch

from cryptography.fernet import Fernet
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import inspect
import pytest

# Set env before importing app modules that initialize settings/engine.
_db_file = Path(tempfile.gettempdir()) / "repo_service_test.db"
if _db_file.exists():
    _db_file.unlink()

os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_db_file.as_posix()}"
os.environ["ACCESS_TOKEN_ENCRYPTION_KEY"] = Fernet.generate_key().decode("utf-8")

from repo_service.config import get_settings  # noqa: E402
from repo_service.main import app  # noqa: E402
from repo_service.database import Base, engine  # noqa: E402
from repo_service.models import APP, QA_Automation  # noqa: E402
from sqlalchemy.orm import Session as SQLAlchemySession  # noqa: E402


Base.metadata.create_all(bind=engine)
with SQLAlchemySession(engine) as session:
    existing = session.query(APP).first()
    if existing is None:
        session.add(APP(app_name="default-app", app_description="Default app for API tests"))
        session.commit()
client = TestClient(app)


@pytest.fixture(autouse=True)
def bypass_github_url_reachability() -> Generator[None, None, None]:
    with patch("repo_service.crud._assert_url_reachable", return_value=None):
        yield


def _create_payload(github_url: str = "https://github.com/org/repo") -> dict:
    return {
        "app_id": 1,
        "github_url": github_url,
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


def test_health_endpoints() -> None:
    for path in ("/healthz", "/readyz"):
        response = client.get(path)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"


def test_request_logging_writes_to_file() -> None:
    log_file = Path(__file__).resolve().parents[1] / "logs" / "api_requests.log"

    response = client.get("/healthz")
    assert response.status_code == 200

    if not log_file.exists():
        raise AssertionError("Request log file was not created")

    log_contents = log_file.read_text(encoding="utf-8")
    assert "GET /healthz" in log_contents
    assert "status=200" in log_contents
    assert "latency_ms=" in log_contents


def test_post_and_get_qa_automation() -> None:
    create_response = client.post("/qa-automation", json=_create_payload())
    assert create_response.status_code == 201

    get_response = client.get("/qa-automation", params={"github_url": "https://github.com/org/repo"})
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["app_id"] == 1
    assert "app_name" not in body
    assert body["is_deleted"] == "N"
    assert body["jira_connection_id"] == 1001
    assert body["jira_base_url"] == "https://mycompany.atlassian.net/"
    assert body["jira_auth_type"] == "API_TOKEN"
    assert body["jira_credential_ref"] == "secret/jira/prod"
    assert body["jira_api_version"] == 3
    assert body["jira_project_key"] == "PAY"
    assert body["jira_board_id"] == 77
    assert body["jira_active"] == "Y"
    assert body["access_token_masked"].endswith("1234")
    assert body["access_token_masked"] != "secret-token-1234"


def test_put_updates_and_invalidate_cache() -> None:
    url = "https://github.com/org/repo2"
    response = client.post(
        "/qa-automation",
        json={
            **_create_payload(github_url=url),
            "jira_connection_id": 1002,
        },
    )
    assert response.status_code == 201

    # Prime LRU cache.
    first_get = client.get("/qa-automation", params={"github_url": url})
    assert first_get.status_code == 200
    assert first_get.json()["app_id"] == 1

    update_response = client.put(
        "/qa-automation",
        params={"github_url": url},
        json={
            "access_token": "new-token-5678",
            "jira_project_key": "PAYX",
            "jira_board_id": 88,
        },
    )
    assert update_response.status_code == 200

    second_get = client.get("/qa-automation", params={"github_url": url})
    assert second_get.status_code == 200
    assert second_get.json()["is_deleted"] == "N"
    assert second_get.json()["jira_project_key"] == "PAYX"
    assert second_get.json()["jira_board_id"] == 88
    assert second_get.json()["access_token_masked"].endswith("5678")


def test_put_rejects_is_deleted_field() -> None:
    url = "https://github.com/org/repo-update-forbid"
    create_response = client.post(
        "/qa-automation",
        json={
            **_create_payload(github_url=url),
            "jira_connection_id": 12001,
        },
    )
    assert create_response.status_code == 201

    update_response = client.put(
        "/qa-automation",
        params={"github_url": url},
        json={"is_deleted": "Y"},
    )
    assert update_response.status_code == 422


def test_put_rejects_app_id_field() -> None:
    url = "https://github.com/org/repo-update-appid-forbid"
    create_response = client.post(
        "/qa-automation",
        json={
            **_create_payload(github_url=url),
            "jira_connection_id": 12002,
        },
    )
    assert create_response.status_code == 201

    update_response = client.put(
        "/qa-automation",
        params={"github_url": url},
        json={"app_id": 2},
    )
    assert update_response.status_code == 422


def test_put_can_rename_github_url() -> None:
    old_url = "https://github.com/org/repo-rename-old"
    new_url = "https://github.com/org/repo-rename-new"

    create_response = client.post(
        "/qa-automation",
        json={
            **_create_payload(github_url=old_url),
            "jira_connection_id": 12003,
        },
    )
    assert create_response.status_code == 201

    update_response = client.put(
        "/qa-automation",
        params={"github_url": old_url},
        json={"new_github_url": new_url},
    )
    assert update_response.status_code == 200
    assert update_response.json()["github_url"] == new_url

    old_get = client.get("/qa-automation", params={"github_url": old_url})
    assert old_get.status_code == 404

    new_get = client.get("/qa-automation", params={"github_url": new_url})
    assert new_get.status_code == 200
    assert new_get.json()["github_url"] == new_url


def test_put_rejects_unreachable_new_github_url() -> None:
    old_url = "https://github.com/org/repo-rename-unreachable-old"
    unreachable_new_url = "https://github.com/org/repo-rename-unreachable-new"

    create_response = client.post(
        "/qa-automation",
        json={
            **_create_payload(github_url=old_url),
            "jira_connection_id": 12014,
        },
    )
    assert create_response.status_code == 201

    with patch(
        "repo_service.crud._assert_github_url_reachable",
        side_effect=HTTPException(status_code=422, detail="github_url is not reachable"),
    ):
        update_response = client.put(
            "/qa-automation",
            params={"github_url": old_url},
            json={"new_github_url": unreachable_new_url},
        )

    assert update_response.status_code == 422


def test_put_rename_github_url_conflict_returns_409() -> None:
    source_url = "https://github.com/org/repo-rename-source"
    target_url = "https://github.com/org/repo-rename-target"

    first_create = client.post(
        "/qa-automation",
        json={
            **_create_payload(github_url=source_url),
            "jira_connection_id": 12004,
        },
    )
    assert first_create.status_code == 201

    second_create = client.post(
        "/qa-automation",
        json={
            **_create_payload(github_url=target_url),
            "jira_connection_id": 12005,
        },
    )
    assert second_create.status_code == 201

    update_response = client.put(
        "/qa-automation",
        params={"github_url": source_url},
        json={"new_github_url": target_url},
    )
    assert update_response.status_code == 409


def test_put_rename_github_url_reuses_soft_deleted_target() -> None:
    source_url = "https://github.com/org/repo-rename-source-soft"
    deleted_target_url = "https://github.com/org/repo-rename-target-soft"

    create_source = client.post(
        "/qa-automation",
        json={
            **_create_payload(github_url=source_url),
            "jira_connection_id": 12006,
        },
    )
    assert create_source.status_code == 201
    source_id = create_source.json()["id"]

    create_target = client.post(
        "/qa-automation",
        json={
            **_create_payload(github_url=deleted_target_url),
            "jira_connection_id": 12007,
        },
    )
    assert create_target.status_code == 201

    soft_delete_target = client.delete(
        "/qa-automation",
        params={"github_url": deleted_target_url},
    )
    assert soft_delete_target.status_code == 204

    rename_response = client.put(
        "/qa-automation",
        params={"github_url": source_url},
        json={"new_github_url": deleted_target_url},
    )
    assert rename_response.status_code == 200
    assert rename_response.json()["id"] == source_id
    assert rename_response.json()["github_url"] == deleted_target_url

    source_get = client.get("/qa-automation", params={"github_url": source_url})
    assert source_get.status_code == 404

    target_get = client.get("/qa-automation", params={"github_url": deleted_target_url})
    assert target_get.status_code == 200

    with SQLAlchemySession(engine) as session:
        rows = session.query(QA_Automation).filter(QA_Automation.github_url == deleted_target_url).all()
        assert len(rows) == 1
        assert rows[0].id == source_id
        assert rows[0].is_deleted == "N"


def test_delete_soft_delete_and_remove_from_cache() -> None:
    url = "https://github.com/org/repo3"
    response = client.post(
        "/qa-automation",
        json={
            **_create_payload(github_url=url),
            "jira_connection_id": 1003,
        },
    )
    assert response.status_code == 201

    # Prime LRU cache.
    first_get = client.get("/qa-automation", params={"github_url": url})
    assert first_get.status_code == 200

    delete_response = client.delete("/qa-automation", params={"github_url": url})
    assert delete_response.status_code == 204

    second_get = client.get("/qa-automation", params={"github_url": url})
    assert second_get.status_code == 404


def test_duplicate_github_url_returns_conflict() -> None:
    url = "https://github.com/org/repo4"
    first = client.post(
        "/qa-automation",
        json={
            **_create_payload(github_url=url),
            "jira_connection_id": 1004,
        },
    )
    assert first.status_code == 201

    second = client.post(
        "/qa-automation",
        json={
            **_create_payload(github_url=url),
            "jira_connection_id": 1005,
        },
    )
    assert second.status_code == 409


def test_post_rejects_duplicate_jira_connection_id() -> None:
    first = client.post(
        "/qa-automation",
        json={
            **_create_payload(github_url="https://github.com/org/repo-jira-dup-1"),
            "jira_connection_id": 13001,
        },
    )
    assert first.status_code == 201

    second = client.post(
        "/qa-automation",
        json={
            **_create_payload(github_url="https://github.com/org/repo-jira-dup-2"),
            "jira_connection_id": 13001,
        },
    )
    assert second.status_code == 409
    assert second.json()["detail"] == "jira_connection_id already exists"


def test_post_reuses_soft_deleted_github_url() -> None:
    url = "https://github.com/org/repo-reuse-soft-deleted"

    first_create = client.post(
        "/qa-automation",
        json={
            **_create_payload(github_url=url),
            "jira_connection_id": 12008,
        },
    )
    assert first_create.status_code == 201

    soft_delete = client.delete("/qa-automation", params={"github_url": url})
    assert soft_delete.status_code == 204

    second_create = client.post(
        "/qa-automation",
        json={
            **_create_payload(github_url=url),
            "jira_connection_id": 12009,
        },
    )
    assert second_create.status_code == 201

    get_response = client.get("/qa-automation", params={"github_url": url})
    assert get_response.status_code == 200
    assert get_response.json()["jira_connection_id"] == 12009

    with SQLAlchemySession(engine) as session:
        rows = session.query(QA_Automation).filter(QA_Automation.github_url == url).all()
        assert len(rows) == 1
        assert rows[0].is_deleted == "N"


def test_post_rejects_is_deleted_field() -> None:
    url = "https://github.com/org/repo-isdeleted-forbid"

    create_response = client.post(
        "/qa-automation",
        json={
            **_create_payload(github_url=url),
            "jira_connection_id": 12012,
            "is_deleted": "Y",
        },
    )
    assert create_response.status_code == 422


def test_post_rejects_unreachable_github_url() -> None:
    with patch(
        "repo_service.crud._assert_github_url_reachable",
        side_effect=HTTPException(status_code=422, detail="github_url is not reachable"),
    ):
        create_response = client.post(
            "/qa-automation",
            json={
                **_create_payload(github_url="https://github.com/org/repo-unreachable"),
                "jira_connection_id": 12013,
            },
        )

    assert create_response.status_code == 422


def test_post_rejects_non_canonical_app_id() -> None:
    url = "https://github.com/org/repo-appid-guard"

    with SQLAlchemySession(engine) as session:
        if session.query(APP).filter(APP.app_id == 2).first() is None:
            session.add(APP(app_name="secondary-app", app_description="Secondary app for API tests"))
            session.commit()

    first_create = client.post(
        "/qa-automation",
        json={
            **_create_payload(github_url=url),
            "jira_connection_id": 12010,
        },
    )
    assert first_create.status_code == 201

    second_url = "https://github.com/org/repo-appid-guard-2"
    second_create = client.post(
        "/qa-automation",
        json={
            **_create_payload(github_url=second_url),
            "app_id": 2,
            "jira_connection_id": 12011,
        },
    )
    assert second_create.status_code == 409


def test_get_handles_legacy_ciphertext_after_key_rotation(monkeypatch) -> None:
    legacy_key = Fernet.generate_key().decode("utf-8")
    current_key = Fernet.generate_key().decode("utf-8")
    url = "https://github.com/org/repo-legacy"

    monkeypatch.setenv("ACCESS_TOKEN_ENCRYPTION_KEY", legacy_key)
    get_settings.cache_clear()

    create_response = client.post(
        "/qa-automation",
        json={
            **_create_payload(github_url=url),
            "jira_connection_id": 1099,
            "access_token": "legacy-token-1234",
        },
    )
    assert create_response.status_code == 201

    monkeypatch.setenv("ACCESS_TOKEN_ENCRYPTION_KEY", current_key)
    get_settings.cache_clear()

    get_response = client.get("/qa-automation", params={"github_url": url})
    assert get_response.status_code == 200
    assert get_response.json()["access_token_masked"] == "***unavailable***"


def test_app_and_app_id_foreign_keys_exist() -> None:
    inspector = inspect(engine)
    repo_columns = [column["name"] for column in inspector.get_columns("qa_automation")]
    devsecops_columns = [column["name"] for column in inspector.get_columns("devsecops")]

    assert inspector.has_table("app")
    assert "app_id" in repo_columns
    assert "app_id" in devsecops_columns
    assert "app_name" not in repo_columns
    assert "qa_automation_id" not in devsecops_columns


def test_devsecops_table_exists() -> None:
    assert inspect(engine).has_table("devsecops")


def test_devsecops_crud_flow() -> None:
    repo_response = client.post(
        "/qa-automation",
        json={
            **_create_payload(github_url="https://github.com/org/repo-devsecops"),
            "jira_connection_id": 2001,
        },
    )
    assert repo_response.status_code == 201

    payload = {
        "app_id": 1,
        "git_repository_url": "https://github.com/org/repo-devsecops",
        "github_token": "ghp_secret",
        "ci_runner": "GitHub Actions",
        "pr_branch": "main",
        "code_coverage_tool": "Codecov",
        "code_coverage_org": "my-org",
        "code_coverage_token": "cover-secret",
        "sast_tool": "SonarQube",
        "sca_tool": "Snyk",
        "dast_tool": "OWASP ZAP",
        "container_image_scan_tool": "Trivy",
        "artifact_repository": "JFrog",
        "container_registry": "ghcr.io",
        "container_registry_owner": "my-org",
        "container_registry_pat": "cr-secret",
    }

    create_response = client.post("/devsecops", json=payload)
    assert create_response.status_code == 201
    body = create_response.json()
    assert body["app_id"] == 1
    assert "qa_automation_id" not in body
    assert body["ci_runner"] == "GitHub Actions"
    assert body["is_deleted"] == "N"

    get_response = client.get("/devsecops", params={"app_id": 1})
    assert get_response.status_code == 200
    assert get_response.json()["sast_tool"] == "SonarQube"

    update_response = client.put(
        "/devsecops",
        params={"app_id": 1},
        json={"ci_runner": "Azure Pipelines", "dast_tool": "Aqua"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["ci_runner"] == "Azure Pipelines"
    assert update_response.json()["dast_tool"] == "Aqua"

    delete_response = client.delete("/devsecops", params={"app_id": 1})
    assert delete_response.status_code == 204

    final_get = client.get("/devsecops", params={"app_id": 1})
    assert final_get.status_code == 404


def test_devsecops_rejects_app_id_and_is_deleted_fields() -> None:
    base_payload = {
        "app_id": 1,
        "git_repository_url": "https://github.com/org/repo-devsecops-immutability",
        "github_token": "ghp_secret",
        "ci_runner": "GitHub Actions",
        "pr_branch": "main",
        "code_coverage_tool": "Codecov",
        "code_coverage_org": "my-org",
        "code_coverage_token": "cover-secret",
        "sast_tool": "SonarQube",
        "sca_tool": "Snyk",
        "dast_tool": "OWASP ZAP",
        "container_image_scan_tool": "Trivy",
        "artifact_repository": "JFrog",
        "container_registry": "ghcr.io",
        "container_registry_owner": "my-org",
        "container_registry_pat": "cr-secret",
    }

    create_response = client.post("/devsecops", json=base_payload)
    assert create_response.status_code == 201

    app_id_response = client.put(
        "/devsecops",
        params={"app_id": 1},
        json={"app_id": 2},
    )
    assert app_id_response.status_code == 422

    is_deleted_response = client.put(
        "/devsecops",
        params={"app_id": 1},
        json={"is_deleted": "Y"},
    )
    assert is_deleted_response.status_code == 422

    cleanup_response = client.delete("/devsecops", params={"app_id": 1})
    assert cleanup_response.status_code == 204


def test_devsecops_rejects_unreachable_git_repository_url_on_update() -> None:
    payload = {
        "app_id": 1,
        "git_repository_url": "https://github.com/org/repo-devsecops-update",
        "github_token": "ghp_secret",
        "ci_runner": "GitHub Actions",
        "pr_branch": "main",
        "code_coverage_tool": "Codecov",
        "code_coverage_org": "my-org",
        "code_coverage_token": "cover-secret",
        "sast_tool": "SonarQube",
        "sca_tool": "Snyk",
        "dast_tool": "OWASP ZAP",
        "container_image_scan_tool": "Trivy",
        "artifact_repository": "JFrog",
        "container_registry": "ghcr.io",
        "container_registry_owner": "my-org",
        "container_registry_pat": "cr-secret",
    }

    create_response = client.post("/devsecops", json=payload)
    assert create_response.status_code == 201

    with patch(
        "repo_service.crud._assert_git_repository_url_reachable",
        side_effect=HTTPException(status_code=404, detail="git_repository_url repo not found (HTTP 404), Please add a valid git repository url"),
    ):
        update_response = client.put(
            "/devsecops",
            params={"app_id": 1},
            json={"git_repository_url": "https://github.com/org/missing-devsecops"},
        )

    assert update_response.status_code == 404

    cleanup_response = client.delete("/devsecops", params={"app_id": 1})
    assert cleanup_response.status_code == 204


def test_devsecops_reuses_soft_deleted_app_id() -> None:
    app_id = 1
    payload = {
        "app_id": app_id,
        "git_repository_url": "https://github.com/org/repo-devsecops-soft-delete",
        "github_token": "ghp_secret",
        "ci_runner": "GitHub Actions",
        "pr_branch": "main",
        "code_coverage_tool": "Codecov",
        "code_coverage_org": "my-org",
        "code_coverage_token": "cover-secret",
        "sast_tool": "SonarQube",
        "sca_tool": "Snyk",
        "dast_tool": "OWASP ZAP",
        "container_image_scan_tool": "Trivy",
        "artifact_repository": "JFrog",
        "container_registry": "ghcr.io",
        "container_registry_owner": "my-org",
        "container_registry_pat": "cr-secret",
    }

    first_create = client.post("/devsecops", json=payload)
    assert first_create.status_code == 201

    delete_response = client.delete("/devsecops", params={"app_id": app_id})
    assert delete_response.status_code == 204

    second_create = client.post("/devsecops", json=payload)
    assert second_create.status_code == 201
    assert second_create.json()["app_id"] == app_id

    cleanup_response = client.delete("/devsecops", params={"app_id": app_id})
    assert cleanup_response.status_code == 204


def test_devsecops_rejects_unreachable_git_repository_url() -> None:
    with patch(
        "repo_service.crud._assert_git_repository_url_reachable",
        side_effect=HTTPException(status_code=404, detail="git_repository_url repo not found (HTTP 404), Please add a valid git repository url"),
    ):
        create_response = client.post(
            "/devsecops",
            json={
                "app_id": 1,
                "git_repository_url": "https://github.com/org/missing-repo",
                "github_token": "ghp_secret",
                "ci_runner": "GitHub Actions",
                "pr_branch": "main",
                "code_coverage_tool": "Codecov",
                "code_coverage_org": "my-org",
                "code_coverage_token": "cover-secret",
                "sast_tool": "SonarQube",
                "sca_tool": "Snyk",
                "dast_tool": "OWASP ZAP",
                "container_image_scan_tool": "Trivy",
                "artifact_repository": "JFrog",
                "container_registry": "ghcr.io",
                "container_registry_owner": "my-org",
                "container_registry_pat": "cr-secret",
            },
        )

    assert create_response.status_code == 404
