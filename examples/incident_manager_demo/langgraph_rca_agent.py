from __future__ import annotations

# Backward-compatible wrappers for existing demo imports.
from agent_idp_sdk.adapters.langgraph_adapter import build_graph
from agent_idp_sdk.adapters.langgraph_adapter import registration as _registration


def registration_payload() -> dict:
    return _registration()
