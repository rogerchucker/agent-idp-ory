from __future__ import annotations

from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import create_app
from app.policy import PolicyEngine
from app.security import TokenService
from app.store import JsonStore


@pytest.fixture
def test_app(tmp_path: Path):
    state_file = tmp_path / "state.json"
    audit_file = tmp_path / "audit.log"
    key_file = tmp_path / "keys.json"

    store = JsonStore(state_file=state_file, audit_file=audit_file)
    tokens = TokenService(key_file=key_file)
    policy = PolicyEngine(opa_url="")

    app = create_app(store=store, token_service=tokens, policy_engine=policy)
    return app


@pytest.fixture
def client(test_app):
    return TestClient(test_app)


@pytest.fixture
def seeded_agent(client):
    payload = {
        "agent_id": "operator-prod",
        "tenant": "org:democorp",
        "owner_principal": "user:raj@example.com",
        "trust_level": "high",
        "allowed_envs": ["prod", "stage"],
        "runtime_bindings": [
            {
                "kind": "k8s",
                "cluster": "cluster-1",
                "namespace": "sre",
                "service_account": "operator",
            }
        ],
        "status": "active",
    }
    resp = client.post("/agents", json=payload)
    assert resp.status_code == 200
    return payload
