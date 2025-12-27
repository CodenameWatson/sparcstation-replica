#!/usr/bin/env bash
set -euo pipefail

LOG="/home/pi/sparc_lock/return_to_lock.log"
exec >>"$LOG" 2>&1

echo "---- return_to_lock.sh $(date --iso-8601=seconds 2>/dev/null || date) ----"

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-/home/pi/.Xauthority}"
export HOME="/home/pi"
export USER="pi"
export LOGNAME="pi"

PIDFILE="/home/pi/sparc_lock/pi_mode_openbox.pid"

# Stop Pi-mode desktop components
pkill -TERM -x lxpanel 2>/dev/null || true
pkill -TERM -x pcmanfm 2>/dev/null || true
pkill -TERM -x lxterminal 2>/dev/null || true
pkill -TERM -x xterm 2>/dev/null || true

# Stop any viewers just in case
pkill -TERM -x vncviewer 2>/dev/null || true
pkill -TERM -x xtigervncviewer 2>/dev/null || true

# Tell Pi Mode to exit by stopping the Pi Mode openbox only
if [[ -f "$PIDFILE" ]]; then
  PID="$(cat "$PIDFILE" 2>/dev/null || true)"
  echo "Pi-mode openbox pid from pidfile: ${PID:-<empty>}"
  if [[ -n "${PID:-}" ]] && kill -0 "$PID" 2>/dev/null; then
    kill -TERM "$PID" 2>/dev/null || true
  fi
  rm -f "$PIDFILE" 2>/dev/null || true
else
  echo "WARN: No pidfile ($PIDFILE). Not killing openbox to avoid impacting kiosk WM."
fi

exit 0
