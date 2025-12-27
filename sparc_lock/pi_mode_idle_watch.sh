#!/usr/bin/env bash
set -u -o pipefail

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-/home/pi/.Xauthority}"

IDLE_SECONDS="${PI_MODE_IDLE_SECONDS:-300}"   # 5 minutes default
IDLE_MS=$((IDLE_SECONDS * 1000))

# If xprintidle isn't installed, do nothing.
command -v xprintidle >/dev/null 2>&1 || exit 0

while true; do
  idle="$(xprintidle 2>/dev/null || echo 0)"
  if [[ "${idle:-0}" -ge "$IDLE_MS" ]]; then
    /home/pi/sparc_lock/return_to_lock.sh
    exit 0
  fi
  sleep 1
done
