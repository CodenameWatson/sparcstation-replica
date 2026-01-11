#!/usr/bin/env bash
set -euo pipefail

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-/home/pi/.Xauthority}"

# Make the background black so if anything unmaps briefly, you don't see the desktop.
command -v xsetroot >/dev/null 2>&1 && xsetroot -solid black || true

while true; do
  /home/pi/sparc_lock/start_lock.sh >> /home/pi/sparc_lock/kiosk.log 2>&1 || true
  sleep 1
done