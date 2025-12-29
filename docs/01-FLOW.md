# Runtime flow

1) Autostart runs:
   /home/pi/sparc_lock/start_lock.sh

2) start_lock.sh launches:
   python3 -u /home/pi/sparc_lock/kiosk_shell.py

3) kiosk_shell.py:
   - enforces singleton (one instance only)
   - ensures VM is running (optional autostart)
   - runs lock by spawning puzzle_lock.py as a child
     - kiosk_shell suspends its display
     - puzzle_lock owns fullscreen
     - puzzle_lock exits rc=0 when unlocked
   - kiosk_shell reclaims fullscreen and shows menu

4) Menu choices:
   - Solaris: spawn /home/pi/sparc_lock/launch_solaris.sh (VNC viewer)
   - Media: spawn mpv in fullscreen
   - Games: spawn a game from manifest
   - Shutdown: calls shutdown
   - Re-lock: goes back to lock (spawns puzzle_lock again)
   - Pi: PIN-gated exit-to-desktop (exit code 42)

5) External apps:
   - kiosk_shell suspends its display
   - external app runs fullscreen
   - kiosk_shell monitors idle (xprintidle) and kills external app if idle threshold reached
   - kiosk_shell reclaims fullscreen and returns to menu
