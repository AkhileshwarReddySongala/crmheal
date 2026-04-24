from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    queued = "QUEUED"
    searching_web = "SEARCHING_WEB"
    parsing_dom = "PARSING_DOM"
    needs_verification = "NEEDS_VERIFICATION"
    calling_lead = "CALLING_LEAD"
    call_pending = "CALL_PENDING"
    call_timeout = "CALL_TIMEOUT"
    verified = "VERIFIED"
    completed = "COMPLETED"
    failed = "FAILED"


class CRMLeadRow(BaseModel):
    id: int
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    company: str = ""
    title: str = ""
    industry: str = ""
    city: str = ""
    state: str = ""
    last_contacted: str = ""
    status: str = ""


class JobState(BaseModel):
    job_id: str
    batch_id: str
    record_id: int
    status: JobStatus = JobStatus.queued
    progress: int = 0
    original: CRMLeadRow
    enriched: dict[str, Any] = Field(default_factory=dict)
    confidence: int = 0
    source: str = "queued"
    mode: str = "mock"
    vapi_call_id: str | None = None
    error: str | None = None


class AuditEntry(BaseModel):
    batch_id: str
    job_id: str | None = None
    record_id: int | None = None
    agent: str
    action: str
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    confidence: int | None = None
    source: str | None = None
    mode: str = "mock"
    timestamp: str


class VapiStructuredData(BaseModel):
    phone_verified: bool = False
    title_confirmed: bool = False
    current_company: str | None = None
    notes: str | None = None
