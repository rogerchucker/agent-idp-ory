# Local Hydra + Tiny Login/Consent App

This setup runs Hydra with PostgreSQL persistence and a minimal FastAPI login/consent app.

## 1) Prepare environment

```bash
cd /Users/raj/ai/agents/agent-idp
cp .env.hydra.example .env.hydra
```

Set a strong dev value for `SECRETS_SYSTEM` in `.env.hydra`.

If your local PostgreSQL listens only on `127.0.0.1` (common on macOS), start a small forwarder first so Docker can reach it:

```bash
./scripts/start_pg_forwarder.sh
```

Then set `DSN` in `.env.hydra` to:

```text
postgres://raj@host.docker.internal:15432/hydra_db?sslmode=disable
```

## 2) Create Hydra database

```bash
./scripts/bootstrap_hydra_db.sh
```

## 3) Start Hydra (with migration)

```bash
docker compose up -d hydra
```

Check health:

```bash
curl -sSf http://localhost:4445/health/ready
curl -sSf http://localhost:4444/health/ready
```

### Native Hydra fallback (recommended when Docker cannot reach localhost Postgres)

If Docker on macOS cannot access your loopback-bound Postgres, run Hydra natively:

```bash
brew install ory-hydra
DSN='postgres://raj@localhost:5432/hydra_db?sslmode=disable' hydra migrate sql up --yes
DSN='postgres://raj@localhost:5432/hydra_db?sslmode=disable' \
URLS_SELF_ISSUER='http://localhost:4444/' \
URLS_LOGIN='http://localhost:3001/login' \
URLS_CONSENT='http://localhost:3001/consent' \
URLS_LOGOUT='http://localhost:3001/logout' \
SECRETS_SYSTEM='replace-with-a-long-random-dev-secret' \
OIDC_SUBJECT_IDENTIFIERS_SUPPORTED_TYPES='public' \
hydra serve all --dev
```

## 4) Start login+consent app (uv)

```bash
cd /Users/raj/ai/agents/agent-idp/login_consent_app
uv sync
uv run uvicorn main:app --host 0.0.0.0 --port 3000
```

If port `3000` is already in use, run on `3001` and update `URLS_LOGIN`, `URLS_CONSENT`, and `URLS_LOGOUT` in `.env.hydra` to use `http://localhost:3001`.

## 5) Bootstrap OAuth client

```bash
cd /Users/raj/ai/agents/agent-idp
./scripts/bootstrap_hydra_client.sh
source .hydra-client.env
```

## 6) Test authorization flow

Open this URL in a browser:

```text
http://localhost:4444/oauth2/auth?client_id=local-agent-idp-client&response_type=code&scope=openid%20offline_access%20profile%20email&redirect_uri=http://localhost:5555/callback&state=abc12345
```

Login with:
- Email: `raj@example.com`
- Password: `devpass123`

Then approve consent. You should be redirected to `http://localhost:5555/callback?code=...`.

## 7) Exchange code for tokens

```bash
curl -sS -X POST http://localhost:4444/oauth2/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode grant_type=authorization_code \
  --data-urlencode code='<CODE_FROM_CALLBACK>' \
  --data-urlencode redirect_uri="$REDIRECT_URI" \
  --data-urlencode client_id="$CLIENT_ID" \
  --data-urlencode client_secret="$CLIENT_SECRET"
```

## 8) Negative test (deny consent)

Repeat auth URL and click `Deny`; callback should include an OAuth access denied error.

## 9) Persistence test

```bash
docker compose restart hydra
./scripts/bootstrap_hydra_client.sh
```

If client update succeeds without recreation issues, persistence is working.

## 10) Run smoke test script

```bash
cd /Users/raj/ai/agents/agent-idp
./scripts/smoke_oauth_flow.sh
```

## 11) Cleanup forwarder (if started)

```bash
./scripts/stop_pg_forwarder.sh
```

## 12) Hydra Admin UI (local)

The app now includes a local admin UI for Hydra OAuth clients:

- URL: `http://localhost:3000/admin/login` (or `3001` if you run app on `3001`)
- Default credentials:
  - Username: `admin`
  - Password: `adminpass123`

Override credentials with env vars before starting the app:

```bash
export ADMIN_USERNAME='your-admin-user'
export ADMIN_PASSWORD='your-admin-password'
```
