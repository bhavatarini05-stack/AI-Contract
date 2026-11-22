import time

import pytest


@pytest.fixture(scope="module")
def client(user_client):
    return user_client


def wait_for_job(client, job_id, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/jobs/{job_id}").json()
        if job["status"] in {"done", "failed"}:
            return job
        time.sleep(0.2)
    raise TimeoutError("analysis did not finish")


@pytest.fixture(scope="module")
def analysed(client, service_pdf):
    with open(service_pdf, "rb") as f:
        r = client.post(
            "/contracts", files={"file": ("service_agreement.pdf", f, "application/pdf")}
        )
    assert r.status_code == 201, r.text
    job = wait_for_job(client, r.json()["job"]["id"])
    assert job["status"] == "done", job.get("error")
    return r.json()["contract"]["id"]


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["llm"]["provider"] == "mock"


def test_user_flow(client, analysed):
    c = client.get(f"/contracts/{analysed}").json()
    assert c["page_count"] == 15
    assert c["contract_type"] == "Service Agreement"
    assert c["governing_law"] == "New York"
    terms = {t["key"]: t["display"] for t in c["terms"]}
    assert terms["term_length"] == "12 months"
    assert terms["auto_renew"].startswith("Yes")
    assert terms["notice_period"] == "60 days"
    assert any(
        f["message"] == "Liability cap is missing — standard is 1x fees" for f in c["risk_flags"]
    )
    assert c["report"]["summary"] and c["report"]["risk_score"] > 0
    assert c["report"]["negotiation"]


def test_report_html(client, analysed):
    r = client.get(f"/contracts/{analysed}/report")
    assert r.status_code == 200 and "Risk flags" in r.text and "not legal advice" in r.text


def test_file_download(client, analysed):
    r = client.get(f"/contracts/{analysed}/file")
    assert r.status_code == 200 and r.content.startswith(b"%PDF")


def test_compare_and_compliance(client, analysed):
    tmpl = client.get("/templates").json()
    assert tmpl, "standard template should be seeded"
    r = client.get(f"/contracts/{analysed}/compare/{tmpl[0]['id']}")
    assert r.status_code == 200 and r.json()["counts"]
    pol = client.get("/policies").json()
    r = client.get(f"/contracts/{analysed}/compliance/{pol[0]['id']}")
    assert r.status_code == 200 and r.json()["overall"] == "non_compliant"


def test_obligations_and_alerts(client, analysed):
    obls = client.get("/obligations").json()
    kinds = {o["kind"] for o in obls if o["contract_id"] == analysed}
    assert {"expiry", "renewal_notice"} <= kinds
    oid = next(o["id"] for o in obls if o["kind"] == "renewal_notice")
    assert client.patch(f"/obligations/{oid}", json={"status": "done"}).json()["status"] == "done"
    assert client.post("/alerts/scan").status_code == 200


def test_policy_validation(admin_client):
    r = admin_client.post(
        "/policies",
        json={"name": "bad", "rules": [{"id": "x", "requirement": "y", "must_include": ["("]}]},
    )
    assert r.status_code == 422


def test_rejects_non_pdf(client):
    r = client.post("/contracts", files={"file": ("x.exe", b"MZ...", "application/octet-stream")})
    assert r.status_code == 400


def test_integrations_disabled_by_default(client):
    items = client.get("/integrations").json()
    assert {i["key"] for i in items} == {"docusign", "dropbox_sign", "adobe_sign", "gdrive"}
    assert not any(i["configured"] for i in items)
    assert client.get("/integrations/gdrive/files").status_code == 400


def test_delete_contract(client, service_pdf):
    with open(service_pdf, "rb") as f:
        cid = client.post("/contracts", files={"file": ("d.pdf", f, "application/pdf")}).json()[
            "contract"
        ]["id"]
    wait_for_job(client, client.get(f"/contracts/{cid}").json()["latest_job"]["id"])
    assert client.delete(f"/contracts/{cid}").status_code == 204
    assert client.get(f"/contracts/{cid}").status_code == 404
