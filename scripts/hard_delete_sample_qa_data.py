"""Hard-delete QA_Automation sample rows by GitHub URL prefix (local DB only)."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from sqlalchemy import delete, select
from sqlalchemy.engine import make_url

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hard-delete QA_Automation rows by generated URL prefix")
    parser.add_argument(
        "--prefix",
        type=str,
        default="acme-service-load",
        help="Repo suffix prefix used by seed script (default: acme-service-load)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show matching rows without deleting records",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required for actual hard delete",
    )
    return parser.parse_args()


def _is_local_database(database_url: str) -> bool:
    url = make_url(database_url)
    backend = url.get_backend_name()
    if backend == "sqlite":
        return True

    host = (url.host or "").lower()
    return host in {"localhost", "127.0.0.1"}


def main() -> None:
    from repo_service.cache import invalidate_github_url
    from repo_service.config import get_settings
    from repo_service.database import SessionLocal
    from repo_service.models import QA_Automation

    args = _parse_args()
    normalized_prefix = args.prefix.strip().lower().replace(" ", "-")
    if not normalized_prefix:
        raise ValueError("--prefix cannot be empty")

    settings = get_settings()
    if not _is_local_database(settings.database_url):
        raise RuntimeError(
            "Hard delete is blocked: DATABASE_URL is not local (only sqlite/localhost/127.0.0.1 allowed)."
        )

    github_like_pattern = f"https://github.com/example/{normalized_prefix}-%"

    with SessionLocal() as db:
        rows = db.execute(
            select(QA_Automation.id, QA_Automation.github_url, QA_Automation.is_deleted).where(
                QA_Automation.github_url.like(github_like_pattern)
            )
        ).all()

        if not rows:
            print(f"No rows matched prefix: {normalized_prefix}")
            return

        print(f"Matched {len(rows)} rows for prefix: {normalized_prefix}")
        for row_id, github_url, is_deleted in rows:
            print(f" - id={row_id} deleted={is_deleted} url={github_url}")

        if args.dry_run:
            print("Dry run only. No records deleted.")
            return

        if not args.confirm:
            raise ValueError("Refusing to hard-delete without --confirm")

        ids = [row_id for row_id, _, _ in rows]
        urls = [github_url for _, github_url, _ in rows]

        db.execute(delete(QA_Automation).where(QA_Automation.id.in_(ids)))
        for github_url in urls:
            invalidate_github_url(github_url)

        db.commit()
        print(f"Hard-deleted {len(ids)} rows.")


if __name__ == "__main__":
    main()
