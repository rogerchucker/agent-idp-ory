from __future__ import annotations

from .base import build_registration


def build_agent():
    from agents import Agent

    return Agent(
        name="OpenAI-SRE-RCA-Agent",
        instructions=(
            "You are an SRE RCA agent for incident response. "
            "Collect telemetry evidence, summarize probable root causes, "
            "and propose safe rollback/mitigation steps with confidence levels."
        ),
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
        agent_id="sre-rca-openai",
        framework=framework or "openai-agents",
        owner_principal=owner_principal,
        self_identified_owner=self_identified_owner,
        target_application=target_application,
        prompt_for_identity=prompt_for_identity,
        service_account="rca-openai-sa",
    ).to_payload()
