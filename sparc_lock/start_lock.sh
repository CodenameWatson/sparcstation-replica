#!/usr/bin/env bash
set -euo pipefail

cd /home/pi/sparc_lock

export HOME="/home/pi"
export USER="pi"
export LOGNAME="pi"

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-/home/pi/.Xauthority}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

# Force SDL to use X11 (prevents DRM/KMS "CRTC/pageflip" failures)
export SDL_VIDEODRIVER="${SDL_VIDEODRIVER:-x11}"
unset WAYLAND_DISPLAY
unset WAYLAND_SOCKET

export SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS="0"
export PYGAME_HIDE_SUPPORT_PROMPT="1"

# Prevent blanking / DPMS (only if xset exists)
if command -v xset >/dev/null 2>&1; then
  xset s off || true
  xset -dpms || true
  xset s noblank || true
fi

mkdir -p /home/pi/sparc_lock/logs
exec python3 -u /home/pi/sparc_lock/kiosk_shell.py >> /home/pi/sparc_lock/logs/kiosk_shell.log 2>&1
