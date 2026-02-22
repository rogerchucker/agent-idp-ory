from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import httpx

from .types import AgentRegistration


@dataclass(frozen=True)
class IdpConfig:
    base_url: str = os.getenv("IDP_BASE_URL", "http://localhost:7001")
    admin_api_key: str = os.getenv("IDP_ADMIN_API_KEY", "")
    timeout_seconds: float = float(os.getenv("IDP_HTTP_TIMEOUT_SECONDS", "10"))


class IdpClient:
    def __init__(self, config: IdpConfig | None = None) -> None:
        self.config = config or IdpConfig()

    def register_agent(self, registration: AgentRegistration | dict[str, Any]) -> dict[str, Any]:
        payload = (
            registration.to_payload()
            if isinstance(registration, AgentRegistration)
            else registration
        )
        headers = {"content-type": "application/json"}
        if self.config.admin_api_key:
            headers["x-admin-api-key"] = self.config.admin_api_key

        with httpx.Client(timeout=self.config.timeout_seconds) as client:
            resp = client.post(
                f"{self.config.base_url}/agents",
                headers=headers,
                content=json.dumps(payload),
            )
            resp.raise_for_status()
            return resp.json()


def register_agent(config: IdpConfig, payload: dict[str, Any]) -> dict[str, Any]:
    return IdpClient(config).register_agent(payload)
