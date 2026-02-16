import pytest
from fastapi import HTTPException

import main


@pytest.mark.integration
def test_admin_login_logout(client) -> None:
    login = client.post(
        "/admin/login",
        data={"username": main.ADMIN_USERNAME, "password": main.ADMIN_PASSWORD},
        follow_redirects=False,
    )
    assert login.status_code == 302
    assert login.headers["location"] == "/admin/clients"
    assert main.ADMIN_COOKIE_NAME in login.headers.get("set-cookie", "")

    logout = client.get("/admin/logout", follow_redirects=False)
    assert logout.status_code == 302
    assert logout.headers["location"] == "/admin/login"


@pytest.mark.integration
def test_admin_clients_requires_auth(client) -> None:
    response = client.get("/admin/clients", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/admin/login"


@pytest.mark.integration
def test_admin_clients_lists_data(client, admin_cookie_header, monkeypatch) -> None:
    async def fake_get(path, params=None):
        if path in {"/admin/health/ready", "/health/ready"}:
            return {"status": "ok"}
        if path == "/admin/clients":
            return [{"client_id": "c1", "client_name": "Client 1", "scope": "openid", "redirect_uris": ["http://x"]}]
        raise AssertionError(path)

    monkeypatch.setattr(main, "hydra_get", fake_get)

    response = client.get("/admin/clients", headers=admin_cookie_header)
    assert response.status_code == 200
    assert "Client 1" in response.text
    assert "Hydra status" in response.text


@pytest.mark.integration
def test_admin_create_client_success(client, admin_cookie_header, monkeypatch) -> None:
    called = {}

    async def fake_post(path, payload):
        called["path"] = path
        called["payload"] = payload
        return {"client_id": payload["client_id"]}

    monkeypatch.setattr(main, "hydra_post", fake_post)

    response = client.post(
        "/admin/clients/new",
        headers=admin_cookie_header,
        data={
            "client_id": "c-new",
            "client_name": "Client New",
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

    assert response.status_code == 302
    assert response.headers["location"] == "/admin/clients"
    assert called["path"] == "/admin/clients"
    assert called["payload"]["client_id"] == "c-new"
    assert called["payload"]["skip_consent"] is True


@pytest.mark.integration
def test_admin_edit_client_not_found(client, admin_cookie_header, monkeypatch) -> None:
    async def fake_get(path, params=None):
        raise HTTPException(status_code=404, detail="missing")

    monkeypatch.setattr(main, "hydra_get", fake_get)

    response = client.get("/admin/clients/missing/edit", headers=admin_cookie_header)
    assert response.status_code == 404


@pytest.mark.integration
def test_admin_delete_client_redirects_even_on_error(client, admin_cookie_header, monkeypatch) -> None:
    async def fake_delete(path):
        raise HTTPException(status_code=500, detail="boom")

    monkeypatch.setattr(main, "hydra_delete", fake_delete)

    response = client.post("/admin/clients/c1/delete", headers=admin_cookie_header, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/admin/clients"
