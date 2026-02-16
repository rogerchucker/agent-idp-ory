from __future__ import annotations

import base64
import json
import time
import uuid
from pathlib import Path
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .config import KEYS_FILE, SETTINGS


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


class TokenService:
    def __init__(self, key_file: Path = KEYS_FILE) -> None:
        self.key_file = key_file
        self.kid = SETTINGS.signing_key_kid
        self._private_key = self._load_or_create_key()
        self._public_key = self._private_key.public_key()

    def _load_or_create_key(self) -> Ed25519PrivateKey:
        if SETTINGS.signing_key_pem:
            pem = SETTINGS.signing_key_pem.encode("utf-8")
            return serialization.load_pem_private_key(pem, password=None)

        if self.key_file.exists():
            payload = json.loads(self.key_file.read_text())
            self.kid = payload.get("kid", self.kid)
            private_pem = payload["private_pem"].encode("utf-8")
            return serialization.load_pem_private_key(private_pem, password=None)

        key = Ed25519PrivateKey.generate()
        private_pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")
        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        self.key_file.write_text(json.dumps({"kid": self.kid, "private_pem": private_pem}, indent=2))
        return key

    def jwks(self) -> dict[str, Any]:
        public_raw = self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return {
            "keys": [
                {
                    "kty": "OKP",
                    "crv": "Ed25519",
                    "kid": self.kid,
                    "alg": "EdDSA",
                    "use": "sig",
                    "x": _b64url(public_raw),
                }
            ]
        }

    def mint_agent_access_token(
        self,
        *,
        agent_id: str,
        env: str,
        tenant: str,
        azp: str,
        trace_id: str,
        session_id: str,
        audiences: list[str] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        now = int(time.time())
        exp = now + SETTINGS.agent_token_ttl_seconds
        payload = {
            "iss": SETTINGS.issuer,
            "sub": f"agent:{agent_id}",
            "aud": audiences or [SETTINGS.agent_token_audience],
            "jti": str(uuid.uuid4()),
            "iat": now,
            "nbf": now,
            "exp": exp,
            "azp": azp,
            "tenant": tenant,
            "env": env,
            "session": {
                "session_id": session_id,
                "trace_id": trace_id,
                "purpose": "attestation_exchange",
                "reason": "runtime_attested",
                "ticket": "N/A",
            },
            "token_type": "agent_access",
        }
        token = jwt.encode(payload, self._private_key, algorithm="EdDSA", headers={"kid": self.kid, "typ": "JWT"})
        return token, payload

    def mint_capability_token(
        self,
        *,
        agent_id: str,
        tenant: str,
        env: str,
        azp: str,
        session: dict[str, Any],
        delegation: dict[str, Any],
        cap: dict[str, Any],
        risk: dict[str, Any],
        limits: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        now = int(time.time())
        exp = now + SETTINGS.capability_token_ttl_seconds
        payload = {
            "iss": SETTINGS.issuer,
            "sub": f"agent:{agent_id}",
            "aud": SETTINGS.capability_token_audience,
            "jti": str(uuid.uuid4()),
            "iat": now,
            "nbf": now,
            "exp": exp,
            "azp": azp,
            "tenant": tenant,
            "env": env,
            "session": session,
            "delegation": delegation,
            "cap": cap,
            "risk": risk,
            "limits": limits,
            "token_type": "capability",
        }
        token = jwt.encode(payload, self._private_key, algorithm="EdDSA", headers={"kid": self.kid, "typ": "JWT"})
        return token, payload

    def decode(self, token: str, audience: str | list[str]) -> dict[str, Any]:
        return jwt.decode(
            token,
            self._public_key,
            algorithms=["EdDSA"],
            audience=audience,
            issuer=SETTINGS.issuer,
            options={"require": ["exp", "iat", "nbf", "iss", "sub", "aud", "jti"]},
            leeway=5,
        )
