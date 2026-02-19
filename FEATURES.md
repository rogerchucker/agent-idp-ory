1. Agent identity registry
- Register/manage agents with owner, trust level, allowed environments, and runtime bindings.

2. Workload attestation-based sign-in
- Agents authenticate using runtime identity (k8s/spire/cloud), then receive short-lived agent access tokens.

3. Delegation/grants model
- Explicit grants for action/resource with purpose, reason, ticket, MFA flag, TTL, and revocation support.

4. Capability token minting
- Short-lived, scoped capability JWTs (EdDSA) aligned with your `JWT.md` structure:
- `session`, `delegation`, `cap`, `risk`, `limits`, `azp`, etc.

5. Tool gateway enforcement
- Verifies JWT signature/audience/expiry.
- Enforces action/resource scope.
- Enforces presenter (`azp`) match.
- Detects replay (single-use `jti`) and blocks revoked tokens.

6. Policy decision layer
- Local guardrail policy fallback.
- Optional external OPA callout (`OPA_URL`) for centralized decisions.

7. Auditing and traceability
- Logs allow/deny events for attestation, grants, minting, and execution.
- Queryable audit API.

8. JWKS publishing
- Exposes `/.well-known/jwks.json` for token verification by downstream services.

9. Production baseline controls
- Admin/internal API key protections.
- Security headers + request IDs.
- Health/readiness endpoints.
- Production config validation (fails fast if required secrets/DB missing).

10. Persistence options
- Local JSON store for dev.
- SQL backend (Postgres-ready via SQLAlchemy/psycopg) for production.

11. Ory/Hydra integration support
- Includes local Hydra + login/consent app stack for human auth and OAuth/OIDC baseline around the Agent IdP.