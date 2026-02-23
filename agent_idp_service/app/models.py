from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class RuntimeBinding(BaseModel):
    kind: Literal["k8s", "spire", "cloud"] = "k8s"
    cluster: str
    namespace: str | None = None
    service_account: str | None = None
    spiffe_id: str | None = None


class Agent(BaseModel):
    agent_id: str
    tenant: str = "org:democorp"
    owner_principal: str
    self_identified_owner: str | None = None
    framework: str | None = None
    target_application: str | None = None
    trust_level: Literal["low", "medium", "high"] = "medium"
    allowed_envs: list[str] = Field(default_factory=lambda: ["stage"])
    runtime_bindings: list[RuntimeBinding] = Field(default_factory=list)
    status: Literal["active", "disabled"] = "active"


class AttestationInput(BaseModel):
    kind: Literal["k8s", "spire", "cloud"] = "k8s"
    cluster: str
    namespace: str | None = None
    service_account: str | None = None
    spiffe_id: str | None = None
    agent_id: str
    env: str
    session_id: str
    trace_id: str


class GrantCreate(BaseModel):
    grant_type: Literal["human_approval", "policy_auto"] = "human_approval"
    granted_by: str
    agent_id: str
    env: str
    action: str
    resource: str
    purpose: str
    reason: str
    ticket: str
    mfa: bool = False
    ttl_seconds: int = 1800


class Grant(BaseModel):
    grant_id: str
    grant_type: str
    granted_by: str
    agent_id: str
    env: str
    action: str
    resource: str
    purpose: str
    reason: str
    ticket: str
    mfa: bool
    granted_at: int
    expires_at: int
    status: Literal["pending", "approved", "revoked", "expired"] = "pending"


class CapabilityMintRequest(BaseModel):
    agent_access_token: str
    grant_id: str
    session_id: str
    trace_id: str
    purpose: str
    reason: str
    ticket: str
    cap_action: str
    cap_resource: str
    constraints: dict[str, Any] = Field(default_factory=dict)
    risk_level: Literal["low", "medium", "high"] = "medium"
    limits: dict[str, Any] = Field(default_factory=lambda: {"rate": "3/5m", "cost_budget": 100})


class ExecuteRequest(BaseModel):
    capability_token: str
    tool: Literal["github", "kubernetes", "grafana", "aws"]
    action: str
    resource: str
    params: dict[str, Any] = Field(default_factory=dict)
    presenter: str | None = None


class RevokeRequest(BaseModel):
    grant_id: str | None = None
    jti: str | None = None


class AuditEvent(BaseModel):
    event_id: str
    timestamp: int
    trace_id: str
    session_id: str
    agent_id: str
    grant_id: str | None = None
    jti: str | None = None
    decision: str
    action: str
    resource: str
    detail: dict[str, Any] = Field(default_factory=dict)
