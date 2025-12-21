#!/usr/bin/env bash
set -euo pipefail

DISK="/home/pi/sparc_vm/sol8.qcow2"
ISO_INSTALL="/home/pi/sparc_vm/sol8_install.iso"   # optional after install
ISO_SOFT1="/home/pi/sparc_vm/sol8_disc1.iso"
ISO_SOFT2="/home/pi/sparc_vm/sol8_disc2.iso"

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

# If a previous instance is still running, refuse to start a second copy.
if [ -f "$PIDFILE" ]; then
  OLD_PID="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [ -n "${OLD_PID:-}" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "QEMU already running (PID $OLD_PID)." >&2
    echo "Stop it with: telnet 127.0.0.1 4444  (then type 'quit')" >&2
    echo "Or: kill $OLD_PID" >&2
    exit 1
  fi
  rm -f "$PIDFILE"
fi

# Basic sanity checks (Disc 2 included)
for f in "$DISK" "$ISO_SOFT1" "$ISO_SOFT2" "$BIOS"; do
  if [ ! -e "$f" ]; then
    echo "Missing required file: $f" >&2
    exit 1
  fi
done

exec qemu-system-sparc \
  -M SS-5 -m 256 -bios "$BIOS" \
  -drive file="$DISK",format=qcow2,if=scsi,media=disk \
  -drive file="$ISO_SOFT1",media=cdrom,if=scsi,readonly=on \
  -drive file="$ISO_SOFT2",media=cdrom,if=scsi,readonly=on \
  -boot c \
  -vga cg3 \
  -display none \
  -vnc :1 \
  -monitor telnet:127.0.0.1:4444,server,nowait \
  -daemonize \
  -pidfile "$PIDFILE" \
  -D "$LOGFILE"
