from __future__ import annotations


def _seed_and_attest(client, seeded_agent):
    att = client.post(
        "/attest/exchange",
        json={
            "kind": "k8s",
            "cluster": "cluster-1",
            "namespace": "sre",
            "service_account": "operator",
            "agent_id": "operator-prod",
            "env": "prod",
            "session_id": "sess-t",
            "trace_id": "trace-t",
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
    return access_token, grant.json()["grant_id"]


def test_mint_grant_not_found(client, seeded_agent):
    access_token, _ = _seed_and_attest(client, seeded_agent)
    resp = client.post(
        "/capabilities/mint",
        json={
            "agent_access_token": access_token,
            "grant_id": "missing",
            "session_id": "s",
            "trace_id": "t",
            "purpose": "p",
            "reason": "r",
            "ticket": "INC-1",
            "cap_action": "a",
            "cap_resource": "r",
            "constraints": {},
            "risk_level": "low",
            "limits": {"rate": "1/1m", "cost_budget": 1},
        },
    )
    assert resp.status_code == 404


def test_mint_grant_agent_mismatch(client, seeded_agent):
    access_token, _ = _seed_and_attest(client, seeded_agent)

    client.post(
        "/agents",
        json={
            "agent_id": "other",
            "tenant": "org:democorp",
            "owner_principal": "user:someone@example.com",
            "trust_level": "medium",
            "allowed_envs": ["prod"],
            "runtime_bindings": [{"kind": "k8s", "cluster": "cluster-1", "namespace": "sre", "service_account": "other"}],
            "status": "active",
        },
    )
    grant = client.post(
        "/grants",
        json={
            "grant_type": "human_approval",
            "granted_by": "user:raj@example.com",
            "agent_id": "other",
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

    resp = client.post(
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
    assert resp.status_code == 403
    assert resp.json()["detail"] == "grant_agent_mismatch"


def test_gateway_presenter_mismatch(client, seeded_agent):
    access_token, grant_id = _seed_and_attest(client, seeded_agent)
    minted = client.post(
        "/capabilities/mint",
        json={
            "agent_access_token": access_token,
            "grant_id": grant_id,
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
    token = minted.json()["capability_token"]

    exec_resp = client.post(
        "/gateway/execute",
        json={
            "capability_token": token,
            "tool": "github",
            "action": "github.actions.rollback",
            "resource": "github:repo:org/app",
            "params": {},
            "presenter": "agent-runtime:k8s:cluster-1:ns/sre:sa/other",
        },
    )
    assert exec_resp.status_code == 403
    assert exec_resp.json()["detail"] == "presenter_mismatch"
