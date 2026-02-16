#!/usr/bin/env bash
set -euo pipefail

CLIENT_ENV_FILE="${CLIENT_ENV_FILE:-/Users/raj/ai/agents/agent-idp/.hydra-client.env}"
APP_BASE_URL="${APP_BASE_URL:-http://localhost:3001}"
HYDRA_PUBLIC_URL="${HYDRA_PUBLIC_URL:-http://localhost:4444}"
STATE="${STATE:-abc12345}"
SCOPES="${SCOPES:-openid offline_access profile email}"

if [[ ! -f "${CLIENT_ENV_FILE}" ]]; then
  echo "Missing client env file: ${CLIENT_ENV_FILE}"
  exit 1
fi

# shellcheck disable=SC1090
source "${CLIENT_ENV_FILE}"

if [[ -z "${CLIENT_ID:-}" || -z "${CLIENT_SECRET:-}" || -z "${REDIRECT_URI:-}" ]]; then
  echo "CLIENT_ID, CLIENT_SECRET, and REDIRECT_URI must be set in ${CLIENT_ENV_FILE}"
  exit 1
fi

COOKIE_JAR="/tmp/hydra_flow_cookies.txt"
rm -f "${COOKIE_JAR}"

AUTH_URL="${HYDRA_PUBLIC_URL}/oauth2/auth?client_id=${CLIENT_ID}&response_type=code&scope=$(printf '%s' "$SCOPES" | sed 's/ /%20/g')&redirect_uri=${REDIRECT_URI}&state=${STATE}"

LOGIN_LOC=$(curl -sS -D - -o /dev/null -c "${COOKIE_JAR}" "${AUTH_URL}" | awk 'tolower($1)=="location:" {print $2}' | tr -d '\r')
LOGIN_CHALLENGE=$(printf '%s' "${LOGIN_LOC}" | sed -E 's/.*login_challenge=([^&]+).*/\1/')

AUTH_AFTER_LOGIN=$(curl -sS -D - -o /dev/null -b "${COOKIE_JAR}" -c "${COOKIE_JAR}" -X POST "${APP_BASE_URL}/login?login_challenge=${LOGIN_CHALLENGE}" \
  --data-urlencode 'email=raj@example.com' \
  --data-urlencode 'password=devpass123' \
  --data-urlencode 'remember=true' | awk 'tolower($1)=="location:" {print $2}' | tr -d '\r')

CONSENT_LOC=$(curl -sS -D - -o /dev/null -b "${COOKIE_JAR}" -c "${COOKIE_JAR}" "${AUTH_AFTER_LOGIN}" | awk 'tolower($1)=="location:" {print $2}' | tr -d '\r')
CONSENT_CHALLENGE=$(printf '%s' "${CONSENT_LOC}" | sed -E 's/.*consent_challenge=([^&]+).*/\1/')

AUTH_AFTER_CONSENT=$(curl -sS -D - -o /dev/null -b "${COOKIE_JAR}" -c "${COOKIE_JAR}" -X POST "${APP_BASE_URL}/consent?consent_challenge=${CONSENT_CHALLENGE}" \
  --data-urlencode 'decision=allow' \
  --data-urlencode 'remember=true' | awk 'tolower($1)=="location:" {print $2}' | tr -d '\r')

CALLBACK_LOC=$(curl -sS -D - -o /dev/null -b "${COOKIE_JAR}" -c "${COOKIE_JAR}" "${AUTH_AFTER_CONSENT}" | awk 'tolower($1)=="location:" {print $2}' | tr -d '\r')
CODE=$(printf '%s' "${CALLBACK_LOC}" | sed -E 's/.*[?&]code=([^&]+).*/\1/')

if [[ -z "${CODE}" || "${CODE}" == "${CALLBACK_LOC}" ]]; then
  echo "Failed to extract authorization code"
  echo "Callback location: ${CALLBACK_LOC}"
  exit 1
fi

TOKEN_HTTP=$(curl -s -o /tmp/hydra_token.json -w '%{http_code}' -X POST "${HYDRA_PUBLIC_URL}/oauth2/token" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode grant_type=authorization_code \
  --data-urlencode code="${CODE}" \
  --data-urlencode redirect_uri="${REDIRECT_URI}" \
  --data-urlencode client_id="${CLIENT_ID}" \
  --data-urlencode client_secret="${CLIENT_SECRET}")

if [[ "${TOKEN_HTTP}" != "200" ]]; then
  echo "Token exchange failed with HTTP ${TOKEN_HTTP}"
  cat /tmp/hydra_token.json
  exit 1
fi

echo "OAuth flow smoke test succeeded"
head -c 250 /tmp/hydra_token.json && echo
