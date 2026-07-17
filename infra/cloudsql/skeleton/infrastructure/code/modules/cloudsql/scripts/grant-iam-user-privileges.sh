#!/usr/bin/env bash
set -euo pipefail

: "${CLUSTER_NAME:?CLUSTER_NAME is required}"
: "${DATABASE_NAME:?DATABASE_NAME is required}"
: "${IAM_USER:?IAM_USER is required}"
: "${PGPASSWORD:?PGPASSWORD is required}"
: "${POSTGRES_ROLES:?POSTGRES_ROLES is required}"
: "${PROJECT_ID:?PROJECT_ID is required}"

PROXY_PID=""

cleanup_proxy() {
  if [[ -n "$PROXY_PID" ]]; then
    echo "Cleaning up Cloud SQL Proxy (PID: $PROXY_PID)..."
    kill "$PROXY_PID" 2>/dev/null || true
    wait "$PROXY_PID" 2>/dev/null || true
  fi
}
trap cleanup_proxy EXIT

echo "Granting privileges on database '$DATABASE_NAME' to '$IAM_USER'..."

CONNECTION_NAME=$(gcloud sql instances describe "$CLUSTER_NAME" \
  --project="$PROJECT_ID" \
  --format="value(connectionName)")

MAX_PORT_RETRIES=10
PROXY_STARTED=false

for port_attempt in $(seq 1 "$MAX_PORT_RETRIES"); do
  PROXY_PORT=$((30000 + RANDOM % 10000))
  echo "Attempt $port_attempt: Starting Cloud SQL Proxy on port $PROXY_PORT..."

  cloud-sql-proxy "$CONNECTION_NAME" --port="$PROXY_PORT" &
  PROXY_PID=$!
  sleep 1

  if kill -0 "$PROXY_PID" 2>/dev/null; then
    PROXY_STARTED=true
    echo "Cloud SQL Proxy started successfully on port $PROXY_PORT"
    break
  fi

  echo "Port $PROXY_PORT was in use, trying another port..."
  PROXY_PID=""
done

if [[ "$PROXY_STARTED" == false ]]; then
  echo "ERROR: Failed to start Cloud SQL Proxy after $MAX_PORT_RETRIES attempts"
  exit 1
fi

echo "Waiting for Cloud SQL Proxy to be ready..."
for attempt in $(seq 1 30); do
  if pg_isready --host=127.0.0.1 --port="$PROXY_PORT" --username=postgres --quiet 2>/dev/null; then
    echo "Cloud SQL Proxy is ready after $attempt seconds"
    break
  fi
  if [[ "$attempt" -eq 30 ]]; then
    echo "ERROR: Cloud SQL Proxy failed to become ready after 30 seconds"
    exit 1
  fi
  sleep 1
done

echo "Executing privilege grants..."
psql \
  --host=127.0.0.1 \
  --port="$PROXY_PORT" \
  --username=postgres \
  --dbname="$DATABASE_NAME" \
  --set=ON_ERROR_STOP=1 \
  --set=database="$DATABASE_NAME" \
  --set=iam_user="$IAM_USER" \
  --set=roles="$POSTGRES_ROLES" <<'SQL'
BEGIN;
GRANT ALL PRIVILEGES ON DATABASE :"database" TO :"iam_user";
GRANT ALL PRIVILEGES ON SCHEMA public TO :"iam_user";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO :"iam_user";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO :"iam_user";
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO :"iam_user";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO :"iam_user";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO :"iam_user";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON FUNCTIONS TO :"iam_user";

SELECT format('GRANT %I TO %I', role_name, :'iam_user')
FROM json_array_elements_text(:'roles'::json) AS roles(role_name)
\gexec
COMMIT;
SQL

echo "Privileges granted successfully"
