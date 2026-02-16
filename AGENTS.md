# AGENTS.md

## Purpose
This repository contains a local-to-production baseline for:
1. Ory Hydra + login/consent integration (`login_consent_app`)
2. Agent Identity Plane service (`agent_idp_service`)

## Non-Negotiables
1. Always use `uv` for Python dependency and run workflows.
2. Do not use `pip` directly.
3. Keep changes backward-compatible unless explicitly requested.
4. Prefer secure defaults over convenience.

## Repository Layout
1. `/Users/raj/ai/agents/agent-idp/login_consent_app`
- FastAPI login/consent app for Hydra integration
- Includes local admin UI and tests

2. `/Users/raj/ai/agents/agent-idp/agent_idp_service`
- Agent registry, attestation exchange, grant lifecycle, capability minting, gateway enforcement, audit
- Supports JSON local store and SQL store (`DATABASE_URL`)

3. `/Users/raj/ai/agents/agent-idp/scripts`
- Hydra bootstrap and smoke scripts

## Standard Commands

### Hydra + login/consent stack
1. Start Hydra:
```bash
cd /Users/raj/ai/agents/agent-idp
docker compose up -d hydra
```
2. Run login/consent app:
```bash
cd /Users/raj/ai/agents/agent-idp/login_consent_app
uv sync --extra dev
uv run uvicorn main:app --host 0.0.0.0 --port 3000 --reload
```

### Agent IdP service (dev)
```bash
cd /Users/raj/ai/agents/agent-idp/agent_idp_service
uv sync --extra dev
uv run uvicorn app.main:app --host 0.0.0.0 --port 7001 --reload
```

### Agent IdP service tests
```bash
cd /Users/raj/ai/agents/agent-idp/agent_idp_service
uv run --extra dev pytest
```

### Agent IdP service (production compose)
```bash
cd /Users/raj/ai/agents/agent-idp/agent_idp_service
cp .env.production.example .env.production
# fill required env vars
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

## Production Requirements (`agent_idp_service`)
When `APP_ENV=production`, these env vars must be set:
1. `DATABASE_URL`
2. `ADMIN_API_KEY`
3. `INTERNAL_API_KEY`
4. `AGENT_IDP_SIGNING_KEY_PEM`

## API Key Routing Rules
1. Admin routes require `x-admin-api-key`:
- `/agents`
- `/grants`
- `/grants/revoke`
- `/audit/events`

2. Internal runtime routes require `x-internal-api-key`:
- `/attest/exchange`
- `/capabilities/mint`
- `/gateway/execute`

## Change Guidelines
1. If updating token claims, keep compatibility with `/Users/raj/ai/agents/agent-idp/JWT.md`.
2. If changing persistence schema, add migration planning notes in PR/commit message.
3. Add or update tests for every behavior change.
4. Do not remove replay protection, revocation checks, or policy gate logic.

## Definition of Done
1. Code compiles and runs.
2. Relevant tests pass with `uv run --extra dev pytest`.
3. README/docs updated for behavior or config changes.
4. No secrets committed to repository.
