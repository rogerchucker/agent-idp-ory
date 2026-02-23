from __future__ import annotations

from dataclasses import dataclass
import sys

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
    owner_principal: str | None = None,
    self_identified_owner: str | None = None,
    target_application: str | None = None,
    prompt_for_identity: bool = False,
    defaults: AdapterDefaults = AdapterDefaults(),
) -> AgentRegistration:
    resolved_owner = owner_principal or defaults.owner_principal
    resolved_self_identified_owner = self_identified_owner
    resolved_framework = framework
    resolved_target_application = target_application

    if prompt_for_identity and sys.stdin.isatty():
        owner_hint = resolved_self_identified_owner or ""
        owner_prompt = f"Self-identifying owner (optional){f' [{owner_hint}]' if owner_hint else ''}: "
        value = input(owner_prompt).strip()
        if value:
            resolved_self_identified_owner = value

        framework_prompt = f"Framework (optional) [{resolved_framework}]: "
        value = input(framework_prompt).strip()
        if value:
            resolved_framework = value

        app_hint = resolved_target_application or ""
        app_prompt = f"Target application (optional){f' [{app_hint}]' if app_hint else ''}: "
        value = input(app_prompt).strip()
        if value:
            resolved_target_application = value

    return AgentRegistration(
        agent_id=agent_id,
        tenant=defaults.tenant,
        owner_principal=resolved_owner,
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
        self_identified_owner=resolved_self_identified_owner,
        framework=resolved_framework,
        target_application=resolved_target_application,
        status="active",
    )
