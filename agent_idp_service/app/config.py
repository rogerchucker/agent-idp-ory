from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("AGENT_IDP_DATA_DIR", BASE_DIR / "data"))
STATE_FILE = DATA_DIR / "state.json"
AUDIT_FILE = DATA_DIR / "audit.log"
KEYS_FILE = DATA_DIR / "keys.json"


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    issuer: str = os.getenv("AGENT_IDP_ISSUER", "https://idp.local.agent")
    agent_token_audience: str = os.getenv("AGENT_TOKEN_AUDIENCE", "agent-idp-platform")
    capability_token_audience: str = os.getenv("CAPABILITY_TOKEN_AUDIENCE", "tool-gateway")
    agent_token_ttl_seconds: int = int(os.getenv("AGENT_TOKEN_TTL_SECONDS", "900"))
    capability_token_ttl_seconds: int = int(os.getenv("CAPABILITY_TOKEN_TTL_SECONDS", "300"))
    opa_url: str = os.getenv("OPA_URL", "")
    database_url: str = os.getenv("DATABASE_URL", "")
    admin_api_key: str = os.getenv("ADMIN_API_KEY", "")
    internal_api_key: str = os.getenv("INTERNAL_API_KEY", "")
    signing_key_pem: str = os.getenv("AGENT_IDP_SIGNING_KEY_PEM", "")
    signing_key_kid: str = os.getenv("AGENT_IDP_SIGNING_KEY_KID", "cap-key-2026-01")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    def validate(self) -> None:
        if self.is_production:
            if not self.database_url:
                raise RuntimeError("DATABASE_URL is required in production")
            if not self.admin_api_key:
                raise RuntimeError("ADMIN_API_KEY is required in production")
            if not self.internal_api_key:
                raise RuntimeError("INTERNAL_API_KEY is required in production")
            if not self.signing_key_pem:
                raise RuntimeError("AGENT_IDP_SIGNING_KEY_PEM is required in production")


SETTINGS = Settings()

# Backward-compatible constants used by existing modules.
ISSUER = SETTINGS.issuer
AGENT_TOKEN_AUDIENCE = SETTINGS.agent_token_audience
CAPABILITY_TOKEN_AUDIENCE = SETTINGS.capability_token_audience
AGENT_TOKEN_TTL_SECONDS = SETTINGS.agent_token_ttl_seconds
CAPABILITY_TOKEN_TTL_SECONDS = SETTINGS.capability_token_ttl_seconds
OPA_URL = SETTINGS.opa_url
