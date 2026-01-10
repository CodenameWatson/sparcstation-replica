#!/usr/bin/env bash
set -euo pipefail

IDLE_MS="${1:-300000}"
SENTINEL="${2:-/tmp/sparc_pi_mode_exit}"

BASE="/home/pi/sparc_lock"
LOG="$BASE/logs/pi_mode.log"
mkdir -p "$BASE/logs"

echo "Idle watcher enabled: threshold=${IDLE_MS}ms sentinel=$SENTINEL" >>"$LOG" 2>&1

# If xprintidle is missing, fall back to a simple sleep (best effort).
if ! command -v xprintidle >/dev/null 2>&1; then
  echo "WARNING: xprintidle not found; sleeping for ${IDLE_MS}ms then exiting" >>"$LOG" 2>&1
  sleep $(( (IDLE_MS + 999) / 1000 ))
  exit 0
fi

while true; do
  if [[ -e "$SENTINEL" ]]; then
    echo "Idle watcher: sentinel present; exiting" >>"$LOG" 2>&1
    exit 0
  fi

  idle="$(xprintidle 2>/dev/null || echo 0)"
  if [[ "$idle" =~ ^[0-9]+$ ]] && (( idle >= IDLE_MS )); then
    echo "Idle watcher: idle ${idle}ms >= ${IDLE_MS}ms; exiting" >>"$LOG" 2>&1
    exit 0
  fi

  sleep 1
done
