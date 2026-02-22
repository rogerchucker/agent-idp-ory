from __future__ import annotations

from .base import build_registration


def build_agent_options():
    from claude_agent_sdk import ClaudeAgentOptions

    return ClaudeAgentOptions(
        system_prompt=(
            "You are a Claude-based SRE RCA agent. "
            "Perform high-signal incident diagnostics, generate a root cause narrative, "
            "and only propose reversible mitigations first."
        ),
        max_turns=2,
    )


def registration() -> dict:
    return build_registration(
        agent_id="sre-rca-claude",
        framework="claude-agent-sdk",
        service_account="rca-claude-sa",
    ).to_payload()
