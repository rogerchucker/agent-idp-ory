import main


def test_parse_multiline_filters_and_trims() -> None:
    raw = "  one\n\n two \nthree\n  "
    assert main.parse_multiline(raw) == ["one", "two", "three"]


def test_build_and_parse_user_cookie_roundtrip(client) -> None:
    token = main.build_session_cookie("user:abc")
    response = client.get("/healthz", headers={"Cookie": f"{main.COOKIE_NAME}={token}"})
    assert response.status_code == 200


def test_build_and_parse_admin_cookie_roundtrip(client) -> None:
    token = main.build_admin_cookie("admin")
    response = client.get("/admin", headers={"Cookie": f"{main.ADMIN_COOKIE_NAME}={token}"}, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/admin/clients"


def test_invalid_cookie_returns_no_session(client) -> None:
    response = client.get("/admin", headers={"Cookie": f"{main.ADMIN_COOKIE_NAME}=tampered"}, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/admin/login"
