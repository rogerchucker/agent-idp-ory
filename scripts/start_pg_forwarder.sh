#!/usr/bin/env bash
set -euo pipefail

LOCAL_BIND_PORT="${LOCAL_BIND_PORT:-15432}"
TARGET_HOST="${TARGET_HOST:-127.0.0.1}"
TARGET_PORT="${TARGET_PORT:-5432}"
PID_FILE="${PID_FILE:-/tmp/agent-idp-pg-forwarder.pid}"

if ! command -v socat >/dev/null 2>&1; then
  echo "socat is required. Install with: brew install socat"
  exit 1
fi

if lsof -nP -iTCP:"${LOCAL_BIND_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port ${LOCAL_BIND_PORT} is already in use; not starting forwarder"
  exit 0
fi

nohup socat "TCP-LISTEN:${LOCAL_BIND_PORT},fork,reuseaddr,bind=0.0.0.0" "TCP:${TARGET_HOST}:${TARGET_PORT}" >/tmp/agent-idp-pg-forwarder.log 2>&1 &
FORWARDER_PID=$!
echo "${FORWARDER_PID}" > "${PID_FILE}"

echo "Started Postgres forwarder PID=${FORWARDER_PID} on 0.0.0.0:${LOCAL_BIND_PORT} -> ${TARGET_HOST}:${TARGET_PORT}"
