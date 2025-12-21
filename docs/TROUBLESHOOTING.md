
---

## `docs/TROUBLESHOOTING.md`
```markdown
# Troubleshooting

## Check if you are in a GUI session
Autostart only works in a graphical session:
```bash
echo $XDG_SESSION_TYPE
pgrep -a lxsession || true
pgrep -a Xorg || pgrep -a Xwayland || pgrep -a wayfire || true
If XDG_SESSION_TYPE=tty, you are not running the desktop.

Puzzle not starting at boot
LXSession path correctness (Bookworm)

Confirm session profile:

ls -la /etc/xdg/lxsession/


If you see rpd-x, your user autostart must be:
/home/pi/.config/lxsession/rpd-x/autostart

Check lock log
tail -200 /home/pi/sparc_lock/kiosk.log || true

VM not ready / black screen
Check systemd QEMU service
systemctl status sol8-qemu.service --no-pager
journalctl -u sol8-qemu.service -b --no-pager | tail -200

Check VNC listener
ss -ltnp | grep 5901 || true


If not listening, QEMU is not running or failed to start.

VNC viewer won’t open or closes immediately

Run it in a terminal to see errors:

vncviewer 127.0.0.1:1


Common causes:

service not running

port blocked (should not be if localhost)

missing viewer package

Solaris slow or stuck booting

This can happen under SS-5 emulation.

Let it boot once and remain running.

Reboots are slower than waking an already-running VM.

Consider Pi 5 for better performance.

Clean restart
sudo systemctl restart sol8-qemu.service

Confirm QEMU process
pgrep -a qemu-system-sparc || true