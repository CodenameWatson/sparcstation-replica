#!/usr/bin/env bash
set -euo pipefail

BASE="/home/pi/sparc_lock"
LOG="$BASE/pi_mode.log"
PANEL_LOG="$BASE/lxpanel.log"
PIDFILE="$BASE/pi_mode_openbox.pid"

exec >>"$LOG" 2>&1
echo "---- start_pi_mode.sh $(date --iso-8601=seconds 2>/dev/null || date) ----"

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-/home/pi/.Xauthority}"
export HOME="/home/pi"
export USER="pi"
export LOGNAME="pi"

# Prevent "(null)" XDG issues and make desktop bits find configs predictably
export XDG_RUNTIME_DIR="/run/user/1000"
export XDG_CONFIG_HOME="/home/pi/.config"
export XDG_DATA_HOME="/home/pi/.local/share"
export XDG_CONFIG_DIRS="/etc/xdg"
export XDG_DATA_DIRS="/usr/local/share:/usr/share"

# Fix lxpanel icon scale issues / white-square icons (forces scale >= 1)
export GDK_SCALE=1
export GDK_DPI_SCALE=1
unset QT_SCALE_FACTOR QT_AUTO_SCREEN_SCALE_FACTOR QT_SCREEN_SCALE_FACTORS || true

command -v xsetroot >/dev/null 2>&1 && xsetroot -solid black || true
command -v xset >/dev/null 2>&1 && xset s off -dpms s noblank || true

# Choose the best LXDE profile available (Raspberry Pi Desktop usually uses LXDE-pi)
PROFILE="LXDE"
if [[ -d "$HOME/.config/pcmanfm/LXDE-pi" ]] || [[ -d "/etc/xdg/pcmanfm/LXDE-pi" ]]; then
  PROFILE="LXDE-pi"
fi
echo "Using profile: $PROFILE"

# Idle auto-return to lock (ms). Default 5 min.
PI_IDLE_LOCK_MS="${PI_IDLE_LOCK_MS:-300000}"

cleanup() {
  echo "Cleanup: stopping Pi-mode components"
  rm -f "$PIDFILE" >/dev/null 2>&1 || true
  pkill -TERM -x lxpanel  >/dev/null 2>&1 || true
  pkill -TERM -x pcmanfm  >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

if ! command -v openbox >/dev/null 2>&1; then
  echo "ERROR: openbox not installed."
  sleep 2
  exit 1
fi

# Start Openbox (Pi-mode WM) and record pid so return_to_lock.sh can end Pi-mode cleanly
openbox &
OB_PID=$!
echo "$OB_PID" >"$PIDFILE"
echo "Pi-mode openbox pid=$OB_PID (pidfile=$PIDFILE)"
sleep 0.4

# Desktop manager (wallpaper/icons)
if command -v pcmanfm >/dev/null 2>&1; then
  pcmanfm --desktop --profile "$PROFILE" >/dev/null 2>&1 &

  # Best-effort wallpaper set if supported
  if pcmanfm --help 2>&1 | grep -q -- '--set-wallpaper'; then
    WALLPAPER=""
    for p in /usr/share/rpd-wallpaper/* /usr/share/backgrounds/* /usr/share/pixmaps/*; do
      [[ -f "$p" ]] || continue
      case "$p" in
        *.jpg|*.jpeg|*.png) WALLPAPER="$p"; break ;;
      esac
    done
    if [[ -n "${WALLPAPER:-}" ]]; then
      echo "Setting wallpaper: $WALLPAPER"
      pcmanfm --set-wallpaper="$WALLPAPER" --wallpaper-mode=stretch >/dev/null 2>&1 || true
    else
      echo "WARN: No wallpaper image found in common locations."
    fi
  fi
else
  echo "WARN: pcmanfm not installed (no desktop icons/background manager)."
fi

# Panel/taskbar (log output; do not redirect to /dev/null so we can debug icon/theme issues)
if command -v lxpanel >/dev/null 2>&1; then
  pkill -TERM -x lxpanel >/dev/null 2>&1 || true
  sleep 0.2

  echo "Starting lxpanel --profile $PROFILE (log=$PANEL_LOG)"
  lxpanel --profile "$PROFILE" >>"$PANEL_LOG" 2>&1 &

  # If it dies immediately, try once more (common when DISPLAY/XDG not ready)
  sleep 0.8
  if ! pgrep -x lxpanel >/dev/null 2>&1; then
    echo "WARN: lxpanel exited quickly; retrying once..."
    lxpanel --profile "$PROFILE" >>"$PANEL_LOG" 2>&1 &
  fi
else
  echo "WARN: lxpanel not installed (no panel/taskbar)."
fi

# Idle watcher to auto-return to lock (Pi Mode only)
if command -v xprintidle >/dev/null 2>&1; then
  (
    echo "Idle watcher enabled: threshold=${PI_IDLE_LOCK_MS}ms"
    while kill -0 "$OB_PID" >/dev/null 2>&1; do
      idle="$(xprintidle 2>/dev/null || echo 0)"
      if [[ "$idle" =~ ^[0-9]+$ ]] && (( idle >= PI_IDLE_LOCK_MS )); then
        echo "Idle ${idle}ms >= ${PI_IDLE_LOCK_MS}ms -> return_to_lock"
        /home/pi/sparc_lock/return_to_lock.sh || true
        break
      fi
      sleep 1
    done
  ) &
else
  echo "WARN: xprintidle not installed; PI MODE will not auto-return to lock."
fi

echo "Terminal not auto-launched (by design)."

# Stay alive until WM exits (return_to_lock.sh should terminate Pi-mode openbox via pidfile)
wait "$OB_PID" || true

# Cleanup PID file (trap also covers this)
rm -f "$PIDFILE" || true
