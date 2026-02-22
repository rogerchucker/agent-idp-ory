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


def registration() -> dict:
    return build_registration(
        agent_id="sre-rca-openai",
        framework="openai-agents",
        service_account="rca-openai-sa",
    ).to_payload()
