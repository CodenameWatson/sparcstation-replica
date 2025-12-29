# SPARCstation Replica Kiosk

## Goal
A Raspberry Pi kiosk that:
1) boots into a full-screen lock (puzzle_lock.py)
2) when unlocked, returns to a full-screen kiosk menu (kiosk_shell.py)
3) launches external experiences (Solaris via VNC, media via mpv, games) and returns to menu on exit/idle
4) can optionally “exit kiosk to Pi desktop” behind a PIN

## Correct process ownership model (critical)
Only ONE fullscreen app at a time:
- kiosk_shell.py owns fullscreen when showing MENU
- puzzle_lock.py owns fullscreen during LOCK
- external apps (xtigervncviewer/mpv/games) own fullscreen during their run

kiosk_shell “suspends” its SDL display before spawning children, then “reclaims” fullscreen after the child exits.

## Runtime locations
- Lock/Menu runtime: /home/pi/sparc_lock/
- VM runtime: /home/pi/sparc_vm/
- Media (optional): /home/pi/sparc_media/{images,music,videos}
- Games (optional): /home/pi/sparc_games/installed/<game>/manifest.json

## Entrypoint
Use ONLY:
  /home/pi/sparc_lock/start_lock.sh

Do NOT also autostart puzzle_lock.py anywhere else. That is the #1 source of “black flash -> lock restarts” and “many puzzle_lock.py processes”.

## Logs
- /home/pi/sparc_lock/logs/kiosk_shell.log
- /home/pi/sparc_lock/logs/lock_child.log
- /home/pi/sparc_lock/logs/solaris_vnc.log
- /home/pi/sparc_lock/logs/mpv.log
- /home/pi/sparc_lock/logs/games/*.log

## Exit codes
- puzzle_lock.py exits 0 when unlocked successfully (this is the contract)
- kiosk_shell.py uses exit code 42 for “exit to Pi desktop”
