import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import jobs, report
from app.auth import get_current_user
from app.config import get_settings
from app.db import get_db
from app.models import Contract, Job, User
from app.schemas import ContractDetail, ContractSummary, JobOut, UploadOut

router = APIRouter(tags=["contracts"])

ALLOWED = {".pdf", ".txt", ".md"}
MAX_BYTES = 50 * 1024 * 1024


def _summary(c: Contract) -> ContractSummary:
    s = ContractSummary.model_validate(c)
    if c.report:
        s.risk_score, s.risk_level = c.report.risk_score, c.report.risk_level
    return s


def get_contract_or_404(db: Session, contract_id: int, user: User) -> Contract:
    """Owners see their own contracts; admins can open any. Others get 404 (no existence leak)."""
    c = db.get(Contract, contract_id)
    if not c or (c.owner_id != user.id and not user.is_admin):
        raise HTTPException(404, "Contract not found")
    return c


def save_upload(data: bytes, filename: str) -> Path:
    storage = get_settings().storage_dir
    storage.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^\w.\-]+", "_", Path(filename).name)[:120]
    path = storage / f"{uuid.uuid4().hex[:12]}_{safe}"
    path.write_bytes(data)
    return path


def create_and_analyze(db: Session, data: bytes, filename: str, owner: User) -> UploadOut:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(400, f"Unsupported file type {ext}. Upload a PDF (or .txt).")
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File too large (max 50 MB).")
    if ext == ".pdf" and not data.startswith(b"%PDF"):
        raise HTTPException(400, "File does not look like a valid PDF.")
    path = save_upload(data, filename)
    contract = Contract(filename=Path(filename).name, file_path=str(path), owner_id=owner.id)
    db.add(contract)
    db.commit()
    db.refresh(contract)
    job = jobs.enqueue_analysis(contract.id)
    return UploadOut(contract=_summary(contract), job=JobOut.model_validate(job))


@router.post("/contracts", response_model=UploadOut, status_code=201)
async def upload_contract(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = await file.read()
    return create_and_analyze(db, data, file.filename or "contract.pdf", user)


@router.get("/contracts", response_model=list[ContractSummary])
def list_contracts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(
        select(Contract).where(Contract.owner_id == user.id).order_by(Contract.uploaded_at.desc())
    ).all()
    return [_summary(c) for c in rows]


@router.get("/contracts/{contract_id}", response_model=ContractDetail)
def get_contract(
    contract_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    c = get_contract_or_404(db, contract_id, user)
    detail = ContractDetail.model_validate(c)
    if c.report:
        detail.risk_score, detail.risk_level = c.report.risk_score, c.report.risk_level
    latest = max(c.jobs, key=lambda j: j.id, default=None)
    detail.latest_job = JobOut.model_validate(latest) if latest else None
    owner = db.get(User, c.owner_id) if c.owner_id else None
    detail.owner = {"id": owner.id, "name": owner.name, "email": owner.email} if owner else None
    detail.is_mine = c.owner_id == user.id
    return detail


@router.get("/contracts/{contract_id}/file")
def get_contract_file(
    contract_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    c = get_contract_or_404(db, contract_id, user)
    path = Path(c.file_path)
    if not path.exists():
        raise HTTPException(404, "File missing from storage")
    media = "application/pdf" if path.suffix.lower() == ".pdf" else "text/plain"
    return FileResponse(
        path, media_type=media, filename=c.filename, content_disposition_type="inline"
    )


@router.get("/contracts/{contract_id}/report", response_class=HTMLResponse)
def get_report(
    contract_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    c = get_contract_or_404(db, contract_id, user)
    if c.status != "done":
        raise HTTPException(409, "Analysis not finished yet")
    return HTMLResponse(report.render(c))


@router.post("/contracts/{contract_id}/reanalyze", response_model=JobOut)
def reanalyze(
    contract_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    get_contract_or_404(db, contract_id, user)
    return JobOut.model_validate(jobs.enqueue_analysis(contract_id))


@router.delete("/contracts/{contract_id}", status_code=204)
def delete_contract(
    contract_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    c = get_contract_or_404(db, contract_id, user)
    Path(c.file_path).unlink(missing_ok=True)
    db.delete(c)
    db.commit()


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    get_contract_or_404(db, job.contract_id, user)
    return job
