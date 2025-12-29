#!/usr/bin/env bash
set -euo pipefail

LOG="/home/pi/sparc_lock/logs/xauth_sync.log"
mkdir -p /home/pi/sparc_lock/logs
{
  echo "[$(date -Is)] xauth sync running"
  ls -la /var/run/lightdm/root/:0 || true

  if [[ -r /var/run/lightdm/root/:0 ]]; then
    install -m 600 -o pi -g pi /var/run/lightdm/root/:0 /home/pi/.Xauthority
    echo "[$(date -Is)] installed /var/run/lightdm/root/:0 -> /home/pi/.Xauthority"
    ls -la /home/pi/.Xauthority || true
  else
    echo "[$(date -Is)] WARNING: cannot read /var/run/lightdm/root/:0"
  fi

  # Best-effort: confirm X access as pi
  sudo -u pi env DISPLAY=:0 XAUTHORITY=/home/pi/.Xauthority xset q >/dev/null 2>&1 \
    && echo "[$(date -Is)] xset OK" \
    || echo "[$(date -Is)] xset FAIL"
} >>"$LOG" 2>&1

exit 0
