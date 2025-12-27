#!/usr/bin/env bash
set -euo pipefail

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-/home/pi/.Xauthority}"

VNC_TARGET="127.0.0.1:1"
VNC_PORT="5901"
VNC_LOG="/home/pi/sparc_lock/vncviewer.log"

IDLE_SECONDS="${IDLE_SECONDS:-300}"
IDLE_MS=$((IDLE_SECONDS * 1000))

IDLE_MANAGED="${SPARC_IDLE_MANAGED:-0}"   # 1 => kiosk_shell enforces idle; this script must NOT
FULLSCREEN="${VNC_FULLSCREEN:-1}"

log() { echo "launch_solaris.sh: $*" >> "$VNC_LOG"; }

# Prevent concurrent launches (double-tap, stale process, manual SSH run, etc.)
LOCK="/tmp/sparc_launch_solaris.lock"
exec 9>"$LOCK"
if ! flock -n 9; then
  # Another launch_solaris.sh is already running
  exit 0
fi
echo "$$" 1>&9 || true

# Optional: reduce flash / prevent blanking
command -v xsetroot >/dev/null 2>&1 && xsetroot -solid black || true
if command -v xset >/dev/null 2>&1; then
  xset s off || true
  xset -dpms || true
  xset s noblank || true
fi

# Ensure VM is running
if ! systemctl is-active --quiet sol8-qemu.service; then
  echo "ERROR: sol8-qemu.service is not running." >&2
  exit 1
fi

# Require xprintidle only in legacy mode (this script enforces idle)
if [ "$IDLE_MANAGED" != "1" ]; then
  if ! command -v xprintidle >/dev/null 2>&1; then
    echo "ERROR: xprintidle not installed (needed for idle relock in legacy mode)." >&2
    exit 2
  fi
fi

# Kill stale viewers (best effort)
pkill -x vncviewer >/dev/null 2>&1 || true
pkill -x xtigervncviewer >/dev/null 2>&1 || true

# Wait for VNC to listen on localhost:5901
for _ in {1..50}; do
  if ss -ltn 2>/dev/null | grep -qE "127\.0\.0\.1:${VNC_PORT}\b"; then
    break
  fi
  sleep 0.2
done
if ! ss -ltn 2>/dev/null | grep -qE "127\.0\.0\.1:${VNC_PORT}\b"; then
  echo "ERROR: VNC not listening on 127.0.0.1:${VNC_PORT}." >&2
  exit 3
fi

echo "---- launch_solaris.sh $(date --iso-8601=seconds) ----" >> "$VNC_LOG"
log "SPARC_IDLE_MANAGED=$IDLE_MANAGED FULLSCREEN=$FULLSCREEN IDLE_SECONDS=$IDLE_SECONDS"

VNC_ARGS=(
  -Shared=1
  -RemoteResize=0
  -AcceptClipboard=0
  -SendClipboard=0
  -FullscreenSystemKeys=1
  -ReconnectOnError=0
  -AlertOnFatalError=0
)
if [ "$FULLSCREEN" = "1" ]; then
  VNC_ARGS+=(-FullScreen=1)
fi

vncviewer "${VNC_ARGS[@]}" "$VNC_TARGET" >> "$VNC_LOG" 2>&1 &
VIEWER_PID=$!

cleanup() {
  # Kill the exact viewer we started…
  kill "$VIEWER_PID" >/dev/null 2>&1 || true
  sleep 0.2
  kill -9 "$VIEWER_PID" >/dev/null 2>&1 || true

  # …and also kill any strays (prevents “black fullscreen ghost” windows)
  pkill -x vncviewer >/dev/null 2>&1 || true
  pkill -x xtigervncviewer >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

viewer_has_established_conn() {
  # Prefer PID-aware detection
  if ss -tnp state established 2>/dev/null | grep -q "pid=${VIEWER_PID},"; then
    ss -tnp state established 2>/dev/null \
      | grep -qE "127\.0\.0\.1:[0-9]+ +127\.0\.0\.1:${VNC_PORT}\b.*pid=${VIEWER_PID},"
    return $?
  fi

  # Fallback: any established connection to :5901
  ss -tn state established 2>/dev/null \
    | grep -qE "127\.0\.0\.1:[0-9]+ +127\.0\.0\.1:${VNC_PORT}\b"
}

had_conn=0
misses=0
DISCONNECT_MISSES=6   # 6 * 0.25 = 1.5s after having connected

while true; do
  # Viewer exited => return
  if ! kill -0 "$VIEWER_PID" >/dev/null 2>&1; then
    log "viewer exited -> returning"
    exit 0
  fi

  # Detect F8->Disconnect (socket goes away but viewer may remain)
  if viewer_has_established_conn; then
    had_conn=1
    misses=0
  else
    if [ "$had_conn" -eq 1 ]; then
      misses=$((misses + 1))
      if [ "$misses" -ge "$DISCONNECT_MISSES" ]; then
        log "VNC disconnected (misses=$misses) -> exiting"
        exit 0
      fi
    fi
  fi

  # Legacy idle enforcement only
  if [ "$IDLE_MANAGED" != "1" ]; then
    idle="$(xprintidle 2>/dev/null || echo 0)"
    if [ "${idle:-0}" -ge "$IDLE_MS" ]; then
      log "idle ${idle}ms >= ${IDLE_MS}ms -> exiting"
      exit 0
    fi
  fi

  sleep 0.25
done
