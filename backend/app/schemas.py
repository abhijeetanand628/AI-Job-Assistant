from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


class Profile(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    designation: str = ""
    title: str = ""
    location: str = ""
    preferred_location: str = ""
    preferred_workplace: Literal["Any", "Remote", "Hybrid", "On-site"] = "Any"
    skills: list[str] = Field(default_factory=list)
    experience: float = 0
    education: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)


class Job(BaseModel):
    id: str
    title: str
    company: str
    location: str
    experience_required: str = "Not specified"
    skills: list[str] = Field(default_factory=list)
    description: str = ""
    source_url: HttpUrl | str
    apply_url: HttpUrl | str | None = None
    workplace_type: str = "unspecified"
    source: str = "unknown"
    posted_at: str | None = None


class MatchedJob(Job):
    match: int = 0
    why: str = ""
    fit_tier: Literal["strong", "possible", "explore"] = "explore"


class ResumeMetadata(BaseModel):
    id: str
    file_name: str
    size: int
    content_type: str
    uploaded_at: datetime
    extracted: Profile


class ApplicationCreate(BaseModel):
    job_id: str


class ApplicationStatusUpdate(BaseModel):
    status: Literal["To submit", "Applied", "Interview", "Rejected", "Offer"]


class Application(BaseModel):
    id: str
    job_id: str
    job_title: str
    company: str
    status: str
    tracked_at: datetime
    applied_at: datetime | None = None
    source_url: str

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_tracking_date(cls, values):
        if isinstance(values, dict) and "tracked_at" not in values:
            values = values.copy()
            values["tracked_at"] = values.get("applied_at") or datetime.now(timezone.utc)
            # Older builds stored the tracking date in `applied_at`, even if
            # the user had not actually submitted an employer application.
            values["applied_at"] = None
        return values


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list)
    job_ids: list[str] = Field(default_factory=list, max_length=500)


class ChatResponse(BaseModel):
    reply: str
    jobs: list[MatchedJob] = Field(default_factory=list)
    applications: list[Application] = Field(default_factory=list)
    action: str | None = None
