from __future__ import annotations

from app.config import CAPABILITY_TOKEN_AUDIENCE


def _attest(client):
    resp = client.post(
        "/attest/exchange",
        json={
            "kind": "k8s",
            "cluster": "cluster-1",
            "namespace": "sre",
            "service_account": "operator",
            "agent_id": "operator-prod",
            "env": "prod",
            "session_id": "sess-1",
            "trace_id": "trace-1",
        },
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _grant(client):
    resp = client.post(
        "/grants",
        json={
            "grant_type": "human_approval",
            "granted_by": "user:raj@example.com",
            "agent_id": "operator-prod",
            "env": "prod",
            "action": "github.actions.rollback",
            "resource": "github:repo:org/app",
            "purpose": "incident_response",
            "reason": "Elevated 5xx after deploy",
            "ticket": "INC-1234",
            "mfa": True,
            "ttl_seconds": 600,
        },
    )
    assert resp.status_code == 200
    return resp.json()["grant_id"]


def test_agent_readback(client, seeded_agent):
    resp = client.get("/agents/operator-prod")
    assert resp.status_code == 200
    assert resp.json()["owner_principal"] == "user:raj@example.com"


def test_agent_readback_with_optional_identity_metadata(client):
    create = client.post(
        "/agents",
        json={
            "agent_id": "operator-metadata",
            "tenant": "org:democorp",
            "owner_principal": "user:raj@example.com",
            "self_identified_owner": "team:sre-platform",
            "framework": "openai-agents",
            "target_application": "incident-manager",
            "trust_level": "high",
            "allowed_envs": ["prod"],
            "runtime_bindings": [
                {
                    "kind": "k8s",
                    "cluster": "cluster-1",
                    "namespace": "sre",
                    "service_account": "operator",
                }
            ],
            "status": "active",
        },
    )
    assert create.status_code == 200
    created = create.json()
    assert created["framework"] == "openai-agents"
    assert created["self_identified_owner"] == "team:sre-platform"
    assert created["target_application"] == "incident-manager"

    read = client.get("/agents/operator-metadata")
    assert read.status_code == 200
    read_back = read.json()
    assert read_back["framework"] == "openai-agents"
    assert read_back["self_identified_owner"] == "team:sre-platform"
    assert read_back["target_application"] == "incident-manager"


def test_attestation_invalid_binding_denied(client, seeded_agent):
    resp = client.post(
        "/attest/exchange",
        json={
            "kind": "k8s",
            "cluster": "cluster-x",
            "namespace": "sre",
            "service_account": "operator",
            "agent_id": "operator-prod",
            "env": "prod",
            "session_id": "sess-1",
            "trace_id": "trace-1",
        },
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "attestation_invalid"


def test_mint_policy_deny_on_change_freeze(client, seeded_agent):
    access_token = _attest(client)
    grant_id = _grant(client)

    resp = client.post(
        "/capabilities/mint",
        json={
            "agent_access_token": access_token,
            "grant_id": grant_id,
            "session_id": "sess-2",
            "trace_id": "trace-2",
            "purpose": "incident_response",
            "reason": "Need rollback",
            "ticket": "INC-1234",
            "cap_action": "github.actions.rollback",
            "cap_resource": "github:repo:org/app",
            "constraints": {"change_freeze": True},
            "risk_level": "high",
            "limits": {"rate": "3/5m", "cost_budget": 100},
        },
    )
    assert resp.status_code == 403
    assert "policy_denied" in resp.json()["detail"]


def test_gateway_scope_mismatch_denied(client, seeded_agent):
    access_token = _attest(client)
    grant_id = _grant(client)
    minted = client.post(
        "/capabilities/mint",
        json={
            "agent_access_token": access_token,
            "grant_id": grant_id,
            "session_id": "sess-3",
            "trace_id": "trace-3",
            "purpose": "incident_response",
            "reason": "Need rollback",
            "ticket": "INC-1234",
            "cap_action": "github.actions.rollback",
            "cap_resource": "github:repo:org/app",
            "constraints": {},
            "risk_level": "high",
            "limits": {"rate": "3/5m", "cost_budget": 100},
        },
    )
    token = minted.json()["capability_token"]

    resp = client.post(
        "/gateway/execute",
        json={
            "capability_token": token,
            "tool": "github",
            "action": "github.actions.delete_repo",
            "resource": "github:repo:org/app",
            "params": {},
        },
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "capability_scope_mismatch"


def test_jwks_and_audit_endpoint(client, seeded_agent):
    assert client.get("/.well-known/jwks.json").status_code == 200

    _attest(client)
    events = client.get("/audit/events?limit=10")
    assert events.status_code == 200
    assert len(events.json()["events"]) >= 1


def test_revoke_grant_and_token(client, seeded_agent):
    access_token = _attest(client)
    grant_id = _grant(client)
    minted = client.post(
        "/capabilities/mint",
        json={
            "agent_access_token": access_token,
            "grant_id": grant_id,
            "session_id": "sess-4",
            "trace_id": "trace-4",
            "purpose": "incident_response",
            "reason": "Need rollback",
            "ticket": "INC-1234",
            "cap_action": "github.actions.rollback",
            "cap_resource": "github:repo:org/app",
            "constraints": {},
            "risk_level": "high",
            "limits": {"rate": "3/5m", "cost_budget": 100},
        },
    )
    jti = minted.json()["jti"]

    revoke = client.post("/grants/revoke", json={"grant_id": grant_id, "jti": jti})
    assert revoke.status_code == 200

    token = minted.json()["capability_token"]
    exec_resp = client.post(
        "/gateway/execute",
        json={
            "capability_token": token,
            "tool": "github",
            "action": "github.actions.rollback",
            "resource": "github:repo:org/app",
            "params": {},
        },
    )
    assert exec_resp.status_code == 403
    assert exec_resp.json()["detail"] == "token_revoked"
