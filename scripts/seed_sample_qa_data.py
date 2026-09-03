"""Seed sample QA_Automation rows for local testing."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from sqlalchemy import select

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

DEFAULT_COUNT = 2
JIRA_CONNECTION_BASE = 990000
JIRA_BOARD_BASE = 800


def _get_or_create_app_id() -> int:
    from repo_service.database import SessionLocal
    from repo_service.models import APP

    with SessionLocal() as db:
        app = db.execute(select(APP).order_by(APP.app_id.asc())).scalars().first()
        if app is None:
            app = APP(app_name="sample-app", app_description="Sample app for QA automation testing")
            db.add(app)
            db.commit()
            db.refresh(app)
        return app.app_id


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed QA_Automation rows for load testing")
    parser.add_argument(
        "-n",
        "--count",
        type=int,
        default=DEFAULT_COUNT,
        help="Number of sample rows to create/update (default: 2)",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default="acme-service-load",
        help="GitHub repo suffix prefix for generated rows",
    )
    return parser.parse_args()


def _project_key(index: int) -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    value = index
    chars: list[str] = []
    while True:
        value, remainder = divmod(value, len(alphabet))
        chars.append(alphabet[remainder])
        if value == 0:
            break
        value -= 1
    return "QA" + "".join(reversed(chars))


def _build_sample_rows(count: int, prefix: str) -> list[dict]:
    rows: list[dict] = []
    normalized_prefix = prefix.strip().lower().replace(" ", "-")
    for i in range(1, count + 1):
        suffix = f"{i:04d}"
        rows.append(
            {
                "github_url": f"https://github.com/example/{normalized_prefix}-{suffix}",
                "access_token": f"sample-token-{suffix}",
                "jira_connection_id": JIRA_CONNECTION_BASE + i,
                "jira_base_url": "https://mycompany.atlassian.net",
                "jira_auth_type": "API_TOKEN",
                "jira_credential_ref": f"secret/jira/{normalized_prefix}-{suffix}",
                "jira_api_version": 3,
                "jira_project_key": _project_key(i),
                "jira_board_id": JIRA_BOARD_BASE + i,
                "jira_active": "Y",
            }
        )
    return rows


def main() -> None:
    from repo_service.database import SessionLocal
    from repo_service.models import QA_Automation
    from repo_service.security import encrypt_token

    args = _parse_args()
    if args.count <= 0:
        raise ValueError("--count must be a positive integer")

    sample_rows = _build_sample_rows(args.count, args.prefix)
    app_id = _get_or_create_app_id()
    inserted = 0
    updated = 0

    with SessionLocal() as db:
        for row in sample_rows:
            existing = db.execute(
                select(QA_Automation).where(QA_Automation.github_url == row["github_url"])
            ).scalar_one_or_none()

            encrypted_token = encrypt_token(row["access_token"])

            if existing is None:
                existing = QA_Automation(
                    app_id=app_id,
                    github_url=row["github_url"],
                    access_token=encrypted_token,
                    jira_connection_id=row["jira_connection_id"],
                    jira_base_url=row["jira_base_url"],
                    jira_auth_type=row["jira_auth_type"],
                    jira_credential_ref=row["jira_credential_ref"],
                    jira_api_version=row["jira_api_version"],
                    jira_project_key=row["jira_project_key"],
                    jira_board_id=row["jira_board_id"],
                    jira_active=row["jira_active"],
                    is_deleted="N",
                    delete_date=None,
                )
                db.add(existing)
                inserted += 1
                print(f"Inserted: {row['github_url']}")
            else:
                existing.app_id = app_id
                existing.access_token = encrypted_token
                existing.jira_connection_id = row["jira_connection_id"]
                existing.jira_base_url = row["jira_base_url"]
                existing.jira_auth_type = row["jira_auth_type"]
                existing.jira_credential_ref = row["jira_credential_ref"]
                existing.jira_api_version = row["jira_api_version"]
                existing.jira_project_key = row["jira_project_key"]
                existing.jira_board_id = row["jira_board_id"]
                existing.jira_active = row["jira_active"]
                existing.is_deleted = "N"
                existing.delete_date = None
                updated += 1
                print(f"Updated/Reactivated: {row['github_url']}")

        db.commit()

    print(f"Sample QA data is ready. inserted={inserted}, updated={updated}, total={len(sample_rows)}")


if __name__ == "__main__":
    main()
