from __future__ import annotations

# Backward-compatible wrappers for existing demo imports.
from agent_idp_sdk.adapters.claude_sdk import build_agent_options
from agent_idp_sdk.adapters.claude_sdk import registration as _registration


def registration_payload() -> dict:
    return _registration()
