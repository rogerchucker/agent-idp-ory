# Agent IdP (Ory + Capability Tokens)

Agent IdP is an open-source reference implementation for running AI agents with workload identity, delegated authorization, short-lived capability tokens, and auditable tool execution.

## What this repo contains

1. `agent_idp_service`: Agent identity plane
- Agent registry
- Runtime attestation exchange
- Delegation/grants
- Capability JWT minting
- Tool gateway enforcement (scope checks, replay defense)
- Audit event APIs

2. `login_consent_app`: Tiny Hydra login/consent app
- Local auth + consent handling for OAuth/OIDC testing

3. Hydra local stack and bootstrap scripts
- `docker-compose.yml`
- `scripts/`

## Architecture

This project follows a layered model:
1. Human auth/approval via Ory/Hydra
2. Agent authentication via runtime attestation
3. Delegation grants from approved incident/operations context
4. Capability token minting for precise action/resource scope
5. Gateway policy enforcement and full audit trail

## Quick start

### Agent IdP service (dev)

```bash
cd agent_idp_service
uv sync --extra dev
uv run uvicorn app.main:app --host 0.0.0.0 --port 7001 --reload
```

### Run tests

```bash
cd agent_idp_service
uv run --extra dev pytest
```

### Production baseline deployment

```bash
cd agent_idp_service
cp .env.production.example .env.production
# fill required values
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

## Security model

- Capability JWTs are Ed25519-signed and short-lived.
- Admin and internal APIs support key-gated access in production.
- Gateway execution enforces action/resource scope and presenter binding.
- JTI replay protection and revocation are enforced.

## Documentation

- Local Hydra setup: `README-local.md`
- Token claim structure: `JWT.md`
- Design requirements: `PLAN.md`

## License

This project is licensed under the GNU Affero General Public License v3.0. See `LICENSE`.

## Incident Manager Demo

A framework-comparison registration demo is included at:
`/Users/raj/ai/agents/agent-idp/examples/incident_manager_demo`

It registers three unique RCA agents (OpenAI Agents SDK, LangGraph, Claude Agent SDK) into the IdP using `POST /agents`.
