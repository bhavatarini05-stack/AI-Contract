"""Template comparison, policy compliance, templates & policies CRUD."""

from pathlib import Path

import pymupdf
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.contracts import get_contract_or_404
from app.auth import get_current_user, require_admin
from app.db import get_db
from app.llm import get_provider
from app.models import Policy, Template, User
from app.pipeline import compare, compliance
from app.pipeline.orchestrator import grouped_from_db, terms_from_db
from app.schemas import PolicyIn, PolicyOut, TemplateIn, TemplateOut

router = APIRouter(tags=["analysis"], dependencies=[Depends(get_current_user)])
ADMIN = [Depends(require_admin)]


def _llm_or_none():
    llm = get_provider()
    return llm if llm.health().get("ok") else None


def _require_done(c):
    if c.status != "done":
        raise HTTPException(409, "Analysis not finished yet")


# ---- comparison -----------------------------------------------------------------------------


@router.get("/contracts/{contract_id}/compare/{template_id}")
def compare_with_template(
    contract_id: int,
    template_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = get_contract_or_404(db, contract_id, user)
    _require_done(c)
    t = db.get(Template, template_id)
    if not t:
        raise HTTPException(404, "Template not found")
    result = compare.compare(grouped_from_db(c), terms_from_db(c), t.content, _llm_or_none())
    return {"template": {"id": t.id, "name": t.name}, **result}


# ---- compliance -----------------------------------------------------------------------------


@router.get("/contracts/{contract_id}/compliance/{policy_id}")
def check_compliance(
    contract_id: int,
    policy_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = get_contract_or_404(db, contract_id, user)
    _require_done(c)
    p = db.get(Policy, policy_id)
    if not p:
        raise HTTPException(404, "Policy not found")
    result = compliance.check(p.rules, c.full_text or "", grouped_from_db(c), _llm_or_none())
    return {"policy": {"id": p.id, "name": p.name}, **result}


# ---- templates ------------------------------------------------------------------------------


@router.get("/templates", response_model=list[TemplateOut])
def list_templates(db: Session = Depends(get_db)):
    return db.scalars(select(Template).order_by(Template.name)).all()


@router.post("/templates", response_model=TemplateOut, status_code=201, dependencies=ADMIN)
def create_template(body: TemplateIn, db: Session = Depends(get_db)):
    t = Template(**body.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.post("/templates/upload", response_model=TemplateOut, status_code=201, dependencies=ADMIN)
async def upload_template(
    name: str = Form(...),
    contract_type: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    data = await file.read()
    if Path(file.filename or "").suffix.lower() == ".pdf":
        with pymupdf.open(stream=data, filetype="pdf") as pdf:
            content = "\n\n".join(pg.get_text("text") for pg in pdf)
    else:
        content = data.decode("utf-8", errors="replace")
    if not content.strip():
        raise HTTPException(400, "Template has no extractable text")
    return create_template(TemplateIn(name=name, contract_type=contract_type, content=content), db)


@router.delete("/templates/{template_id}", status_code=204, dependencies=ADMIN)
def delete_template(template_id: int, db: Session = Depends(get_db)):
    t = db.get(Template, template_id)
    if t:
        db.delete(t)
        db.commit()


# ---- policies -------------------------------------------------------------------------------


@router.get("/policies", response_model=list[PolicyOut])
def list_policies(db: Session = Depends(get_db)):
    return db.scalars(select(Policy).order_by(Policy.name)).all()


@router.post("/policies", response_model=PolicyOut, status_code=201, dependencies=ADMIN)
def create_policy(body: PolicyIn, db: Session = Depends(get_db)):
    _validate_rules(body.rules)
    p = Policy(**body.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.put("/policies/{policy_id}", response_model=PolicyOut, dependencies=ADMIN)
def update_policy(policy_id: int, body: PolicyIn, db: Session = Depends(get_db)):
    _validate_rules(body.rules)
    p = db.get(Policy, policy_id)
    if not p:
        raise HTTPException(404, "Policy not found")
    p.name, p.description, p.rules = body.name, body.description, body.rules
    db.commit()
    return p


@router.delete("/policies/{policy_id}", status_code=204, dependencies=ADMIN)
def delete_policy(policy_id: int, db: Session = Depends(get_db)):
    p = db.get(Policy, policy_id)
    if p:
        db.delete(p)
        db.commit()


def _validate_rules(rules: list[dict]) -> None:
    import re

    for i, r in enumerate(rules):
        if not r.get("id") or not r.get("requirement"):
            raise HTTPException(422, f"Rule {i}: 'id' and 'requirement' are required")
        for key in ("must_include", "must_not_include"):
            for pat in r.get(key, []) or []:
                try:
                    re.compile(pat)
                except re.error as e:
                    raise HTTPException(422, f"Rule {r['id']}: invalid regex in {key}: {e}") from e
