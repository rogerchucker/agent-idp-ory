#!/usr/bin/env bash
set -euo pipefail

HYDRA_ADMIN_URL="${HYDRA_ADMIN_URL:-http://localhost:4445}"
CLIENT_ID="${CLIENT_ID:-local-agent-idp-client}"
REDIRECT_URI="${REDIRECT_URI:-http://localhost:5555/callback}"
SCOPES="${SCOPES:-openid offline_access profile email}"
OUTPUT_ENV_FILE="${OUTPUT_ENV_FILE:-.hydra-client.env}"

payload=$(cat <<JSON
{
  "client_id": "${CLIENT_ID}",
  "client_name": "Local Agent IdP Integration Client",
  "grant_types": ["authorization_code", "refresh_token"],
  "response_types": ["code"],
  "scope": "${SCOPES}",
  "redirect_uris": ["${REDIRECT_URI}"],
  "token_endpoint_auth_method": "client_secret_post",
  "audience": ["tool-gateway", "agent-idp"]
}
JSON
)

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required but not found"
  exit 1
fi

existing_status=$(curl -s -o /tmp/hydra_client_get.json -w "%{http_code}" \
  "${HYDRA_ADMIN_URL}/admin/clients/${CLIENT_ID}")

if [[ "$existing_status" == "200" && -z "${FORCE_CREATE:-}" ]]; then
  echo "Updating existing Hydra client: ${CLIENT_ID}"
  curl -sS -X PUT "${HYDRA_ADMIN_URL}/admin/clients/${CLIENT_ID}" \
    -H 'Content-Type: application/json' \
    --data "$payload" >/tmp/hydra_client_upsert.json
else
  if [[ "$existing_status" == "200" ]]; then
    echo "Deleting existing Hydra client to rotate secret: ${CLIENT_ID}"
    curl -sS -X DELETE "${HYDRA_ADMIN_URL}/admin/clients/${CLIENT_ID}" >/dev/null
  fi
  echo "Creating Hydra client: ${CLIENT_ID}"
  curl -sS -X POST "${HYDRA_ADMIN_URL}/admin/clients" \
    -H 'Content-Type: application/json' \
    --data "$payload" >/tmp/hydra_client_upsert.json
fi

cat /tmp/hydra_client_upsert.json

if command -v jq >/dev/null 2>&1; then
  CREATED_CLIENT_ID=$(jq -r '.client_id // empty' /tmp/hydra_client_upsert.json)
  CREATED_CLIENT_SECRET=$(jq -r '.client_secret // empty' /tmp/hydra_client_upsert.json)
else
  CREATED_CLIENT_ID=$(python3 -c 'import json; print(json.load(open("/tmp/hydra_client_upsert.json")).get("client_id",""))')
  CREATED_CLIENT_SECRET=$(python3 -c 'import json; print(json.load(open("/tmp/hydra_client_upsert.json")).get("client_secret",""))')
fi

if [[ -n "${CREATED_CLIENT_ID}" ]]; then
  {
    echo "CLIENT_ID=${CREATED_CLIENT_ID}"
    if [[ -n "${CREATED_CLIENT_SECRET}" ]]; then
      echo "CLIENT_SECRET=${CREATED_CLIENT_SECRET}"
    fi
    echo "REDIRECT_URI=${REDIRECT_URI}"
    echo "HYDRA_ADMIN_URL=${HYDRA_ADMIN_URL}"
  } > "${OUTPUT_ENV_FILE}"
  echo "Wrote client credentials to ${OUTPUT_ENV_FILE}"
fi
