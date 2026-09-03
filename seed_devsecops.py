"""Seed example APP, QA_Automation, and DevSecOps rows for local testing."""

from __future__ import annotations

from sqlalchemy import select

from src.repo_service.database import Base, SessionLocal, engine
from src.repo_service.models import APP, DevSecOps, QA_Automation


def seed_example_data() -> None:
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        app = db.execute(select(APP).where(APP.app_name == "acme-service")).scalar_one_or_none()
        if app is None:
            app = APP(
                app_name="acme-service",
                app_description="Sample application used for pgAdmin validation of QA automation and DevSecOps rows.",
            )
            db.add(app)
            db.commit()
            db.refresh(app)
            print(f"Inserted APP seed row with app_id={app.app_id}")

        repo = db.execute(
            select(QA_Automation).where(QA_Automation.github_url == "https://github.com/example/acme-service")
        ).scalar_one_or_none()

        if repo is None:
            repo = QA_Automation(
                app_id=app.app_id,
                github_url="https://github.com/example/acme-service",
                access_token="example-token",
                jira_connection_id=9001,
                jira_base_url="https://example.atlassian.net",
                jira_auth_type="API_TOKEN",
                jira_credential_ref="secret/jira/default",
                jira_api_version=3,
                jira_project_key="ACME",
                jira_board_id=12,
                jira_active="Y",
                is_deleted="N",
            )
            db.add(repo)
            db.commit()
            db.refresh(repo)
            print(f"Inserted QA_Automation seed row with id={repo.id}")
        else:
            print(f"QA_Automation row already exists with id={repo.id}")

        row = db.execute(
            select(DevSecOps).where(
                DevSecOps.app_id == app.app_id,
                DevSecOps.is_deleted == "N",
            )
        ).scalar_one_or_none()

        if row is None:
            row = DevSecOps(
                app_id=app.app_id,
                git_repository_url="https://github.com/example/acme-service",
                github_token="ghp_example_token",
                ci_runner="GitHub Actions",
                pr_branch="main",
                code_coverage_tool="Codecov",
                code_coverage_org="acme",
                code_coverage_token="codecov_token",
                sast_tool="SonarQube",
                sca_tool="Snyk",
                dast_tool="OWASP ZAP",
                container_image_scan_tool="Trivy",
                artifact_repository="JFrog Artifactory",
                container_registry="ghcr.io",
                container_registry_owner="acme",
                container_registry_pat="ghcr_pat",
                is_deleted="N",
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            print(f"Inserted DevSecOps seed row with id={row.id}")
        else:
            print(f"DevSecOps row already exists with id={row.id}")

        print(
            "Seed data ready: "
            f"APP(app_id={app.app_id}), QA_Automation(id={repo.id}), DevSecOps(id={row.id})"
        )


if __name__ == "__main__":
    seed_example_data()
