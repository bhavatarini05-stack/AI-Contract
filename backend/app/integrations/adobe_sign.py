"""Adobe Acrobat Sign REST v6 — free developer account."""

from __future__ import annotations

import httpx

from app.config import get_settings
from app.integrations import credentials, oauth
from app.integrations.base import IntegrationError, SignatureProvider, Signer

STATUS_MAP = {
    "OUT_FOR_SIGNATURE": "sent",
    "OUT_FOR_APPROVAL": "sent",
    "IN_PROCESS": "delivered",
    "SIGNED": "completed",
    "APPROVED": "completed",
    "COMPLETED": "completed",
    "CANCELLED": "voided",
    "EXPIRED": "voided",
    "DECLINED": "declined",
}


class AdobeSign(SignatureProvider):
    key = "adobe_sign"
    label = "Adobe Acrobat Sign (developer)"

    @property
    def oauth(self) -> oauth.OAuthConfig:
        s = get_settings()
        shard = s.adobe_sign_shard
        return oauth.OAuthConfig(
            provider=self.key,
            client_id=s.adobe_sign_client_id,
            client_secret=s.adobe_sign_client_secret,
            authorize_url=f"https://secure.{shard}.adobesign.com/public/oauth/v2",
            token_url=f"https://api.{shard}.adobesign.com/oauth/v2/token",
            refresh_url=f"https://api.{shard}.adobesign.com/oauth/v2/refresh",
            scopes="agreement_read:self agreement_write:self agreement_send:self",
        )

    def is_configured(self) -> bool:
        s = get_settings()
        return s.enable_adobe_sign and bool(s.adobe_sign_client_id and s.adobe_sign_client_secret)

    def is_connected(self) -> bool:
        return credentials.load(self.key) is not None

    def _base(self) -> tuple[str, dict]:
        token = oauth.access_token(self.oauth)
        tok = credentials.load(self.key) or {}
        api = (
            tok.get("api_access_point")
            or f"https://api.{get_settings().adobe_sign_shard}.adobesign.com/"
        )
        return f"{api.rstrip('/')}/api/rest/v6", {"Authorization": f"Bearer {token}"}

    def send(
        self, pdf: bytes, filename: str, signers: list[Signer], subject: str, message: str
    ) -> str:
        base, headers = self._base()
        r = httpx.post(
            f"{base}/transientDocuments",
            headers=headers,
            files={"File": (filename, pdf, "application/pdf")},
            data={"File-Name": filename},
            timeout=60,
        )
        _raise(r)
        doc_id = r.json()["transientDocumentId"]
        agreement = {
            "fileInfos": [{"transientDocumentId": doc_id}],
            "name": subject[:255],
            "message": message,
            "participantSetsInfo": [
                {"memberInfos": [{"email": s.email}], "order": i, "role": "SIGNER"}
                for i, s in enumerate(signers, start=1)
            ],
            "signatureType": "ESIGN",
            "state": "IN_PROCESS",
        }
        r = httpx.post(f"{base}/agreements", headers=headers, json=agreement, timeout=60)
        _raise(r)
        return r.json()["id"]

    def status(self, external_id: str) -> str:
        base, headers = self._base()
        r = httpx.get(f"{base}/agreements/{external_id}", headers=headers, timeout=30)
        _raise(r)
        return STATUS_MAP.get(r.json().get("status", ""), "unknown")

    def download_signed(self, external_id: str) -> bytes:
        base, headers = self._base()
        r = httpx.get(
            f"{base}/agreements/{external_id}/combinedDocument", headers=headers, timeout=120
        )
        _raise(r)
        return r.content


def _raise(r: httpx.Response) -> None:
    if r.is_error:
        raise IntegrationError(f"Adobe Sign API error {r.status_code}: {r.text[:300]}")
