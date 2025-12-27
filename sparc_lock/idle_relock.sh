#!/usr/bin/env bash
set -euo pipefail

export DISPLAY=:0

# Seconds of inactivity before re-locking while Solaris is displayed
IDLE_SECONDS="${IDLE_SECONDS:-180}"   # default 3 minutes
IDLE_MS=$((IDLE_SECONDS * 1000))

LOCK_START="/home/pi/sparc_lock/start_lock.sh"

# Requires xprintidle (X11). Install: sudo apt install -y xprintidle
if ! command -v xprintidle >/dev/null 2>&1; then
  exit 0
fi

while true; do
  # Only act when Solaris is being displayed (vncviewer is running)
  if pgrep -x vncviewer >/dev/null 2>&1; then
    idle="$(xprintidle 2>/dev/null || echo 0)"
    if [ "${idle:-0}" -ge "$IDLE_MS" ]; then
      # Close the Solaris display
      pkill -x vncviewer >/dev/null 2>&1 || true
      sleep 0.5
      # Re-launch lockscreen
#      if [ -x "$LOCK_START" ]; then
 #       "$LOCK_START" >/dev/null 2>&1 &
      fi
      # Give the lock time to come up before continuing checks
      sleep 3
    fi
  fi
  sleep 1
done
