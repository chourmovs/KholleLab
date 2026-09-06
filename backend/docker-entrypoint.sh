#!/bin/sh
set -eu

if [ "$(id -u)" = "0" ]; then
  mkdir -p /runtime-logs
  chown -R app:app /runtime-logs
  exec gosu app "$@"
fi

exec "$@"
