#!/usr/bin/env bash
set -u -o pipefail

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-/home/pi/.Xauthority}"
export HOME="/home/pi"
export USER="pi"
export LOGNAME="pi"

BASE="/home/pi/sparc_lock"
KIOSK_LOG="$BASE/kiosk.log"
OPENBOX_LOG="$BASE/openbox.log"
LOCK_START="$BASE/start_lock.sh"
PI_MODE_SCRIPT="$BASE/start_pi_mode.sh"

ADMIN_RC=42

log() {
  printf '[%s] %s\n' "$(date --iso-8601=seconds 2>/dev/null || date)" "$*" >>"$KIOSK_LOG"
}

black_screen() {
  command -v xsetroot >/dev/null 2>&1 && xsetroot -solid black || true
}

start_lock_wm() {
  if ! pgrep -x openbox >/dev/null 2>&1; then
    log "Starting openbox WM (lock)"
    openbox >>"$OPENBOX_LOG" 2>&1 &

    # Wait briefly for WM hints to appear
    for _ in {1..30}; do
      DISPLAY="$DISPLAY" XAUTHORITY="$XAUTHORITY" xprop -root _NET_SUPPORTING_WM_CHECK >/dev/null 2>&1 && break
      sleep 0.1
    done
  fi
}

stop_wm_and_agents() {
  log "Stopping kiosk WM + any viewers/agents"

  # Stop VNC viewers if up
  pkill -x vncviewer >/dev/null 2>&1 || true
  pkill -x xtigervncviewer >/dev/null 2>&1 || true

  # Stop any polkit agents that can collide
  pkill -u pi -f 'lxpolkit' >/dev/null 2>&1 || true
  pkill -u pi -f 'polkit-gnome-authentication-agent-1' >/dev/null 2>&1 || true
  pkill -u pi -f 'polkit-kde-authentication-agent-1' >/dev/null 2>&1 || true
  pkill -u pi -f 'mate-polkit' >/dev/null 2>&1 || true
  pkill -u pi -f 'xfce-polkit' >/dev/null 2>&1 || true

  # Stop openbox cleanly then hard if needed
  pkill -x openbox >/dev/null 2>&1 || true
  sleep 0.3
  pkill -9 -x openbox >/dev/null 2>&1 || true

  black_screen
}

run_pi_mode() {
  log "Entering PI MODE via $PI_MODE_SCRIPT"

  stop_wm_and_agents

  if [[ ! -x "$PI_MODE_SCRIPT" ]]; then
    log "ERROR: PI MODE script missing or not executable: $PI_MODE_SCRIPT"
    sleep 2
    return 1
  fi

  # IMPORTANT: run in foreground, do NOT exec
  log "PI MODE starting (foreground)"
  "$PI_MODE_SCRIPT"
  PI_RC=$?
  log "PI MODE exited rc=$PI_RC"

  black_screen
  start_lock_wm
  return 0
}

# Reduce flash at session start
black_screen
start_lock_wm

while true; do
  if [[ ! -x "$LOCK_START" ]]; then
    log "ERROR: $LOCK_START is missing or not executable"
    sleep 2
    continue
  fi

  log "Starting lock: $LOCK_START"

  rc=0
  "$LOCK_START" >>"$KIOSK_LOG" 2>&1 || rc=$?

  log "Lock exited rc=$rc"

  # Admin requested Pi desktop
  if [[ "$rc" -eq "$ADMIN_RC" ]]; then
    run_pi_mode
  fi

  # If lock exits/crashes, keep kiosk alive and restart it
  sleep 1
done
