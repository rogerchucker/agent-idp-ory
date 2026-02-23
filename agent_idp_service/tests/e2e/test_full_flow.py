from __future__ import annotations


def test_happy_path_and_replay_protection(client, seeded_agent):
    att = client.post(
        "/attest/exchange",
        json={
            "kind": "k8s",
            "cluster": "cluster-1",
            "namespace": "sre",
            "service_account": "operator",
            "agent_id": "operator-prod",
            "env": "prod",
            "session_id": "sess-10",
            "trace_id": "trace-10",
        },
    )
    assert att.status_code == 200
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
            "reason": "Elevated 5xx after deploy",
            "ticket": "INC-1234",
            "mfa": True,
            "ttl_seconds": 600,
        },
    )
    assert grant.status_code == 200
    grant_id = grant.json()["grant_id"]

    minted = client.post(
        "/capabilities/mint",
        json={
            "agent_access_token": access_token,
            "grant_id": grant_id,
            "session_id": "sess-10",
            "trace_id": "trace-10",
            "purpose": "incident_response",
            "reason": "Elevated 5xx after deploy",
            "ticket": "INC-1234",
            "cap_action": "github.actions.rollback",
            "cap_resource": "github:repo:org/app",
            "constraints": {"branch": "main"},
            "risk_level": "high",
            "limits": {"rate": "3/5m", "cost_budget": 100},
        },
    )
    assert minted.status_code == 200
    cap_token = minted.json()["capability_token"]

    execute_first = client.post(
        "/gateway/execute",
        json={
            "capability_token": cap_token,
            "tool": "github",
            "action": "github.actions.rollback",
            "resource": "github:repo:org/app",
            "params": {"sha": "abc123"},
            "presenter": "agent-runtime:k8s:cluster-1:ns/sre:sa/operator",
        },
    )
    assert execute_first.status_code == 200
    assert execute_first.json()["status"] == "executed"

    execute_replay = client.post(
        "/gateway/execute",
        json={
            "capability_token": cap_token,
            "tool": "github",
            "action": "github.actions.rollback",
            "resource": "github:repo:org/app",
            "params": {"sha": "abc123"},
            "presenter": "agent-runtime:k8s:cluster-1:ns/sre:sa/operator",
        },
    )
    assert execute_replay.status_code == 409
    assert execute_replay.json()["detail"] == "replay_detected"

    events = client.get("/audit/events?limit=50")
    assert events.status_code == 200
    assert len(events.json()["events"]) >= 4


def test_happy_path_with_identity_metadata_roundtrip(client):
    create = client.post(
        "/agents",
        json={
            "agent_id": "operator-prod-meta",
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
                    "service_account": "operator-meta",
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

    readback = client.get("/agents/operator-prod-meta")
    assert readback.status_code == 200
    read = readback.json()
    assert read["framework"] == "openai-agents"
    assert read["self_identified_owner"] == "team:sre-platform"
    assert read["target_application"] == "incident-manager"

    att = client.post(
        "/attest/exchange",
        json={
            "kind": "k8s",
            "cluster": "cluster-1",
            "namespace": "sre",
            "service_account": "operator-meta",
            "agent_id": "operator-prod-meta",
            "env": "prod",
            "session_id": "sess-20",
            "trace_id": "trace-20",
        },
    )
    assert att.status_code == 200
    access_token = att.json()["access_token"]

    grant = client.post(
        "/grants",
        json={
            "grant_type": "human_approval",
            "granted_by": "user:raj@example.com",
            "agent_id": "operator-prod-meta",
            "env": "prod",
            "action": "github.actions.rollback",
            "resource": "github:repo:org/app",
            "purpose": "incident_response",
            "reason": "Elevated 5xx after deploy",
            "ticket": "INC-2234",
            "mfa": True,
            "ttl_seconds": 600,
        },
    )
    assert grant.status_code == 200
    grant_id = grant.json()["grant_id"]

    minted = client.post(
        "/capabilities/mint",
        json={
            "agent_access_token": access_token,
            "grant_id": grant_id,
            "session_id": "sess-20",
            "trace_id": "trace-20",
            "purpose": "incident_response",
            "reason": "Elevated 5xx after deploy",
            "ticket": "INC-2234",
            "cap_action": "github.actions.rollback",
            "cap_resource": "github:repo:org/app",
            "constraints": {"branch": "main"},
            "risk_level": "high",
            "limits": {"rate": "3/5m", "cost_budget": 100},
        },
    )
    assert minted.status_code == 200
    cap_token = minted.json()["capability_token"]

    execute = client.post(
        "/gateway/execute",
        json={
            "capability_token": cap_token,
            "tool": "github",
            "action": "github.actions.rollback",
            "resource": "github:repo:org/app",
            "params": {"sha": "def456"},
            "presenter": "agent-runtime:k8s:cluster-1:ns/sre:sa/operator-meta",
        },
    )
    assert execute.status_code == 200
    assert execute.json()["status"] == "executed"
