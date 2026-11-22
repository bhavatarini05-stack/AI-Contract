"""Common interfaces for document-storage and e-signature providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class IntegrationError(RuntimeError):
    pass


@dataclass
class Signer:
    name: str
    email: str


@dataclass
class RemoteFile:
    id: str
    name: str
    mime_type: str
    modified: str | None = None


class SignatureProvider(ABC):
    key: str
    label: str

    @abstractmethod
    def is_configured(self) -> bool: ...

    @abstractmethod
    def is_connected(self) -> bool: ...

    @abstractmethod
    def send(
        self, pdf: bytes, filename: str, signers: list[Signer], subject: str, message: str
    ) -> str:
        """Send for signature; return the provider's request/envelope id."""

    @abstractmethod
    def status(self, external_id: str) -> str:
        """Return a normalized status: sent|delivered|completed|declined|voided|unknown."""

    @abstractmethod
    def download_signed(self, external_id: str) -> bytes:
        """Return the completed, signed PDF."""


class StorageProvider(ABC):
    key: str
    label: str

    @abstractmethod
    def is_configured(self) -> bool: ...

    @abstractmethod
    def is_connected(self) -> bool: ...

    @abstractmethod
    def list_files(self, query: str | None = None) -> list[RemoteFile]: ...

    @abstractmethod
    def download(self, file_id: str) -> tuple[str, bytes]: ...

    @abstractmethod
    def upload(self, name: str, data: bytes, mime_type: str) -> str: ...
