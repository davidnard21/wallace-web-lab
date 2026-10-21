#!/usr/bin/env bash
# Start the Wallace Washes lab: Flask apps + the PHP execution backend
# that serves webapp-b's uploaded files.
# Usage: ./start-lab.sh        (start)
#        ./start-lab.sh stop   (stop everything)
set -euo pipefail
cd "$(dirname "$0")"

LOGDIR=/tmp/wallace-lab
mkdir -p "$LOGDIR"

if [[ "${1:-}" == "stop" ]]; then
    stopped_any=0
    for entry in \
        "webapp-b|.venv/bin/python webapps/webapp-b/app.py" \
        "php-exec|php -S 127.0.0.1:8080 -t webapps/webapp-b/uploads"
    do
        name="${entry%%|*}"
        pattern="${entry#*|}"
        if pgrep -f "$pattern" >/dev/null 2>&1; then
            pkill -f "$pattern" || true
            echo "[ ok ] stopped $name"
            stopped_any=1
        else
            echo "[skip] $name was not running"
        fi
    done
    [[ $stopped_any -eq 1 ]] || echo "nothing was running"
    exit 0
fi

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
