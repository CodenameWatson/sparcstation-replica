#!/usr/bin/env bash
# If launched under /bin/sh (dash), re-exec under bash.
if [ -z "${BASH_VERSION:-}" ]; then
  exec /usr/bin/env bash "$0" "$@"
fi

# Prevent duplicate start_lock instances (critical)
exec 9>/tmp/sparc_start_lock.lock
flock -n 9 || exit 0

set -euo pipefail

BASE="/home/pi/sparc_lock"
LOGDIR="$BASE/logs"
LOG="$LOGDIR/start_lock.log"
mkdir -p "$LOGDIR"

exec >>"$LOG" 2>&1
echo "[$(date -Is)] start_lock.sh begin (uid=$(id -u) user=$(id -un))"

export HOME="/home/pi"
export USER="pi"
export LOGNAME="pi"
export DISPLAY="${DISPLAY:-:0}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/1000}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"

echo "[$(date -Is)] DISPLAY=$DISPLAY XAUTHORITY=$XAUTHORITY XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR"

if command -v xset >/dev/null 2>&1; then
  for i in $(seq 1 80); do
    if xset q >/dev/null 2>&1; then
      echo "[$(date -Is)] X ready (xset q ok)"
      break
    fi
    sleep 0.25
  done
fi

if command -v xset >/dev/null 2>&1; then
  xset s off  || true
  xset -dpms || true
  xset s noblank || true
fi

while true; do
  echo "[$(date -Is)] Launching kiosk_shell.py"

  # IMPORTANT: kiosk_shell intentionally exits non-zero to signal actions.
  # With `set -e`, we must suppress immediate exit so we can capture rc.
  set +e
  /usr/bin/python3 -u "$BASE/kiosk_shell.py"
  rc=$?
  set -e

  echo "[$(date -Is)] kiosk_shell.py exited rc=$rc"

  case "$rc" in
    0)
      echo "[$(date -Is)] rc=0 -> relock / restart loop"
      ;;

    42)
      echo "[$(date -Is)] rc=42 -> entering Pi mode (foreground)"
      /usr/bin/env bash "$BASE/start_pi_mode.sh" || true
      ;;

    43)
      echo "[$(date -Is)] rc=43 -> entering Solaris mode (foreground)"
      /usr/bin/env bash "$BASE/launch_solaris.sh" || true
      ;;

    46)
      echo "[$(date -Is)] rc=46 -> entering Games mode (foreground)"
      if [[ -x "$BASE/launch_games.sh" ]]; then
        /usr/bin/env bash "$BASE/launch_games.sh" || true
      else
        echo "[$(date -Is)] launch_games.sh missing or not executable; relocking"
      fi
      ;;

    47)
      echo "[$(date -Is)] rc=47 -> entering Media mode (foreground)"
      if [[ -x "$BASE/launch_media.sh" ]]; then
        /usr/bin/env bash "$BASE/launch_media.sh" || true
      else
        echo "[$(date -Is)] launch_media.sh missing or not executable; relocking"
      fi
      ;;

    44)
      echo "[$(date -Is)] rc=44 -> shutdown requested"
      sudo /sbin/poweroff || true
      ;;

    45)
      echo "[$(date -Is)] rc=45 -> reboot requested"
      sudo /sbin/reboot || true
      ;;

    *)
      echo "[$(date -Is)] rc=$rc -> unhandled, restarting loop"
      ;;
  esac

  sleep 1
done
