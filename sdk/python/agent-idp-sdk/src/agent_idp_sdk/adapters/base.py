from __future__ import annotations

from dataclasses import dataclass

from agent_idp_sdk.types import AgentRegistration, RuntimeBinding


@dataclass(frozen=True)
class AdapterDefaults:
    tenant: str = "org:democorp"
    owner_principal: str = "user:incident-manager@company.com"
    trust_level: str = "high"
    allowed_envs: tuple[str, ...] = ("prod", "stage")
    cluster: str = "cluster-1"
    namespace: str = "sre"


def build_registration(
    *,
    agent_id: str,
    framework: str,
    service_account: str,
    defaults: AdapterDefaults = AdapterDefaults(),
) -> AgentRegistration:
    return AgentRegistration(
        agent_id=agent_id,
        tenant=defaults.tenant,
        owner_principal=defaults.owner_principal,
        trust_level=defaults.trust_level,
        allowed_envs=list(defaults.allowed_envs),
        runtime_bindings=[
            RuntimeBinding(
                kind="k8s",
                cluster=defaults.cluster,
                namespace=defaults.namespace,
                service_account=service_account,
            )
        ],
        status="active",
    )
