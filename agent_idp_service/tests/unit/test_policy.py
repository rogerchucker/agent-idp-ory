from __future__ import annotations

from app.policy import PolicyEngine


BASE_INPUT = {
    "env": "prod",
    "grant": {
        "status": "approved",
        "expires_at": 4_000_000_000,
        "env": "prod",
        "action": "github.actions.rollback",
        "resource": "github:repo:org/app",
        "mfa": True,
    },
    "cap": {
        "action": "github.actions.rollback",
        "resource": "github:repo:org/app",
        "constraints": {},
    },
    "risk": {"level": "high", "step_up_required": False},
    "change_freeze": False,
}


def test_local_policy_allow():
    allowed, reason = PolicyEngine(opa_url="").evaluate(BASE_INPUT)
    assert allowed is True
    assert reason == "allowed"


def test_local_policy_denies_on_mfa_missing():
    data = dict(BASE_INPUT)
    data["grant"] = dict(BASE_INPUT["grant"])
    data["grant"]["mfa"] = False
    allowed, reason = PolicyEngine(opa_url="").evaluate(data)
    assert allowed is False
    assert reason == "step_up_required"


def test_local_policy_denies_on_change_freeze():
    data = dict(BASE_INPUT)
    data["change_freeze"] = True
    allowed, reason = PolicyEngine(opa_url="").evaluate(data)
    assert allowed is False
    assert reason == "global_guardrail_change_freeze"


def test_local_policy_denies_on_expired():
    data = dict(BASE_INPUT)
    data["grant"] = dict(BASE_INPUT["grant"])
    data["grant"]["expires_at"] = 1
    allowed, reason = PolicyEngine(opa_url="").evaluate(data)
    assert allowed is False
    assert reason == "grant_expired"


def test_local_policy_denies_on_env_mismatch():
    data = dict(BASE_INPUT)
    data["grant"] = dict(BASE_INPUT["grant"])
    data["grant"]["env"] = "stage"
    allowed, reason = PolicyEngine(opa_url="").evaluate(data)
    assert allowed is False
    assert reason == "grant_env_mismatch"


def test_local_policy_denies_on_action_and_resource_mismatch():
    data = dict(BASE_INPUT)
    data["grant"] = dict(BASE_INPUT["grant"])
    data["grant"]["action"] = "x"
    allowed, reason = PolicyEngine(opa_url="").evaluate(data)
    assert allowed is False
    assert reason == "grant_action_mismatch"

    data2 = dict(BASE_INPUT)
    data2["grant"] = dict(BASE_INPUT["grant"])
    data2["grant"]["resource"] = "x"
    allowed2, reason2 = PolicyEngine(opa_url="").evaluate(data2)
    assert allowed2 is False
    assert reason2 == "grant_resource_mismatch"
