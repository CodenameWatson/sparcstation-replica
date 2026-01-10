#!/usr/bin/env bash
set -euo pipefail

BASE="/home/pi/sparc_lock"
LOGDIR="$BASE/logs"
LOG="$LOGDIR/pi_mode.log"
mkdir -p "$LOGDIR"

exec >>"$LOG" 2>&1
echo "---- start_pi_mode.sh $(date -Is) ----"

export HOME="/home/pi"
export USER="pi"
export LOGNAME="pi"
export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-/home/pi/.Xauthority}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/1000}"

# Default: 5 minutes. You can override by exporting PI_MODE_IDLE_MS before calling.
IDLE_MS="${PI_MODE_IDLE_MS:-300000}"
SENTINEL="/tmp/sparc_pi_mode_exit"
rm -f "$SENTINEL" 2>/dev/null || true

echo "DISPLAY=$DISPLAY XAUTHORITY=$XAUTHORITY XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR"
echo "Idle threshold: ${IDLE_MS}ms"

# Detect whether a WM is already running.
if xprop -root _NET_SUPPORTING_WM_CHECK >/dev/null 2>&1; then
  echo "WM detected; not starting a second Openbox."
else
  echo "No WM detected; starting Openbox."
  openbox >/dev/null 2>&1 &
  echo $! > "$BASE/pi_mode_openbox.pid"
  disown || true
fi

# Start a simple "desktop" layer (panel + icons), if available.
if command -v lxpanel >/dev/null 2>&1; then
  echo "Starting lxpanel --profile LXDE"
  lxpanel --profile LXDE >/dev/null 2>&1 &
  echo $! > "$BASE/pi_mode_lxpanel.pid"
else
  echo "WARNING: lxpanel not found"
fi

if command -v pcmanfm >/dev/null 2>&1; then
  echo "Starting pcmanfm desktop (profile LXDE)"
  pcmanfm --desktop --profile LXDE >/dev/null 2>&1 &
  echo $! > "$BASE/pi_mode_pcmanfm.pid"
else
  echo "WARNING: pcmanfm not found (no desktop icons/background layer)"
fi

# Start idle watcher and wait until it exits (idle or sentinel).
"$BASE/pi_mode_idle_watch.sh" "$IDLE_MS" "$SENTINEL" &
WATCH_PID=$!
wait "$WATCH_PID" || true

echo "Pi mode exit triggered; cleaning up desktop components"

# Stop panel + desktop layer we started (but DO NOT kill Openbox).
for pf in "$BASE/pi_mode_lxpanel.pid" "$BASE/pi_mode_pcmanfm.pid"; do
  if [[ -f "$pf" ]]; then
    pid="$(cat "$pf" 2>/dev/null || true)"
    if [[ -n "${pid:-}" ]]; then
      kill "$pid" 2>/dev/null || true
      sleep 0.2
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$pf"
  fi
done

# IMPORTANT: do not kill openbox here; killing the WM can end the LightDM session.
rm -f "$BASE/pi_mode_openbox.pid" 2>/dev/null || true
rm -f "$SENTINEL" 2>/dev/null || true

echo "Pi mode complete; returning control to kiosk_shell"
exit 0
