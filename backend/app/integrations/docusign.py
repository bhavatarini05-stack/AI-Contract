"""DocuSign eSignature REST API — free developer sandbox (account-d.docusign.com)."""

from __future__ import annotations

import base64

import httpx

from app.config import get_settings
from app.integrations import credentials, oauth
from app.integrations.base import IntegrationError, SignatureProvider, Signer

STATUS_MAP = {
    "sent": "sent",
    "delivered": "delivered",
    "completed": "completed",
    "declined": "declined",
    "voided": "voided",
    "created": "sent",
}


class DocuSign(SignatureProvider):
    key = "docusign"
    label = "DocuSign (sandbox)"

    @property
    def oauth(self) -> oauth.OAuthConfig:
        s = get_settings()
        return oauth.OAuthConfig(
            provider=self.key,
            client_id=s.docusign_integration_key,
            client_secret=s.docusign_secret_key,
            authorize_url=f"{s.docusign_auth_server}/oauth/auth",
            token_url=f"{s.docusign_auth_server}/oauth/token",
            scopes="signature",
            basic_auth=True,
        )

    def is_configured(self) -> bool:
        s = get_settings()
        return s.enable_docusign and bool(s.docusign_integration_key and s.docusign_secret_key)

    def is_connected(self) -> bool:
        return credentials.load(self.key) is not None

    def _account(self) -> tuple[str, dict]:
        token = oauth.access_token(self.oauth)
        tok = credentials.load(self.key) or {}
        if "account_id" not in tok:
            r = httpx.get(
                f"{get_settings().docusign_auth_server}/oauth/userinfo",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30,
            )
            _raise(r)
            acct = next(
                (a for a in r.json()["accounts"] if a.get("is_default")), r.json()["accounts"][0]
            )
            tok.update(account_id=acct["account_id"], base_uri=acct["base_uri"])
            credentials.save(self.key, tok)
        base = f"{tok['base_uri']}/restapi/v2.1/accounts/{tok['account_id']}"
        return base, {"Authorization": f"Bearer {token}"}

    def send(
        self, pdf: bytes, filename: str, signers: list[Signer], subject: str, message: str
    ) -> str:
        base, headers = self._account()
        envelope = {
            "emailSubject": subject[:100],
            "emailBlurb": message,
            "documents": [
                {
                    "documentBase64": base64.b64encode(pdf).decode(),
                    "name": filename,
                    "fileExtension": "pdf",
                    "documentId": "1",
                }
            ],
            "recipients": {
                "signers": [
                    {
                        "email": s.email,
                        "name": s.name,
                        "recipientId": str(i),
                        "routingOrder": str(i),
                        "tabs": {
                            "signHereTabs": [
                                {
                                    "anchorString": "Signature",
                                    "anchorUnits": "pixels",
                                    "anchorYOffset": "-10",
                                    "anchorIgnoreIfNotPresent": "true",
                                }
                            ]
                        },
                    }
                    for i, s in enumerate(signers, start=1)
                ]
            },
            "status": "sent",
        }
        r = httpx.post(f"{base}/envelopes", headers=headers, json=envelope, timeout=60)
        _raise(r)
        return r.json()["envelopeId"]

    def status(self, external_id: str) -> str:
        base, headers = self._account()
        r = httpx.get(f"{base}/envelopes/{external_id}", headers=headers, timeout=30)
        _raise(r)
        return STATUS_MAP.get(r.json().get("status", ""), "unknown")

    def download_signed(self, external_id: str) -> bytes:
        base, headers = self._account()
        r = httpx.get(
            f"{base}/envelopes/{external_id}/documents/combined", headers=headers, timeout=120
        )
        _raise(r)
        return r.content


def _raise(r: httpx.Response) -> None:
    if r.is_error:
        raise IntegrationError(f"DocuSign API error {r.status_code}: {r.text[:300]}")
