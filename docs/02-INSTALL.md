# Install / Enable

## 1) Put files in place
Copy sparc_lock/* to:
  /home/pi/sparc_lock/

Ensure scripts are executable:
  chmod +x /home/pi/sparc_lock/start_lock.sh
  chmod +x /home/pi/sparc_lock/launch_solaris.sh

## 2) Ensure dependencies
Required:
  sudo apt-get update
  sudo apt-get install -y python3-pygame xprintidle xtigervncviewer mpv python3-yaml

Optional (if EXIF rotation needed in lock):
  sudo apt-get install -y python3-pil

## 3) Stop duplicate launchers (IMPORTANT)
You must have only ONE autostart path.

Search for accidental launches:
  pgrep -fa 'kiosk_shell.py|puzzle_lock.py|start_lock.sh'
  grep -R --line-number -E 'puzzle_lock\.py|kiosk_shell\.py|start_lock\.sh' \
    ~/.config/lxsession ~/.config/openbox ~/.config/autostart /etc/xdg 2>/dev/null

Then remove/comment any extra autostart lines that launch puzzle_lock.py directly.

## 4) Choose ONE autostart method

### Option A (simple): LXSession autostart
Add to:
  ~/.config/lxsession/LXDE-pi/autostart

Line:
  @/home/pi/sparc_lock/start_lock.sh

### Option B (recommended long-term): systemd user service
Install:
  mkdir -p ~/.config/systemd/user
  cp /home/pi/sparc_lock/systemd/sparc-kiosk.service ~/.config/systemd/user/

Enable:
  systemctl --user daemon-reload
  systemctl --user enable --now sparc-kiosk.service

If you use systemd, REMOVE LXSession autostart entry to avoid duplicates.

## 5) Test manually
From an SSH session inside X session:
  DISPLAY=:0 XAUTHORITY=/home/pi/.Xauthority /home/pi/sparc_lock/start_lock.sh
