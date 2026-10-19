#!/usr/bin/env bash
# Start the Wallace Washes lab: Flask apps + the PHP execution backend
# that serves webapp-b's uploaded files.
set -euo pipefail
cd "$(dirname "$0")"

LOGDIR=/tmp/wallace-lab
mkdir -p "$LOGDIR"

start() { # name, logfile, command...
    local name=$1 log=$2
    shift 2
    if pgrep -f "$*" >/dev/null 2>&1; then
        echo "[skip] $name already running"
    else
        ( "$@" >"$log" 2>&1 & ) || true
        sleep 1
        echo "[ ok ] $name (log: $log)"
    fi
}

start webapp-b  $LOGDIR/webapp-b.log  .venv/bin/python webapps/webapp-b/app.py
start php-exec  $LOGDIR/php-exec.log  php -S 127.0.0.1:8080 -t webapps/webapp-b/uploads

echo
echo "Lab endpoints:"
echo "  webapp-b (HomeHub dashboard): http://localhost:5001"
echo "  PHP execution backend:        http://localhost:8080"
