# SPARCstation Replica (Pi + Puzzle Lock + Solaris 8 SPARC in QEMU)

This project builds a Sun SPARCstation-style “appliance”:
- Raspberry Pi boots and presents a fullscreen puzzle lock.
- The Solaris 8 SPARC VM is started at boot (QEMU).
- On unlock, a fullscreen VNC viewer opens instantly to the already-running Solaris desktop.

## Repository structure

sparcstation-replica/
-sparc_lock/
-  puzzle_lock.py
-  launch_solaris.sh
-  start_lock.sh
-  images/ (.keep)
-  sounds/ (.keep)
-sparc_vm/
-  run_sol8.sh
-  stop_sol8.sh
-  install_sol8.sh (optional)
-systemd/
-  sol8-qemu.service
-boot/
-  lxsession-rpd-x-autostart.example
-  lightdm-50-sparc-lock.conf.example
-  xsessions-sparc-lock.desktop
-docs/
-  SETUP.md
-  TROUBLESHOOTING.md
-.gitignore
-README.md


## What is not committed (by design)

- Solaris ISO media (`*.iso`)
- VM disks (`*.qcow2`)
- Personal image/sound libraries

These must be supplied locally on the Pi:
- `/home/pi/sparc_vm/sol8.qcow2`
- (optional for install) `/home/pi/sparc_vm/sol8_install.iso`, etc.

## Quick start (manual)

### Start VM (headless VNC)
```bash
/home/pi/sparc_vm/run_sol8.sh
Start lock
python3 /home/pi/sparc_lock/puzzle_lock.py

Show Solaris instantly (once VM is running)
/home/pi/sparc_lock/launch_solaris.sh

Boot-time behavior (recommended)

QEMU service runs at boot via systemd (sol8-qemu.service)

Puzzle lock runs as the LightDM session (no desktop), or via LXSession autostart during development