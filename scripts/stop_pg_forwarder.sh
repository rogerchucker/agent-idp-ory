#!/usr/bin/env bash
set -euo pipefail

PID_FILE="${PID_FILE:-/tmp/agent-idp-pg-forwarder.pid}"

if [[ -f "${PID_FILE}" ]]; then
  PID=$(cat "${PID_FILE}")
  if kill -0 "${PID}" >/dev/null 2>&1; then
    kill "${PID}"
    echo "Stopped forwarder PID=${PID}"
  else
    echo "Forwarder PID ${PID} not running"
  fi
  rm -f "${PID_FILE}"
else
  echo "No PID file found at ${PID_FILE}"
fi
