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


def registration() -> dict:
    return build_registration(
        agent_id="sre-rca-google-adk",
        framework="google-adk",
        service_account="rca-google-adk-sa",
    ).to_payload()
