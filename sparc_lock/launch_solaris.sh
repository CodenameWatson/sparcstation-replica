#!/usr/bin/env bash
set -euo pipefail

export DISPLAY="${DISPLAY:-:0}"

VNC_TARGET="127.0.0.1:1"
VNC_LOG="/home/pi/sparc_lock/vncviewer.log"

# Seconds of inactivity before re-locking while Solaris is displayed
IDLE_SECONDS="${IDLE_SECONDS:-300}"   # default 5 minutes
IDLE_MS=$((IDLE_SECONDS * 1000))

# Optional: reduce “flash” / prevent screen blanking
command -v xsetroot >/dev/null 2>&1 && xsetroot -solid black || true
command -v xset >/dev/null 2>&1 && xset s off -dpms s noblank || true

# Ensure VM is running (started by systemd at boot)
if ! systemctl is-active --quiet sol8-qemu.service; then
  echo "ERROR: sol8-qemu.service is not running." >&2
  exit 1
fi

# Require xprintidle for idle relock
if ! command -v xprintidle >/dev/null 2>&1; then
  echo "ERROR: xprintidle not installed (needed for idle relock)." >&2
  exit 2
fi

# Ensure no stale viewer processes
pkill -x vncviewer >/dev/null 2>&1 || true
pkill -x xtigervncviewer >/dev/null 2>&1 || true

# Wait for VNC to listen on 127.0.0.1:5901 (display :1)
for _ in {1..50}; do
  if ss -ltn 2>/dev/null | grep -qE '127\.0\.0\.1:5901\b'; then
    break
  fi
  sleep 0.2
done

if ! ss -ltn 2>/dev/null | grep -qE '127\.0\.0\.1:5901\b'; then
  echo "ERROR: VNC not listening on 127.0.0.1:5901." >&2
  exit 3
fi

# Allow windowed mode for debugging: VNC_FULLSCREEN=0 ./launch_solaris.sh
FULLSCREEN="${VNC_FULLSCREEN:-1}"

echo "---- launch_solaris.sh $(date --iso-8601=seconds) ----" >> "$VNC_LOG"

VNC_ARGS=(
  -Shared=1
  -RemoteResize=0
  -AcceptClipboard=0
  -SendClipboard=0
  -FullscreenSystemKeys=1
)

if [ "$FULLSCREEN" = "1" ]; then
  VNC_ARGS+=(-FullScreen=1)
fi

# Start viewer (NOT exec) so this script can monitor idle and kill it
vncviewer "${VNC_ARGS[@]}" "$VNC_TARGET" >> "$VNC_LOG" 2>&1 &
VIEWER_PID=$!

cleanup() {
  # best-effort cleanup
  kill "$VIEWER_PID" >/dev/null 2>&1 || true
  sleep 0.2
  kill -9 "$VIEWER_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

# Monitor: if viewer exits OR idle exceeds threshold, exit (caller returns to lock)
while true; do
  if ! kill -0 "$VIEWER_PID" >/dev/null 2>&1; then
    exit 0
  fi

  idle="$(xprintidle 2>/dev/null || echo 0)"
  if [ "${idle:-0}" -ge "$IDLE_MS" ]; then
    exit 0
  fi

  sleep 0.5
done
