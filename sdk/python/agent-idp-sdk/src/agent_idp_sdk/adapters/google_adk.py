from __future__ import annotations

from dataclasses import dataclass

from .base import build_registration


@dataclass(frozen=True)
class GoogleAdkAgentSpec:
    name: str
    goal: str


def build_agent_spec() -> GoogleAdkAgentSpec:
    return GoogleAdkAgentSpec(
        name="Google-ADK-SRE-RCA-Agent",
        goal="Perform high-confidence RCA and propose reversible remediations",
    )


def registration(
    *,
    owner_principal: str | None = None,
    self_identified_owner: str | None = None,
    framework: str | None = None,
    target_application: str | None = None,
    prompt_for_identity: bool = False,
) -> dict:
    return build_registration(
        agent_id="sre-rca-google-adk",
        framework=framework or "google-adk",
        owner_principal=owner_principal,
        self_identified_owner=self_identified_owner,
        target_application=target_application,
        prompt_for_identity=prompt_for_identity,
        service_account="rca-google-adk-sa",
    ).to_payload()
