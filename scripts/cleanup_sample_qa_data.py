"""Soft-delete QA_Automation sample rows by GitHub URL prefix."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

from sqlalchemy import select

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Soft-delete QA_Automation rows by generated URL prefix")
    parser.add_argument(
        "--prefix",
        type=str,
        default="acme-service-load",
        help="Repo suffix prefix used by seed script (default: acme-service-load)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show matching rows without applying soft delete",
    )
    return parser.parse_args()


def main() -> None:
    from repo_service.cache import invalidate_github_url
    from repo_service.database import SessionLocal
    from repo_service.models import QA_Automation

    args = _parse_args()
    normalized_prefix = args.prefix.strip().lower().replace(" ", "-")
    if not normalized_prefix:
        raise ValueError("--prefix cannot be empty")

    github_like_pattern = f"https://github.com/example/{normalized_prefix}-%"

    with SessionLocal() as db:
        rows = db.execute(
            select(QA_Automation).where(
                QA_Automation.github_url.like(github_like_pattern),
                QA_Automation.is_deleted == "N",
            )
        ).scalars().all()

        if not rows:
            print(f"No active rows matched prefix: {normalized_prefix}")
            return

        print(f"Matched {len(rows)} active rows for prefix: {normalized_prefix}")
        for row in rows:
            print(f" - {row.github_url}")

        if args.dry_run:
            print("Dry run only. No records updated.")
            return

        deleted_at = datetime.now(timezone.utc)
        for row in rows:
            row.is_deleted = "Y"
            row.delete_date = deleted_at
            invalidate_github_url(row.github_url)

        db.commit()
        print(f"Soft-deleted {len(rows)} rows.")


if __name__ == "__main__":
    main()
