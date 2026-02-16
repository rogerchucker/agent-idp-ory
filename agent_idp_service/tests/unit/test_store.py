from __future__ import annotations

from app.store import JsonStore


def test_store_roundtrip_and_cleanup(tmp_path):
    store = JsonStore(state_file=tmp_path / "state.json", audit_file=tmp_path / "audit.log")

    store.upsert_agent({"agent_id": "a1", "allowed_envs": ["prod"]})
    assert store.get_agent("a1")["allowed_envs"] == ["prod"]

    store.create_grant({"grant_id": "g1", "status": "approved", "expires_at": 1})
    store.update_grant("g1", {"status": "revoked"})
    assert store.get_grant("g1")["status"] == "revoked"

    store.revoke_jti("j1", 1)
    store.remember_jti("j2", 1)
    assert store.is_revoked("j1") is True
    assert store.is_replayed("j2") is True

    store.append_audit({"event_id": "e1"})
    assert store.list_audit(limit=10)[0]["event_id"] == "e1"

    store.cleanup(now_ts=2)
    assert store.is_revoked("j1") is False
    assert store.is_replayed("j2") is False


def test_cleanup_expires_non_revoked_grant(tmp_path):
    store = JsonStore(state_file=tmp_path / "state.json", audit_file=tmp_path / "audit.log")
    store.create_grant({"grant_id": "g2", "status": "approved", "expires_at": 1})
    store.cleanup(now_ts=2)
    assert store.get_grant("g2")["status"] == "expired"
