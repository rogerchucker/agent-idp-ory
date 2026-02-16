import pytest

import main


@pytest.mark.e2e
def test_complete_login_then_consent_flow(client, monkeypatch) -> None:
    state = {
        "login_challenge": "lc-1",
        "consent_challenge": "cc-1",
        "login_accepted": False,
        "consent_accepted": False,
    }

    async def fake_get(path, params=None):
        if path == "/admin/oauth2/auth/requests/login":
            assert params["login_challenge"] == state["login_challenge"]
            return {"subject": "", "skip": False}

        if path == "/admin/oauth2/auth/requests/consent":
            assert params["consent_challenge"] == state["consent_challenge"]
            return {
                "requested_scope": ["openid", "profile"],
                "requested_access_token_audience": ["tool-gateway"],
                "client": {"client_id": "local-agent-idp-client", "client_name": "Local App"},
                "skip": False,
            }

        raise AssertionError(f"Unexpected GET path: {path}")

    async def fake_put(path, payload, params=None):
        if path == "/admin/oauth2/auth/requests/login/accept":
            assert params["login_challenge"] == state["login_challenge"]
            state["login_accepted"] = True
            return {
                "redirect_to": f"{main.APP_BASE_URL}/consent?consent_challenge={state['consent_challenge']}"
            }

        if path == "/admin/oauth2/auth/requests/consent/accept":
            assert params["consent_challenge"] == state["consent_challenge"]
            state["consent_accepted"] = True
            return {"redirect_to": "http://localhost:5555/callback?code=abc123&state=abc12345"}

        raise AssertionError(f"Unexpected PUT path: {path}")

    monkeypatch.setattr(main, "hydra_get", fake_get)
    monkeypatch.setattr(main, "hydra_put", fake_put)

    login_page = client.get("/login", params={"login_challenge": state["login_challenge"]})
    assert login_page.status_code == 200

    login_submit = client.post(
        "/login",
        params={"login_challenge": state["login_challenge"]},
        data={"email": "raj@example.com", "password": "devpass123", "remember": "true"},
        follow_redirects=False,
    )
    assert login_submit.status_code == 302
    assert "consent_challenge=" in login_submit.headers["location"]

    consent_page = client.get(login_submit.headers["location"])
    assert consent_page.status_code == 200
    assert "Requested scopes" in consent_page.text

    consent_submit = client.post(
        "/consent",
        params={"consent_challenge": state["consent_challenge"]},
        data={"decision": "allow", "remember": "true"},
        follow_redirects=False,
    )
    assert consent_submit.status_code == 302
    assert "code=abc123" in consent_submit.headers["location"]
    assert state["login_accepted"] is True
    assert state["consent_accepted"] is True


@pytest.mark.e2e
def test_admin_end_to_end_create_edit_delete(client, monkeypatch) -> None:
    db = {
        "c1": {
            "client_id": "c1",
            "client_name": "Client 1",
            "scope": "openid",
            "redirect_uris": ["http://localhost:5555/callback"],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "audience": ["tool-gateway"],
            "token_endpoint_auth_method": "client_secret_post",
            "skip_consent": False,
        }
    }

    async def fake_get(path, params=None):
        if path in {"/admin/health/ready", "/health/ready"}:
            return {"status": "ok"}
        if path == "/admin/clients":
            return list(db.values())
        if path.startswith("/admin/clients/"):
            cid = path.rsplit("/", 1)[-1]
            if cid not in db:
                raise main.HTTPException(status_code=404, detail="missing")
            return db[cid]
        raise AssertionError(path)

    async def fake_post(path, payload):
        db[payload["client_id"]] = payload
        return payload

    async def fake_put(path, payload, params=None):
        cid = path.rsplit("/", 1)[-1]
        db[cid] = payload
        return payload

    async def fake_delete(path):
        cid = path.rsplit("/", 1)[-1]
        db.pop(cid, None)

    monkeypatch.setattr(main, "hydra_get", fake_get)
    monkeypatch.setattr(main, "hydra_post", fake_post)
    monkeypatch.setattr(main, "hydra_put", fake_put)
    monkeypatch.setattr(main, "hydra_delete", fake_delete)

    login = client.post(
        "/admin/login",
        data={"username": main.ADMIN_USERNAME, "password": main.ADMIN_PASSWORD},
        follow_redirects=False,
    )
    assert login.status_code == 302
    cookie = login.headers["set-cookie"].split(";", 1)[0]

    list_before = client.get("/admin/clients", headers={"Cookie": cookie})
    assert "Client 1" in list_before.text

    create = client.post(
        "/admin/clients/new",
        headers={"Cookie": cookie},
        data={
            "client_id": "c2",
            "client_name": "Client 2",
            "scope": "openid profile",
            "redirect_uris": "http://localhost:5555/callback",
            "grant_types": "authorization_code\\nrefresh_token",
            "response_types": "code",
            "audience": "tool-gateway",
            "token_endpoint_auth_method": "client_secret_post",
            "skip_consent": "on",
        },
        follow_redirects=False,
    )
    assert create.status_code == 302
    assert "c2" in db

    edit = client.post(
        "/admin/clients/c2/edit",
        headers={"Cookie": cookie},
        data={
            "client_name": "Client 2 Updated",
            "scope": "openid",
            "redirect_uris": "http://localhost:5555/callback",
            "grant_types": "authorization_code",
            "response_types": "code",
            "audience": "tool-gateway",
            "token_endpoint_auth_method": "client_secret_post",
        },
        follow_redirects=False,
    )
    assert edit.status_code == 302
    assert db["c2"]["client_name"] == "Client 2 Updated"

    delete = client.post("/admin/clients/c2/delete", headers={"Cookie": cookie}, follow_redirects=False)
    assert delete.status_code == 302
    assert "c2" not in db
