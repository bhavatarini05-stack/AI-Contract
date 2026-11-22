from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Alert, Contract, Obligation, User
from app.scheduler import scan_alerts
from app.schemas import AlertOut, ObligationOut, ObligationPatch

router = APIRouter(tags=["obligations"])


@router.get("/obligations")
def list_obligations(
    days: int | None = None,
    status: str | None = "open",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = (
        select(Obligation, Contract.filename)
        .join(Contract, Contract.id == Obligation.contract_id)
        .where(Contract.owner_id == user.id)
    )
    if status:
        q = q.where(Obligation.status == status)
    if days is not None:
        q = q.where(
            Obligation.due_date.is_not(None),
            Obligation.due_date <= date.today() + timedelta(days=days),
        )
    rows = db.execute(q.order_by(Obligation.due_date.is_(None), Obligation.due_date)).all()
    return [
        {
            **ObligationOut.model_validate(o).model_dump(mode="json"),
            "contract_filename": fn,
            "days_left": (o.due_date - date.today()).days if o.due_date else None,
        }
        for o, fn in rows
    ]


@router.patch("/obligations/{obligation_id}", response_model=ObligationOut)
def update_obligation(
    obligation_id: int,
    body: ObligationPatch,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if body.status not in {"open", "done", "dismissed"}:
        raise HTTPException(422, "status must be open, done or dismissed")
    o = db.get(Obligation, obligation_id)
    if not o or db.get(Contract, o.contract_id).owner_id != user.id:
        raise HTTPException(404, "Obligation not found")
    o.status = body.status
    db.commit()
    return o


@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(
    unread_only: bool = False, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    q = (
        select(Alert)
        .join(Contract, Contract.id == Alert.contract_id)
        .where(Contract.owner_id == user.id)
        .order_by(Alert.created_at.desc())
    )
    if unread_only:
        q = q.where(Alert.read.is_(False))
    return db.scalars(q.limit(100)).all()


@router.post("/alerts/{alert_id}/read", response_model=AlertOut)
def mark_read(alert_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    a = db.get(Alert, alert_id)
    if not a or db.get(Contract, a.contract_id).owner_id != user.id:
        raise HTTPException(404, "Alert not found")
    a.read = True
    db.commit()
    return a


@router.post("/alerts/scan", dependencies=[Depends(get_current_user)])
def run_scan():
    return {"created": scan_alerts()}
