from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException

from app.schemas import Application, Job
from app.storage.json_store import JsonStore


def track_application(store: JsonStore, job: Job) -> tuple[Application, bool]:
    rows = store.read("applications.json", [])
    existing = next((row for row in rows if row["job_id"] == job.id), None)
    if existing:
        return Application(**existing), False
    item = Application(id=str(uuid4()), job_id=job.id, job_title=job.title, company=job.company,
                       status="To submit", tracked_at=datetime.now(timezone.utc), applied_at=None,
                       source_url=str(job.apply_url or job.source_url))
    rows.insert(0, item.model_dump(mode="json"))
    store.write("applications.json", rows)
    return item, True


def mark_application_applied(store: JsonStore, job_id: str) -> tuple[Application | None, bool]:
    rows = store.read("applications.json", [])
    for row in rows:
        if row.get("job_id") != job_id:
            continue
        changed = row.get("status") != "Applied" or not row.get("applied_at")
        row["status"] = "Applied"
        if not row.get("applied_at"):
            row["applied_at"] = datetime.now(timezone.utc).isoformat()
        if changed:
            store.write("applications.json", rows)
        return Application(**row), changed
    return None, False


def update_application_status(store: JsonStore, application_id: str, status: str) -> Application | None:
    """Update tracker status and keep applied_at consistent with submission."""
    rows = store.read("applications.json", [])
    for row in rows:
        if row.get("id") != application_id:
            continue
        row["status"] = status
        if status == "To submit":
            row["applied_at"] = None
        elif status == "Applied" and not row.get("applied_at"):
            row["applied_at"] = datetime.now(timezone.utc).isoformat()
        store.write("applications.json", rows)
        return Application(**row)
    return None
