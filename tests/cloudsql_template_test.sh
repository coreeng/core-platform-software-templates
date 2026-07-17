#!/usr/bin/env bash
set -euo pipefail

module="infra/cloudsql/skeleton/infrastructure/code/modules/cloudsql"
main_tf="$module/main.tf"
grant_script="$module/scripts/grant-iam-user-privileges.sh"
failures=0

check_file_contains() {
  local file=$1
  local pattern=$2
  local message=$3

  if ! grep -qE -- "$pattern" "$file"; then
    printf 'FAIL: %s: %s\n' "$file" "$message"
    failures=$((failures + 1))
  fi
}

check_file_not_contains() {
  local file=$1
  local pattern=$2
  local message=$3

  if grep -qE -- "$pattern" "$file"; then
    printf 'FAIL: %s: %s\n' "$file" "$message"
    failures=$((failures + 1))
  fi
}

check_file_contains "$main_tf" 'scripts/grant-iam-user-privileges\.sh' "privilege grants must use the tested script"
check_file_contains "$main_tf" 'POSTGRES_ROLES[[:space:]]+= jsonencode\(each\.value\.roles\)' "roles must pass through the environment as JSON"
check_file_contains "$main_tf" 'grant_version = "v1"' "existing privilege resources must not be forced to rerun"
check_file_contains "$main_tf" 'roles[[:space:]]+= join\(",", each\.value\.roles\)' "existing role triggers must remain unchanged"
check_file_contains "$grant_script" '--set=ON_ERROR_STOP=1' "psql must stop on the first SQL error"
check_file_contains "$grant_script" 'GRANT %I TO %I' "role grants must quote PostgreSQL identifiers"
check_file_contains "$grant_script" '^BEGIN;$' "privilege grants must run in a transaction"
check_file_contains "$grant_script" '^COMMIT;$' "privilege grants must commit atomically"
check_file_not_contains "$main_tf" 'Failed to grant role.*Warning' "requested role grant failures must not be suppressed"

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT
mkdir "$tmpdir/bin"

cat >"$tmpdir/bin/gcloud" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" >"$MOCK_LOG_DIR/gcloud.args"
printf '%s\n' 'project:region:instance'
EOF

cat >"$tmpdir/bin/cloud-sql-proxy" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" >"$MOCK_LOG_DIR/proxy.args"
trap 'exit 0' TERM INT
while true; do
  /bin/sleep 1
done
EOF

cat >"$tmpdir/bin/pg_isready" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" >"$MOCK_LOG_DIR/pg_isready.args"
EOF

cat >"$tmpdir/bin/psql" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" >"$MOCK_LOG_DIR/psql.args"
cat >"$MOCK_LOG_DIR/psql.sql"
exit "${PSQL_EXIT_CODE:-0}"
EOF

chmod +x "$tmpdir/bin/"*

run_grant_script() {
  env \
    PATH="$tmpdir/bin:$PATH" \
    MOCK_LOG_DIR="$tmpdir" \
    CLUSTER_NAME='cluster name; touch injected' \
    DATABASE_NAME='database "quoted"' \
    IAM_USER='service"account@example.com' \
    PGPASSWORD='not-a-real-secret' \
    POSTGRES_ROLES='["role one","role\"two"]' \
    PROJECT_ID='project with spaces' \
    PSQL_EXIT_CODE="${1:-0}" \
    bash "$grant_script"
}

run_grant_script >"$tmpdir/success.log"

for expected in \
  'cluster name; touch injected' \
  '--project=project with spaces' \
  '--format=value(connectionName)'; do
  if ! grep -Fxq -- "$expected" "$tmpdir/gcloud.args"; then
    printf 'FAIL: gcloud did not receive argument safely: %s\n' "$expected"
    failures=$((failures + 1))
  fi
done

for expected in \
  '--dbname=database "quoted"' \
  '--set=ON_ERROR_STOP=1' \
  '--set=database=database "quoted"' \
  '--set=iam_user=service"account@example.com' \
  '--set=roles=["role one","role\"two"]'; do
  if ! grep -Fxq -- "$expected" "$tmpdir/psql.args"; then
    printf 'FAIL: psql did not receive argument safely: %s\n' "$expected"
    failures=$((failures + 1))
  fi
done

if grep -Fq 'service"account@example.com' "$tmpdir/psql.sql"; then
  printf 'FAIL: IAM user was interpolated directly into SQL\n'
  failures=$((failures + 1))
fi

if run_grant_script 42 >"$tmpdir/failure.log" 2>&1; then
  printf 'FAIL: privilege script succeeded after psql failed\n'
  failures=$((failures + 1))
else
  status=$?
  if [[ "$status" -ne 42 ]]; then
    printf 'FAIL: privilege script returned %s instead of psql status 42\n' "$status"
    failures=$((failures + 1))
  fi
fi

if grep -Fq 'Privileges granted successfully' "$tmpdir/failure.log"; then
  printf 'FAIL: privilege script reported success after psql failed\n'
  failures=$((failures + 1))
fi

if [[ "$failures" -gt 0 ]]; then
  exit 1
fi

printf 'Cloud SQL template checks passed\n'
