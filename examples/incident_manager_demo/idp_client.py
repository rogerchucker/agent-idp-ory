from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class IdpConfig:
    base_url: str = os.getenv("IDP_BASE_URL", "http://localhost:7001")
    admin_api_key: str = os.getenv("IDP_ADMIN_API_KEY", "")


def register_agent(config: IdpConfig, payload: dict[str, Any]) -> dict[str, Any]:
    headers = {"content-type": "application/json"}
    if config.admin_api_key:
        headers["x-admin-api-key"] = config.admin_api_key

    with httpx.Client(timeout=10.0) as client:
        resp = client.post(f"{config.base_url}/agents", headers=headers, content=json.dumps(payload))
        resp.raise_for_status()
        return resp.json()
