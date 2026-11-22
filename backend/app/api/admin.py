"""Admin-only endpoints: user management and organisation-wide overview."""

from datetime import date, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import hash_password, require_admin
from app.db import get_db
from app.models import Contract, Job, Obligation, Report, User
from app.schemas import ContractSummary, UserOut

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = "user"


class UserPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    role: str | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


def _check_role(role: str | None) -> None:
    if role is not None and role not in {"user", "admin"}:
        raise HTTPException(422, "role must be 'user' or 'admin'")


def _admins_left(db: Session, excluding: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(User)
        .where(User.role == "admin", User.is_active.is_(True), User.id != excluding)
    )


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    count = lambda q: db.scalar(select(func.count()).select_from(q))  # noqa: E731
    by_status = dict(
        db.execute(select(Contract.status, func.count()).group_by(Contract.status)).all()
    )
    by_level = dict(
        db.execute(select(Report.risk_level, func.count()).group_by(Report.risk_level)).all()
    )
    avg = db.scalar(select(func.avg(Report.risk_score)))
    soon = date.today() + timedelta(days=30)
    per_user = db.execute(
        select(User.id, User.name, func.count(Contract.id))
        .join(Contract, Contract.owner_id == User.id, isouter=True)
        .group_by(User.id)
        .order_by(func.count(Contract.id).desc())
    ).all()
    recent_jobs = db.execute(
        select(Job, Contract.filename, User.name)
        .join(Contract, Contract.id == Job.contract_id)
        .join(User, User.id == Contract.owner_id, isouter=True)
        .order_by(Job.created_at.desc())
        .limit(8)
    ).all()
    return {
        "users": count(User),
        "active_users": db.scalar(
            select(func.count()).select_from(User).where(User.is_active.is_(True))
        ),
        "admins": db.scalar(select(func.count()).select_from(User).where(User.role == "admin")),
        "contracts": count(Contract),
        "by_status": by_status,
        "by_risk_level": by_level,
        "avg_risk_score": round(avg) if avg is not None else None,
        "deadlines_30d": db.scalar(
            select(func.count())
            .select_from(Obligation)
            .where(
                Obligation.status == "open",
                Obligation.due_date.is_not(None),
                Obligation.due_date <= soon,
            )
        ),
        "contracts_per_user": [{"user_id": i, "name": n, "contracts": c} for i, n, c in per_user],
        "recent_activity": [
            {
                "job_id": j.id,
                "contract_id": j.contract_id,
                "filename": fn,
                "owner": owner,
                "status": j.status,
                "stage": j.stage,
                "created_at": j.created_at,
            }
            for j, fn, owner in recent_jobs
        ],
    }


@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    counts = dict(
        db.execute(select(Contract.owner_id, func.count()).group_by(Contract.owner_id)).all()
    )
    users = db.scalars(select(User).order_by(User.created_at)).all()
    return [
        {**UserOut.model_validate(u).model_dump(mode="json"), "contracts": counts.get(u.id, 0)}
        for u in users
    ]


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, db: Session = Depends(get_db)):
    _check_role(body.role)
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    u = User(
        name=body.name.strip(),
        email=email,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int, body: UserPatch, db: Session = Depends(get_db), me: User = Depends(require_admin)
):
    _check_role(body.role)
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    demoting = (body.role == "user" and u.role == "admin") or (
        body.is_active is False and u.role == "admin"
    )
    if demoting and _admins_left(db, u.id) == 0:
        raise HTTPException(400, "At least one active admin is required")
    if u.id == me.id and body.is_active is False:
        raise HTTPException(400, "You can't deactivate your own account")
    if body.name is not None:
        u.name = body.name.strip()
    if body.role is not None:
        u.role = body.role
    if body.is_active is not None:
        u.is_active = body.is_active
    if body.password:
        u.password_hash = hash_password(body.password)
    db.commit()
    return u


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db), me: User = Depends(require_admin)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    if u.id == me.id:
        raise HTTPException(400, "You can't delete your own account")
    if u.role == "admin" and _admins_left(db, u.id) == 0:
        raise HTTPException(400, "At least one active admin is required")
    for c in db.scalars(select(Contract).where(Contract.owner_id == u.id)):
        Path(c.file_path).unlink(missing_ok=True)
        db.delete(c)
    db.delete(u)
    db.commit()


@router.get("/contracts")
def all_contracts(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Contract, User.name, User.email)
        .join(User, User.id == Contract.owner_id, isouter=True)
        .order_by(Contract.uploaded_at.desc())
    ).all()
    out = []
    for c, name, email in rows:
        s = ContractSummary.model_validate(c)
        if c.report:
            s.risk_score, s.risk_level = c.report.risk_score, c.report.risk_level
        out.append({**s.model_dump(mode="json"), "owner_name": name, "owner_email": email})
    return out
