from __future__ import annotations

import json
from typing import Any

from sqlalchemy import Column, Integer, String, Text, create_engine, delete, select
from sqlalchemy.orm import Session, declarative_base, sessionmaker

Base = declarative_base()


class AgentRow(Base):
    __tablename__ = "agent_idp_agents"
    agent_id = Column(String(255), primary_key=True)
    payload = Column(Text, nullable=False)


class GrantRow(Base):
    __tablename__ = "agent_idp_grants"
    grant_id = Column(String(255), primary_key=True)
    payload = Column(Text, nullable=False)


class RevokedRow(Base):
    __tablename__ = "agent_idp_revoked_jti"
    jti = Column(String(255), primary_key=True)
    expires_at = Column(Integer, nullable=False)


class ReplayRow(Base):
    __tablename__ = "agent_idp_replay_cache"
    jti = Column(String(255), primary_key=True)
    expires_at = Column(Integer, nullable=False)


class AuditRow(Base):
    __tablename__ = "agent_idp_audit"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(Integer, nullable=False)
    payload = Column(Text, nullable=False)


class SqlStore:
    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.session_local = sessionmaker(bind=self.engine, expire_on_commit=False, class_=Session)
        Base.metadata.create_all(self.engine)

    @staticmethod
    def _dump(payload: dict[str, Any]) -> str:
        return json.dumps(payload, sort_keys=True)

    @staticmethod
    def _load(payload: str) -> dict[str, Any]:
        return json.loads(payload)

    def upsert_agent(self, agent: dict[str, Any]) -> dict[str, Any]:
        with self.session_local() as db:
            row = db.get(AgentRow, agent["agent_id"])
            if row:
                row.payload = self._dump(agent)
            else:
                row = AgentRow(agent_id=agent["agent_id"], payload=self._dump(agent))
                db.add(row)
            db.commit()
        return agent

    def get_agent(self, agent_id: str) -> dict[str, Any] | None:
        with self.session_local() as db:
            row = db.get(AgentRow, agent_id)
            return self._load(row.payload) if row else None

    def create_grant(self, grant: dict[str, Any]) -> dict[str, Any]:
        with self.session_local() as db:
            row = GrantRow(grant_id=grant["grant_id"], payload=self._dump(grant))
            db.merge(row)
            db.commit()
        return grant

    def get_grant(self, grant_id: str) -> dict[str, Any] | None:
        with self.session_local() as db:
            row = db.get(GrantRow, grant_id)
            return self._load(row.payload) if row else None

    def update_grant(self, grant_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        with self.session_local() as db:
            row = db.get(GrantRow, grant_id)
            if not row:
                return None
            payload = self._load(row.payload)
            payload.update(updates)
            row.payload = self._dump(payload)
            db.commit()
            return payload

    def revoke_jti(self, jti: str, expires_at: int) -> None:
        with self.session_local() as db:
            db.merge(RevokedRow(jti=jti, expires_at=expires_at))
            db.commit()

    def is_revoked(self, jti: str) -> bool:
        with self.session_local() as db:
            return db.get(RevokedRow, jti) is not None

    def remember_jti(self, jti: str, expires_at: int) -> None:
        with self.session_local() as db:
            db.merge(ReplayRow(jti=jti, expires_at=expires_at))
            db.commit()

    def is_replayed(self, jti: str) -> bool:
        with self.session_local() as db:
            return db.get(ReplayRow, jti) is not None

    def append_audit(self, event: dict[str, Any]) -> None:
        with self.session_local() as db:
            db.add(AuditRow(timestamp=int(event.get("timestamp", 0)), payload=self._dump(event)))
            db.commit()

    def list_audit(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.session_local() as db:
            rows = db.execute(select(AuditRow).order_by(AuditRow.id.desc()).limit(limit)).scalars().all()
            rows.reverse()
            return [self._load(row.payload) for row in rows]

    def cleanup(self, now_ts: int) -> None:
        with self.session_local() as db:
            db.execute(delete(RevokedRow).where(RevokedRow.expires_at <= now_ts))
            db.execute(delete(ReplayRow).where(ReplayRow.expires_at <= now_ts))

            grants = db.execute(select(GrantRow)).scalars().all()
            for row in grants:
                payload = self._load(row.payload)
                if payload.get("status") != "revoked" and payload.get("expires_at", 0) <= now_ts:
                    payload["status"] = "expired"
                    row.payload = self._dump(payload)
            db.commit()

    def close(self) -> None:
        self.engine.dispose()
