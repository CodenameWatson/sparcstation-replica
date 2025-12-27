#!/usr/bin/env bash
set -euo pipefail

cd /home/pi/sparc_lock

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-/home/pi/.Xauthority}"

# Prevent blanking / DPMS (only if xset exists)
if command -v xset >/dev/null 2>&1; then
  xset s off || true
  xset -dpms || true
  xset s noblank || true
fi

# Run lock; exit code propagates to the session wrapper (rc=42 should mean "Admin desktop")
exec python3 -u /home/pi/sparc_lock/puzzle_lock.py
