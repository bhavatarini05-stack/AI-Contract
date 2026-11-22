"""Minimal OAuth2 authorization-code helper shared by Google, DocuSign and Adobe Sign."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.config import get_settings
from app.integrations import credentials
from app.integrations.base import IntegrationError

_pending_states: dict[str, tuple[str, float]] = {}  # state -> (provider, created)


@dataclass
class OAuthConfig:
    provider: str
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    scopes: str
    refresh_url: str | None = None
    extra_auth_params: dict | None = None
    basic_auth: bool = False

    @property
    def redirect_uri(self) -> str:
        return f"{get_settings().backend_url}/integrations/{self.provider}/callback"


def authorize_url(cfg: OAuthConfig) -> str:
    state = secrets.token_urlsafe(24)
    _pending_states[state] = (cfg.provider, time.time())
    params = {
        "response_type": "code",
        "client_id": cfg.client_id,
        "redirect_uri": cfg.redirect_uri,
        "scope": cfg.scopes,
        "state": state,
        **(cfg.extra_auth_params or {}),
    }
    return f"{cfg.authorize_url}?{urlencode(params)}"


def exchange_code(cfg: OAuthConfig, code: str, state: str) -> dict:
    provider, created = _pending_states.pop(state, (None, 0))
    if provider != cfg.provider or time.time() - created > 900:
        raise IntegrationError("Invalid or expired OAuth state; please try connecting again.")
    tok = _token_request(
        cfg,
        cfg.token_url,
        {"grant_type": "authorization_code", "code": code, "redirect_uri": cfg.redirect_uri},
    )
    credentials.save(cfg.provider, tok)
    return tok


def access_token(cfg: OAuthConfig) -> str:
    tok = credentials.load(cfg.provider)
    if not tok:
        raise IntegrationError(f"{cfg.provider} is not connected.")
    if tok.get("expires_at", 0) - 60 < time.time():
        if not tok.get("refresh_token"):
            raise IntegrationError(f"{cfg.provider} token expired; please reconnect.")
        new = _token_request(
            cfg,
            cfg.refresh_url or cfg.token_url,
            {"grant_type": "refresh_token", "refresh_token": tok["refresh_token"]},
        )
        new.setdefault("refresh_token", tok["refresh_token"])
        new = {**tok, **new}
        credentials.save(cfg.provider, new)
        tok = new
    return tok["access_token"]


def _token_request(cfg: OAuthConfig, url: str, data: dict) -> dict:
    auth = (cfg.client_id, cfg.client_secret) if cfg.basic_auth else None
    if not cfg.basic_auth:
        data = {**data, "client_id": cfg.client_id, "client_secret": cfg.client_secret}
    try:
        r = httpx.post(url, data=data, auth=auth, timeout=30)
        r.raise_for_status()
    except httpx.HTTPError as e:
        raise IntegrationError(f"OAuth token request to {cfg.provider} failed: {e}") from e
    tok = r.json()
    tok["expires_at"] = time.time() + int(tok.get("expires_in", 3600))
    return tok
