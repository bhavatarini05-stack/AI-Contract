"""API response/request models."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserOut(ORM):
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: datetime | None = None


class JobOut(ORM):
    id: int
    contract_id: int
    stage: str
    progress: int
    status: str
    error: str | None = None
    created_at: datetime
    finished_at: datetime | None = None


class ClauseOut(ORM):
    id: int
    type: str
    heading: str | None
    text: str
    page: int | None
    confidence: float
    source: str
    needs_review: bool


class TermOut(ORM):
    id: int
    key: str
    label: str
    display: str
    raw_text: str | None
    normalized_value: dict | None
    page: int | None


class RiskFlagOut(ORM):
    id: int
    clause_id: int | None
    rule_id: str
    category: str
    severity: str
    message: str
    suggestion: str | None
    evidence: str | None
    page: int | None
    source: str


class ObligationOut(ORM):
    id: int
    contract_id: int
    kind: str
    description: str
    due_date: date | None
    status: str
    page: int | None


class ReportOut(ORM):
    summary: str
    key_points: list[str] | None
    risk_score: int
    risk_level: str
    negotiation: list[dict] | None
    llm_model: str | None
    generated_at: datetime


class ContractSummary(ORM):
    id: int
    filename: str
    status: str
    page_count: int | None
    language: str | None
    contract_type: str | None
    governing_law: str | None
    effective_date: date | None
    expiry_date: date | None
    uploaded_at: datetime
    risk_score: int | None = None
    risk_level: str | None = None


class ContractDetail(ContractSummary):
    type_confidence: float | None
    parties: list[dict] | None
    entities: dict | None
    page_info: list[dict] | None
    warnings: list[str] | None
    clauses: list[ClauseOut]
    terms: list[TermOut]
    risk_flags: list[RiskFlagOut]
    obligations: list[ObligationOut]
    report: ReportOut | None
    latest_job: JobOut | None = None
    owner: dict | None = None
    is_mine: bool = True


class UploadOut(BaseModel):
    contract: ContractSummary
    job: JobOut


class TemplateIn(BaseModel):
    name: str
    contract_type: str | None = None
    content: str


class TemplateOut(ORM):
    id: int
    name: str
    contract_type: str | None
    content: str
    created_at: datetime


class PolicyIn(BaseModel):
    name: str
    description: str | None = None
    rules: list[dict]


class PolicyOut(ORM):
    id: int
    name: str
    description: str | None
    rules: list[dict]
    created_at: datetime


class ObligationPatch(BaseModel):
    status: str


class AlertOut(ORM):
    id: int
    obligation_id: int
    contract_id: int
    message: str
    threshold_days: int
    fire_date: date
    read: bool
    created_at: datetime
