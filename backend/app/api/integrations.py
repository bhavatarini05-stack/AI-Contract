"""Google Drive and e-signature endpoints (sandbox/test modes; off unless enabled in .env)."""

from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import report
from app.api.contracts import create_and_analyze, get_contract_or_404
from app.auth import get_current_user, require_admin
from app.config import get_settings
from app.db import get_db
from app.integrations import (
    OAUTH_PROVIDERS,
    SIGNATURE_PROVIDERS,
    STORAGE_PROVIDERS,
    IntegrationError,
    credentials,
    oauth,
)
from app.integrations.base import Signer
from app.models import Contract, SignatureRequest, User

router = APIRouter(prefix="/integrations", tags=["integrations"])


def _provider(key: str):
    p = SIGNATURE_PROVIDERS.get(key) or STORAGE_PROVIDERS.get(key)
    if not p:
        raise HTTPException(404, f"Unknown integration {key}")
    if not p.is_configured():
        raise HTTPException(
            400,
            f"{p.label} is not enabled/configured. Set the ENABLE_* flag and credentials in .env.",
        )
    return p


def _wrap(fn, *args):
    try:
        return fn(*args)
    except IntegrationError as e:
        raise HTTPException(502, str(e)) from e


@router.get("", dependencies=[Depends(get_current_user)])
def list_integrations():
    out = []
    for kind, reg in (("signature", SIGNATURE_PROVIDERS), ("storage", STORAGE_PROVIDERS)):
        for p in reg.values():
            out.append(
                {
                    "key": p.key,
                    "label": p.label,
                    "kind": kind,
                    "configured": p.is_configured(),
                    "connected": p.is_configured() and p.is_connected(),
                    "oauth": p.key in OAUTH_PROVIDERS,
                }
            )
    return out


# ---- OAuth connect / disconnect --------------------------------------------------------------


@router.get("/{key}/connect", dependencies=[Depends(require_admin)])
def connect(key: str):
    p = _provider(key)
    if key not in OAUTH_PROVIDERS:
        raise HTTPException(400, f"{p.label} uses an API key from .env; no connect step needed.")
    return {"authorize_url": oauth.authorize_url(p.oauth)}


@router.get("/{key}/callback")
def callback(key: str, code: str | None = None, state: str | None = None, error: str | None = None):
    p = _provider(key)
    front = get_settings().frontend_url
    if error or not code or not state:
        return RedirectResponse(f"{front}/settings?error={error or 'missing_code'}")
    try:
        oauth.exchange_code(p.oauth, code, state)  # saves the encrypted token
    except IntegrationError as e:
        return RedirectResponse(f"{front}/settings?error={quote(str(e)[:120])}")
    return RedirectResponse(f"{front}/settings?connected={key}")


@router.delete("/{key}/connection", status_code=204, dependencies=[Depends(require_admin)])
def disconnect(key: str):
    credentials.delete(key)


# ---- Google Drive ----------------------------------------------------------------------------


@router.get("/gdrive/files", dependencies=[Depends(get_current_user)])
def drive_files(q: str | None = None):
    p = _provider("gdrive")
    return [f.__dict__ for f in _wrap(p.list_files, q)]


@router.post("/gdrive/import/{file_id}", status_code=201)
def drive_import(
    file_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    p = _provider("gdrive")
    name, data = _wrap(p.download, file_id)
    return create_and_analyze(db, data, name, user)


@router.post("/gdrive/export/{contract_id}")
def drive_export_report(
    contract_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    p = _provider("gdrive")
    c = get_contract_or_404(db, contract_id, user)
    if c.status != "done":
        raise HTTPException(409, "Analysis not finished yet")
    name = f"{Path(c.filename).stem} - risk report.html"
    file_id = _wrap(p.upload, name, report.render(c).encode("utf-8"), "text/html")
    return {"file_id": file_id, "name": name}


# ---- E-signature -----------------------------------------------------------------------------


class SignerIn(BaseModel):
    name: str
    email: EmailStr


class SendIn(BaseModel):
    signers: list[SignerIn]
    subject: str | None = None
    message: str = "Please review and sign this contract."


@router.post("/{key}/send/{contract_id}", status_code=201)
def send_for_signature(
    key: str,
    contract_id: int,
    body: SendIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if key not in SIGNATURE_PROVIDERS:
        raise HTTPException(404, "Not an e-signature provider")
    p = _provider(key)
    if not body.signers:
        raise HTTPException(422, "At least one signer is required")
    c = get_contract_or_404(db, contract_id, user)
    path = Path(c.file_path)
    if path.suffix.lower() != ".pdf":
        raise HTTPException(400, "Only PDF contracts can be sent for signature")
    ext_id = _wrap(
        p.send,
        path.read_bytes(),
        c.filename,
        [Signer(s.name, s.email) for s in body.signers],
        body.subject or f"Please sign: {c.filename}",
        body.message,
    )
    sr = SignatureRequest(
        contract_id=c.id,
        provider=key,
        external_id=ext_id,
        signers=[s.model_dump() for s in body.signers],
    )
    db.add(sr)
    db.commit()
    db.refresh(sr)
    return _sr_out(sr)


@router.get("/signature-requests")
def list_signature_requests(
    contract_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = (
        select(SignatureRequest)
        .join(Contract, Contract.id == SignatureRequest.contract_id)
        .where(Contract.owner_id == user.id)
        .order_by(SignatureRequest.created_at.desc())
    )
    if contract_id:
        q = q.where(SignatureRequest.contract_id == contract_id)
    return [_sr_out(s) for s in db.scalars(q)]


@router.post("/signature-requests/{request_id}/refresh")
def refresh_signature_request(
    request_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    sr = db.get(SignatureRequest, request_id)
    if not sr:
        raise HTTPException(404, "Signature request not found")
    orig = get_contract_or_404(db, sr.contract_id, user)
    p = _provider(sr.provider)
    status = _wrap(p.status, sr.external_id)
    result = {"imported_contract_id": None}
    if status == "completed" and sr.status != "completed":
        # Pull the signed copy back in and re-analyze it (e.g. to catch last-minute edits).
        signed = _wrap(p.download_signed, sr.external_id)
        owner = db.get(User, orig.owner_id) or user
        up = create_and_analyze(db, signed, f"signed_{Path(orig.filename).stem}.pdf", owner)
        result["imported_contract_id"] = up.contract.id
    sr.status, sr.updated_at = status, datetime.now(UTC)
    db.commit()
    return {**_sr_out(sr), **result}


def _sr_out(sr: SignatureRequest) -> dict:
    return {
        "id": sr.id,
        "contract_id": sr.contract_id,
        "provider": sr.provider,
        "external_id": sr.external_id,
        "status": sr.status,
        "signers": sr.signers,
        "created_at": sr.created_at,
        "updated_at": sr.updated_at,
    }
