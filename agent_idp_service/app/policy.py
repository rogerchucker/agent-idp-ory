from __future__ import annotations

import time
from typing import Any

import httpx

from .config import OPA_URL


class PolicyEngine:
    def __init__(self, opa_url: str = OPA_URL) -> None:
        self.opa_url = opa_url.rstrip("/")

    def evaluate(self, input_doc: dict[str, Any]) -> tuple[bool, str]:
        if self.opa_url:
            try:
                with httpx.Client(timeout=2.0) as client:
                    resp = client.post(f"{self.opa_url}/v1/data/agent_idp/allow", json={"input": input_doc})
                    resp.raise_for_status()
                    result = resp.json().get("result")
                    if isinstance(result, dict):
                        allowed = bool(result.get("allow", False))
                        reason = result.get("reason", "opa_decision")
                        return allowed, reason
                    return bool(result), "opa_decision"
            except Exception:
                # Fall through to deterministic local policy when OPA is unavailable.
                pass

        return self._local_policy(input_doc)

    def _local_policy(self, input_doc: dict[str, Any]) -> tuple[bool, str]:
        now = int(time.time())
        env = input_doc["env"]
        grant = input_doc["grant"]
        cap = input_doc["cap"]
        risk = input_doc.get("risk", {})

        if env == "prod" and input_doc.get("change_freeze", False):
            return False, "global_guardrail_change_freeze"
        if grant.get("status") != "approved":
            return False, "grant_not_approved"
        if grant.get("expires_at", 0) <= now:
            return False, "grant_expired"
        if grant.get("env") != env:
            return False, "grant_env_mismatch"
        if grant.get("action") != cap.get("action"):
            return False, "grant_action_mismatch"
        if grant.get("resource") != cap.get("resource"):
            return False, "grant_resource_mismatch"
        if risk.get("level") == "high" and not grant.get("mfa", False):
            return False, "step_up_required"

        return True, "allowed"
