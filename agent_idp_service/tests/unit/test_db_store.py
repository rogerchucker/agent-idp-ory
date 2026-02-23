from __future__ import annotations

from app.db_store import SqlStore


def test_sql_store_roundtrip(tmp_path):
    db_url = f"sqlite+pysqlite:///{tmp_path / 'idp.db'}"
    store = SqlStore(db_url)

    store.upsert_agent(
        {
            "agent_id": "a1",
            "allowed_envs": ["prod"],
            "framework": "langgraph",
            "self_identified_owner": "team:incident-response",
            "target_application": "incident-manager",
        }
    )
    assert store.get_agent("a1")["allowed_envs"] == ["prod"]
    assert store.get_agent("a1")["target_application"] == "incident-manager"

    store.create_grant({"grant_id": "g1", "status": "approved", "expires_at": 100})
    assert store.get_grant("g1")["status"] == "approved"

    store.update_grant("g1", {"status": "revoked"})
    assert store.get_grant("g1")["status"] == "revoked"

    store.revoke_jti("j1", 1)
    assert store.is_revoked("j1") is True

    store.remember_jti("j2", 1)
    assert store.is_replayed("j2") is True

    store.append_audit({"timestamp": 1, "event_id": "e1"})
    assert store.list_audit(limit=10)[0]["event_id"] == "e1"

    store.cleanup(now_ts=2)
    assert store.is_revoked("j1") is False
    assert store.is_replayed("j2") is False
    store.close()


def test_sql_store_missing_update(tmp_path):
    db_url = f"sqlite+pysqlite:///{tmp_path / 'idp2.db'}"
    store = SqlStore(db_url)
    assert store.update_grant("missing", {"status": "revoked"}) is None
    store.close()
