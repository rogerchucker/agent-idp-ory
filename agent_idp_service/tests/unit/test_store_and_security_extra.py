from __future__ import annotations

from app.security import TokenService
from app.store import JsonStore


def test_store_handles_missing_audit_and_missing_update(tmp_path):
    store = JsonStore(state_file=tmp_path / "state.json", audit_file=tmp_path / "audit.log")
    assert store.list_audit(limit=10) == []
    assert store.update_grant("missing", {"status": "revoked"}) is None


def test_store_load_existing_state(tmp_path):
    state_file = tmp_path / "state.json"
    audit_file = tmp_path / "audit.log"
    one = JsonStore(state_file=state_file, audit_file=audit_file)
    one.upsert_agent({"agent_id": "a1"})

    two = JsonStore(state_file=state_file, audit_file=audit_file)
    assert two.get_agent("a1")["agent_id"] == "a1"


def test_token_service_reloads_existing_key(tmp_path):
    key_file = tmp_path / "keys.json"
    svc1 = TokenService(key_file=key_file)
    jwks1 = svc1.jwks()
    svc2 = TokenService(key_file=key_file)
    jwks2 = svc2.jwks()
    assert jwks1["keys"][0]["x"] == jwks2["keys"][0]["x"]
