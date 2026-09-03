#!/usr/bin/env sh
set -eu

BASE_URL="${BASE_URL:-http://localhost:${KHOLLELAB_PORT:-8080}}"
ATTEMPTS="${SMOKE_ATTEMPTS:-30}"

attempt=1
while [ "$attempt" -le "$ATTEMPTS" ]; do
  if curl -fsS "$BASE_URL/api/v1/health" | grep -q '"status":"ok"'; then
    break
  fi
  if [ "$attempt" -eq "$ATTEMPTS" ]; then
    echo "API smoke check failed after $ATTEMPTS attempts" >&2
    exit 1
  fi
  attempt=$((attempt + 1))
  sleep 2
done

curl -fsS "$BASE_URL/" | grep -q 'KholleLab'
echo "KholleLab smoke test: OK"
