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


def registration(
    *,
    owner_principal: str | None = None,
    self_identified_owner: str | None = None,
    framework: str | None = None,
    target_application: str | None = None,
    prompt_for_identity: bool = False,
) -> dict:
    return build_registration(
        agent_id="sre-rca-claude",
        framework=framework or "claude-agent-sdk",
        owner_principal=owner_principal,
        self_identified_owner=self_identified_owner,
        target_application=target_application,
        prompt_for_identity=prompt_for_identity,
        service_account="rca-claude-sa",
    ).to_payload()
