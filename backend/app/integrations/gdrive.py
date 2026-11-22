"""Google Drive (free API quota): import contracts, export reports."""

from __future__ import annotations

import json

import httpx

from app.config import get_settings
from app.integrations import credentials, oauth
from app.integrations.base import IntegrationError, RemoteFile, StorageProvider

API = "https://www.googleapis.com/drive/v3"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"


class GoogleDrive(StorageProvider):
    key = "gdrive"
    label = "Google Drive"

    @property
    def oauth(self) -> oauth.OAuthConfig:
        s = get_settings()
        return oauth.OAuthConfig(
            provider=self.key,
            client_id=s.google_client_id,
            client_secret=s.google_client_secret,
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes="https://www.googleapis.com/auth/drive.readonly https://www.googleapis.com/auth/drive.file",
            extra_auth_params={"access_type": "offline", "prompt": "consent"},
        )

    def is_configured(self) -> bool:
        s = get_settings()
        return s.enable_gdrive and bool(s.google_client_id and s.google_client_secret)

    def is_connected(self) -> bool:
        return credentials.load(self.key) is not None

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {oauth.access_token(self.oauth)}"}

    def list_files(self, query: str | None = None) -> list[RemoteFile]:
        q = "trashed = false and (mimeType = 'application/pdf' or mimeType = 'application/vnd.google-apps.document')"
        if query:
            q += f" and name contains '{query.replace(chr(39), '')}'"
        r = httpx.get(
            f"{API}/files",
            headers=self._headers(),
            timeout=30,
            params={
                "q": q,
                "pageSize": 50,
                "orderBy": "modifiedTime desc",
                "fields": "files(id,name,mimeType,modifiedTime)",
            },
        )
        _raise(r)
        return [
            RemoteFile(f["id"], f["name"], f["mimeType"], f.get("modifiedTime"))
            for f in r.json()["files"]
        ]

    def download(self, file_id: str) -> tuple[str, bytes]:
        meta = httpx.get(
            f"{API}/files/{file_id}",
            headers=self._headers(),
            params={"fields": "name,mimeType"},
            timeout=30,
        )
        _raise(meta)
        m = meta.json()
        if m["mimeType"] == "application/vnd.google-apps.document":
            r = httpx.get(
                f"{API}/files/{file_id}/export",
                headers=self._headers(),
                params={"mimeType": "application/pdf"},
                timeout=120,
            )
            name = m["name"] + ".pdf"
        else:
            r = httpx.get(
                f"{API}/files/{file_id}",
                headers=self._headers(),
                params={"alt": "media"},
                timeout=120,
            )
            name = m["name"]
        _raise(r)
        return name, r.content

    def upload(self, name: str, data: bytes, mime_type: str) -> str:
        boundary = "contract_analyzer_boundary"
        body = (
            (
                f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n"
                f"{json.dumps({'name': name})}\r\n--{boundary}\r\nContent-Type: {mime_type}\r\n\r\n"
            ).encode()
            + data
            + f"\r\n--{boundary}--".encode()
        )
        r = httpx.post(
            UPLOAD,
            headers={**self._headers(), "Content-Type": f"multipart/related; boundary={boundary}"},
            content=body,
            timeout=120,
        )
        _raise(r)
        return r.json()["id"]


def _raise(r: httpx.Response) -> None:
    if r.is_error:
        raise IntegrationError(f"Google Drive API error {r.status_code}: {r.text[:300]}")
