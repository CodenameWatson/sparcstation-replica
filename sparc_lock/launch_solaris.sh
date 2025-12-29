#!/usr/bin/env bash
set -euo pipefail

export DISPLAY="${DISPLAY:-:0}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export SDL_VIDEODRIVER="${SDL_VIDEODRIVER:-x11}"
export SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS="0"

# Use discovered/propagated XAUTHORITY if present; do not force a missing file.
: "${XAUTHORITY:=}"

VNC_TARGET="${VNC_TARGET:-127.0.0.1:1}"

# Pick an available viewer
if command -v xtigervncviewer >/dev/null 2>&1; then
  exec xtigervncviewer \
    -FullScreen=1 \
    -Shared=1 \
    -RemoteResize=0 \
    -SendClipboard=0 \
    -AcceptClipboard=0 \
    "$VNC_TARGET"
elif command -v vncviewer >/dev/null 2>&1; then
  exec vncviewer \
    -FullScreen=1 \
    -Shared=1 \
    "$VNC_TARGET"
else
  echo "No VNC viewer found (xtigervncviewer/vncviewer)."
  exit 127
fi

