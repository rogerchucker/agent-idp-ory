from __future__ import annotations

from app.config import AGENT_TOKEN_AUDIENCE, CAPABILITY_TOKEN_AUDIENCE
from app.security import TokenService


def test_jwks_and_agent_token_decode(tmp_path):
    svc = TokenService(key_file=tmp_path / "keys.json")
    jwks = svc.jwks()
    assert jwks["keys"][0]["alg"] == "EdDSA"

    token, claims = svc.mint_agent_access_token(
        agent_id="operator-prod",
        env="prod",
        tenant="org:democorp",
        azp="agent-runtime:k8s:cluster-1:ns/sre:sa/operator",
        trace_id="trace-1",
        session_id="session-1",
    )
    decoded = svc.decode(token, audience=AGENT_TOKEN_AUDIENCE)
    assert decoded["sub"] == claims["sub"]
    assert decoded["token_type"] == "agent_access"


def test_capability_token_decode(tmp_path):
    svc = TokenService(key_file=tmp_path / "keys.json")
    token, _ = svc.mint_capability_token(
        agent_id="operator-prod",
        tenant="org:democorp",
        env="prod",
        azp="agent-runtime:k8s:cluster-1:ns/sre:sa/operator",
        session={
            "session_id": "sess-1",
            "trace_id": "trace-1",
            "purpose": "incident_response",
            "reason": "Elevated 5xx",
            "ticket": "INC-1234",
        },
        delegation={
            "grant_id": "grant-1",
            "grant_type": "human_approval",
            "granted_by": "user:raj@example.com",
            "granted_at": 1,
            "expires_at": 9999999999,
            "mfa": True,
        },
        cap={"action": "github.actions.rollback", "resource": "github:repo:org/app", "constraints": {}},
        risk={"level": "high", "step_up_required": False},
        limits={"rate": "3/5m", "cost_budget": 100},
    )
    decoded = svc.decode(token, audience=CAPABILITY_TOKEN_AUDIENCE)
    assert decoded["cap"]["action"] == "github.actions.rollback"
    assert decoded["token_type"] == "capability"
