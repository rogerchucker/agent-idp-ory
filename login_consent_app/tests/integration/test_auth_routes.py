import pytest

import main


@pytest.mark.integration
def test_login_page_renders(client, monkeypatch) -> None:
    async def fake_get(path, params=None):
        assert path == "/admin/oauth2/auth/requests/login"
        assert params["login_challenge"] == "lc-1"
        return {"subject": "raj@example.com", "skip": False}

    monkeypatch.setattr(main, "hydra_get", fake_get)

    response = client.get("/login", params={"login_challenge": "lc-1"})
    assert response.status_code == 200
    assert "Sign in with a local mock user" in response.text


@pytest.mark.integration
def test_login_submit_accepts_and_sets_cookie(client, monkeypatch) -> None:
    async def fake_put(path, payload, params=None):
        assert path == "/admin/oauth2/auth/requests/login/accept"
        assert payload["subject"] == "user:raj@example.com"
        assert params["login_challenge"] == "lc-1"
        return {"redirect_to": "http://localhost:4454/oauth2/auth?login_verifier=ok"}

    monkeypatch.setattr(main, "hydra_put", fake_put)

    response = client.post(
        "/login",
        params={"login_challenge": "lc-1"},
        data={"email": "raj@example.com", "password": "devpass123", "remember": "true"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "login_verifier=ok" in response.headers["location"]
    assert main.COOKIE_NAME in response.headers.get("set-cookie", "")


@pytest.mark.integration
def test_login_submit_invalid_credentials(client) -> None:
    response = client.post(
        "/login",
        params={"login_challenge": "lc-1"},
        data={"email": "raj@example.com", "password": "wrong"},
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.text


@pytest.mark.integration
def test_consent_allow_flow(client, monkeypatch) -> None:
    async def fake_get(path, params=None):
        assert path == "/admin/oauth2/auth/requests/consent"
        return {
            "requested_scope": ["openid", "profile"],
            "requested_access_token_audience": ["tool-gateway"],
            "client": {"client_id": "c1", "client_name": "Client One"},
            "skip": False,
        }

    async def fake_put(path, payload, params=None):
        assert path == "/admin/oauth2/auth/requests/consent/accept"
        assert payload["grant_scope"] == ["openid", "profile"]
        return {"redirect_to": "http://localhost:5555/callback?code=abc"}

    monkeypatch.setattr(main, "hydra_get", fake_get)
    monkeypatch.setattr(main, "hydra_put", fake_put)

    page = client.get("/consent", params={"consent_challenge": "cc-1"})
    assert page.status_code == 200
    assert "Requested scopes" in page.text

    response = client.post(
        "/consent",
        params={"consent_challenge": "cc-1"},
        data={"decision": "allow", "remember": "true"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "code=abc" in response.headers["location"]


@pytest.mark.integration
def test_consent_deny_flow(client, monkeypatch) -> None:
    async def fake_get(path, params=None):
        return {
            "requested_scope": ["openid"],
            "requested_access_token_audience": [],
            "client": {"client_id": "c1"},
            "skip": False,
        }

    async def fake_put(path, payload, params=None):
        assert path == "/admin/oauth2/auth/requests/consent/reject"
        return {"redirect_to": "http://localhost:5555/callback?error=access_denied"}

    monkeypatch.setattr(main, "hydra_get", fake_get)
    monkeypatch.setattr(main, "hydra_put", fake_put)

    response = client.post(
        "/consent",
        params={"consent_challenge": "cc-1"},
        data={"decision": "deny"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "error=access_denied" in response.headers["location"]


@pytest.mark.integration
def test_missing_challenges_return_400(client) -> None:
    r1 = client.post("/login", data={"email": "raj@example.com", "password": "devpass123"})
    assert r1.status_code == 400
    assert "login_challenge is required" in r1.text

    r2 = client.post("/consent", data={"decision": "allow"})
    assert r2.status_code == 400
    assert "consent_challenge is required" in r2.text
