"""Encrypted (Fernet) storage of OAuth tokens in SQLite."""

from __future__ import annotations

import json

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.integrations.base import IntegrationError
from app.models import IntegrationCredential, utcnow


def _fernet() -> Fernet:
    key = get_settings().fernet_key
    if not key:
        raise IntegrationError(
            "FERNET_KEY is not set. Generate one with: "
            'python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"'
        )
    return Fernet(key.encode())


def save(provider: str, data: dict) -> None:
    token = _fernet().encrypt(json.dumps(data).encode()).decode()
    with SessionLocal() as db:
        row = db.scalar(
            select(IntegrationCredential).where(IntegrationCredential.provider == provider)
        )
        if row:
            row.encrypted_data, row.updated_at = token, utcnow()
        else:
            db.add(IntegrationCredential(provider=provider, encrypted_data=token))
        db.commit()


def load(provider: str) -> dict | None:
    with SessionLocal() as db:
        row = db.scalar(
            select(IntegrationCredential).where(IntegrationCredential.provider == provider)
        )
    if not row:
        return None
    try:
        return json.loads(_fernet().decrypt(row.encrypted_data.encode()))
    except (InvalidToken, IntegrationError):
        return None


def delete(provider: str) -> None:
    with SessionLocal() as db:
        row = db.scalar(
            select(IntegrationCredential).where(IntegrationCredential.provider == provider)
        )
        if row:
            db.delete(row)
            db.commit()
