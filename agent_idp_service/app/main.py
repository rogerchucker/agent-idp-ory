from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Protocol

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from .config import SETTINGS
from .db_store import SqlStore
from .models import Agent, AttestationInput, CapabilityMintRequest, ExecuteRequest, Grant, GrantCreate, RevokeRequest
from .policy import PolicyEngine
from .security import TokenService
from .store import JsonStore

logger = logging.getLogger("agent_idp")
logging.basicConfig(level=getattr(logging, SETTINGS.log_level.upper(), logging.INFO))


class StoreProtocol(Protocol):
    def upsert_agent(self, agent: dict[str, Any]) -> dict[str, Any]: ...
    def get_agent(self, agent_id: str) -> dict[str, Any] | None: ...
    def create_grant(self, grant: dict[str, Any]) -> dict[str, Any]: ...
    def get_grant(self, grant_id: str) -> dict[str, Any] | None: ...
    def update_grant(self, grant_id: str, updates: dict[str, Any]) -> dict[str, Any] | None: ...
    def revoke_jti(self, jti: str, expires_at: int) -> None: ...
    def is_revoked(self, jti: str) -> bool: ...
    def remember_jti(self, jti: str, expires_at: int) -> None: ...
    def is_replayed(self, jti: str) -> bool: ...
    def append_audit(self, event: dict[str, Any]) -> None: ...
    def list_audit(self, limit: int = 100) -> list[dict[str, Any]]: ...
    def cleanup(self, now_ts: int) -> None: ...


def _default_store() -> StoreProtocol:
    if SETTINGS.database_url:
        return SqlStore(SETTINGS.database_url)
    return JsonStore()


def create_app(
    *,
    store: StoreProtocol | None = None,
    token_service: TokenService | None = None,
    policy_engine: PolicyEngine | None = None,
) -> FastAPI:
    SETTINGS.validate()

    resolved_store = store or _default_store()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        close_fn = getattr(resolved_store, "close", None)
        if callable(close_fn):
            close_fn()

    app = FastAPI(
        title="Agent IdP Service",
        version="0.2.0",
        docs_url=None if SETTINGS.is_production else "/docs",
        redoc_url=None if SETTINGS.is_production else "/redoc",
        lifespan=lifespan,
    )
    app.state.store = resolved_store
    app.state.tokens = token_service or TokenService()
    app.state.policy = policy_engine or PolicyEngine(opa_url=SETTINGS.opa_url)

    def require_admin_api_key(x_admin_api_key: str | None = Header(default=None)) -> None:
        if SETTINGS.admin_api_key and x_admin_api_key != SETTINGS.admin_api_key:
            raise HTTPException(status_code=401, detail="unauthorized_admin")

    def require_internal_api_key(x_internal_api_key: str | None = Header(default=None)) -> None:
        if SETTINGS.internal_api_key and x_internal_api_key != SETTINGS.internal_api_key:
            raise HTTPException(status_code=401, detail="unauthorized_internal")

    def _runtime_to_azp(att: AttestationInput) -> str:
        if att.kind == "k8s":
            return f"agent-runtime:k8s:{att.cluster}:ns/{att.namespace}:sa/{att.service_account}"
        if att.kind == "spire":
            return f"agent-runtime:spire:{att.spiffe_id}"
        return f"agent-runtime:cloud:{att.cluster}"

    def _audit(
        *,
        trace_id: str,
        session_id: str,
        agent_id: str,
        decision: str,
        action: str,
        resource: str,
        detail: dict[str, Any],
        grant_id: str | None = None,
        jti: str | None = None,
    ) -> None:
        event = {
            "event_id": f"evt-{int(time.time() * 1000)}",
            "timestamp": int(time.time()),
            "trace_id": trace_id,
            "session_id": session_id,
            "agent_id": agent_id,
            "grant_id": grant_id,
            "jti": jti,
            "decision": decision,
            "action": action,
            "resource": resource,
            "detail": detail,
        }
        app.state.store.append_audit(event)

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        req_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        start = time.time()
        response = await call_next(request)
        response.headers["x-request-id"] = req_id
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["x-frame-options"] = "DENY"
        response.headers["referrer-policy"] = "no-referrer"
        if SETTINGS.is_production:
            response.headers["strict-transport-security"] = "max-age=31536000; includeSubDomains"
        duration_ms = int((time.time() - start) * 1000)
        logger.info("request_complete", extra={"path": request.url.path, "method": request.method, "status": response.status_code, "duration_ms": duration_ms, "request_id": req_id})
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception):
        logger.exception("unhandled_exception")
        return JSONResponse(status_code=500, content={"detail": "internal_server_error"})

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        app.state.store.cleanup(int(time.time()))
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict[str, str]:
        try:
            app.state.store.list_audit(limit=1)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"not_ready:{exc}") from exc
        return {"status": "ready"}

    @app.get("/.well-known/jwks.json")
    def jwks() -> dict[str, Any]:
        return app.state.tokens.jwks()

    @app.post("/agents", response_model=Agent)
    def upsert_agent(agent: Agent, _: None = Depends(require_admin_api_key)) -> Agent:
        return Agent(**app.state.store.upsert_agent(agent.model_dump()))

    @app.get("/agents/{agent_id}", response_model=Agent)
    def get_agent(agent_id: str, _: None = Depends(require_admin_api_key)) -> Agent:
        item = app.state.store.get_agent(agent_id)
        if not item:
            raise HTTPException(status_code=404, detail="agent_not_found")
        return Agent(**item)

    @app.post("/attest/exchange")
    def attest_exchange(att: AttestationInput, _: None = Depends(require_internal_api_key)) -> dict[str, Any]:
        agent = app.state.store.get_agent(att.agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="agent_not_found")
        if agent.get("status") != "active":
            raise HTTPException(status_code=403, detail="agent_disabled")
        if att.env not in agent["allowed_envs"]:
            raise HTTPException(status_code=403, detail="env_not_allowed")

        matched = False
        for binding in agent["runtime_bindings"]:
            if binding["kind"] != att.kind:
                continue
            if att.kind == "k8s":
                matched = (
                    binding.get("cluster") == att.cluster
                    and binding.get("namespace") == att.namespace
                    and binding.get("service_account") == att.service_account
                )
            elif att.kind == "spire":
                matched = binding.get("spiffe_id") == att.spiffe_id
            else:
                matched = binding.get("cluster") == att.cluster
            if matched:
                break

        if not matched:
            raise HTTPException(status_code=403, detail="attestation_invalid")

        azp = _runtime_to_azp(att)
        token, claims = app.state.tokens.mint_agent_access_token(
            agent_id=att.agent_id,
            env=att.env,
            tenant=agent["tenant"],
            azp=azp,
            trace_id=att.trace_id,
            session_id=att.session_id,
        )
        _audit(
            trace_id=att.trace_id,
            session_id=att.session_id,
            agent_id=att.agent_id,
            decision="allow",
            action="attestation.exchange",
            resource=f"agent:{att.agent_id}",
            detail={"azp": azp},
            jti=claims["jti"],
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": claims["exp"] - claims["iat"],
        }

    @app.post("/grants", response_model=Grant)
    def create_grant(req: GrantCreate, _: None = Depends(require_admin_api_key)) -> Grant:
        agent = app.state.store.get_agent(req.agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="agent_not_found")
        if req.env not in agent["allowed_envs"]:
            raise HTTPException(status_code=403, detail="env_not_allowed")

        now = int(time.time())
        grant = {
            "grant_id": f"grant-{uuid.uuid4()}",
            "grant_type": req.grant_type,
            "granted_by": req.granted_by,
            "agent_id": req.agent_id,
            "env": req.env,
            "action": req.action,
            "resource": req.resource,
            "purpose": req.purpose,
            "reason": req.reason,
            "ticket": req.ticket,
            "mfa": req.mfa,
            "granted_at": now,
            "expires_at": now + req.ttl_seconds,
            "status": "approved",
        }
        app.state.store.create_grant(grant)
        _audit(
            trace_id=f"trace-grant-{now}",
            session_id=f"session-grant-{now}",
            agent_id=req.agent_id,
            grant_id=grant["grant_id"],
            decision="allow",
            action=req.action,
            resource=req.resource,
            detail={"kind": "grant_created", "granted_by": req.granted_by},
        )
        return Grant(**grant)

    @app.post("/grants/revoke")
    def revoke(req: RevokeRequest, _: None = Depends(require_admin_api_key)) -> dict[str, str]:
        if not req.grant_id and not req.jti:
            raise HTTPException(status_code=400, detail="grant_id_or_jti_required")

        if req.grant_id:
            grant = app.state.store.get_grant(req.grant_id)
            if not grant:
                raise HTTPException(status_code=404, detail="grant_not_found")
            app.state.store.update_grant(req.grant_id, {"status": "revoked"})

        if req.jti:
            app.state.store.revoke_jti(req.jti, int(time.time()) + 3600)

        return {"status": "revoked"}

    @app.post("/capabilities/mint")
    def mint_capability(req: CapabilityMintRequest, _: None = Depends(require_internal_api_key)) -> dict[str, Any]:
        try:
            access_claims = app.state.tokens.decode(req.agent_access_token, audience=SETTINGS.agent_token_audience)
        except Exception as exc:
            raise HTTPException(status_code=401, detail=f"invalid_agent_access_token: {exc}") from exc

        if access_claims.get("token_type") != "agent_access":
            raise HTTPException(status_code=401, detail="wrong_token_type")

        agent_id = access_claims["sub"].replace("agent:", "", 1)
        grant = app.state.store.get_grant(req.grant_id)
        if not grant:
            raise HTTPException(status_code=404, detail="grant_not_found")
        if grant["agent_id"] != agent_id:
            raise HTTPException(status_code=403, detail="grant_agent_mismatch")

        cap_doc = {
            "action": req.cap_action,
            "resource": req.cap_resource,
            "constraints": req.constraints,
        }
        allowed, reason = app.state.policy.evaluate(
            {
                "env": access_claims["env"],
                "grant": grant,
                "cap": cap_doc,
                "risk": {"level": req.risk_level, "step_up_required": False},
                "change_freeze": bool(req.constraints.get("change_freeze", False)),
            }
        )
        if not allowed:
            _audit(
                trace_id=req.trace_id,
                session_id=req.session_id,
                agent_id=agent_id,
                grant_id=grant["grant_id"],
                decision="deny",
                action=req.cap_action,
                resource=req.cap_resource,
                detail={"reason": reason},
            )
            raise HTTPException(status_code=403, detail=f"policy_denied:{reason}")

        session = {
            "session_id": req.session_id,
            "trace_id": req.trace_id,
            "purpose": req.purpose,
            "reason": req.reason,
            "ticket": req.ticket,
        }
        delegation = {
            "grant_id": grant["grant_id"],
            "grant_type": grant["grant_type"],
            "granted_by": grant["granted_by"],
            "granted_at": grant["granted_at"],
            "expires_at": grant["expires_at"],
            "mfa": grant["mfa"],
        }
        risk = {"level": req.risk_level, "step_up_required": False}
        token, claims = app.state.tokens.mint_capability_token(
            agent_id=agent_id,
            tenant=access_claims["tenant"],
            env=access_claims["env"],
            azp=access_claims["azp"],
            session=session,
            delegation=delegation,
            cap=cap_doc,
            risk=risk,
            limits=req.limits,
        )
        _audit(
            trace_id=req.trace_id,
            session_id=req.session_id,
            agent_id=agent_id,
            grant_id=grant["grant_id"],
            jti=claims["jti"],
            decision="allow",
            action=req.cap_action,
            resource=req.cap_resource,
            detail={"reason": reason},
        )
        return {
            "capability_token": token,
            "expires_in": claims["exp"] - claims["iat"],
            "jti": claims["jti"],
        }

    @app.post("/gateway/execute")
    def gateway_execute(req: ExecuteRequest, _: None = Depends(require_internal_api_key)) -> dict[str, Any]:
        try:
            claims = app.state.tokens.decode(req.capability_token, audience=SETTINGS.capability_token_audience)
        except Exception as exc:
            raise HTTPException(status_code=401, detail=f"invalid_capability_token: {exc}") from exc

        if claims.get("token_type") != "capability":
            raise HTTPException(status_code=401, detail="wrong_token_type")

        jti = claims["jti"]
        if app.state.store.is_revoked(jti):
            raise HTTPException(status_code=403, detail="token_revoked")
        if app.state.store.is_replayed(jti):
            raise HTTPException(status_code=409, detail="replay_detected")

        cap = claims["cap"]
        if cap["action"] != req.action or cap["resource"] != req.resource:
            raise HTTPException(status_code=403, detail="capability_scope_mismatch")

        if req.presenter and req.presenter != claims["azp"]:
            raise HTTPException(status_code=403, detail="presenter_mismatch")

        app.state.store.remember_jti(jti, int(claims["exp"]))

        agent_id = claims["sub"].replace("agent:", "", 1)
        _audit(
            trace_id=claims["session"]["trace_id"],
            session_id=claims["session"]["session_id"],
            agent_id=agent_id,
            grant_id=claims["delegation"]["grant_id"],
            jti=jti,
            decision="allow",
            action=req.action,
            resource=req.resource,
            detail={"tool": req.tool, "params": req.params},
        )

        return {
            "status": "executed",
            "tool": req.tool,
            "action": req.action,
            "resource": req.resource,
            "trace_id": claims["session"]["trace_id"],
        }

    @app.get("/audit/events")
    def list_events(limit: int = Query(default=100, ge=1, le=1000), _: None = Depends(require_admin_api_key)) -> dict[str, Any]:
        return {"events": app.state.store.list_audit(limit=limit)}

    return app


app = create_app()
