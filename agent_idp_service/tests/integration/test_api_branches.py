from __future__ import annotations


def _create_agent(client):
    client.post(
        "/agents",
        json={
            "agent_id": "operator-stage",
            "tenant": "org:democorp",
            "owner_principal": "user:raj@example.com",
            "trust_level": "medium",
            "allowed_envs": ["stage"],
            "runtime_bindings": [{"kind": "spire", "cluster": "cluster-1", "spiffe_id": "spiffe://svc/agent"}],
            "status": "active",
        },
    )


def test_healthz_and_missing_agent(client):
    assert client.get("/healthz").status_code == 200
    missing = client.get("/agents/nope")
    assert missing.status_code == 404


def test_create_grant_missing_agent(client):
    resp = client.post(
        "/grants",
        json={
            "granted_by": "user:raj@example.com",
            "agent_id": "nope",
            "env": "prod",
            "action": "a",
            "resource": "r",
            "purpose": "p",
            "reason": "r",
            "ticket": "t",
            "mfa": False,
            "ttl_seconds": 60,
        },
    )
    assert resp.status_code == 404


def test_attest_env_not_allowed(client, seeded_agent):
    resp = client.post(
        "/attest/exchange",
        json={
            "kind": "k8s",
            "cluster": "cluster-1",
            "namespace": "sre",
            "service_account": "operator",
            "agent_id": "operator-prod",
            "env": "dev",
            "session_id": "sess-1",
            "trace_id": "trace-1",
        },
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "env_not_allowed"


def test_spire_attestation_path(client):
    _create_agent(client)
    resp = client.post(
        "/attest/exchange",
        json={
            "kind": "spire",
            "cluster": "cluster-1",
            "spiffe_id": "spiffe://svc/agent",
            "agent_id": "operator-stage",
            "env": "stage",
            "session_id": "sess-1",
            "trace_id": "trace-1",
        },
    )
    assert resp.status_code == 200


def test_revoke_requires_identifier_and_unknown_grant(client):
    bad = client.post("/grants/revoke", json={})
    assert bad.status_code == 400

    missing = client.post("/grants/revoke", json={"grant_id": "missing"})
    assert missing.status_code == 404


def test_mint_invalid_agent_token(client, seeded_agent):
    resp = client.post(
        "/capabilities/mint",
        json={
            "agent_access_token": "bad",
            "grant_id": "g1",
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
    assert resp.status_code == 401


def test_gateway_invalid_token(client):
    resp = client.post(
        "/gateway/execute",
        json={
            "capability_token": "bad",
            "tool": "github",
            "action": "a",
            "resource": "r",
            "params": {},
        },
    )
    assert resp.status_code == 401


def test_readyz(client):
    resp = client.get("/readyz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"
