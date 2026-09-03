"""CRUD operations for QA_Automation and DevSecOps."""
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from cryptography.fernet import InvalidToken
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .cache import get_cached_qa_automation, invalidate_github_url
from .config import get_settings
from .models import APP, DevSecOps, QA_Automation
from .schemas import DevSecOpsCreate, DevSecOpsUpdate, QA_AutomationCreate, QA_AutomationUpdate
from .security import decrypt_token, encrypt_token, mask_token


UNAVAILABLE_TOKEN_MASK = "***unavailable***"


def _get_validation_token(url: str, github_token: str | None) -> str | None:
    if "github.com" not in url.lower():
        return None

    if github_token and github_token.strip():
        return github_token.strip()

    fallback = get_settings().github_validation_token.strip()
    return fallback or None


def _assert_url_reachable(url: str, field_name: str, github_token: str | None = None) -> None:
    if not get_settings().strict_repo_url_validation:
        return

    headers = {
        "User-Agent": "repo_service/0.1",
        "Accept": "*/*",
    }
    validation_token = _get_validation_token(url, github_token)
    if validation_token is not None:
        headers["Authorization"] = f"Bearer {validation_token}"

    request = Request(
        url,
        headers=headers,
        method="GET",
    )
    try:
        with urlopen(request, timeout=5):
            return
    except HTTPError as exc:
        if 300 <= exc.code < 400:
            return
        if exc.code == 404:
            raise HTTPException(
                status_code=exc.code,
                detail=f"{field_name} repo not found (HTTP 404), Please add a valid {field_name.replace('_', ' ')}",
            ) from exc
        raise HTTPException(
            status_code=exc.code,
            detail=f"{field_name} is not reachable (HTTP {exc.code})",
        ) from exc
    except URLError as exc:
        raise HTTPException(status_code=422, detail=f"{field_name} is not reachable: {exc.reason}") from exc


def _assert_github_url_reachable(github_url: str, github_token: str | None = None) -> None:
    _assert_url_reachable(github_url, "github_url", github_token)


def _assert_git_repository_url_reachable(git_repository_url: str, github_token: str | None = None) -> None:
    _assert_url_reachable(git_repository_url, "git_repository_url", github_token)


def _get_canonical_qa_app_id(db: Session) -> int | None:
    existing_app_ids = db.execute(select(QA_Automation.app_id).distinct()).scalars().all()
    if not existing_app_ids:
        return None

    unique_app_ids = set(existing_app_ids)
    if len(unique_app_ids) > 1:
        raise HTTPException(
            status_code=409,
            detail="Existing QA_Automation rows use multiple app_id values; normalize the table before creating new rows",
        )

    return next(iter(unique_app_ids))


def _encrypt_access_token_or_raise(raw_token: str) -> str:
    try:
        return encrypt_token(raw_token)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _decrypt_access_token_or_raise(encrypted_token: str) -> str:
    try:
        return decrypt_token(encrypted_token)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except InvalidToken as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to decrypt access token with ACCESS_TOKEN_ENCRYPTION_KEY. "
                "Verify the key matches the one used when records were created."
            ),
        ) from exc


def _masked_token_for_response(encrypted_token: str) -> str:
    try:
        decrypted = _decrypt_access_token_or_raise(encrypted_token)
    except HTTPException as exc:
        if exc.detail == (
            "Unable to decrypt access token with ACCESS_TOKEN_ENCRYPTION_KEY. "
            "Verify the key matches the one used when records were created."
        ):
            return UNAVAILABLE_TOKEN_MASK
        raise
    return mask_token(decrypted)


def _to_response_payload(row_data: dict) -> dict:
    return {
        "id": row_data["id"],
        "app_id": row_data["app_id"],
        "github_url": row_data["github_url"],
        "jira_connection_id": row_data["jira_connection_id"],
        "jira_base_url": row_data["jira_base_url"],
        "jira_auth_type": row_data["jira_auth_type"],
        "jira_credential_ref": row_data["jira_credential_ref"],
        "jira_api_version": row_data["jira_api_version"],
        "jira_project_key": row_data["jira_project_key"],
        "jira_board_id": row_data["jira_board_id"],
        "jira_active": row_data.get("jira_active", "Y"),
        "is_deleted": row_data["is_deleted"],
        "delete_date": row_data["delete_date"],
        "access_token_masked": _masked_token_for_response(row_data["access_token"]),
    }


def create_qa_automation(db: Session, payload: QA_AutomationCreate) -> dict:
    github_url = str(payload.github_url)
    _assert_github_url_reachable(github_url, payload.access_token)

    canonical_app_id = _get_canonical_qa_app_id(db)
    if canonical_app_id is not None and payload.app_id != canonical_app_id:
        raise HTTPException(
            status_code=409,
            detail=f"app_id must match existing QA_Automation records (expected {canonical_app_id})",
        )

    app = db.get(APP, payload.app_id)
    if app is None:
        raise HTTPException(status_code=404, detail="APP record not found")

    existing_jira_connection = db.execute(
        select(QA_Automation).where(QA_Automation.jira_connection_id == payload.jira_connection_id)
    ).scalar_one_or_none()
    if existing_jira_connection is not None:
        if existing_jira_connection.is_deleted == "N":
            raise HTTPException(status_code=409, detail="jira_connection_id already exists")
        db.delete(existing_jira_connection)
        db.flush()

    existing_row = db.execute(
        select(QA_Automation).where(QA_Automation.github_url == github_url)
    ).scalar_one_or_none()
    if existing_row is not None:
        if existing_row.is_deleted == "N":
            raise HTTPException(status_code=409, detail="github_url already exists")
        db.delete(existing_row)
        db.flush()

    row = QA_Automation(
        app_id=payload.app_id,
        github_url=github_url,
        access_token=_encrypt_access_token_or_raise(payload.access_token),
        jira_connection_id=payload.jira_connection_id,
        jira_base_url=str(payload.jira_base_url),
        jira_auth_type=payload.jira_auth_type,
        jira_credential_ref=payload.jira_credential_ref,
        jira_api_version=payload.jira_api_version,
        jira_project_key=payload.jira_project_key,
        jira_board_id=payload.jira_board_id,
        jira_active=payload.jira_active,
        is_deleted="N",
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="github_url or jira_connection_id already exists") from exc

    db.refresh(row)
    invalidate_github_url(row.github_url)

    return {
        "id": row.id,
        "app_id": row.app_id,
        "github_url": row.github_url,
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
        "access_token_masked": mask_token(payload.access_token),
    }


def get_qa_automation_by_github_url(github_url: str) -> dict:
    row_data = get_cached_qa_automation(github_url)
    if row_data is None:
        raise HTTPException(status_code=404, detail="Non-deleted record not found for github_url")
    return _to_response_payload(row_data)


def update_qa_automation(db: Session, github_url: str, payload: QA_AutomationUpdate) -> dict:
    row = db.execute(
        select(QA_Automation).where(
            QA_Automation.github_url == github_url,
            QA_Automation.is_deleted == "N",
        )
    ).scalar_one_or_none()

    if row is None:
        raise HTTPException(status_code=404, detail="Non-deleted record not found for github_url")

    original_github_url = row.github_url

    if payload.new_github_url is not None:
        renamed_github_url = str(payload.new_github_url)
        if renamed_github_url != row.github_url:
            _assert_github_url_reachable(renamed_github_url, payload.access_token)
            existing_row = db.execute(
                select(QA_Automation).where(
                    QA_Automation.github_url == renamed_github_url,
                    QA_Automation.id != row.id,
                )
            ).scalar_one_or_none()
            if existing_row is not None:
                if existing_row.is_deleted == "N":
                    raise HTTPException(status_code=409, detail="github_url already exists")
                db.delete(existing_row)
                db.flush()
            row.github_url = renamed_github_url

    if payload.access_token is not None:
        row.access_token = _encrypt_access_token_or_raise(payload.access_token)

    if payload.jira_connection_id is not None:
        row.jira_connection_id = payload.jira_connection_id

    if payload.jira_base_url is not None:
        row.jira_base_url = str(payload.jira_base_url)

    if payload.jira_auth_type is not None:
        row.jira_auth_type = payload.jira_auth_type

    if payload.jira_credential_ref is not None:
        row.jira_credential_ref = payload.jira_credential_ref

    if payload.jira_api_version is not None:
        row.jira_api_version = payload.jira_api_version

    if payload.jira_project_key is not None:
        row.jira_project_key = payload.jira_project_key

    if "jira_board_id" in payload.model_fields_set:
        row.jira_board_id = payload.jira_board_id

    if payload.jira_active is not None:
        row.jira_active = payload.jira_active

    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if payload.new_github_url is not None:
            raise HTTPException(status_code=409, detail="github_url already exists") from exc
        raise
    db.refresh(row)
    invalidate_github_url(original_github_url)
    if row.github_url != original_github_url:
        invalidate_github_url(row.github_url)

    if payload.access_token is not None:
        masked_token = mask_token(payload.access_token)
    else:
        masked_token = _masked_token_for_response(row.access_token)

    return {
        "id": row.id,
        "app_id": row.app_id,
        "github_url": row.github_url,
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
        "access_token_masked": masked_token,
    }


def soft_delete_qa_automation(db: Session, github_url: str) -> None:
    row = db.execute(
        select(QA_Automation).where(
            QA_Automation.github_url == github_url,
            QA_Automation.is_deleted == "N",
        )
    ).scalar_one_or_none()

    if row is None:
        raise HTTPException(status_code=404, detail="Non-deleted record not found for github_url")

    row.is_deleted = "Y"
    row.delete_date = datetime.now(timezone.utc)
    db.add(row)
    db.commit()
    invalidate_github_url(github_url)


def _devsecops_to_response(row: DevSecOps) -> dict:
    return {
        "id": row.id,
        "app_id": row.app_id,
        "git_repository_url": row.git_repository_url,
        "github_token": row.github_token,
        "ci_runner": row.ci_runner,
        "pr_branch": row.pr_branch,
        "code_coverage_tool": row.code_coverage_tool,
        "code_coverage_org": row.code_coverage_org,
        "code_coverage_token": row.code_coverage_token,
        "sast_tool": row.sast_tool,
        "sca_tool": row.sca_tool,
        "dast_tool": row.dast_tool,
        "container_image_scan_tool": row.container_image_scan_tool,
        "artifact_repository": row.artifact_repository,
        "container_registry": row.container_registry,
        "container_registry_owner": row.container_registry_owner,
        "container_registry_pat": row.container_registry_pat,
        "is_deleted": row.is_deleted,
        "delete_date": row.delete_date,
    }


def create_devsecops(db: Session, payload: DevSecOpsCreate) -> dict:
    if db.get(APP, payload.app_id) is None:
        raise HTTPException(status_code=404, detail="APP record not found")

    _assert_git_repository_url_reachable(payload.git_repository_url, payload.github_token)

    existing = db.execute(
        select(DevSecOps).where(DevSecOps.app_id == payload.app_id)
    ).scalar_one_or_none()
    if existing is not None:
        if existing.is_deleted == "N":
            raise HTTPException(status_code=409, detail="DevSecOps record already exists for app_id")
        db.delete(existing)
        db.flush()

    row = DevSecOps(
        app_id=payload.app_id,
        git_repository_url=payload.git_repository_url,
        github_token=payload.github_token,
        ci_runner=payload.ci_runner,
        pr_branch=payload.pr_branch,
        code_coverage_tool=payload.code_coverage_tool,
        code_coverage_org=payload.code_coverage_org,
        code_coverage_token=payload.code_coverage_token,
        sast_tool=payload.sast_tool,
        sca_tool=payload.sca_tool,
        dast_tool=payload.dast_tool,
        container_image_scan_tool=payload.container_image_scan_tool,
        artifact_repository=payload.artifact_repository,
        container_registry=payload.container_registry,
        container_registry_owner=payload.container_registry_owner,
        container_registry_pat=payload.container_registry_pat,
        is_deleted="N",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _devsecops_to_response(row)


def get_devsecops_by_app_id(db: Session, app_id: int) -> dict:
    row = db.execute(
        select(DevSecOps).where(
            DevSecOps.app_id == app_id,
            DevSecOps.is_deleted == "N",
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Active DevSecOps record not found for app_id")
    return _devsecops_to_response(row)


def update_devsecops(db: Session, app_id: int, payload: DevSecOpsUpdate) -> dict:
    row = db.execute(
        select(DevSecOps).where(
            DevSecOps.app_id == app_id,
            DevSecOps.is_deleted == "N",
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Active DevSecOps record not found for app_id")

    if payload.git_repository_url is not None:
        _assert_git_repository_url_reachable(payload.git_repository_url, payload.github_token)

    for field_name in (
        "git_repository_url",
        "github_token",
        "ci_runner",
        "pr_branch",
        "code_coverage_tool",
        "code_coverage_org",
        "code_coverage_token",
        "sast_tool",
        "sca_tool",
        "dast_tool",
        "container_image_scan_tool",
        "artifact_repository",
        "container_registry",
        "container_registry_owner",
        "container_registry_pat",
    ):
        value = getattr(payload, field_name)
        if value is not None:
            setattr(row, field_name, value)

    db.add(row)
    db.commit()
    db.refresh(row)
    return _devsecops_to_response(row)


def soft_delete_devsecops(db: Session, app_id: int) -> None:
    row = db.execute(
        select(DevSecOps).where(
            DevSecOps.app_id == app_id,
            DevSecOps.is_deleted == "N",
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Active DevSecOps record not found for app_id")

    row.is_deleted = "Y"
    row.delete_date = datetime.now(timezone.utc)
    db.add(row)
    db.commit()
