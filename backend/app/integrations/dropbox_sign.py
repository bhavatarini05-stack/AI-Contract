"""Dropbox Sign (formerly HelloSign) API — free test mode (test_mode=1, non-binding)."""

from __future__ import annotations

import httpx

from app.config import get_settings
from app.integrations.base import IntegrationError, SignatureProvider, Signer

API = "https://api.hellosign.com/v3"


class DropboxSign(SignatureProvider):
    key = "dropbox_sign"
    label = "Dropbox Sign / HelloSign (test mode)"

    def is_configured(self) -> bool:
        s = get_settings()
        return s.enable_dropbox_sign and bool(s.dropbox_sign_api_key)

    def is_connected(self) -> bool:
        return self.is_configured()

    @property
    def _auth(self) -> tuple[str, str]:
        return (get_settings().dropbox_sign_api_key, "")

    def send(
        self, pdf: bytes, filename: str, signers: list[Signer], subject: str, message: str
    ) -> str:
        data: dict = {
            "title": filename,
            "subject": subject,
            "message": message,
            "test_mode": "1" if get_settings().dropbox_sign_test_mode else "0",
        }
        for i, s in enumerate(signers):
            data[f"signers[{i}][email_address]"] = s.email
            data[f"signers[{i}][name]"] = s.name
            data[f"signers[{i}][order]"] = str(i)
        r = httpx.post(
            f"{API}/signature_request/send",
            auth=self._auth,
            data=data,
            files={"files[0]": (filename, pdf, "application/pdf")},
            timeout=60,
        )
        _raise(r)
        return r.json()["signature_request"]["signature_request_id"]

    def status(self, external_id: str) -> str:
        r = httpx.get(f"{API}/signature_request/{external_id}", auth=self._auth, timeout=30)
        _raise(r)
        sr = r.json()["signature_request"]
        if sr.get("is_complete"):
            return "completed"
        if sr.get("is_declined"):
            return "declined"
        if any(s.get("status_code") == "signed" for s in sr.get("signatures", [])):
            return "delivered"
        return "sent"

    def download_signed(self, external_id: str) -> bytes:
        r = httpx.get(
            f"{API}/signature_request/files/{external_id}",
            auth=self._auth,
            params={"file_type": "pdf"},
            timeout=120,
            follow_redirects=True,
        )
        _raise(r)
        return r.content


def _raise(r: httpx.Response) -> None:
    if r.is_error:
        raise IntegrationError(f"Dropbox Sign API error {r.status_code}: {r.text[:300]}")
