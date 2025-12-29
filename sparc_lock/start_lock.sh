#!/usr/bin/env bash
trap 'echo "[$(date -Is)] start_lock.sh got SIGTERM/SIGINT; exiting"; exit 0' TERM INT
set -euo pipefail

BASE="/home/pi/sparc_lock"
LOGDIR="$BASE/logs"
LOG="$LOGDIR/start_lock.log"
mkdir -p "$LOGDIR"

# log everything
exec >>"$LOG" 2>&1
echo "[$(date -Is)] start_lock.sh begin (uid=$(id -u) user=$(id -un))"

export HOME="/home/pi"
export USER="pi"
export LOGNAME="pi"
export DISPLAY="${DISPLAY:-:0}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/1000}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"

# Force SDL to use X11 (prevents accidental fallback)
export SDL_VIDEODRIVER=x11

echo "[$(date -Is)] DISPLAY=$DISPLAY XAUTHORITY=$XAUTHORITY XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR SDL_VIDEODRIVER=$SDL_VIDEODRIVER"

# Single-instance lock:
# If a previous session is still shutting down, WAIT for it to release the lock.
LOCKFILE="/tmp/sparc_kiosk.lock"
exec 9>"$LOCKFILE"
if ! flock -n 9; then
  echo "[$(date -Is)] Another kiosk instance holds $LOCKFILE; waiting for it to exit..."
  flock 9
  echo "[$(date -Is)] Lock acquired; continuing."
fi

# Wait for X to be ready (must succeed, not best-effort)
if command -v xset >/dev/null 2>&1; then
  for i in $(seq 1 120); do
    if xset q >/dev/null 2>&1; then
      echo "[$(date -Is)] X ready (xset q ok)"
      break
    fi
    sleep 0.25
  done
  if ! xset q >/dev/null 2>&1; then
    echo "[$(date -Is)] ERROR: X still not reachable after wait; sleeping forever."
    while true; do sleep 60; done
  fi
fi

# Disable blanking (best-effort)
if command -v xset >/dev/null 2>&1; then
  xset s off  || true
  xset -dpms || true
  xset s noblank || true
fi

# Keep session alive; restart kiosk shell if it exits
while true; do
  echo "[$(date -Is)] Launching kiosk_shell.py"
  /usr/bin/python3 -u "$BASE/kiosk_shell.py"
  rc=$?
  echo "[$(date -Is)] kiosk_shell.py exited rc=$rc; restarting in 2s"
  sleep 2
done
