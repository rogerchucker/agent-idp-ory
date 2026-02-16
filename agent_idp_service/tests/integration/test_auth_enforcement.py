from __future__ import annotations

from dataclasses import replace

from fastapi.testclient import TestClient

import app.main as main_module
from app.policy import PolicyEngine
from app.security import TokenService
from app.store import JsonStore


def test_admin_and_internal_keys_enforced(tmp_path, monkeypatch):
    patched = replace(main_module.SETTINGS, admin_api_key="admin-secret", internal_api_key="internal-secret", app_env="development")
    monkeypatch.setattr(main_module, "SETTINGS", patched)

    app = main_module.create_app(
        store=JsonStore(state_file=tmp_path / "state.json", audit_file=tmp_path / "audit.log"),
        token_service=TokenService(key_file=tmp_path / "keys.json"),
        policy_engine=PolicyEngine(opa_url=""),
    )
    client = TestClient(app)

    no_admin = client.post(
        "/agents",
        json={
            "agent_id": "a1",
            "tenant": "org:democorp",
            "owner_principal": "u",
            "trust_level": "medium",
            "allowed_envs": ["stage"],
            "runtime_bindings": [],
            "status": "active",
        },
    )
    assert no_admin.status_code == 401

    ok_admin = client.post(
        "/agents",
        headers={"x-admin-api-key": "admin-secret"},
        json={
            "agent_id": "a1",
            "tenant": "org:democorp",
            "owner_principal": "u",
            "trust_level": "medium",
            "allowed_envs": ["stage"],
            "runtime_bindings": [],
            "status": "active",
        },
    )
    assert ok_admin.status_code == 200

    no_internal = client.post(
        "/attest/exchange",
        json={
            "kind": "k8s",
            "cluster": "c",
            "namespace": "n",
            "service_account": "s",
            "agent_id": "a1",
            "env": "stage",
            "session_id": "sess",
            "trace_id": "trace",
        },
    )
    assert no_internal.status_code == 401
