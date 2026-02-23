# Agent IdP Service

Production-ready baseline implementation of the Agent IdP design from `/Users/raj/ai/agents/agent-idp/PLAN.md`.

## What This Now Includes

1. Agent registry and lifecycle APIs
2. Runtime attestation exchange (k8s/spire/cloud)
3. Delegation grants and revocation
4. Capability JWT minting (EdDSA, JWT shape aligned to `/Users/raj/ai/agents/agent-idp/JWT.md`)
5. Gateway enforcement with replay protection and presenter (`azp`) checks
6. Audit event trail
7. OPA integration hook with local fallback policy
8. Production hardening:
- API key enforcement for admin/internal APIs
- Security headers and request IDs
- Production config validation (fails fast if secrets/DB are missing)
- SQL persistence support (Postgres via SQLAlchemy)
- Containerized deployment artifacts

## API Surface

- `GET /healthz`
- `GET /readyz`
- `GET /.well-known/jwks.json`
- `POST /agents` (admin key)
- `GET /agents/{agent_id}` (admin key)
- `POST /attest/exchange` (internal key)
- `POST /grants` (admin key)
- `POST /grants/revoke` (admin key)
- `POST /capabilities/mint` (internal key)
- `POST /gateway/execute` (internal key)
- `GET /audit/events` (admin key)

### Agent registration metadata

`POST /agents` supports optional self-identifying metadata and will return it on both create and read:

- `self_identified_owner`
- `framework`
- `target_application`

## Local Dev Run

```bash
cd /Users/raj/ai/agents/agent-idp/agent_idp_service
uv sync --extra dev
uv run uvicorn app.main:app --host 0.0.0.0 --port 7001 --reload
```

## Production Deployment (Docker Compose)

1. Create env file:
```bash
cd /Users/raj/ai/agents/agent-idp/agent_idp_service
cp .env.production.example .env.production
```

2. Fill required values in `.env.production`:
- `DATABASE_URL`
- `ADMIN_API_KEY`
- `INTERNAL_API_KEY`
- `AGENT_IDP_SIGNING_KEY_PEM`

3. Start stack:
```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

4. Verify:
```bash
curl -s http://localhost:7001/healthz
curl -s http://localhost:7001/readyz
```

## Security Model for API Access

- `x-admin-api-key`: required for control-plane APIs (`/agents`, `/grants`, `/audit`)
- `x-internal-api-key`: required for runtime/mint/gateway APIs
- In development, keys are optional if env vars are unset.
- In production (`APP_ENV=production`), keys are mandatory and startup fails if missing.

## Persistence Modes

- If `DATABASE_URL` is set: SQL backend (Postgres recommended)
- If `DATABASE_URL` is unset: local JSON backend (`/Users/raj/ai/agents/agent-idp/agent_idp_service/data`)

## Tests

```bash
cd /Users/raj/ai/agents/agent-idp/agent_idp_service
uv run --extra dev pytest
```

Current result: all tests passing (unit + integration + e2e).

## Next Production Steps (Optional but Recommended)

1. Move signing key material to a KMS/HSM-backed key provider.
2. Put this service behind mTLS ingress and rotate API keys via a secret manager.
3. Add DB migrations (Alembic) and run schema changes via CI/CD pipeline.
4. Replace API key internal auth with workload identity + mTLS SPIFFE verification.
5. Stream audit events to SIEM (instead of only DB/local retrieval).
