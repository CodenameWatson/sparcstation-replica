#!/usr/bin/env bash
set -euo pipefail

PIDFILE="/home/pi/sparc_vm/qemu-sparc.pid"
MON_HOST="127.0.0.1"
MON_PORT="4444"

# Try to shut down cleanly via QEMU monitor first
if command -v nc >/dev/null 2>&1; then
  # "quit" cleanly exits QEMU
  printf "quit\n" | nc -w 2 "$MON_HOST" "$MON_PORT" >/dev/null 2>&1 || true
elif command -v telnet >/dev/null 2>&1; then
  # telnet is interactive; nc is preferred. Fall back to PID kill if telnet exists but isn't used.
  true
fi

# If still running, kill by PID file
if [ -f "$PIDFILE" ]; then
  PID="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [ -n "${PID:-}" ] && kill -0 "$PID" 2>/dev/null; then
    kill "$PID" || true
    # Wait briefly for clean exit
    for _ in 1 2 3 4 5; do
      sleep 1
      kill -0 "$PID" 2>/dev/null || break
    done
    # Force if needed
    if kill -0 "$PID" 2>/dev/null; then
      kill -9 "$PID" || true
    fi
  fi
  rm -f "$PIDFILE"
fi

# As a last resort, kill any remaining qemu-system-sparc instances
pkill -f qemu-system-sparc >/dev/null 2>&1 || true

echo "Stopped Solaris/QEMU instance (if it was running)."
