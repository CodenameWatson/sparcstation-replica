#!/usr/bin/env bash
set -euo pipefail

PIDFILE="/home/pi/sparc_vm/qemu-sparc.pid"
MON_HOST="127.0.0.1"
MON_PORT="4444"

# Try graceful shutdown via QEMU monitor
if command -v nc >/dev/null 2>&1; then
  printf "quit\n" | nc -w 2 "$MON_HOST" "$MON_PORT" >/dev/null 2>&1 || true
fi

# Kill by PID file if still running
if [ -f "$PIDFILE" ]; then
  PID="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [ -n "${PID:-}" ] && kill -0 "$PID" 2>/dev/null; then
    kill "$PID" >/dev/null 2>&1 || true
    for _ in 1 2 3 4 5; do
      sleep 1
      kill -0 "$PID" 2>/dev/null || break
    done
    if kill -0 "$PID" 2>/dev/null; then
      kill -9 "$PID" >/dev/null 2>&1 || true
    fi
  fi
  rm -f "$PIDFILE" >/dev/null 2>&1 || true
fi

# Last resort: only kill qemu instances that reference THIS pidfile path
pkill -f "qemu-system-sparc.*-pidfile /home/pi/sparc_vm/qemu-sparc.pid" >/dev/null 2>&1 || true

echo "Stopped Solaris/QEMU instance (if it was running)."
