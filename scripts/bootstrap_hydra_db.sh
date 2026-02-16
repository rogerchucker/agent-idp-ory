#!/usr/bin/env bash
set -euo pipefail

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-raj}"
DB_NAME="${DB_NAME:-hydra_db}"

if ! command -v psql >/dev/null 2>&1; then
  echo "psql is required but not found"
  exit 1
fi

exists=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -Atc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'")
if [[ "$exists" == "1" ]]; then
  echo "Database ${DB_NAME} already exists"
else
  echo "Creating database ${DB_NAME}"
  psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE ${DB_NAME};"
fi
