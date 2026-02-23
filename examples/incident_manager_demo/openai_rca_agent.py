from __future__ import annotations

# Backward-compatible wrappers for existing demo imports.
from agent_idp_sdk.adapters.openai_agents import build_agent
from agent_idp_sdk.adapters.openai_agents import registration as _registration


def registration_payload(**kwargs) -> dict:
    return _registration(**kwargs)
