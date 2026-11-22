from app.integrations.adobe_sign import AdobeSign
from app.integrations.base import IntegrationError, SignatureProvider, StorageProvider
from app.integrations.docusign import DocuSign
from app.integrations.dropbox_sign import DropboxSign
from app.integrations.gdrive import GoogleDrive

SIGNATURE_PROVIDERS: dict[str, SignatureProvider] = {
    p.key: p for p in (DocuSign(), DropboxSign(), AdobeSign())
}
STORAGE_PROVIDERS: dict[str, StorageProvider] = {p.key: p for p in (GoogleDrive(),)}
OAUTH_PROVIDERS = {"gdrive", "docusign", "adobe_sign"}

__all__ = ["IntegrationError", "SIGNATURE_PROVIDERS", "STORAGE_PROVIDERS", "OAUTH_PROVIDERS"]
