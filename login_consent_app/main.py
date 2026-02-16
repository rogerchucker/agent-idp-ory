import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from itsdangerous import BadSignature, URLSafeSerializer

HYDRA_ADMIN_URL = os.getenv("HYDRA_ADMIN_URL", "http://localhost:4445")
COOKIE_SECRET = os.getenv("COOKIE_SECRET", "local-dev-cookie-secret-change-me")
COOKIE_NAME = os.getenv("COOKIE_NAME", "lc_session")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:3000")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "adminpass123")
ADMIN_COOKIE_NAME = os.getenv("ADMIN_COOKIE_NAME", "lc_admin_session")

DEFAULT_GRANT_TYPES = ["authorization_code", "refresh_token"]
DEFAULT_RESPONSE_TYPES = ["code"]
DEFAULT_SCOPES = "openid offline_access profile email"
DEFAULT_AUDIENCE = ["tool-gateway", "agent-idp"]

MOCK_USERS = {
    "raj@example.com": {"password": "devpass123", "subject": "user:raj@example.com", "name": "Raj"},
    "ops@example.com": {"password": "devpass123", "subject": "user:ops@example.com", "name": "Ops User"},
}

app = FastAPI(title="Tiny Hydra Login+Consent")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
serializer = URLSafeSerializer(COOKIE_SECRET, salt="lc-session")
admin_serializer = URLSafeSerializer(COOKIE_SECRET, salt="lc-admin")


@app.on_event("startup")
async def startup_check() -> None:
    if os.getenv("SKIP_STARTUP_HYDRA_CHECK", "").lower() in {"1", "true", "yes"}:
        return
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.get(f"{HYDRA_ADMIN_URL}/health/ready")
            r.raise_for_status()
            return
        except Exception:
            r = await client.get(f"{HYDRA_ADMIN_URL}/admin/health/ready")
            r.raise_for_status()


def parse_multiline(value: str) -> list[str]:
    items = []
    for line in value.splitlines():
        line = line.strip()
        if line:
            items.append(line)
    return items


def get_session_subject(request: Request) -> str | None:
    cookie_val = request.cookies.get(COOKIE_NAME)
    if not cookie_val:
        return None
    try:
        data = serializer.loads(cookie_val)
    except BadSignature:
        return None
    return data.get("subject")


def build_session_cookie(subject: str) -> str:
    return serializer.dumps({"subject": subject, "issued_at": datetime.now(timezone.utc).isoformat()})


def get_admin_user(request: Request) -> str | None:
    cookie_val = request.cookies.get(ADMIN_COOKIE_NAME)
    if not cookie_val:
        return None
    try:
        data = admin_serializer.loads(cookie_val)
    except BadSignature:
        return None
    return data.get("username")


def build_admin_cookie(username: str) -> str:
    return admin_serializer.dumps({"username": username, "issued_at": datetime.now(timezone.utc).isoformat()})


async def hydra_get(path: str, params: dict[str, Any] | None = None) -> Any:
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(f"{HYDRA_ADMIN_URL}{path}", params=params)
        if res.status_code >= 400:
            raise HTTPException(status_code=res.status_code, detail=res.text)
        return res.json()


async def hydra_post(path: str, payload: dict[str, Any]) -> Any:
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.post(f"{HYDRA_ADMIN_URL}{path}", json=payload)
        if res.status_code >= 400:
            raise HTTPException(status_code=res.status_code, detail=res.text)
        return res.json()


async def hydra_put(
    path: str, payload: dict[str, Any], params: dict[str, Any] | None = None
) -> Any:
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.put(f"{HYDRA_ADMIN_URL}{path}", params=params, json=payload)
        if res.status_code >= 400:
            raise HTTPException(status_code=res.status_code, detail=res.text)
        return res.json()


async def hydra_delete(path: str) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.delete(f"{HYDRA_ADMIN_URL}{path}")
        if res.status_code >= 400:
            raise HTTPException(status_code=res.status_code, detail=res.text)


@app.get("/healthz")
async def healthz() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.get("/logout")
async def logout() -> RedirectResponse:
    response = RedirectResponse(url=f"{APP_BASE_URL}/login", status_code=302)
    response.delete_cookie(COOKIE_NAME, path="/")
    return response


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, login_challenge: str) -> HTMLResponse:
    existing_subject = get_session_subject(request)

    challenge = await hydra_get(
        "/admin/oauth2/auth/requests/login", params={"login_challenge": login_challenge}
    )

    if challenge.get("skip") and existing_subject:
        accepted = await hydra_put(
            "/admin/oauth2/auth/requests/login/accept",
            {
                "subject": existing_subject,
                "remember": True,
                "remember_for": 3600,
            },
            params={"login_challenge": login_challenge},
        )
        return RedirectResponse(url=accepted["redirect_to"], status_code=302)

    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "login_challenge": login_challenge,
            "error": None,
            "email": challenge.get("subject", ""),
        },
    )


@app.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    login_challenge: str = "",
    email: str = Form(...),
    password: str = Form(...),
    remember: str | None = Form(default=None),
) -> HTMLResponse:
    if not login_challenge:
        raise HTTPException(status_code=400, detail="login_challenge is required")
    user = MOCK_USERS.get(email.lower())
    if not user or user["password"] != password:
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "login_challenge": login_challenge,
                "error": "Invalid email or password.",
                "email": email,
            },
            status_code=401,
        )

    remember_bool = remember == "true"

    accepted = await hydra_put(
        "/admin/oauth2/auth/requests/login/accept",
        {
            "subject": user["subject"],
            "remember": remember_bool,
            "remember_for": 3600 if remember_bool else 0,
        },
        params={"login_challenge": login_challenge},
    )

    response = RedirectResponse(url=accepted["redirect_to"], status_code=302)
    response.set_cookie(
        key=COOKIE_NAME,
        value=build_session_cookie(user["subject"]),
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
        max_age=86400,
    )
    return response


@app.get("/consent", response_class=HTMLResponse)
async def consent_page(request: Request, consent_challenge: str) -> HTMLResponse:
    consent_req = await hydra_get(
        "/admin/oauth2/auth/requests/consent", params={"consent_challenge": consent_challenge}
    )

    if consent_req.get("skip"):
        accepted = await hydra_put(
            "/admin/oauth2/auth/requests/consent/accept",
            {
                "grant_scope": consent_req.get("requested_scope", []),
                "grant_access_token_audience": consent_req.get("requested_access_token_audience", []),
                "remember": True,
                "remember_for": 3600,
            },
            params={"consent_challenge": consent_challenge},
        )
        return RedirectResponse(url=accepted["redirect_to"], status_code=302)

    client = consent_req.get("client", {})
    return templates.TemplateResponse(
        request,
        "consent.html",
        {
            "consent_challenge": consent_challenge,
            "requested_scopes": consent_req.get("requested_scope", []),
            "client_id": client.get("client_id", "unknown"),
            "client_name": client.get("client_name", client.get("client_id", "unknown")),
        },
    )


@app.post("/consent")
async def consent_submit(
    consent_challenge: str = "",
    decision: str = Form(...),
    remember: str | None = Form(default=None),
) -> RedirectResponse:
    if not consent_challenge:
        raise HTTPException(status_code=400, detail="consent_challenge is required")
    consent_req = await hydra_get(
        "/admin/oauth2/auth/requests/consent", params={"consent_challenge": consent_challenge}
    )

    if decision == "deny":
        rejected = await hydra_put(
            "/admin/oauth2/auth/requests/consent/reject",
            {
                "error": "access_denied",
                "error_description": "The resource owner denied the request",
                "status_code": 403,
            },
            params={"consent_challenge": consent_challenge},
        )
        return RedirectResponse(url=rejected["redirect_to"], status_code=302)

    remember_bool = remember == "true"
    accepted = await hydra_put(
        "/admin/oauth2/auth/requests/consent/accept",
        {
            "grant_scope": consent_req.get("requested_scope", []),
            "grant_access_token_audience": consent_req.get("requested_access_token_audience", []),
            "remember": remember_bool,
            "remember_for": 3600 if remember_bool else 0,
            "session": {
                "id_token": {
                    "email": "raj@example.com",
                    "name": "Raj",
                }
            },
        },
        params={"consent_challenge": consent_challenge},
    )
    return RedirectResponse(url=accepted["redirect_to"], status_code=302)


@app.get("/admin")
async def admin_home(request: Request) -> RedirectResponse:
    if not get_admin_user(request):
        return RedirectResponse(url="/admin/login", status_code=302)
    return RedirectResponse(url="/admin/clients", status_code=302)


@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request) -> HTMLResponse:
    if get_admin_user(request):
        return RedirectResponse(url="/admin/clients", status_code=302)
    return templates.TemplateResponse(request, "admin_login.html", {"error": None})


@app.post("/admin/login", response_class=HTMLResponse)
async def admin_login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
) -> HTMLResponse:
    if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
        return templates.TemplateResponse(
            request,
            "admin_login.html",
            {"error": "Invalid admin credentials."},
            status_code=401,
        )

    response = RedirectResponse(url="/admin/clients", status_code=302)
    response.set_cookie(
        key=ADMIN_COOKIE_NAME,
        value=build_admin_cookie(username),
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
        max_age=86400,
    )
    return response


@app.get("/admin/logout")
async def admin_logout() -> RedirectResponse:
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie(ADMIN_COOKIE_NAME, path="/")
    return response


@app.get("/admin/clients", response_class=HTMLResponse)
async def admin_clients(request: Request) -> HTMLResponse:
    admin_user = get_admin_user(request)
    if not admin_user:
        return RedirectResponse(url="/admin/login", status_code=302)

    health = "down"
    clients: list[dict[str, Any]] = []
    error: str | None = None

    try:
        await hydra_get("/admin/health/ready")
        health = "up"
    except HTTPException:
        try:
            await hydra_get("/health/ready")
            health = "up"
        except HTTPException as exc:
            error = f"Hydra health check failed: {exc.detail}"

    try:
        raw_clients = await hydra_get("/admin/clients")
        if isinstance(raw_clients, list):
            clients = raw_clients
    except HTTPException as exc:
        error = f"Failed to fetch clients: {exc.detail}"

    return templates.TemplateResponse(
        request,
        "admin_clients.html",
        {
            "admin_user": admin_user,
            "clients": clients,
            "health": health,
            "error": error,
        },
    )


@app.get("/admin/clients/new", response_class=HTMLResponse)
async def admin_client_new_page(request: Request) -> HTMLResponse:
    admin_user = get_admin_user(request)
    if not admin_user:
        return RedirectResponse(url="/admin/login", status_code=302)

    return templates.TemplateResponse(
        request,
        "admin_client_form.html",
        {
            "admin_user": admin_user,
            "is_edit": False,
            "error": None,
            "client": {
                "client_id": "",
                "client_name": "",
                "scope": DEFAULT_SCOPES,
                "redirect_uris": ["http://localhost:5555/callback"],
                "grant_types": DEFAULT_GRANT_TYPES,
                "response_types": DEFAULT_RESPONSE_TYPES,
                "audience": DEFAULT_AUDIENCE,
                "token_endpoint_auth_method": "client_secret_post",
                "skip_consent": False,
            },
        },
    )


@app.post("/admin/clients/new", response_class=HTMLResponse)
async def admin_client_new_submit(
    request: Request,
    client_id: str = Form(...),
    client_name: str = Form(default=""),
    client_secret: str = Form(default=""),
    scope: str = Form(default=DEFAULT_SCOPES),
    redirect_uris: str = Form(default=""),
    grant_types: str = Form(default="authorization_code\nrefresh_token"),
    response_types: str = Form(default="code"),
    audience: str = Form(default="tool-gateway\nagent-idp"),
    token_endpoint_auth_method: str = Form(default="client_secret_post"),
    skip_consent: str | None = Form(default=None),
) -> HTMLResponse:
    admin_user = get_admin_user(request)
    if not admin_user:
        return RedirectResponse(url="/admin/login", status_code=302)

    payload: dict[str, Any] = {
        "client_id": client_id.strip(),
        "client_name": client_name.strip(),
        "scope": scope.strip(),
        "redirect_uris": parse_multiline(redirect_uris),
        "grant_types": parse_multiline(grant_types),
        "response_types": parse_multiline(response_types),
        "audience": parse_multiline(audience),
        "token_endpoint_auth_method": token_endpoint_auth_method.strip(),
        "skip_consent": skip_consent == "on",
    }
    if client_secret.strip():
        payload["client_secret"] = client_secret.strip()

    try:
        await hydra_post("/admin/clients", payload)
        return RedirectResponse(url="/admin/clients", status_code=302)
    except HTTPException as exc:
        return templates.TemplateResponse(
            request,
            "admin_client_form.html",
            {
                "admin_user": admin_user,
                "is_edit": False,
                "error": exc.detail,
                "client": payload,
            },
            status_code=400,
        )


@app.get("/admin/clients/{client_id}/edit", response_class=HTMLResponse)
async def admin_client_edit_page(request: Request, client_id: str) -> HTMLResponse:
    admin_user = get_admin_user(request)
    if not admin_user:
        return RedirectResponse(url="/admin/login", status_code=302)

    try:
        client = await hydra_get(f"/admin/clients/{quote(client_id, safe='')}")
    except HTTPException as exc:
        raise HTTPException(status_code=404, detail=f"Client not found: {exc.detail}") from exc

    return templates.TemplateResponse(
        request,
        "admin_client_form.html",
        {
            "admin_user": admin_user,
            "is_edit": True,
            "error": None,
            "client": client,
        },
    )


@app.post("/admin/clients/{client_id}/edit", response_class=HTMLResponse)
async def admin_client_edit_submit(
    request: Request,
    client_id: str,
    client_name: str = Form(default=""),
    client_secret: str = Form(default=""),
    scope: str = Form(default=DEFAULT_SCOPES),
    redirect_uris: str = Form(default=""),
    grant_types: str = Form(default="authorization_code\nrefresh_token"),
    response_types: str = Form(default="code"),
    audience: str = Form(default="tool-gateway\nagent-idp"),
    token_endpoint_auth_method: str = Form(default="client_secret_post"),
    skip_consent: str | None = Form(default=None),
) -> HTMLResponse:
    admin_user = get_admin_user(request)
    if not admin_user:
        return RedirectResponse(url="/admin/login", status_code=302)

    payload: dict[str, Any] = {
        "client_id": client_id,
        "client_name": client_name.strip(),
        "scope": scope.strip(),
        "redirect_uris": parse_multiline(redirect_uris),
        "grant_types": parse_multiline(grant_types),
        "response_types": parse_multiline(response_types),
        "audience": parse_multiline(audience),
        "token_endpoint_auth_method": token_endpoint_auth_method.strip(),
        "skip_consent": skip_consent == "on",
    }
    if client_secret.strip():
        payload["client_secret"] = client_secret.strip()

    try:
        await hydra_put(f"/admin/clients/{quote(client_id, safe='')}", payload)
        return RedirectResponse(url="/admin/clients", status_code=302)
    except HTTPException as exc:
        return templates.TemplateResponse(
            request,
            "admin_client_form.html",
            {
                "admin_user": admin_user,
                "is_edit": True,
                "error": exc.detail,
                "client": payload,
            },
            status_code=400,
        )


@app.post("/admin/clients/{client_id}/delete")
async def admin_client_delete(request: Request, client_id: str) -> RedirectResponse:
    if not get_admin_user(request):
        return RedirectResponse(url="/admin/login", status_code=302)

    try:
        await hydra_delete(f"/admin/clients/{quote(client_id, safe='')}")
    except HTTPException:
        pass

    return RedirectResponse(url="/admin/clients", status_code=302)
