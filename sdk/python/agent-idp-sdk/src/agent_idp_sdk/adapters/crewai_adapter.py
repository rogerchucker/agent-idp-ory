from __future__ import annotations

from dataclasses import dataclass

from .base import build_registration


@dataclass(frozen=True)
class CrewAiAgentSpec:
    role: str
    goal: str
    backstory: str


def build_agent_spec() -> CrewAiAgentSpec:
    return CrewAiAgentSpec(
        role="SRE RCA Specialist",
        goal="Identify probable incident root cause with evidence",
        backstory="A production reliability engineer focused on safe mitigation",
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
        agent_id="sre-rca-crewai",
        framework=framework or "crewai",
        owner_principal=owner_principal,
        self_identified_owner=self_identified_owner,
        target_application=target_application,
        prompt_for_identity=prompt_for_identity,
        service_account="rca-crewai-sa",
    ).to_payload()
