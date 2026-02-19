from __future__ import annotations

from agents import Agent


def build_agent() -> Agent:
    return Agent(
        name="OpenAI-SRE-RCA-Agent",
        instructions=(
            "You are an SRE RCA agent for incident response. "
            "Collect telemetry evidence, summarize probable root causes, "
            "and propose safe rollback/mitigation steps with confidence levels."
        ),
    )


def registration_payload() -> dict:
    return {
        "agent_id": "sre-rca-openai",
        "tenant": "org:democorp",
        "owner_principal": "user:incident-manager@company.com",
        "trust_level": "high",
        "allowed_envs": ["prod", "stage"],
        "runtime_bindings": [
            {
                "kind": "k8s",
                "cluster": "cluster-1",
                "namespace": "sre",
                "service_account": "rca-openai-sa",
            }
        ],
        "status": "active",
    }
