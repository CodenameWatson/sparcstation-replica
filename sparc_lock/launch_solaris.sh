#!/usr/bin/env bash
set -euo pipefail

LOG="/home/pi/sparc_lock/logs/solaris_vnc.log"
mkdir -p "$(dirname "$LOG")"
exec >>"$LOG" 2>&1

echo "=== launch_solaris.sh $(date -Is) ==="

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-/home/pi/.Xauthority}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/1000}"

echo "DISPLAY=$DISPLAY"
echo "XAUTHORITY=$XAUTHORITY"
echo "XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR"

# 1) Ensure X is available
if command -v xset >/dev/null 2>&1; then
  xset q >/dev/null 2>&1 || { echo "ERROR: xset q failed (X not available)"; exit 2; }
fi

# 2) Reduce flash (cosmetic)
if command -v xsetroot >/dev/null 2>&1; then
  xsetroot -solid black || true
fi

# 3) Ensure the VM VNC port is listening
# QEMU VNC :1 -> TCP 5901
if command -v nc >/dev/null 2>&1; then
  for i in {1..50}; do
    if nc -z 127.0.0.1 5901 >/dev/null 2>&1; then
      echo "VNC port 5901 ready after $i tries"
      break
    fi
    sleep 0.1
    if [ "$i" -eq 50 ]; then
      echo "ERROR: VNC port 5901 not listening"
      exit 3
    fi
  done
fi

# 4) Kill any existing viewer (avoid stale/hidden/fullscreen issues)
# IMPORTANT: remove any flags you know your viewer doesn't support (e.g. -NoXdamage caused failures).
if pgrep -fa 'xtigervncviewer' >/dev/null 2>&1; then
  echo "Killing existing xtigervncviewer instances"
  pkill -TERM -f 'xtigervncviewer' || true
  sleep 0.3
  pkill -KILL -f 'xtigervncviewer' || true
fi

# 5) Launch viewer in foreground and wait for exit
VIEWER="$(command -v xtigervncviewer || true)"
if [ -z "$VIEWER" ]; then
  echo "ERROR: xtigervncviewer not found"
  exit 4
fi

TARGET="127.0.0.1:1"
echo "Starting viewer: $VIEWER -FullScreen $TARGET"

# Add only flags you have confirmed are supported by *your* xtigervncviewer build.
exec "$VIEWER" -FullScreen "$TARGET"
