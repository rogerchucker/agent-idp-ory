import asyncio
import os

import pytest
from fastapi import HTTPException

import main


class DummyResponse:
    def __init__(self, status_code=200, payload=None, text="ok"):
        self.status_code = status_code
        self._payload = payload if payload is not None else {"ok": True}
        self.text = text

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("boom")


class FakeAsyncClient:
    def __init__(self, get_responses=None, post_response=None, put_response=None, delete_response=None):
        self._get_responses = list(get_responses or [])
        self._post_response = post_response or DummyResponse()
        self._put_response = put_response or DummyResponse()
        self._delete_response = delete_response or DummyResponse()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, *_args, **_kwargs):
        if self._get_responses:
            return self._get_responses.pop(0)
        return DummyResponse()

    async def post(self, *_args, **_kwargs):
        return self._post_response

    async def put(self, *_args, **_kwargs):
        return self._put_response

    async def delete(self, *_args, **_kwargs):
        return self._delete_response


@pytest.mark.unit
def test_startup_check_skips_when_env_set(monkeypatch):
    monkeypatch.setenv("SKIP_STARTUP_HYDRA_CHECK", "true")
    asyncio.run(main.startup_check())


@pytest.mark.unit
def test_startup_check_fallback_success(monkeypatch):
    monkeypatch.setenv("SKIP_STARTUP_HYDRA_CHECK", "false")
    client = FakeAsyncClient(
        get_responses=[
            DummyResponse(status_code=500),
            DummyResponse(status_code=200),
        ]
    )
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda timeout=5.0: client)
    asyncio.run(main.startup_check())


@pytest.mark.unit
def test_startup_check_primary_success(monkeypatch):
    monkeypatch.setenv("SKIP_STARTUP_HYDRA_CHECK", "false")
    client = FakeAsyncClient(get_responses=[DummyResponse(status_code=200)])
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda timeout=5.0: client)
    asyncio.run(main.startup_check())


@pytest.mark.unit
def test_startup_check_raises_when_both_fail(monkeypatch):
    monkeypatch.setenv("SKIP_STARTUP_HYDRA_CHECK", "false")
    client = FakeAsyncClient(
        get_responses=[
            DummyResponse(status_code=500),
            DummyResponse(status_code=500),
        ]
    )
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda timeout=5.0: client)
    with pytest.raises(RuntimeError):
        asyncio.run(main.startup_check())


@pytest.mark.unit
def test_hydra_http_wrappers_success(monkeypatch):
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda timeout=10.0: FakeAsyncClient())
    assert asyncio.run(main.hydra_get("/x")) == {"ok": True}
    assert asyncio.run(main.hydra_post("/x", {"a": 1})) == {"ok": True}
    assert asyncio.run(main.hydra_put("/x", {"a": 1})) == {"ok": True}
    assert asyncio.run(main.hydra_delete("/x")) is None


@pytest.mark.unit
def test_hydra_http_wrappers_raise_http_exception(monkeypatch):
    err = DummyResponse(status_code=500, text="failed")
    monkeypatch.setattr(
        main.httpx,
        "AsyncClient",
        lambda timeout=10.0: FakeAsyncClient(
            get_responses=[err],
            post_response=err,
            put_response=err,
            delete_response=err,
        ),
    )

    with pytest.raises(HTTPException):
        asyncio.run(main.hydra_get("/x"))
    with pytest.raises(HTTPException):
        asyncio.run(main.hydra_post("/x", {"a": 1}))
    with pytest.raises(HTTPException):
        asyncio.run(main.hydra_put("/x", {"a": 1}))
    with pytest.raises(HTTPException):
        asyncio.run(main.hydra_delete("/x"))


@pytest.mark.unit
def test_get_session_subject_bad_signature_returns_none(client) -> None:
    response = client.get("/healthz", headers={"Cookie": f"{main.COOKIE_NAME}=bad-token"})
    assert response.status_code == 200
