import os
import tempfile
from pathlib import Path

# Configure an isolated, offline environment BEFORE the app is imported.
_TMP = Path(tempfile.mkdtemp(prefix="contract-tests-"))
os.environ["LLM_PROVIDER"] = "mock"  # tests/test_ollama.py builds its own real provider
os.environ["DATABASE_URL"] = f"sqlite:///{(_TMP / 'test.db').as_posix()}"
os.environ["STORAGE_DIR"] = str(_TMP / "storage")
os.environ.setdefault("FERNET_KEY", "")

import pymupdf  # noqa: E402
import pytest  # noqa: E402

from tests.fixtures.contracts import SCHEDULE_A, SCHEDULE_A_HEADING, SERVICE_AGREEMENT  # noqa: E402


@pytest.fixture(scope="session")
def tmp_dir() -> Path:
    return _TMP


@pytest.fixture(scope="session")
def service_pdf(tmp_dir) -> Path:
    from scripts.make_samples import text_to_pdf

    path = tmp_dir / "service_agreement.pdf"
    text = (
        SERVICE_AGREEMENT
        + "\n\f"
        + SCHEDULE_A_HEADING
        + "\n\n"
        + "\n".join(SCHEDULE_A.format(n=i) for i in range(1, 72))
    )
    text_to_pdf(text, path)
    return path


@pytest.fixture(scope="session")
def scanned_pdf(tmp_dir, service_pdf) -> Path:
    from scripts.make_samples import rasterize

    path = tmp_dir / "scanned.pdf"
    rasterize(service_pdf, path, max_pages=2)
    return path


@pytest.fixture
def blank_pdf(tmp_dir) -> Path:
    path = tmp_dir / "blank.pdf"
    doc = pymupdf.open()
    doc.new_page()
    doc.save(path)
    return path


# ---------------------------------------------------------------- authenticated API clients

ADMIN = {"name": "Ada Admin", "email": "admin@example.com", "password": "admin-pass-123"}
USER = {"name": "Uma User", "email": "user@example.com", "password": "user-pass-123"}
OTHER = {"name": "Otto Other", "email": "other@example.com", "password": "other-pass-123"}


@pytest.fixture(scope="session")
def admin_client():
    """Session app client (runs startup once). The first registered account becomes admin."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        r = c.post("/auth/register", json=ADMIN)
        assert r.status_code == 201 and r.json()["role"] == "admin", r.text
        yield c


def _client_for(creds: dict):
    from fastapi.testclient import TestClient

    from app.main import app

    c = TestClient(app)  # app already started by admin_client; separate cookie jar per user
    r = c.post("/auth/register", json=creds)
    assert r.status_code == 201, r.text
    return c


@pytest.fixture(scope="session")
def user_client(admin_client):
    return _client_for(USER)


@pytest.fixture(scope="session")
def other_client(admin_client):
    return _client_for(OTHER)
