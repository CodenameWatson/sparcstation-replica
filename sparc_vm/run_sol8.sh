#!/usr/bin/env bash
set -euo pipefail

DISK="/home/pi/sparc_vm/sol8.qcow2"
PIDFILE="/home/pi/sparc_vm/qemu-sparc.pid"
LOGFILE="/home/pi/sparc_vm/qemu-sparc.log"

# Locate OpenBIOS
if [ -f /usr/share/openbios/openbios-sparc32 ]; then
  BIOS="/usr/share/openbios/openbios-sparc32"
elif [ -f /usr/share/qemu/openbios-sparc32 ]; then
  BIOS="/usr/share/qemu/openbios-sparc32"
else
  echo "OpenBIOS SPARC32 not found" >&2
  exit 1
fi

# If already running, exit successfully (idempotent)
if [ -f "$PIDFILE" ]; then
  PID="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [ -n "${PID:-}" ] && kill -0 "$PID" 2>/dev/null; then
    echo "QEMU already running (PID $PID)."
    exit 0
  fi
  # stale pidfile
  rm -f "$PIDFILE" 2>/dev/null || true
fi

exec qemu-system-sparc \
  -M SS-5 -m 256 -bios "$BIOS" \
  -drive file="$DISK",format=qcow2,if=scsi,media=disk \
  -prom-env 'auto-boot?=true' \
  -prom-env 'boot-device=disk:a' \
  -boot c \
  -vga cg3 \
  -display none \
  -vnc 127.0.0.1:1 \
  -monitor telnet:127.0.0.1:4444,server,nowait \
  -daemonize \
  -pidfile "$PIDFILE" \
  -D "$LOGFILE"
