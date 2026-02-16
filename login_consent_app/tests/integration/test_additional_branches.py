import pytest
from fastapi import HTTPException

import main


@pytest.mark.integration
def test_login_page_skip_branch_redirects(client, monkeypatch, user_cookie_header):
    async def fake_get(path, params=None):
        return {"skip": True}

    async def fake_put(path, payload, params=None):
        assert payload["subject"] == "user:raj@example.com"
        return {"redirect_to": "http://localhost:4454/oauth2/auth?login_verifier=skipped"}

    monkeypatch.setattr(main, "hydra_get", fake_get)
    monkeypatch.setattr(main, "hydra_put", fake_put)

    response = client.get(
        "/login",
        params={"login_challenge": "lc-1"},
        headers=user_cookie_header,
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "login_verifier=skipped" in response.headers["location"]


@pytest.mark.integration
def test_consent_page_skip_branch_redirects(client, monkeypatch):
    async def fake_get(path, params=None):
        return {
            "skip": True,
            "requested_scope": ["openid"],
            "requested_access_token_audience": ["tool-gateway"],
        }

    async def fake_put(path, payload, params=None):
        return {"redirect_to": "http://localhost:5555/callback?code=from-skip"}

    monkeypatch.setattr(main, "hydra_get", fake_get)
    monkeypatch.setattr(main, "hydra_put", fake_put)

    response = client.get("/consent", params={"consent_challenge": "cc-1"}, follow_redirects=False)
    assert response.status_code == 302
    assert "code=from-skip" in response.headers["location"]


@pytest.mark.integration
def test_admin_login_invalid_credentials(client):
    response = client.post("/admin/login", data={"username": "bad", "password": "bad"})
    assert response.status_code == 401
    assert "Invalid admin credentials" in response.text


@pytest.mark.integration
def test_admin_login_page_redirects_when_already_logged(client, admin_cookie_header):
    response = client.get("/admin/login", headers=admin_cookie_header, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/admin/clients"


@pytest.mark.integration
def test_admin_login_page_renders_when_logged_out(client):
    response = client.get("/admin/login")
    assert response.status_code == 200
    assert "Hydra Admin" in response.text


@pytest.mark.integration
def test_admin_clients_health_and_clients_error_rendered(client, admin_cookie_header, monkeypatch):
    async def fake_get(path, params=None):
        if path == "/admin/health/ready":
            raise HTTPException(status_code=500, detail="admin down")
        if path == "/health/ready":
            raise HTTPException(status_code=500, detail="health down")
        if path == "/admin/clients":
            raise HTTPException(status_code=500, detail="clients down")
        raise AssertionError(path)

    monkeypatch.setattr(main, "hydra_get", fake_get)

    response = client.get("/admin/clients", headers=admin_cookie_header)
    assert response.status_code == 200
    assert "Failed to fetch clients" in response.text


@pytest.mark.integration
def test_admin_clients_health_fallback_succeeds(client, admin_cookie_header, monkeypatch):
    calls = {"count": 0}

    async def fake_get(path, params=None):
        if path == "/admin/health/ready":
            calls["count"] += 1
            raise HTTPException(status_code=500, detail="admin down")
        if path == "/health/ready":
            return {"status": "ok"}
        if path == "/admin/clients":
            return []
        raise AssertionError(path)

    monkeypatch.setattr(main, "hydra_get", fake_get)
    response = client.get("/admin/clients", headers=admin_cookie_header)
    assert response.status_code == 200
    assert "Hydra status" in response.text
    assert "up" in response.text
    assert calls["count"] == 1


@pytest.mark.integration
def test_logout_redirects_to_login(client):
    response = client.get("/logout", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"].endswith("/login")


@pytest.mark.integration
def test_login_page_with_invalid_cookie_still_renders(client, monkeypatch):
    async def fake_get(path, params=None):
        return {"subject": "", "skip": False}

    monkeypatch.setattr(main, "hydra_get", fake_get)
    response = client.get(
        "/login",
        params={"login_challenge": "lc-1"},
        headers={"Cookie": f"{main.COOKIE_NAME}=not-a-valid-signed-cookie"},
    )
    assert response.status_code == 200
    assert "Sign in with a local mock user" in response.text


@pytest.mark.integration
def test_admin_client_new_page_authorized(client, admin_cookie_header):
    response = client.get("/admin/clients/new", headers=admin_cookie_header)
    assert response.status_code == 200
    assert "Create Client" in response.text


@pytest.mark.integration
def test_admin_client_new_page_unauthorized(client):
    response = client.get("/admin/clients/new", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/admin/login"


@pytest.mark.integration
def test_admin_client_new_post_unauthorized_redirects(client):
    response = client.post("/admin/clients/new", data={"client_id": "x"}, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/admin/login"


@pytest.mark.integration
def test_admin_client_new_error_renders_form(client, admin_cookie_header, monkeypatch):
    async def fake_post(path, payload):
        raise HTTPException(status_code=400, detail="invalid payload")

    monkeypatch.setattr(main, "hydra_post", fake_post)

    response = client.post(
        "/admin/clients/new",
        headers=admin_cookie_header,
        data={
            "client_id": "bad",
            "client_name": "Bad",
            "scope": "openid",
            "redirect_uris": "http://localhost:5555/callback",
            "grant_types": "authorization_code",
            "response_types": "code",
            "audience": "tool-gateway",
            "token_endpoint_auth_method": "client_secret_post",
            "client_secret": "secret123",
        },
    )
    assert response.status_code == 400
    assert "invalid payload" in response.text


@pytest.mark.integration
def test_admin_client_edit_page_unauthorized(client):
    response = client.get("/admin/clients/c1/edit", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/admin/login"


@pytest.mark.integration
def test_admin_client_edit_page_success(client, admin_cookie_header, monkeypatch):
    async def fake_get(path, params=None):
        return {
            "client_id": "c1",
            "client_name": "Client 1",
            "scope": "openid",
            "redirect_uris": ["http://localhost:5555/callback"],
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "audience": ["tool-gateway"],
            "token_endpoint_auth_method": "client_secret_post",
            "skip_consent": False,
        }

    monkeypatch.setattr(main, "hydra_get", fake_get)
    response = client.get("/admin/clients/c1/edit", headers=admin_cookie_header)
    assert response.status_code == 200
    assert "Edit Client" in response.text


@pytest.mark.integration
def test_admin_client_edit_submit_error_renders_form(client, admin_cookie_header, monkeypatch):
    async def fake_put(path, payload, params=None):
        raise HTTPException(status_code=400, detail="bad update")

    monkeypatch.setattr(main, "hydra_put", fake_put)

    response = client.post(
        "/admin/clients/c1/edit",
        headers=admin_cookie_header,
        data={
            "client_name": "Bad",
            "scope": "openid",
            "redirect_uris": "http://localhost:5555/callback",
            "grant_types": "authorization_code",
            "response_types": "code",
            "audience": "tool-gateway",
            "token_endpoint_auth_method": "client_secret_post",
            "client_secret": "newsecret",
        },
    )
    assert response.status_code == 400
    assert "bad update" in response.text


@pytest.mark.integration
def test_admin_client_edit_submit_unauthorized_redirects(client):
    response = client.post("/admin/clients/c1/edit", data={"client_name": "x"}, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/admin/login"


@pytest.mark.integration
def test_admin_client_delete_unauthorized_redirects(client):
    response = client.post("/admin/clients/c1/delete", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/admin/login"
