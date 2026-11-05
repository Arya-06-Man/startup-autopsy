from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4
from pydantic import BaseModel, Field


def now():
    return datetime.now(timezone.utc).isoformat()


class Evidence(BaseModel):
    id: str = Field(default_factory=lambda: 'E-' + uuid4().hex[:12])
    company_id: str
    category: str
    fact: str
    value: Any
    provider: str = 'Crustdata'
    source: str
    event_date: str | None = None
    observation_date: str | None = None
    provider_updated_at: str | None = None
    data_mode: str = 'Unknown / legacy record'
    publication_date: str | None = None
    retrieved_at: str = Field(default_factory=now)
    status: Literal['single-source observation', 'corroborated observation', 'hypothesis', 'disputed/conflicting', 'unknown'] = 'single-source observation'
    corroborating_ids: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    limitations: str = 'Provider observation; not independently verified.'


class Signal(BaseModel):
    category: str
    change_pct: float | None = None
    severity: float = Field(ge=0, le=100)
    evidence_ids: list[str]
    explanation: str
    alternatives: list[str] = Field(default_factory=list)


class Assessment(BaseModel):
    score: float | None = None
    coverage: float = 0
    label: str = 'Insufficient evidence'
    signals: list[Signal] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)


class Dossier(BaseModel):
    query: str
    company_id: str = ''
    name: str = ''
    domain: str = ''
    metadata: dict = Field(default_factory=dict)
    evidence: list[Evidence] = Field(default_factory=list)
    assessment: Assessment = Field(default_factory=Assessment)
    errors: list[str] = Field(default_factory=list)
    trace: list[dict] = Field(default_factory=list)
    advice: dict = Field(default_factory=dict)
    status: str = 'pending'


class Run(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    created_at: str = Field(default_factory=now)
    mode: str = 'LIVE DATA'
    status: str = 'running'
    companies: list[Dossier] = Field(default_factory=list)
    usage: dict = Field(default_factory=dict)
