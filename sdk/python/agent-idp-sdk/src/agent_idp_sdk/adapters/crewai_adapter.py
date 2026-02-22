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


def registration() -> dict:
    return build_registration(
        agent_id="sre-rca-crewai",
        framework="crewai",
        service_account="rca-crewai-sa",
    ).to_payload()
