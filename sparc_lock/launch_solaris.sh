#!/usr/bin/env bash
set -euo pipefail

export DISPLAY=:0

DISK="/home/pi/sparc_vm/sol8.qcow2"
PIDFILE="/home/pi/sparc_vm/qemu-sparc.pid"
LOGFILE="/home/pi/sparc_vm/qemu-sparc.log"

# Locate OpenBIOS (SPARC32)
if [ -f /usr/share/openbios/openbios-sparc32 ]; then
  BIOS="/usr/share/openbios/openbios-sparc32"
elif [ -f /usr/share/qemu/openbios-sparc32 ]; then
  BIOS="/usr/share/qemu/openbios-sparc32"
else
  echo "OpenBIOS SPARC32 not found" >&2
  exit 1
fi

# Refuse to start if already running
if [ -f "$PIDFILE" ]; then
  OLD_PID="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [ -n "${OLD_PID:-}" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "QEMU already running (PID $OLD_PID). Stop it first." >&2
    exit 1
  fi
  rm -f "$PIDFILE" || true
fi

exec qemu-system-sparc \
  -M SS-5 \
  -m 256 \
  -bios "$BIOS" \
  -drive file="$DISK",format=qcow2,if=scsi,media=disk \
  -prom-env 'auto-boot?=true' \
  -prom-env 'boot-device=disk:a' \
  -boot c \
  -vga cg3 \
  -display sdl -full-screen \
  -monitor telnet:127.0.0.1:4444,server,nowait \
  -pidfile "$PIDFILE" \
  -D "$LOGFILE"
