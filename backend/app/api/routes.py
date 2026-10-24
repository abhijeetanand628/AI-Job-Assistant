from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from app.agents.application_agent import track_application, update_application_status
from app.agents.job_matcher import rank_jobs
from app.agents.orchestrator import answer_chat
from app import settings
from app.schemas import Application, ApplicationCreate, ApplicationStatusUpdate, ChatRequest, ChatResponse, Job, Profile, ResumeMetadata
from app.services.resume_parser import basic_profile, extract_text

router = APIRouter(prefix="/api")
DEFAULT_PROFILE = Profile()


def store(request: Request):
    return request.app.state.store


@router.get("/health")
def health(request: Request):
    return {"status": "ok", "gemini_configured": bool(settings.GEMINI_API_KEY), "jobs": len(store(request).read("jobs.json", []))}


@router.get("/profile", response_model=Profile)
def get_profile(request: Request):
    raw = store(request).read("profile.json", None)
    return Profile(**raw) if raw else DEFAULT_PROFILE


@router.put("/profile", response_model=Profile)
def update_profile(profile: Profile, request: Request):
    store(request).write("profile.json", profile.model_dump(mode="json"))
    return profile


@router.get("/jobs", response_model=list[Job])
def get_jobs(request: Request, q: str = "", location: str = "", workplace: str = "", limit: int = 250):
    rows = [Job(**row) for row in store(request).read("jobs.json", [])]
    if q:
        terms = q.lower().split()
        rows = [job for job in rows if all(term in f"{job.title} {job.company} {' '.join(job.skills)} {job.description}".lower() for term in terms)]
    if location:
        rows = [job for job in rows if location.lower() in job.location.lower()]
    if workplace:
        rows = [job for job in rows if workplace.lower() in job.workplace_type.lower()]
    return rows[:max(1, min(limit, 500))]


@router.get("/jobs/matches")
def job_matches(request: Request, q: str = "", limit: int = 250):
    jobs = [Job(**row) for row in store(request).read("jobs.json", [])]
    return rank_jobs(jobs, get_profile(request), q, limit)


@router.get("/applications", response_model=list[Application])
def get_applications(request: Request):
    return [Application(**item) for item in store(request).read("applications.json", [])]


@router.post("/applications", response_model=Application)
def create_application(payload: ApplicationCreate, request: Request):
    jobs = store(request).read("jobs.json", [])
    row = next((row for row in jobs if row["id"] == payload.job_id), None)
    if not row:
        raise HTTPException(404, "Job not found in the current catalogue.")
    item, _ = track_application(store(request), Job(**row))
    return item


@router.patch("/applications/{application_id}", response_model=Application)
def update_application(application_id: str, payload: ApplicationStatusUpdate, request: Request):
    db = store(request)
    rows = db.read("applications.json", [])
    # Migrate old tracker records before validating the returned model.
    for row in rows:
        if "tracked_at" not in row:
            row["tracked_at"] = row.get("applied_at") or datetime.now(timezone.utc).isoformat()
            row["applied_at"] = None
    db.write("applications.json", rows)
    updated = update_application_status(db, application_id, payload.status)
    if updated is None:
        raise HTTPException(404, "Application not found.")
    return updated


@router.delete("/applications/{application_id}", status_code=204)
def delete_application(application_id: str, request: Request):
    db = store(request)
    rows = db.read("applications.json", [])
    remaining = [row for row in rows if row["id"] != application_id]
    if len(remaining) == len(rows):
        raise HTTPException(404, "Application not found.")
    db.write("applications.json", remaining)


@router.get("/resumes/latest")
def latest_resume(request: Request):
    raw = store(request).read("resume.json", None)
    return {key: value for key, value in raw.items() if key != "stored_name"} if raw else None


@router.get("/resumes/latest/file")
def resume_file(request: Request):
    raw = store(request).read("resume.json", None)
    if not raw:
        raise HTTPException(404, "No resume has been uploaded.")
    path = settings.RESUME_DIR / raw["stored_name"]
    if not path.is_file():
        raise HTTPException(404, "The resume file is missing.")
    return FileResponse(path, filename=raw["file_name"])


@router.post("/resumes", response_model=ResumeMetadata)
async def upload_resume(request: Request, file: UploadFile = File(...), consent_gemini: bool = Form(False)):
    data = await file.read(settings.MAX_RESUME_BYTES + 1)
    if len(data) > settings.MAX_RESUME_BYTES:
        raise HTTPException(413, "Resume exceeds the 10 MB limit.")
    name = file.filename or "resume"
    if not name.lower().endswith((".pdf", ".docx")):
        raise HTTPException(415, "Upload a PDF or DOCX resume.")
    try:
        text = extract_text(name, data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    extracted = basic_profile(text)
    metadata = {"id": str(uuid.uuid4()), "file_name": name, "size": len(data), "content_type": file.content_type or "application/octet-stream", "uploaded_at": datetime.now(timezone.utc).isoformat(), "extracted": extracted}
    settings.RESUME_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = metadata["id"] + (".pdf" if name.lower().endswith(".pdf") else ".docx")
    (settings.RESUME_DIR / stored_name).write_bytes(data)
    metadata["stored_name"] = stored_name
    store(request).write("resume.json", metadata)
    # Resume-derived fields always come from the newly uploaded file. Preserve
    # the target role and search preferences because those are user choices.
    current = get_profile(request).model_dump()
    for key in ("name", "email", "phone", "designation", "skills", "experience", "education", "projects"):
        current[key] = extracted.get(key, [] if key in ("skills", "education", "projects") else "")
    store(request).write("profile.json", Profile(**current).model_dump(mode="json"))
    return ResumeMetadata(**{k: v for k, v in metadata.items() if k != "stored_name"})


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request):
    reply, jobs, applications, action = answer_chat(payload, get_profile(request), store(request))
    return ChatResponse(reply=reply, jobs=jobs, applications=[Application(**item) for item in applications], action=action)
