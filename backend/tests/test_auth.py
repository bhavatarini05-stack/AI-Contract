"""Authentication, roles and per-user data isolation."""

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import ADMIN, USER


def _upload(client, service_pdf) -> int:
    with open(service_pdf, "rb") as f:
        r = client.post("/contracts", files={"file": ("mine.pdf", f, "application/pdf")})
    assert r.status_code == 201, r.text
    return r.json()["contract"]["id"]


def test_requires_login():
    anon = TestClient(app)
    for path in ("/contracts", "/obligations", "/alerts", "/templates", "/auth/me", "/admin/users"):
        assert anon.get(path).status_code == 401, path
    assert anon.get("/health").status_code == 200  # public


def test_auth_config_public():
    body = TestClient(app).get("/auth/config").json()
    assert set(body) == {"allow_registration", "first_run"}


def test_first_user_is_admin_and_others_are_users(admin_client, user_client):
    assert admin_client.get("/auth/me").json()["role"] == "admin"
    assert user_client.get("/auth/me").json()["role"] == "user"


def test_login_logout_and_bad_password(user_client):
    c = TestClient(app)
    assert (
        c.post(
            "/auth/login", json={"email": USER["email"], "password": "wrong-password"}
        ).status_code
        == 401
    )
    r = c.post("/auth/login", json={"email": USER["email"].upper(), "password": USER["password"]})
    assert r.status_code == 200 and "cl_session" in r.cookies
    assert c.get("/auth/me").status_code == 200
    assert c.post("/auth/logout").status_code == 204
    assert c.get("/auth/me").status_code == 401


def test_bearer_token_also_works(user_client):
    from app.auth import create_token
    from app.db import SessionLocal
    from app.models import User

    with SessionLocal() as db:
        u = db.query(User).filter_by(email=USER["email"]).one()
        token = create_token(u)
    assert (
        TestClient(app).get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code
        == 200
    )


def test_duplicate_email_rejected(user_client):
    r = TestClient(app).post("/auth/register", json={**USER, "name": "Dup"})
    assert r.status_code == 409


def test_users_only_see_their_own_contracts(user_client, other_client, admin_client, service_pdf):
    cid = _upload(user_client, service_pdf)
    assert cid in [c["id"] for c in user_client.get("/contracts").json()]
    # another user can't list, open, download or delete it (404 - existence not leaked)
    assert cid not in [c["id"] for c in other_client.get("/contracts").json()]
    for path in (f"/contracts/{cid}", f"/contracts/{cid}/file", f"/contracts/{cid}/report"):
        assert other_client.get(path).status_code == 404, path
    assert other_client.delete(f"/contracts/{cid}").status_code == 404
    # admin can open any contract and sees it in the org-wide list with its owner
    detail = admin_client.get(f"/contracts/{cid}").json()
    assert detail["owner"]["email"] == USER["email"] and detail["is_mine"] is False
    rows = admin_client.get("/admin/contracts").json()
    assert any(r["id"] == cid and r["owner_email"] == USER["email"] for r in rows)


def test_admin_endpoints_forbidden_for_users(user_client):
    assert user_client.get("/admin/users").status_code == 403
    assert user_client.get("/admin/stats").status_code == 403
    assert user_client.post("/templates", json={"name": "x", "content": "y"}).status_code == 403
    assert user_client.post("/policies", json={"name": "x", "rules": []}).status_code == 403
    assert user_client.get("/templates").status_code == 200  # read is allowed


def test_admin_user_management(admin_client):
    r = admin_client.post(
        "/admin/users",
        json={"name": "Temp", "email": "temp@example.com", "password": "temp-pass-123"},
    )
    assert r.status_code == 201
    uid = r.json()["id"]
    users = admin_client.get("/admin/users").json()
    assert any(u["email"] == "temp@example.com" for u in users)

    # deactivated users can't sign in
    admin_client.patch(f"/admin/users/{uid}", json={"is_active": False})
    login = TestClient(app).post(
        "/auth/login", json={"email": "temp@example.com", "password": "temp-pass-123"}
    )
    assert login.status_code == 403

    # promote, then delete
    assert (
        admin_client.patch(f"/admin/users/{uid}", json={"role": "admin", "is_active": True}).json()[
            "role"
        ]
        == "admin"
    )
    assert admin_client.delete(f"/admin/users/{uid}").status_code == 204

    stats = admin_client.get("/admin/stats").json()
    assert stats["users"] >= 2 and "contracts_per_user" in stats


def test_admin_cannot_remove_last_admin_or_self(admin_client):
    me = admin_client.get("/auth/me").json()
    assert admin_client.patch(f"/admin/users/{me['id']}", json={"role": "user"}).status_code == 400
    assert admin_client.delete(f"/admin/users/{me['id']}").status_code == 400


def test_change_password(other_client):
    from tests.conftest import OTHER

    assert (
        other_client.post(
            "/auth/password", json={"current_password": "nope-nope", "new_password": "new-pass-456"}
        ).status_code
        == 400
    )
    assert (
        other_client.post(
            "/auth/password",
            json={"current_password": OTHER["password"], "new_password": "new-pass-456"},
        ).status_code
        == 204
    )
    assert (
        TestClient(app)
        .post("/auth/login", json={"email": OTHER["email"], "password": "new-pass-456"})
        .status_code
        == 200
    )


def test_admin_password_unchanged(admin_client):
    assert (
        TestClient(app)
        .post("/auth/login", json={"email": ADMIN["email"], "password": ADMIN["password"]})
        .status_code
        == 200
    )
