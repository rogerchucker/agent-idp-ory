from __future__ import annotations

from claude_agent_sdk import ClaudeAgentOptions


def build_agent_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=(
            "You are a Claude-based SRE RCA agent. "
            "Perform high-signal incident diagnostics, generate a root cause narrative, "
            "and only propose reversible mitigations first."
        ),
        max_turns=2,
    )


def registration_payload() -> dict:
    return {
        "agent_id": "sre-rca-claude",
        "tenant": "org:democorp",
        "owner_principal": "user:incident-manager@company.com",
        "trust_level": "high",
        "allowed_envs": ["prod", "stage"],
        "runtime_bindings": [
            {
                "kind": "k8s",
                "cluster": "cluster-1",
                "namespace": "sre",
                "service_account": "rca-claude-sa",
            }
        ],
        "status": "active",
    }
