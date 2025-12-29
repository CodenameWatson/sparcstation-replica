# Troubleshooting

## Symptom: unlock -> black flash -> lock restarts
Cause: lock exited non-zero OR duplicate autostart spawns new lock.
Fix:
- verify lock exit rc:
    tail -n 120 /home/pi/sparc_lock/logs/kiosk_shell.log
- verify only one autostart path exists (remove duplicates)
- ensure env has:
    SDL_VIDEODRIVER=x11
    XDG_RUNTIME_DIR=/run/user/1000 (or similar)

## Symptom: XDG_RUNTIME_DIR invalid or not set
Fix:
- start_lock.sh exports XDG_RUNTIME_DIR automatically
- ensure kiosk_shell spawns child with that env (it does in this package)

## Symptom: Could not queue pageflip: -13 / CRTC errors
Cause: SDL chose kmsdrm backend instead of x11.
Fix:
- force SDL_VIDEODRIVER=x11 (done in start_lock.sh + kiosk_shell.py + puzzle_lock.py)

## Symptom: pygame.error: font not initialized
Cause: display quit/init cycles without font re-init.
Fix:
- kiosk_shell.py defensively calls pygame.font.init() before creating fonts.

## Symptom: multiple kiosk_shell.py running
Fix:
- kill them:
    pkill -f kiosk_shell.py
  remove lock:
    rm -f /tmp/sparc_kiosk_shell.lock
  start again:
    /home/pi/sparc_lock/start_lock.sh

## Quick debug commands
  pgrep -fa 'kiosk_shell.py|puzzle_lock.py|xtigervncviewer|mpv'
  tail -n 120 /home/pi/sparc_lock/logs/kiosk_shell.log
  tail -n 120 /home/pi/sparc_lock/logs/lock_child.log
