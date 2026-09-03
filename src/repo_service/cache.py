"""In-process LRU caching for github_url lookup."""
from functools import lru_cache
from threading import Lock

from sqlalchemy import select

from .config import get_settings
from .database import SessionLocal
from .models import QA_Automation

_cache_key_version: dict[str, int] = {}
_cache_lock = Lock()


@lru_cache(maxsize=get_settings().cache_maxsize)
def _cached_fetch(github_url: str, version: int) -> dict | None:
    del version
    with SessionLocal() as db:
        row = db.execute(
            select(QA_Automation).where(
                QA_Automation.github_url == github_url,
                QA_Automation.is_deleted == "N",
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        return {
            "id": row.id,
            "app_id": row.app_id,
            "github_url": row.github_url,
            "access_token": row.access_token,
            "jira_connection_id": row.jira_connection_id,
            "jira_base_url": row.jira_base_url,
            "jira_auth_type": row.jira_auth_type,
            "jira_credential_ref": row.jira_credential_ref,
            "jira_api_version": row.jira_api_version,
            "jira_project_key": row.jira_project_key,
            "jira_board_id": row.jira_board_id,
            "jira_active": row.jira_active,
            "is_deleted": row.is_deleted,
            "delete_date": row.delete_date,
        }


def get_cached_qa_automation(github_url: str) -> dict | None:
    with _cache_lock:
        version = _cache_key_version.get(github_url, 0)
    return _cached_fetch(github_url, version)


def invalidate_github_url(github_url: str) -> None:
    with _cache_lock:
        _cache_key_version[github_url] = _cache_key_version.get(github_url, 0) + 1


def clear_all_cache() -> None:
    _cached_fetch.cache_clear()
