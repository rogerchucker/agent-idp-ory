from __future__ import annotations

from app.policy import PolicyEngine


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, *_args, **_kwargs):
        return _FakeResponse(self.payload)


def test_opa_dict_result(monkeypatch):
    monkeypatch.setattr("app.policy.httpx.Client", lambda timeout: _FakeClient({"result": {"allow": True, "reason": "opa_ok"}}))
    allowed, reason = PolicyEngine(opa_url="http://opa").evaluate({"env": "stage", "grant": {}, "cap": {}})
    assert allowed is True
    assert reason == "opa_ok"


def test_opa_bool_result(monkeypatch):
    monkeypatch.setattr("app.policy.httpx.Client", lambda timeout: _FakeClient({"result": False}))
    allowed, reason = PolicyEngine(opa_url="http://opa").evaluate({"env": "stage", "grant": {}, "cap": {}})
    assert allowed is False
    assert reason == "opa_decision"
