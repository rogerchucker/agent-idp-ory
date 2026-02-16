from __future__ import annotations


def test_cloud_attestation_path(client):
    client.post(
        "/agents",
        json={
            "agent_id": "cloud-agent",
            "tenant": "org:democorp",
            "owner_principal": "user:raj@example.com",
            "trust_level": "medium",
            "allowed_envs": ["stage"],
            "runtime_bindings": [{"kind": "cloud", "cluster": "aws-usw2"}],
            "status": "active",
        },
    )

    resp = client.post(
        "/attest/exchange",
        json={
            "kind": "cloud",
            "cluster": "aws-usw2",
            "agent_id": "cloud-agent",
            "env": "stage",
            "session_id": "sess-cloud",
            "trace_id": "trace-cloud",
        },
    )
    assert resp.status_code == 200
