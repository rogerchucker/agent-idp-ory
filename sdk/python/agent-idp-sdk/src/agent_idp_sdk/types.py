from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

TrustLevel = Literal["low", "medium", "high"]
AgentStatus = Literal["active", "disabled"]


@dataclass(frozen=True)
class RuntimeBinding:
    kind: str
    cluster: str
    namespace: str
    service_account: str


@dataclass(frozen=True)
class AgentRegistration:
    agent_id: str
    tenant: str
    owner_principal: str
    trust_level: TrustLevel
    allowed_envs: list[str]
    runtime_bindings: list[RuntimeBinding]
    status: AgentStatus = "active"

    def to_payload(self) -> dict:
        data = asdict(self)
        return data
