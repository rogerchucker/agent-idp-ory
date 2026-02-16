from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import AUDIT_FILE, DATA_DIR, STATE_FILE


@dataclass
class AppState:
    agents: dict[str, dict[str, Any]]
    grants: dict[str, dict[str, Any]]
    revoked_jti: dict[str, int]
    replay_cache: dict[str, int]


class JsonStore:
    def __init__(self, state_file: Path = STATE_FILE, audit_file: Path = AUDIT_FILE) -> None:
        self.state_file = state_file
        self.audit_file = audit_file
        self._lock = threading.Lock()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.state = self._load_state()

    def _load_state(self) -> AppState:
        if not self.state_file.exists():
            state = AppState(agents={}, grants={}, revoked_jti={}, replay_cache={})
            self._persist_state(state)
            return state

        raw = json.loads(self.state_file.read_text())
        return AppState(
            agents=raw.get("agents", {}),
            grants=raw.get("grants", {}),
            revoked_jti=raw.get("revoked_jti", {}),
            replay_cache=raw.get("replay_cache", {}),
        )

    def _persist_state(self, state: AppState) -> None:
        payload = {
            "agents": state.agents,
            "grants": state.grants,
            "revoked_jti": state.revoked_jti,
            "replay_cache": state.replay_cache,
        }
        self.state_file.write_text(json.dumps(payload, indent=2, sort_keys=True))

    def upsert_agent(self, agent: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self.state.agents[agent["agent_id"]] = agent
            self._persist_state(self.state)
            return agent

    def get_agent(self, agent_id: str) -> dict[str, Any] | None:
        return self.state.agents.get(agent_id)

    def create_grant(self, grant: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self.state.grants[grant["grant_id"]] = grant
            self._persist_state(self.state)
            return grant

    def get_grant(self, grant_id: str) -> dict[str, Any] | None:
        return self.state.grants.get(grant_id)

    def update_grant(self, grant_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        with self._lock:
            grant = self.state.grants.get(grant_id)
            if not grant:
                return None
            grant.update(updates)
            self._persist_state(self.state)
            return grant

    def revoke_jti(self, jti: str, expires_at: int) -> None:
        with self._lock:
            self.state.revoked_jti[jti] = expires_at
            self._persist_state(self.state)

    def is_revoked(self, jti: str) -> bool:
        return jti in self.state.revoked_jti

    def remember_jti(self, jti: str, expires_at: int) -> None:
        with self._lock:
            self.state.replay_cache[jti] = expires_at
            self._persist_state(self.state)

    def is_replayed(self, jti: str) -> bool:
        return jti in self.state.replay_cache

    def append_audit(self, event: dict[str, Any]) -> None:
        with self._lock:
            with self.audit_file.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event) + "\n")

    def list_audit(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self.audit_file.exists():
            return []
        lines = self.audit_file.read_text().splitlines()
        items = [json.loads(line) for line in lines if line.strip()]
        return items[-limit:]

    def cleanup(self, now_ts: int) -> None:
        with self._lock:
            self.state.revoked_jti = {
                jti: exp for jti, exp in self.state.revoked_jti.items() if exp > now_ts
            }
            self.state.replay_cache = {
                jti: exp for jti, exp in self.state.replay_cache.items() if exp > now_ts
            }
            for grant in self.state.grants.values():
                if grant.get("status") != "revoked" and grant.get("expires_at", 0) <= now_ts:
                    grant["status"] = "expired"
            self._persist_state(self.state)
