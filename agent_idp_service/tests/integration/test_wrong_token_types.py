from __future__ import annotations


def test_mint_rejects_capability_token_as_agent_access(client, seeded_agent):
    # Build a real capability token first.
    att = client.post(
        "/attest/exchange",
        json={
            "kind": "k8s",
            "cluster": "cluster-1",
            "namespace": "sre",
            "service_account": "operator",
            "agent_id": "operator-prod",
            "env": "prod",
            "session_id": "sess-z",
            "trace_id": "trace-z",
        },
    )
    access_token = att.json()["access_token"]
    grant = client.post(
        "/grants",
        json={
            "grant_type": "human_approval",
            "granted_by": "user:raj@example.com",
            "agent_id": "operator-prod",
            "env": "prod",
            "action": "github.actions.rollback",
            "resource": "github:repo:org/app",
            "purpose": "incident_response",
            "reason": "Elevated 5xx",
            "ticket": "INC-1",
            "mfa": True,
            "ttl_seconds": 600,
        },
    )
    minted = client.post(
        "/capabilities/mint",
        json={
            "agent_access_token": access_token,
            "grant_id": grant.json()["grant_id"],
            "session_id": "s",
            "trace_id": "t",
            "purpose": "p",
            "reason": "r",
            "ticket": "INC-1",
            "cap_action": "github.actions.rollback",
            "cap_resource": "github:repo:org/app",
            "constraints": {},
            "risk_level": "high",
            "limits": {"rate": "1/1m", "cost_budget": 1},
        },
    )
    capability_token = minted.json()["capability_token"]

    bad = client.post(
        "/capabilities/mint",
        json={
            "agent_access_token": capability_token,
            "grant_id": grant.json()["grant_id"],
            "session_id": "s2",
            "trace_id": "t2",
            "purpose": "p",
            "reason": "r",
            "ticket": "INC-1",
            "cap_action": "github.actions.rollback",
            "cap_resource": "github:repo:org/app",
            "constraints": {},
            "risk_level": "high",
            "limits": {"rate": "1/1m", "cost_budget": 1},
        },
    )
    assert bad.status_code == 401
    assert "invalid_agent_access_token" in bad.json()["detail"]


def test_gateway_rejects_agent_access_token(client, seeded_agent):
    att = client.post(
        "/attest/exchange",
        json={
            "kind": "k8s",
            "cluster": "cluster-1",
            "namespace": "sre",
            "service_account": "operator",
            "agent_id": "operator-prod",
            "env": "prod",
            "session_id": "sess-k",
            "trace_id": "trace-k",
        },
    )
    access_token = att.json()["access_token"]

    bad = client.post(
        "/gateway/execute",
        json={
            "capability_token": access_token,
            "tool": "github",
            "action": "github.actions.rollback",
            "resource": "github:repo:org/app",
            "params": {},
        },
    )
    assert bad.status_code == 401
    assert "invalid_capability_token" in bad.json()["detail"]
