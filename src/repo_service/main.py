"""FastAPI entry point for the QA_Automation service."""
import json
import logging
import time
from pathlib import Path

from fastapi import Depends, FastAPI, Query, status
from sqlalchemy.orm import Session

from .config import get_settings
from .crud import (
    create_devsecops,
    create_qa_automation,
    get_devsecops_by_app_id,
    get_qa_automation_by_github_url,
    soft_delete_devsecops,
    soft_delete_qa_automation,
    update_devsecops,
    update_qa_automation,
)
from .database import Base, engine, get_db
from .schemas import (
    DevSecOpsCreate,
    DevSecOpsResponse,
    DevSecOpsUpdate,
    HealthResponse,
    QA_AutomationCreate,
    QA_AutomationResponse,
    QA_AutomationUpdate,
)

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("repo_service.api")
logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
logger.propagate = False

log_dir = Path(__file__).resolve().parents[2] / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "api_requests.log"
if not any(isinstance(handler, logging.FileHandler) and Path(handler.baseFilename) == log_file for handler in logger.handlers):
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s"))
    logger.addHandler(file_handler)


def _summarize_payload(payload):
    if isinstance(payload, dict):
        summary = {key: value for key, value in payload.items()}
        for key in ("access_token", "github_token", "code_coverage_token", "container_registry_pat", "jira_credential_ref"):
            if key in summary and isinstance(summary[key], str):
                summary[key] = "***redacted***"
        return summary
    if isinstance(payload, list):
        return [_summarize_payload(item) for item in payload]
    if isinstance(payload, str):
        return payload[:200]
    return payload


app = FastAPI(
    title="qa_automation_service",
    description="CRUD service for QA_Automation with soft delete and in-process caching",
    version="0.1.0",
)


@app.middleware("http")
async def log_request_middleware(request, call_next):
    method = request.method
    path = request.url.path
    payload_summary = "-"

    if method in {"POST", "PUT", "PATCH"}:
        try:
            body = await request.body()
            if body:
                content_type = request.headers.get("content-type", "")
                if "application/json" in content_type:
                    try:
                        payload_summary = _summarize_payload(json.loads(body.decode("utf-8")))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        payload_summary = body[:200].decode("utf-8", errors="replace")
                else:
                    payload_summary = body[:200].decode("utf-8", errors="replace")
        except Exception:
            payload_summary = "<unreadable>"

    logger.info("API request start: %s %s payload=%s", method, path, payload_summary)
    start = time.perf_counter()
    response = await call_next(request)
    latency_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info("API request complete: %s %s status=%s latency_ms=%.2f payload=%s", method, path, response.status_code, latency_ms, payload_summary)
    return response


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.service_name)


@app.get("/readyz", response_model=HealthResponse)
def readyz() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.service_name)


@app.post("/qa-automation", response_model=QA_AutomationResponse, status_code=status.HTTP_201_CREATED)
def create_qa_automation_endpoint(
    payload: QA_AutomationCreate,
    db: Session = Depends(get_db),
) -> QA_AutomationResponse:
    return QA_AutomationResponse(**create_qa_automation(db, payload))


@app.get("/qa-automation", response_model=QA_AutomationResponse)
def get_qa_automation(
    github_url: str = Query(..., description="Unique github_url key"),
) -> QA_AutomationResponse:
    return QA_AutomationResponse(**get_qa_automation_by_github_url(github_url))


@app.put("/qa-automation", response_model=QA_AutomationResponse)
def update_qa_automation_endpoint(
    payload: QA_AutomationUpdate,
    github_url: str = Query(
        ...,
        description=(
            "Unique github_url selector for the row to update. This value must be a valid reachable URL "
            "and is not updated by PUT. If the repo does not exist, validation returns: "
            "github_url repo not found (HTTP 404), Please add a valid github url."
        ),
        examples=["https://github.com/example/acme-service"],
    ),
    db: Session = Depends(get_db),
) -> QA_AutomationResponse:
    return QA_AutomationResponse(**update_qa_automation(db, github_url, payload))


@app.delete("/qa-automation", status_code=status.HTTP_204_NO_CONTENT)
def delete_qa_automation(
    github_url: str = Query(
        ...,
        description="Unique github_url selector for soft delete (sets is_deleted=Y).",
        examples=["https://github.com/example/acme-service"],
    ),
    db: Session = Depends(get_db),
) -> None:
    soft_delete_qa_automation(db, github_url)


@app.post("/devsecops", response_model=DevSecOpsResponse, status_code=status.HTTP_201_CREATED)
def create_devsecops_endpoint(
    payload: DevSecOpsCreate,
    db: Session = Depends(get_db),
) -> DevSecOpsResponse:
    return DevSecOpsResponse(**create_devsecops(db, payload))


@app.get("/devsecops", response_model=DevSecOpsResponse)
def get_devsecops(
    app_id: int = Query(..., description="APP.app_id reference"),
    db: Session = Depends(get_db),
) -> DevSecOpsResponse:
    return DevSecOpsResponse(**get_devsecops_by_app_id(db, app_id))


@app.put("/devsecops", response_model=DevSecOpsResponse)
def update_devsecops_endpoint(
    payload: DevSecOpsUpdate,
    app_id: int = Query(..., description="APP.app_id reference"),
    db: Session = Depends(get_db),
) -> DevSecOpsResponse:
    return DevSecOpsResponse(**update_devsecops(db, app_id, payload))


@app.delete("/devsecops", status_code=status.HTTP_204_NO_CONTENT)
def delete_devsecops(
    app_id: int = Query(..., description="APP.app_id reference"),
    db: Session = Depends(get_db),
) -> None:
    soft_delete_devsecops(db, app_id)


def main() -> None:
    import uvicorn

    uvicorn.run("repo_service.main:app", host="0.0.0.0", port=8090, reload=False)


if __name__ == "__main__":
    main()
