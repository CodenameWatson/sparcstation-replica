# # # # # # #!/usr/bin/env python3
# # # # # # """
# # # # # # SPARCstation Kiosk Shell (X11 / pygame)
# # # # # #
# # # # # # Design:
# # # # # # - LightDM autologin starts one X session.
# # # # # # - Openbox runs once for the whole session (managed by sparc-lock-session.sh).
# # # # # # - start_lock.sh supervises kiosk_shell.py.
# # # # # # - kiosk_shell.py runs the lock screen, then a menu.
# # # # # # - "Pi" runs Pi admin mode INLINE (no LightDM logout / no greeter).
# # # # # # - "Solaris" runs the VNC viewer INLINE.
# # # # # #
# # # # # # Key anti-flash change:
# # # # # # - Do NOT pygame.display.quit()/init() around child processes.
# # # # # #   Keep the kiosk fullscreen window alive, paint it black, ungrab input, and let the child
# # # # # #   fullscreen window cover it. On return, just re-grab and repaint.
# # # # # # """
# # # # # #
# # # # # # import os
# # # # # # import sys
# # # # # # import time
# # # # # # import json
# # # # # # import yaml
# # # # # # import signal
# # # # # # import subprocess
# # # # # # from dataclasses import dataclass
# # # # # # from typing import Optional, TextIO, List, Dict, Any, Tuple
# # # # # # import fcntl
# # # # # #
# # # # # # # Hide pygame's banner BEFORE importing pygame
# # # # # # os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
# # # # # #
# # # # # # import pygame
# # # # # #
# # # # # #
# # # # # # # ---- Environment hardening (X11-only kiosk) ----
# # # # # # def _runtime_dir_for_uid(uid: int) -> str:
# # # # # #     return os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{uid}"
# # # # # #
# # # # # #
# # # # # # def _force_x11_env_base() -> None:
# # # # # #     uid = os.getuid()
# # # # # #     os.environ.setdefault("DISPLAY", ":0")
# # # # # #     os.environ.setdefault("XAUTHORITY", "/home/pi/.Xauthority")
# # # # # #     os.environ.setdefault("XDG_RUNTIME_DIR", _runtime_dir_for_uid(uid))
# # # # # #
# # # # # #     # Force SDL to X11 to avoid Wayland/KMS/DRM paths
# # # # # #     os.environ.setdefault("SDL_VIDEODRIVER", "x11")
# # # # # #     os.environ.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")
# # # # # #
# # # # # #     # Avoid SDL choosing Wayland paths
# # # # # #     os.environ.pop("WAYLAND_DISPLAY", None)
# # # # # #     os.environ.pop("WAYLAND_SOCKET", None)
# # # # # #
# # # # # #
# # # # # # _force_x11_env_base()
# # # # # #
# # # # # #
# # # # # # def _with_x_env(env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
# # # # # #     e = dict(env) if env else os.environ.copy()
# # # # # #     uid = os.getuid()
# # # # # #
# # # # # #     e.setdefault("DISPLAY", os.environ.get("DISPLAY", ":0"))
# # # # # #     e.setdefault("XAUTHORITY", os.environ.get("XAUTHORITY", "/home/pi/.Xauthority"))
# # # # # #     e.setdefault("XDG_RUNTIME_DIR", os.environ.get("XDG_RUNTIME_DIR", _runtime_dir_for_uid(uid)))
# # # # # #
# # # # # #     e.setdefault("SDL_VIDEODRIVER", "x11")
# # # # # #     e.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")
# # # # # #
# # # # # #     e.pop("WAYLAND_DISPLAY", None)
# # # # # #     e.pop("WAYLAND_SOCKET", None)
# # # # # #
# # # # # #     # Keep pygame banner suppressed in subprocesses too
# # # # # #     e.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
# # # # # #     return e
# # # # # #
# # # # # #
# # # # # # # ------------------------------
# # # # # # # Utilities: logging
# # # # # # # ------------------------------
# # # # # # def log_line(path: str, msg: str) -> None:
# # # # # #     ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
# # # # # #     line = f"[{ts}] {msg}\n"
# # # # # #     try:
# # # # # #         d = os.path.dirname(path)
# # # # # #         if d:
# # # # # #             os.makedirs(d, exist_ok=True)
# # # # # #         with open(path, "a", buffering=1) as f:
# # # # # #             f.write(line)
# # # # # #     except Exception:
# # # # # #         sys.stderr.write(line)
# # # # # #
# # # # # #
# # # # # # # ------------------------------
# # # # # # # Utilities: singleton lock
# # # # # # # ------------------------------
# # # # # # def ensure_singleton(lock_path: Optional[str] = None) -> int:
# # # # # #     """
# # # # # #     Prevent multiple kiosk_shell instances.
# # # # # #
# # # # # #     If another instance is running, we BLOCK until the lock becomes free.
# # # # # #     This prevents start_lock.sh from spinning if it starts kiosk_shell twice.
# # # # # #     """
# # # # # #     uid = os.getuid()
# # # # # #     rdir = _runtime_dir_for_uid(uid)
# # # # # #     try:
# # # # # #         os.makedirs(rdir, exist_ok=True)
# # # # # #     except Exception:
# # # # # #         rdir = "/tmp"
# # # # # #
# # # # # #     if lock_path is None:
# # # # # #         lock_path = os.path.join(rdir, "sparc_kiosk_shell.lock")
# # # # # #
# # # # # #     fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
# # # # # #
# # # # # #     # Try non-blocking first, then block if held
# # # # # #     try:
# # # # # #         fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
# # # # # #     except BlockingIOError:
# # # # # #         fcntl.flock(fd, fcntl.LOCK_EX)
# # # # # #
# # # # # #     try:
# # # # # #         os.ftruncate(fd, 0)
# # # # # #         os.write(fd, f"{os.getpid()}\n".encode())
# # # # # #     except Exception:
# # # # # #         pass
# # # # # #
# # # # # #     return fd
# # # # # #
# # # # # #
# # # # # # # ------------------------------
# # # # # # # Utilities: xprintidle
# # # # # # # ------------------------------
# # # # # # def read_xprintidle_ms(xprintidle_bin: str = "xprintidle") -> Optional[int]:
# # # # # #     env = _with_x_env(os.environ.copy())
# # # # # #     try:
# # # # # #         out = subprocess.check_output([xprintidle_bin], text=True, env=env, timeout=0.8).strip()
# # # # # #         return int(out)
# # # # # #     except Exception:
# # # # # #         return None
# # # # # #
# # # # # #
# # # # # # # ------------------------------
# # # # # # # Utilities: process management
# # # # # # # ------------------------------
# # # # # # @dataclass
# # # # # # class ManagedProcess:
# # # # # #     name: str
# # # # # #     popen: subprocess.Popen
# # # # # #     log_handle: Optional[TextIO] = None
# # # # # #
# # # # # #
# # # # # # def kill_process_group(p: subprocess.Popen, log_path: str, name: str) -> None:
# # # # # #     if p.poll() is not None:
# # # # # #         return
# # # # # #
# # # # # #     try:
# # # # # #         pgid = os.getpgid(p.pid)
# # # # # #     except Exception:
# # # # # #         pgid = None
# # # # # #
# # # # # #     def _wait_brief(deadline_s: float) -> bool:
# # # # # #         end = time.monotonic() + deadline_s
# # # # # #         while time.monotonic() < end:
# # # # # #             if p.poll() is not None:
# # # # # #                 return True
# # # # # #             time.sleep(0.05)
# # # # # #         return p.poll() is not None
# # # # # #
# # # # # #     if not pgid or pgid <= 0:
# # # # # #         try:
# # # # # #             log_line(log_path, f"Killing {name}: SIGTERM pid={p.pid} (no pgid)")
# # # # # #             p.terminate()
# # # # # #         except Exception:
# # # # # #             pass
# # # # # #         if _wait_brief(2.0):
# # # # # #             return
# # # # # #         try:
# # # # # #             log_line(log_path, f"Killing {name}: SIGKILL pid={p.pid} (no pgid)")
# # # # # #             p.kill()
# # # # # #         except Exception:
# # # # # #             pass
# # # # # #         try:
# # # # # #             p.wait(timeout=1.0)
# # # # # #         except Exception:
# # # # # #             pass
# # # # # #         return
# # # # # #
# # # # # #     try:
# # # # # #         log_line(log_path, f"Killing {name}: SIGTERM pgid={pgid}")
# # # # # #         os.killpg(pgid, signal.SIGTERM)
# # # # # #     except Exception:
# # # # # #         pass
# # # # # #     if _wait_brief(2.0):
# # # # # #         return
# # # # # #     try:
# # # # # #         log_line(log_path, f"Killing {name}: SIGKILL pgid={pgid}")
# # # # # #         os.killpg(pgid, signal.SIGKILL)
# # # # # #     except Exception:
# # # # # #         pass
# # # # # #     try:
# # # # # #         p.wait(timeout=1.0)
# # # # # #     except Exception:
# # # # # #         pass
# # # # # #
# # # # # #
# # # # # # def spawn_process(
# # # # # #     name: str,
# # # # # #     argv: List[str],
# # # # # #     log_path: Optional[str],
# # # # # #     env: Optional[Dict[str, str]] = None,
# # # # # #     cwd: Optional[str] = None,
# # # # # # ) -> ManagedProcess:
# # # # # #     log_handle = None
# # # # # #     if log_path:
# # # # # #         d = os.path.dirname(log_path)
# # # # # #         if d:
# # # # # #             os.makedirs(d, exist_ok=True)
# # # # # #         log_handle = open(log_path, "ab", buffering=0)
# # # # # #
# # # # # #     stdout_target = log_handle if log_handle else subprocess.DEVNULL
# # # # # #
# # # # # #     p = subprocess.Popen(
# # # # # #         argv,
# # # # # #         env=_with_x_env(env),
# # # # # #         cwd=cwd,
# # # # # #         stdin=subprocess.DEVNULL,
# # # # # #         stdout=stdout_target,
# # # # # #         stderr=subprocess.STDOUT,
# # # # # #         start_new_session=True,
# # # # # #         close_fds=True,
# # # # # #     )
# # # # # #     return ManagedProcess(name=name, popen=p, log_handle=log_handle)
# # # # # #
# # # # # #
# # # # # # # ------------------------------
# # # # # # # Kiosk Shell
# # # # # # # ------------------------------
# # # # # # class KioskShell:
# # # # # #     def __init__(self, cfg_path: str):
# # # # # #         self.cfg_path = cfg_path
# # # # # #         self.cfg = self._load_cfg(cfg_path)
# # # # # #         self.log_path = self.cfg["logs"]["shell_log"]
# # # # # #
# # # # # #         self._singleton_fd = ensure_singleton()
# # # # # #         self._shutting_down = False
# # # # # #
# # # # # #         self.active_child: Optional[subprocess.Popen] = None
# # # # # #         self.in_external = False
# # # # # #
# # # # # #         # VM (QEMU) management
# # # # # #         self.vm_pidfile = self.cfg["vm"]["pidfile"]
# # # # # #         self.vm_start_cmd = self.cfg["vm"]["start_cmd"]
# # # # # #         self.vm_cwd = self.cfg["vm"]["cwd"]
# # # # # #         self.vm_autostart = bool(self.cfg["vm"]["enable_autostart"])
# # # # # #         self.vm_startup_grace_s = float(self.cfg["vm"]["startup_grace_s"])
# # # # # #
# # # # # #         # PINs
# # # # # #         self.pi_pin = str(self.cfg["security"]["pi_pin"])
# # # # # #
# # # # # #         def _handle_term(signum, frame):
# # # # # #             self._shutting_down = True
# # # # # #             log_line(self.log_path, f"Signal {signum} received; stopping active child and exiting")
# # # # # #             p = self.active_child
# # # # # #             if p and p.poll() is None:
# # # # # #                 kill_process_group(p, self.log_path, "active_child")
# # # # # #             try:
# # # # # #                 self._release_pygame_completely("signal_exit")
# # # # # #             except Exception:
# # # # # #                 pass
# # # # # #             try:
# # # # # #                 pygame.quit()
# # # # # #             except Exception:
# # # # # #                 pass
# # # # # #             raise SystemExit(0)
# # # # # #
# # # # # #         signal.signal(signal.SIGTERM, _handle_term)
# # # # # #         signal.signal(signal.SIGINT, _handle_term)
# # # # # #
# # # # # #         pygame.init()
# # # # # #         try:
# # # # # #             pygame.font.init()
# # # # # #         except Exception:
# # # # # #             pass
# # # # # #
# # # # # #         self._init_display_with_retry()
# # # # # #
# # # # # #     def _blackout_frame(self, delay_s: float = 0.02) -> None:
# # # # # #         """Paint a single black frame (best-effort)."""
# # # # # #         try:
# # # # # #             if pygame.display.get_init():
# # # # # #                 surf = pygame.display.get_surface()
# # # # # #                 if surf:
# # # # # #                     surf.fill((0, 0, 0))
# # # # # #                     pygame.display.flip()
# # # # # #                     pygame.event.pump()
# # # # # #                     if delay_s > 0:
# # # # # #                         time.sleep(delay_s)
# # # # # #         except Exception:
# # # # # #             pass
# # # # # #
# # # # # #     # --------------------------
# # # # # #     # X11 helpers / blanking
# # # # # #     # --------------------------
# # # # # #     def _xset(self, args: List[str]) -> bool:
# # # # # #         try:
# # # # # #             subprocess.run(
# # # # # #                 ["xset"] + args,
# # # # # #                 env=_with_x_env(os.environ.copy()),
# # # # # #                 stdout=subprocess.DEVNULL,
# # # # # #                 stderr=subprocess.DEVNULL,
# # # # # #                 timeout=1.0,
# # # # # #                 check=False,
# # # # # #             )
# # # # # #             return True
# # # # # #         except Exception:
# # # # # #             return False
# # # # # #
# # # # # #     def _wait_for_x_ready(self, retries: int = 60, sleep_s: float = 0.25) -> bool:
# # # # # #         env = _with_x_env(os.environ.copy())
# # # # # #         for _ in range(retries):
# # # # # #             try:
# # # # # #                 subprocess.run(
# # # # # #                     ["xset", "q"],
# # # # # #                     env=env,
# # # # # #                     stdout=subprocess.DEVNULL,
# # # # # #                     stderr=subprocess.DEVNULL,
# # # # # #                     timeout=1.0,
# # # # # #                     check=True,
# # # # # #                 )
# # # # # #                 return True
# # # # # #             except Exception:
# # # # # #                 time.sleep(sleep_s)
# # # # # #         return False
# # # # # #
# # # # # #     def _disable_screen_blanking(self) -> None:
# # # # # #         self._xset(["s", "off"])
# # # # # #         self._xset(["s", "noblank"])
# # # # # #         self._xset(["-dpms"])
# # # # # #
# # # # # #     # --------------------------
# # # # # #     # Display lifecycle
# # # # # #     # --------------------------
# # # # # #     def _init_display_with_retry(self, retries: int = 40, sleep_s: float = 0.25) -> None:
# # # # # #         last_err: Optional[Exception] = None
# # # # # #         for _ in range(retries):
# # # # # #             try:
# # # # # #                 if not self._wait_for_x_ready(retries=6, sleep_s=0.2):
# # # # # #                     raise RuntimeError("X not ready (xset q failed)")
# # # # # #
# # # # # #                 pygame.display.init()
# # # # # #                 try:
# # # # # #                     if not pygame.font.get_init():
# # # # # #                         pygame.font.init()
# # # # # #                 except Exception:
# # # # # #                     pass
# # # # # #
# # # # # #                 self.init_display()
# # # # # #                 return
# # # # # #             except Exception as e:
# # # # # #                 last_err = e
# # # # # #                 time.sleep(sleep_s)
# # # # # #
# # # # # #         log_line(self.log_path, f"FATAL: unable to init display after retries: {last_err}")
# # # # # #         raise last_err if last_err else RuntimeError("unable to init display")
# # # # # #
# # # # # #     def init_display(self) -> None:
# # # # # #         ui = self.cfg.get("ui", {})
# # # # # #         self.title = ui.get("title", "SPARCstation")
# # # # # #
# # # # # #         pygame.display.set_caption(self.title)
# # # # # #         self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
# # # # # #         self.W, self.H = self.screen.get_size()
# # # # # #
# # # # # #         # Paint black immediately
# # # # # #         self.screen.fill((0, 0, 0))
# # # # # #         pygame.display.flip()
# # # # # #         pygame.event.pump()
# # # # # #
# # # # # #         self.font = pygame.font.SysFont(None, int(ui.get("font_size", 54)))
# # # # # #         self.font_small = pygame.font.SysFont(None, int(ui.get("small_font_size", 28)))
# # # # # #
# # # # # #         self.fps = int(ui.get("fps", 60))
# # # # # #         self.clock = pygame.time.Clock()
# # # # # #
# # # # # #         self._set_input_mode(grab=True, show_cursor=True)
# # # # # #         self._blackout_frame(delay_s=0.02)
# # # # # #
# # # # # #     def _ensure_display_ready(self) -> None:
# # # # # #         """Recreate the display if something external destroyed it."""
# # # # # #         try:
# # # # # #             if not pygame.display.get_init() or pygame.display.get_surface() is None:
# # # # # #                 self._init_display_with_retry()
# # # # # #                 return
# # # # # #             # refresh surface refs
# # # # # #             self.screen = pygame.display.get_surface()
# # # # # #             if self.screen:
# # # # # #                 self.W, self.H = self.screen.get_size()
# # # # # #         except Exception:
# # # # # #             self._init_display_with_retry()
# # # # # #
# # # # # #     def _set_input_mode(self, grab: bool, show_cursor: bool) -> None:
# # # # # #         try:
# # # # # #             pygame.event.set_grab(bool(grab))
# # # # # #         except Exception:
# # # # # #             pass
# # # # # #         try:
# # # # # #             pygame.mouse.set_visible(bool(show_cursor))
# # # # # #         except Exception:
# # # # # #             pass
# # # # # #         try:
# # # # # #             pygame.event.pump()
# # # # # #         except Exception:
# # # # # #             pass
# # # # # #
# # # # # #     def _release_pygame_completely(self, reason: str) -> None:
# # # # # #         """Full teardown (only for final exit paths)."""
# # # # # #         try:
# # # # # #             self._set_input_mode(grab=False, show_cursor=True)
# # # # # #         except Exception:
# # # # # #             pass
# # # # # #         try:
# # # # # #             pygame.event.clear()
# # # # # #             pygame.event.pump()
# # # # # #         except Exception:
# # # # # #             pass
# # # # # #         self._blackout_frame(delay_s=0.02)
# # # # # #         try:
# # # # # #             if pygame.display.get_init():
# # # # # #                 pygame.display.quit()
# # # # # #         except Exception:
# # # # # #             pass
# # # # # #         log_line(self.log_path, f"Released pygame display ({reason})")
# # # # # #
# # # # # #     # Legacy exit-code handoff (disabled unless explicitly allowed)
# # # # # #     def _hard_exit(self, code: int, reason: str) -> None:
# # # # # #         self._shutting_down = True
# # # # # #         log_line(self.log_path, f"Exiting kiosk_shell rc={code} ({reason})")
# # # # # #         try:
# # # # # #             self._release_pygame_completely(f"exit:{reason}")
# # # # # #         except Exception:
# # # # # #             pass
# # # # # #         try:
# # # # # #             pygame.quit()
# # # # # #         except Exception:
# # # # # #             pass
# # # # # #         raise SystemExit(code)
# # # # # #
# # # # # #     def _allow_exit_codes(self) -> bool:
# # # # # #         return os.environ.get("SPARC_ALLOW_EXIT_CODES", "0") == "1"
# # # # # #
# # # # # #     def _suspend_display(self, reason: str) -> None:
# # # # # #         """
# # # # # #         Anti-flash: do NOT pygame.display.quit() here.
# # # # # #         Just paint black and release input so the child fullscreen window can take over.
# # # # # #         """
# # # # # #         try:
# # # # # #             self._ensure_display_ready()
# # # # # #         except Exception:
# # # # # #             pass
# # # # # #
# # # # # #         try:
# # # # # #             self._set_input_mode(grab=False, show_cursor=False)
# # # # # #         except Exception:
# # # # # #             pass
# # # # # #
# # # # # #         self._blackout_frame(delay_s=0.02)
# # # # # #         log_line(self.log_path, f"Suspend display (keep window) ({reason})")
# # # # # #
# # # # # #     def _reclaim_fullscreen(self, reason: str = "return") -> None:
# # # # # #         """
# # # # # #         Anti-flash: do NOT quit/init; just ensure surface exists and re-grab.
# # # # # #         """
# # # # # #         if self._shutting_down:
# # # # # #             log_line(self.log_path, f"Skip reclaim fullscreen during shutdown ({reason})")
# # # # # #             return
# # # # # #
# # # # # #         try:
# # # # # #             pygame.event.clear()
# # # # # #         except Exception:
# # # # # #             pass
# # # # # #
# # # # # #         try:
# # # # # #             self._ensure_display_ready()
# # # # # #             self._set_input_mode(grab=True, show_cursor=True)
# # # # # #             self._blackout_frame(delay_s=0.01)
# # # # # #             log_line(self.log_path, f"Reclaimed fullscreen (no reinit) ({reason})")
# # # # # #         except Exception as e:
# # # # # #             log_line(self.log_path, f"ERROR reclaiming fullscreen ({reason}): {e}")
# # # # # #             self._init_display_with_retry()
# # # # # #
# # # # # #     # --------------------------
# # # # # #     # Config
# # # # # #     # --------------------------
# # # # # #     def _load_cfg(self, path: str) -> Dict[str, Any]:
# # # # # #         with open(path, "r") as f:
# # # # # #             cfg = yaml.safe_load(f) or {}
# # # # # #
# # # # # #         cfg.setdefault("feature_flags", {})
# # # # # #         cfg.setdefault("idle", {})
# # # # # #         cfg.setdefault("ui", {})
# # # # # #         cfg.setdefault("paths", {})
# # # # # #         cfg.setdefault("logs", {})
# # # # # #         cfg.setdefault("vm", {})
# # # # # #         cfg.setdefault("security", {})
# # # # # #
# # # # # #         cfg["idle"].setdefault("menu_seconds", 120)
# # # # # #         cfg["idle"].setdefault("external_seconds", 300)
# # # # # #
# # # # # #         cfg["logs"].setdefault("shell_log", "/home/pi/sparc_lock/logs/kiosk_shell.log")
# # # # # #         cfg["logs"].setdefault("lock_child_log", "/home/pi/sparc_lock/logs/lock_child.log")
# # # # # #         cfg["logs"].setdefault("mpv_log", "/home/pi/sparc_lock/logs/mpv.log")
# # # # # #         cfg["logs"].setdefault("solaris_log", "/home/pi/sparc_lock/logs/solaris_vnc.log")
# # # # # #         cfg["logs"].setdefault("games_log_dir", "/home/pi/sparc_lock/logs/games")
# # # # # #
# # # # # #         cfg["paths"].setdefault("lock_py", "/home/pi/sparc_lock/puzzle_lock.py")
# # # # # #         cfg["paths"].setdefault("launch_solaris_sh", "/home/pi/sparc_lock/launch_solaris.sh")
# # # # # #         cfg["paths"].setdefault("start_pi_mode_sh", "/home/pi/sparc_lock/start_pi_mode.sh")
# # # # # #         cfg["paths"].setdefault("mpv_input_conf", "/home/pi/sparc_lock/mpv.input.conf")
# # # # # #         cfg["paths"].setdefault("media_images", "/home/pi/sparc_media/images")
# # # # # #         cfg["paths"].setdefault("media_music", "/home/pi/sparc_media/music")
# # # # # #         cfg["paths"].setdefault("media_videos", "/home/pi/sparc_media/videos")
# # # # # #         cfg["paths"].setdefault("games_root", "/home/pi/sparc_games/installed")
# # # # # #
# # # # # #         # VM defaults
# # # # # #         cfg["vm"].setdefault("enable_autostart", True)
# # # # # #         cfg["vm"].setdefault("pidfile", "/home/pi/sparc_vm/qemu-sparc.pid")
# # # # # #         cfg["vm"].setdefault("start_cmd", ["/home/pi/sparc_vm/run_sol8.sh"])
# # # # # #         cfg["vm"].setdefault("cwd", "/home/pi/sparc_vm")
# # # # # #         cfg["vm"].setdefault("startup_grace_s", 1.0)
# # # # # #
# # # # # #         # Feature flags (menu composition)
# # # # # #         cfg["feature_flags"].setdefault("enable_pi", True)
# # # # # #         cfg["feature_flags"].setdefault("enable_solaris", True)
# # # # # #         cfg["feature_flags"].setdefault("enable_games", True)
# # # # # #         cfg["feature_flags"].setdefault("enable_media", True)
# # # # # #         cfg["feature_flags"].setdefault("enable_power", True)
# # # # # #
# # # # # #         # IMPORTANT: default to INLINE behavior to avoid LightDM greeter/login loops
# # # # # #         cfg["feature_flags"].setdefault("solaris_via_exit_code", False)
# # # # # #         cfg["feature_flags"].setdefault("pi_via_exit_code", False)
# # # # # #
# # # # # #         # Security
# # # # # #         cfg["security"].setdefault("pi_pin", "1193")
# # # # # #
# # # # # #         return cfg
# # # # # #
# # # # # #     # --------------------------
# # # # # #     # VM management (QEMU)
# # # # # #     # --------------------------
# # # # # #     def _vm_is_running(self) -> bool:
# # # # # #         try:
# # # # # #             with open(self.vm_pidfile, "r") as f:
# # # # # #                 pid_str = f.read().strip()
# # # # # #             if not pid_str:
# # # # # #                 return False
# # # # # #             pid = int(pid_str)
# # # # # #             os.kill(pid, 0)
# # # # # #             return True
# # # # # #         except FileNotFoundError:
# # # # # #             return False
# # # # # #         except ProcessLookupError:
# # # # # #             try:
# # # # # #                 os.remove(self.vm_pidfile)
# # # # # #             except Exception:
# # # # # #                 pass
# # # # # #             return False
# # # # # #         except Exception:
# # # # # #             return False
# # # # # #
# # # # # #     def _ensure_vm_running(self) -> None:
# # # # # #         if not self.vm_autostart:
# # # # # #             return
# # # # # #         if self._vm_is_running():
# # # # # #             return
# # # # # #         try:
# # # # # #             log_line(self.log_path, f"Starting VM: {self.vm_start_cmd}")
# # # # # #             subprocess.Popen(
# # # # # #                 self.vm_start_cmd,
# # # # # #                 cwd=self.vm_cwd,
# # # # # #                 env=_with_x_env(),
# # # # # #                 stdout=subprocess.DEVNULL,
# # # # # #                 stderr=subprocess.DEVNULL,
# # # # # #                 start_new_session=True,
# # # # # #             )
# # # # # #             time.sleep(self.vm_startup_grace_s)
# # # # # #         except Exception as e:
# # # # # #             log_line(self.log_path, f"WARNING: failed to start VM: {e}")
# # # # # #
# # # # # #     # --------------------------
# # # # # #     # PIN UI
# # # # # #     # --------------------------
# # # # # #     def _pin_prompt(self, title: str, msg: str, expected_pin: str) -> bool:
# # # # # #         pin_input = ""
# # # # # #         err_msg = ""
# # # # # #         err_t0 = 0.0
# # # # # #
# # # # # #         keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "C", "0", "OK"]
# # # # # #         cols, rows = 3, 4
# # # # # #         cancel_rect = pygame.Rect(16, 16, 170, 52)
# # # # # #
# # # # # #         def draw():
# # # # # #             self.screen.fill((0, 0, 0))
# # # # # #             overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
# # # # # #             overlay.fill((0, 0, 0, 210))
# # # # # #             self.screen.blit(overlay, (0, 0))
# # # # # #
# # # # # #             pygame.draw.rect(self.screen, (40, 40, 40), cancel_rect, border_radius=14)
# # # # # #             pygame.draw.rect(self.screen, (200, 200, 200), cancel_rect, 2, border_radius=14)
# # # # # #             ct = self.font_small.render("CANCEL", True, (255, 255, 255))
# # # # # #             self.screen.blit(ct, (cancel_rect.centerx - ct.get_width() // 2, cancel_rect.centery - ct.get_height() // 2))
# # # # # #
# # # # # #             t = self.font.render(title, True, (255, 255, 255))
# # # # # #             self.screen.blit(t, (self.W // 2 - t.get_width() // 2, 90))
# # # # # #
# # # # # #             m = self.font_small.render(msg, True, (220, 220, 220))
# # # # # #             self.screen.blit(m, (self.W // 2 - m.get_width() // 2, 150))
# # # # # #
# # # # # #             masked = "*" * len(pin_input)
# # # # # #             e = self.font.render(masked, True, (255, 255, 0))
# # # # # #             self.screen.blit(e, (self.W // 2 - e.get_width() // 2, 190))
# # # # # #
# # # # # #             pad_w = min(520, int(self.W * 0.42))
# # # # # #             pad_h = min(520, int(self.H * 0.62))
# # # # # #             pad_x = (self.W - pad_w) // 2
# # # # # #             pad_y = (self.H - pad_h) // 2 + 40
# # # # # #             cell_w = pad_w // cols
# # # # # #             cell_h = pad_h // rows
# # # # # #
# # # # # #             pygame.draw.rect(self.screen, (35, 35, 35), pygame.Rect(pad_x, pad_y, pad_w, pad_h), border_radius=16)
# # # # # #             rects = []
# # # # # #             for r in range(rows):
# # # # # #                 for c in range(cols):
# # # # # #                     x = pad_x + c * cell_w + 10
# # # # # #                     y = pad_y + r * cell_h + 10
# # # # # #                     rects.append(pygame.Rect(x, y, cell_w - 20, cell_h - 20))
# # # # # #
# # # # # #             mx, my = pygame.mouse.get_pos()
# # # # # #             for i, rr in enumerate(rects):
# # # # # #                 hot = rr.collidepoint(mx, my)
# # # # # #                 bg = (70, 70, 70) if hot else (55, 55, 55)
# # # # # #                 pygame.draw.rect(self.screen, bg, rr, border_radius=12)
# # # # # #                 pygame.draw.rect(self.screen, (170, 170, 170), rr, 2, border_radius=12)
# # # # # #                 kt = self.font.render(keys[i], True, (255, 255, 255))
# # # # # #                 self.screen.blit(kt, (rr.centerx - kt.get_width() // 2, rr.centery - kt.get_height() // 2))
# # # # # #
# # # # # #             if err_msg and (time.time() - err_t0) < 2.0:
# # # # # #                 em = self.font_small.render(err_msg, True, (255, 90, 90))
# # # # # #                 self.screen.blit(em, (self.W // 2 - em.get_width() // 2, pad_y + pad_h + 18))
# # # # # #
# # # # # #             tip = self.font_small.render("Enter=submit, Backspace=delete, OK=submit. Esc/CANCEL=back.", True, (200, 200, 200))
# # # # # #             self.screen.blit(tip, (self.W // 2 - tip.get_width() // 2, pad_y + pad_h + 52))
# # # # # #
# # # # # #             pygame.display.flip()
# # # # # #
# # # # # #         def hit_key(x: int, y: int) -> Optional[str]:
# # # # # #             pad_w = min(520, int(self.W * 0.42))
# # # # # #             pad_h = min(520, int(self.H * 0.62))
# # # # # #             pad_x = (self.W - pad_w) // 2
# # # # # #             pad_y = (self.H - pad_h) // 2 + 40
# # # # # #             cell_w = pad_w // cols
# # # # # #             cell_h = pad_h // rows
# # # # # #
# # # # # #             idx = 0
# # # # # #             for r in range(rows):
# # # # # #                 for c in range(cols):
# # # # # #                     rx = pad_x + c * cell_w + 10
# # # # # #                     ry = pad_y + r * cell_h + 10
# # # # # #                     rect = pygame.Rect(rx, ry, cell_w - 20, cell_h - 20)
# # # # # #                     if rect.collidepoint(x, y):
# # # # # #                         return keys[idx]
# # # # # #                     idx += 1
# # # # # #             return None
# # # # # #
# # # # # #         self._set_input_mode(grab=True, show_cursor=True)
# # # # # #         pygame.event.clear()
# # # # # #         pygame.event.pump()
# # # # # #
# # # # # #         while True:
# # # # # #             for ev in pygame.event.get():
# # # # # #                 if ev.type == pygame.QUIT:
# # # # # #                     raise SystemExit(0)
# # # # # #
# # # # # #                 if ev.type == pygame.KEYDOWN:
# # # # # #                     if ev.key in (pygame.K_ESCAPE,):
# # # # # #                         return False
# # # # # #                     if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
# # # # # #                         if pin_input == expected_pin:
# # # # # #                             return True
# # # # # #                         err_msg = "Incorrect PIN"
# # # # # #                         err_t0 = time.time()
# # # # # #                         pin_input = ""
# # # # # #                     elif ev.key == pygame.K_BACKSPACE:
# # # # # #                         pin_input = pin_input[:-1]
# # # # # #                     else:
# # # # # #                         ch = ev.unicode
# # # # # #                         if ch.isdigit() and len(pin_input) < 12:
# # # # # #                             pin_input += ch
# # # # # #
# # # # # #                 if ev.type == pygame.MOUSEBUTTONDOWN:
# # # # # #                     x, y = ev.pos
# # # # # #                     if cancel_rect.collidepoint(x, y):
# # # # # #                         return False
# # # # # #                     k = hit_key(x, y)
# # # # # #                     if k:
# # # # # #                         if k == "C":
# # # # # #                             pin_input = ""
# # # # # #                         elif k == "OK":
# # # # # #                             if pin_input == expected_pin:
# # # # # #                                 return True
# # # # # #                             err_msg = "Incorrect PIN"
# # # # # #                             err_t0 = time.time()
# # # # # #                             pin_input = ""
# # # # # #                         else:
# # # # # #                             if len(pin_input) < 12:
# # # # # #                                 pin_input += k
# # # # # #
# # # # # #                 if ev.type == pygame.FINGERDOWN:
# # # # # #                     x = int(ev.x * self.W)
# # # # # #                     y = int(ev.y * self.H)
# # # # # #                     if cancel_rect.collidepoint(x, y):
# # # # # #                         return False
# # # # # #                     k = hit_key(x, y)
# # # # # #                     if k:
# # # # # #                         if k == "C":
# # # # # #                             pin_input = ""
# # # # # #                         elif k == "OK":
# # # # # #                             if pin_input == expected_pin:
# # # # # #                                 return True
# # # # # #                             err_msg = "Incorrect PIN"
# # # # # #                             err_t0 = time.time()
# # # # # #                             pin_input = ""
# # # # # #                         else:
# # # # # #                             if len(pin_input) < 12:
# # # # # #                                 pin_input += k
# # # # # #
# # # # # #             draw()
# # # # # #             self.clock.tick(self.fps)
# # # # # #
# # # # # #     # --------------------------
# # # # # #     # Main loop
# # # # # #     # --------------------------
# # # # # #     def run(self) -> None:
# # # # # #         log_line(self.log_path, "kiosk_shell starting")
# # # # # #         self._ensure_vm_running()
# # # # # #
# # # # # #         while True:
# # # # # #             rc = self.run_lock()
# # # # # #             if rc != 0:
# # # # # #                 log_line(self.log_path, f"Lock returned rc={rc} -> restarting lock")
# # # # # #                 continue
# # # # # #
# # # # # #             choice = self.menu_loop()
# # # # # #             log_line(self.log_path, f"Menu returned choice={choice}")
# # # # # #
# # # # # #             if choice == "relock":
# # # # # #                 continue
# # # # # #
# # # # # #             if choice == "pi":
# # # # # #                 ok = self._pin_prompt("PI DESKTOP", "Enter PIN to open Pi admin desktop", self.pi_pin)
# # # # # #                 if not ok:
# # # # # #                     log_line(self.log_path, "Pi PIN canceled/failed -> back to menu")
# # # # # #                     continue
# # # # # #
# # # # # #                 log_line(self.log_path, "Pi PIN accepted -> entering Pi mode (inline)")
# # # # # #
# # # # # #                 if bool(self.cfg["feature_flags"].get("pi_via_exit_code", False)) and self._allow_exit_codes():
# # # # # #                     self._suspend_display("exit_to_pi")
# # # # # #                     self._hard_exit(42, "pi_mode")
# # # # # #                 else:
# # # # # #                     self._run_pi_mode_inline()
# # # # # #                 continue
# # # # # #
# # # # # #             if choice == "solaris":
# # # # # #                 log_line(self.log_path, "Solaris selected")
# # # # # #
# # # # # #                 if bool(self.cfg["feature_flags"].get("solaris_via_exit_code", False)) and self._allow_exit_codes():
# # # # # #                     self._suspend_display("exit_to_solaris")
# # # # # #                     self._hard_exit(43, "solaris")
# # # # # #                 else:
# # # # # #                     self.run_solaris()
# # # # # #                 continue
# # # # # #
# # # # # #             if choice == "games":
# # # # # #                 self.run_games()
# # # # # #                 continue
# # # # # #
# # # # # #             if choice == "media":
# # # # # #                 self.run_media()
# # # # # #                 continue
# # # # # #
# # # # # #             if choice == "shutdown":
# # # # # #                 self.run_shutdown()
# # # # # #                 continue
# # # # # #
# # # # # #     # --------------------------
# # # # # #     # Lock runner
# # # # # #     # --------------------------
# # # # # #     def run_lock(self) -> int:
# # # # # #         lock_py = self.cfg["paths"]["lock_py"]
# # # # # #         env = _with_x_env(os.environ.copy())
# # # # # #
# # # # # #         log_line(self.log_path, "Starting lock (puzzle_lock.py)")
# # # # # #         mp: Optional[ManagedProcess] = None
# # # # # #
# # # # # #         self._suspend_display("before_lock")
# # # # # #
# # # # # #         try:
# # # # # #             mp = spawn_process(
# # # # # #                 name="lock",
# # # # # #                 argv=["python3", "-u", lock_py],
# # # # # #                 log_path=self.cfg["logs"]["lock_child_log"],
# # # # # #                 env=env,
# # # # # #                 cwd="/home/pi/sparc_lock",
# # # # # #             )
# # # # # #             self.active_child = mp.popen
# # # # # #             rc = mp.popen.wait()
# # # # # #             log_line(self.log_path, f"Lock exited rc={rc}")
# # # # # #             return rc
# # # # # #         finally:
# # # # # #             self.active_child = None
# # # # # #             if mp and mp.log_handle:
# # # # # #                 try:
# # # # # #                     mp.log_handle.close()
# # # # # #                 except Exception:
# # # # # #                     pass
# # # # # #             self._reclaim_fullscreen("after_lock")
# # # # # #
# # # # # #     # --------------------------
# # # # # #     # Menu UI
# # # # # #     # --------------------------
# # # # # #     def menu_loop(self) -> str:
# # # # # #         flags = self.cfg.get("feature_flags", {})
# # # # # #         enable_pi = bool(flags.get("enable_pi", True))
# # # # # #         enable_solaris = bool(flags.get("enable_solaris", True))
# # # # # #         enable_games = bool(flags.get("enable_games", True))
# # # # # #         enable_media = bool(flags.get("enable_media", True))
# # # # # #         enable_power = bool(flags.get("enable_power", True))
# # # # # #
# # # # # #         items: List[Tuple[str, str]] = []
# # # # # #         if enable_pi:
# # # # # #             items.append(("Pi", "pi"))
# # # # # #         if enable_solaris:
# # # # # #             items.append(("Solaris", "solaris"))
# # # # # #         if enable_games:
# # # # # #             items.append(("Games", "games"))
# # # # # #         if enable_media:
# # # # # #             items.append(("Media Library", "media"))
# # # # # #         if enable_power:
# # # # # #             items.append(("Shutdown", "shutdown"))
# # # # # #         items.append(("Re-lock", "relock"))
# # # # # #
# # # # # #         idle_limit = int(self.cfg["idle"]["menu_seconds"])
# # # # # #         last_input = time.time()
# # # # # #         sel = 0
# # # # # #
# # # # # #         self._set_input_mode(grab=True, show_cursor=True)
# # # # # #         self._disable_screen_blanking()
# # # # # #         try:
# # # # # #             pygame.event.clear()
# # # # # #             pygame.event.pump()
# # # # # #         except Exception:
# # # # # #             pass
# # # # # #
# # # # # #         while True:
# # # # # #             if (time.time() - last_input) >= idle_limit:
# # # # # #                 log_line(self.log_path, f"Menu idle >= {idle_limit}s -> relock")
# # # # # #                 return "relock"
# # # # # #
# # # # # #             for ev in pygame.event.get():
# # # # # #                 if ev.type == pygame.QUIT:
# # # # # #                     raise SystemExit(0)
# # # # # #
# # # # # #                 if ev.type in (
# # # # # #                     pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION,
# # # # # #                     pygame.KEYDOWN,
# # # # # #                     pygame.FINGERDOWN, pygame.FINGERMOTION
# # # # # #                 ):
# # # # # #                     last_input = time.time()
# # # # # #
# # # # # #                 if ev.type == pygame.KEYDOWN:
# # # # # #                     if ev.key in (pygame.K_ESCAPE, pygame.K_q):
# # # # # #                         return "relock"
# # # # # #                     if ev.key == pygame.K_UP:
# # # # # #                         sel = max(0, sel - 1)
# # # # # #                     elif ev.key == pygame.K_DOWN:
# # # # # #                         sel = min(len(items) - 1, sel + 1)
# # # # # #                     elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
# # # # # #                         action = items[sel][1]
# # # # # #                         log_line(self.log_path, f"Menu key select -> {action}")
# # # # # #                         return action
# # # # # #
# # # # # #                 if ev.type == pygame.MOUSEBUTTONDOWN:
# # # # # #                     hit = self._hit_test_menu(items, ev.pos[0], ev.pos[1])
# # # # # #                     if hit:
# # # # # #                         log_line(self.log_path, f"Menu click -> {hit}")
# # # # # #                         return hit
# # # # # #
# # # # # #                 if ev.type == pygame.FINGERDOWN:
# # # # # #                     x = int(ev.x * self.W)
# # # # # #                     y = int(ev.y * self.H)
# # # # # #                     hit = self._hit_test_menu(items, x, y)
# # # # # #                     if hit:
# # # # # #                         log_line(self.log_path, f"Menu touch -> {hit}")
# # # # # #                         return hit
# # # # # #
# # # # # #             self._draw_menu(items, sel=sel)
# # # # # #             pygame.display.flip()
# # # # # #             self.clock.tick(self.fps)
# # # # # #
# # # # # #     def _draw_menu(self, items: List[Tuple[str, str]], sel: int = 0) -> None:
# # # # # #         self.screen.fill((0, 0, 0))
# # # # # #
# # # # # #         title = self.font.render(self.title, True, (255, 255, 255))
# # # # # #         self.screen.blit(title, (self.W // 2 - title.get_width() // 2, 40))
# # # # # #
# # # # # #         btn_w = int(self.W * 0.70)
# # # # # #         btn_h = 90
# # # # # #         gap = 22
# # # # # #         start_y = 160
# # # # # #
# # # # # #         for i, (label, _action) in enumerate(items):
# # # # # #             x = self.W // 2 - btn_w // 2
# # # # # #             y = start_y + i * (btn_h + gap)
# # # # # #             rect = pygame.Rect(x, y, btn_w, btn_h)
# # # # # #
# # # # # #             is_sel = (i == sel)
# # # # # #             bg = (55, 55, 55) if is_sel else (30, 30, 30)
# # # # # #             border = (200, 200, 200) if is_sel else (120, 120, 120)
# # # # # #
# # # # # #             pygame.draw.rect(self.screen, bg, rect, border_radius=18)
# # # # # #             pygame.draw.rect(self.screen, border, rect, width=2, border_radius=18)
# # # # # #
# # # # # #             text = self.font.render(label, True, (240, 240, 240))
# # # # # #             self.screen.blit(text, (
# # # # # #                 rect.centerx - text.get_width() // 2,
# # # # # #                 rect.centery - text.get_height() // 2
# # # # # #             ))
# # # # # #
# # # # # #         hint = self.font_small.render("Click/tap or use Up/Down + Enter. Idle returns to lock.", True, (180, 180, 180))
# # # # # #         self.screen.blit(hint, (self.W // 2 - hint.get_width() // 2, self.H - 60))
# # # # # #
# # # # # #     def _hit_test_menu(self, items: List[Tuple[str, str]], x: int, y: int) -> Optional[str]:
# # # # # #         btn_w = int(self.W * 0.70)
# # # # # #         btn_h = 90
# # # # # #         gap = 22
# # # # # #         start_y = 160
# # # # # #         for i, (_label, action) in enumerate(items):
# # # # # #             rx = self.W // 2 - btn_w // 2
# # # # # #             ry = start_y + i * (btn_h + gap)
# # # # # #             rect = pygame.Rect(rx, ry, btn_w, btn_h)
# # # # # #             if rect.collidepoint(x, y):
# # # # # #                 return action
# # # # # #         return None
# # # # # #
# # # # # #     # --------------------------
# # # # # #     # Pi mode (INLINE)
# # # # # #     # --------------------------
# # # # # #     def _run_pi_mode_inline(self) -> None:
# # # # # #         sh = self.cfg["paths"]["start_pi_mode_sh"]
# # # # # #         logp = "/home/pi/sparc_lock/logs/pi_mode.log"
# # # # # #         self._run_external(
# # # # # #             name="pi_mode",
# # # # # #             argv=["/bin/bash", sh],
# # # # # #             log_path=logp,
# # # # # #             env=_with_x_env(os.environ.copy()),
# # # # # #             idle_seconds=int(self.cfg["idle"]["external_seconds"]),
# # # # # #             cwd="/home/pi",
# # # # # #         )
# # # # # #
# # # # # #     # --------------------------
# # # # # #     # Solaris (INLINE)
# # # # # #     # --------------------------
# # # # # #     def run_solaris(self) -> int:
# # # # # #         log_line(self.log_path, "run_solaris() entered")
# # # # # #         if self.in_external:
# # # # # #             log_line(self.log_path, "Ignoring Solaris launch: external already active")
# # # # # #             return 0
# # # # # #
# # # # # #         self._ensure_vm_running()
# # # # # #         self.in_external = True
# # # # # #         try:
# # # # # #             sh = self.cfg["paths"]["launch_solaris_sh"]
# # # # # #             idle_s = int(self.cfg["idle"]["external_seconds"])
# # # # # #             env = _with_x_env(os.environ.copy())
# # # # # #             env["SPARC_IDLE_MANAGED"] = "1"
# # # # # #             return self._run_external(
# # # # # #                 name="solaris",
# # # # # #                 argv=[sh],
# # # # # #                 log_path=self.cfg["logs"]["solaris_log"],
# # # # # #                 env=env,
# # # # # #                 idle_seconds=idle_s,
# # # # # #                 cwd="/home/pi",
# # # # # #             )
# # # # # #         finally:
# # # # # #             self.in_external = False
# # # # # #
# # # # # #     # --------------------------
# # # # # #     # Media
# # # # # #     # --------------------------
# # # # # #     def run_media(self) -> None:
# # # # # #         roots = [
# # # # # #             ("Images", self.cfg["paths"]["media_images"]),
# # # # # #             ("Music", self.cfg["paths"]["media_music"]),
# # # # # #             ("Videos", self.cfg["paths"]["media_videos"]),
# # # # # #         ]
# # # # # #         choice = self._simple_list_screen("Media Library", [r[0] for r in roots])
# # # # # #         if choice is None:
# # # # # #             return
# # # # # #         _label, path = roots[choice]
# # # # # #         self._browse_and_play(path)
# # # # # #
# # # # # #     def _browse_and_play(self, folder: str) -> None:
# # # # # #         try:
# # # # # #             files = sorted([f for f in os.listdir(folder) if not f.startswith(".")])
# # # # # #         except Exception:
# # # # # #             self._toast(f"Cannot open: {folder}")
# # # # # #             return
# # # # # #
# # # # # #         idx = self._simple_list_screen(os.path.basename(folder), files)
# # # # # #         if idx is None:
# # # # # #             return
# # # # # #
# # # # # #         target = os.path.join(folder, files[idx])
# # # # # #         self._play_with_mpv(target)
# # # # # #
# # # # # #     def _play_with_mpv(self, path: str) -> None:
# # # # # #         idle_s = int(self.cfg["idle"]["external_seconds"])
# # # # # #         mpv_conf = self.cfg["paths"]["mpv_input_conf"]
# # # # # #         argv = ["mpv", "--fs", "--input-conf=" + mpv_conf, path]
# # # # # #         self._run_external(
# # # # # #             name="mpv",
# # # # # #             argv=argv,
# # # # # #             log_path=self.cfg["logs"]["mpv_log"],
# # # # # #             env=_with_x_env(os.environ.copy()),
# # # # # #             idle_seconds=idle_s,
# # # # # #         )
# # # # # #
# # # # # #     # --------------------------
# # # # # #     # Games
# # # # # #     # --------------------------
# # # # # #     def run_games(self) -> None:
# # # # # #         games_root = self.cfg["paths"]["games_root"]
# # # # # #         games = self._discover_games(games_root)
# # # # # #         if not games:
# # # # # #             self._toast("No games installed.")
# # # # # #             return
# # # # # #
# # # # # #         labels = [g["title"] for g in games]
# # # # # #         idx = self._simple_list_screen("Games", labels)
# # # # # #         if idx is None:
# # # # # #             return
# # # # # #
# # # # # #         g = games[idx]
# # # # # #         argv = g["exec"]
# # # # # #         cwd = g.get("cwd") or g["dir"]
# # # # # #         name = f"game_{g['id']}"
# # # # # #
# # # # # #         log_dir = self.cfg["logs"]["games_log_dir"]
# # # # # #         os.makedirs(log_dir, exist_ok=True)
# # # # # #         log_path = os.path.join(log_dir, f"{g['id']}.log")
# # # # # #
# # # # # #         idle_s = int(self.cfg["idle"]["external_seconds"])
# # # # # #         self._run_external(name=name, argv=argv, log_path=log_path, env=_with_x_env(os.environ.copy()), idle_seconds=idle_s, cwd=cwd)
# # # # # #
# # # # # #     def _discover_games(self, root: str) -> List[Dict[str, Any]]:
# # # # # #         out: List[Dict[str, Any]] = []
# # # # # #         try:
# # # # # #             dirs = sorted([d for d in os.listdir(root) if not d.startswith(".")])
# # # # # #         except Exception:
# # # # # #             return out
# # # # # #
# # # # # #         for d in dirs:
# # # # # #             gdir = os.path.join(root, d)
# # # # # #             mpath = os.path.join(gdir, "manifest.json")
# # # # # #             if not os.path.isdir(gdir) or not os.path.isfile(mpath):
# # # # # #                 continue
# # # # # #             try:
# # # # # #                 with open(mpath, "r") as f:
# # # # # #                     m = json.load(f)
# # # # # #                 gid = str(m.get("id", d)).strip()
# # # # # #                 title = str(m.get("title", gid)).strip()
# # # # # #                 execv = m.get("exec")
# # # # # #                 if not isinstance(execv, list) or not execv:
# # # # # #                     continue
# # # # # #                 out.append({"id": gid, "title": title, "exec": execv, "cwd": m.get("cwd"), "dir": gdir})
# # # # # #             except Exception:
# # # # # #                 continue
# # # # # #         return out
# # # # # #
# # # # # #     # --------------------------
# # # # # #     # Shutdown
# # # # # #     # --------------------------
# # # # # #     def run_shutdown(self) -> None:
# # # # # #         ok = self._confirm("Shutdown", "Power off the system?")
# # # # # #         if not ok:
# # # # # #             return
# # # # # #         self._run_external(
# # # # # #             name="shutdown",
# # # # # #             argv=["sudo", "-n", "/usr/sbin/shutdown", "-h", "now"],
# # # # # #             log_path=os.path.join(os.path.dirname(self.log_path), "shutdown.log"),
# # # # # #             env=_with_x_env(os.environ.copy()),
# # # # # #             idle_seconds=999999,
# # # # # #         )
# # # # # #
# # # # # #     # --------------------------
# # # # # #     # External runner
# # # # # #     # --------------------------
# # # # # #     def _run_external(
# # # # # #         self,
# # # # # #         name: str,
# # # # # #         argv: List[str],
# # # # # #         log_path: str,
# # # # # #         env: Optional[Dict[str, str]],
# # # # # #         idle_seconds: int,
# # # # # #         cwd: Optional[str] = None,
# # # # # #     ) -> int:
# # # # # #         mp: Optional[ManagedProcess] = None
# # # # # #         try:
# # # # # #             self._disable_screen_blanking()
# # # # # #             self._suspend_display(f"before_external:{name}")
# # # # # #             time.sleep(0.05)
# # # # # #
# # # # # #             log_line(self.log_path, f"Starting external: {name} argv={argv}")
# # # # # #             mp = spawn_process(name=name, argv=argv, log_path=log_path, env=env, cwd=cwd)
# # # # # #             self.active_child = mp.popen
# # # # # #
# # # # # #             threshold_ms = int(idle_seconds * 1000)
# # # # # #             hard_start = time.monotonic()
# # # # # #             xprintidle_missing_since: Optional[float] = None
# # # # # #
# # # # # #             baseline_idle_ms = read_xprintidle_ms()
# # # # # #             if baseline_idle_ms is None:
# # # # # #                 baseline_idle_ms = 0
# # # # # #
# # # # # #             while True:
# # # # # #                 rc = mp.popen.poll()
# # # # # #                 if rc is not None:
# # # # # #                     log_line(self.log_path, f"External exited: {name} rc={rc}")
# # # # # #                     return rc
# # # # # #
# # # # # #                 idle_now = read_xprintidle_ms()
# # # # # #                 GRACE_S = 3.0
# # # # # #
# # # # # #                 if idle_now is None:
# # # # # #                     if xprintidle_missing_since is None:
# # # # # #                         xprintidle_missing_since = time.monotonic()
# # # # # #                         log_line(self.log_path, f"WARNING: xprintidle unavailable in {name}; using hard timeout={idle_seconds}s")
# # # # # #                     if (time.monotonic() - xprintidle_missing_since) < GRACE_S:
# # # # # #                         time.sleep(0.25)
# # # # # #                         continue
# # # # # #                     elapsed = time.monotonic() - hard_start
# # # # # #                     if elapsed >= float(idle_seconds):
# # # # # #                         log_line(self.log_path, f"Hard timeout {elapsed:.1f}s >= {idle_seconds}s in {name} -> kill and return")
# # # # # #                         kill_process_group(mp.popen, self.log_path, name)
# # # # # #                         return 0
# # # # # #                 else:
# # # # # #                     delta = max(0, int(idle_now) - int(baseline_idle_ms))
# # # # # #                     if delta >= threshold_ms:
# # # # # #                         log_line(self.log_path, f"Idle since launch {delta}ms >= {threshold_ms}ms in {name} -> kill and return")
# # # # # #                         kill_process_group(mp.popen, self.log_path, name)
# # # # # #                         return 0
# # # # # #
# # # # # #                 time.sleep(0.25)
# # # # # #
# # # # # #         finally:
# # # # # #             self.active_child = None
# # # # # #             if mp and mp.log_handle:
# # # # # #                 try:
# # # # # #                     mp.log_handle.close()
# # # # # #                 except Exception:
# # # # # #                     pass
# # # # # #             self._reclaim_fullscreen(f"after_external:{name}")
# # # # # #
# # # # # #     # --------------------------
# # # # # #     # Simple list screens / confirm / toast
# # # # # #     # --------------------------
# # # # # #     def _simple_list_screen(self, title: str, items: List[str]) -> Optional[int]:
# # # # # #         if not items:
# # # # # #             return None
# # # # # #
# # # # # #         idx = 0
# # # # # #         last_input = time.time()
# # # # # #         idle_limit = max(10, int(self.cfg["idle"]["menu_seconds"]))
# # # # # #
# # # # # #         self._set_input_mode(grab=True, show_cursor=True)
# # # # # #         self._disable_screen_blanking()
# # # # # #
# # # # # #         while True:
# # # # # #             if (time.time() - last_input) >= idle_limit:
# # # # # #                 return None
# # # # # #
# # # # # #             visible = min(8, len(items))
# # # # # #             start = max(0, min(idx - visible // 2, len(items) - visible))
# # # # # #
# # # # # #             for ev in pygame.event.get():
# # # # # #                 if ev.type == pygame.QUIT:
# # # # # #                     raise SystemExit(0)
# # # # # #
# # # # # #                 if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN, pygame.FINGERDOWN):
# # # # # #                     last_input = time.time()
# # # # # #
# # # # # #                 if ev.type == pygame.KEYDOWN:
# # # # # #                     if ev.key in (pygame.K_ESCAPE, pygame.K_q):
# # # # # #                         return None
# # # # # #                     if ev.key == pygame.K_UP:
# # # # # #                         idx = max(0, idx - 1)
# # # # # #                     elif ev.key == pygame.K_DOWN:
# # # # # #                         idx = min(len(items) - 1, idx + 1)
# # # # # #                     elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
# # # # # #                         return idx
# # # # # #
# # # # # #                 if ev.type == pygame.MOUSEBUTTONDOWN:
# # # # # #                     hit = self._hit_test_list(ev.pos[0], ev.pos[1], start, visible)
# # # # # #                     if hit is not None:
# # # # # #                         return hit
# # # # # #
# # # # # #                 if ev.type == pygame.FINGERDOWN:
# # # # # #                     x = int(ev.x * self.W)
# # # # # #                     y = int(ev.y * self.H)
# # # # # #                     hit = self._hit_test_list(x, y, start, visible)
# # # # # #                     if hit is not None:
# # # # # #                         return hit
# # # # # #
# # # # # #             self._draw_list(title, items, idx)
# # # # # #             pygame.display.flip()
# # # # # #             self.clock.tick(self.fps)
# # # # # #
# # # # # #     def _draw_list(self, title: str, items: List[str], sel: int) -> None:
# # # # # #         self.screen.fill((0, 0, 0))
# # # # # #         t = self.font.render(title, True, (255, 255, 255))
# # # # # #         self.screen.blit(t, (self.W // 2 - t.get_width() // 2, 40))
# # # # # #
# # # # # #         row_h = 70
# # # # # #         gap = 12
# # # # # #         start_y = 140
# # # # # #         visible = min(8, len(items))
# # # # # #         start = max(0, min(sel - visible // 2, len(items) - visible))
# # # # # #
# # # # # #         for vi, i in enumerate(range(start, min(len(items), start + visible))):
# # # # # #             y = start_y + vi * (row_h + gap)
# # # # # #             rect = pygame.Rect(int(self.W * 0.10), y, int(self.W * 0.80), row_h)
# # # # # #             is_sel = (i == sel)
# # # # # #             pygame.draw.rect(self.screen, (50, 50, 50) if is_sel else (25, 25, 25), rect, border_radius=14)
# # # # # #             pygame.draw.rect(self.screen, (140, 140, 140), rect, width=2, border_radius=14)
# # # # # #             text = self.font_small.render(items[i], True, (255, 255, 255))
# # # # # #             self.screen.blit(text, (rect.x + 18, rect.centery - text.get_height() // 2))
# # # # # #
# # # # # #         hint = self.font_small.render("Tap an item. ESC/Q to go back.", True, (180, 180, 180))
# # # # # #         self.screen.blit(hint, (self.W // 2 - hint.get_width() // 2, self.H - 60))
# # # # # #
# # # # # #     def _hit_test_list(self, x: int, y: int, start: int, visible: int) -> Optional[int]:
# # # # # #         row_h = 70
# # # # # #         gap = 12
# # # # # #         start_y = 140
# # # # # #         for vi in range(visible):
# # # # # #             ry = start_y + vi * (row_h + gap)
# # # # # #             rect = pygame.Rect(int(self.W * 0.10), ry, int(self.W * 0.80), row_h)
# # # # # #             if rect.collidepoint(x, y):
# # # # # #                 return start + vi
# # # # # #         return None
# # # # # #
# # # # # #     def _confirm(self, title: str, msg: str) -> bool:
# # # # # #         yes_rect = pygame.Rect(int(self.W * 0.15), int(self.H * 0.60), int(self.W * 0.30), 90)
# # # # # #         no_rect = pygame.Rect(int(self.W * 0.55), int(self.H * 0.60), int(self.W * 0.30), 90)
# # # # # #
# # # # # #         self._set_input_mode(grab=True, show_cursor=True)
# # # # # #         self._disable_screen_blanking()
# # # # # #
# # # # # #         while True:
# # # # # #             for ev in pygame.event.get():
# # # # # #                 if ev.type == pygame.QUIT:
# # # # # #                     raise SystemExit(0)
# # # # # #                 if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_q):
# # # # # #                     return False
# # # # # #                 if ev.type == pygame.MOUSEBUTTONDOWN:
# # # # # #                     x, y = ev.pos
# # # # # #                     if yes_rect.collidepoint(x, y):
# # # # # #                         return True
# # # # # #                     if no_rect.collidepoint(x, y):
# # # # # #                         return False
# # # # # #                 if ev.type == pygame.FINGERDOWN:
# # # # # #                     x = int(ev.x * self.W)
# # # # # #                     y = int(ev.y * self.H)
# # # # # #                     if yes_rect.collidepoint(x, y):
# # # # # #                         return True
# # # # # #                     if no_rect.collidepoint(x, y):
# # # # # #                         return False
# # # # # #
# # # # # #             self.screen.fill((0, 0, 0))
# # # # # #             t = self.font.render(title, True, (255, 255, 255))
# # # # # #             self.screen.blit(t, (self.W // 2 - t.get_width() // 2, 80))
# # # # # #
# # # # # #             m = self.font_small.render(msg, True, (220, 220, 220))
# # # # # #             self.screen.blit(m, (self.W // 2 - m.get_width() // 2, 200))
# # # # # #
# # # # # #             pygame.draw.rect(self.screen, (30, 30, 30), yes_rect, border_radius=18)
# # # # # #             pygame.draw.rect(self.screen, (120, 120, 120), yes_rect, width=2, border_radius=18)
# # # # # #             yt = self.font.render("YES", True, (255, 255, 255))
# # # # # #             self.screen.blit(yt, (yes_rect.centerx - yt.get_width() // 2, yes_rect.centery - yt.get_height() // 2))
# # # # # #
# # # # # #             pygame.draw.rect(self.screen, (30, 30, 30), no_rect, border_radius=18)
# # # # # #             pygame.draw.rect(self.screen, (120, 120, 120), no_rect, width=2, border_radius=18)
# # # # # #             nt = self.font.render("NO", True, (255, 255, 255))
# # # # # #             self.screen.blit(nt, (no_rect.centerx - nt.get_width() // 2, no_rect.centery - nt.get_height() // 2))
# # # # # #
# # # # # #             pygame.display.flip()
# # # # # #             self.clock.tick(self.fps)
# # # # # #
# # # # # #     def _toast(self, msg: str, seconds: float = 1.6) -> None:
# # # # # #         t0 = time.time()
# # # # # #         self._set_input_mode(grab=True, show_cursor=False)
# # # # # #         self._disable_screen_blanking()
# # # # # #         while (time.time() - t0) < seconds:
# # # # # #             for ev in pygame.event.get():
# # # # # #                 if ev.type == pygame.QUIT:
# # # # # #                     raise SystemExit(0)
# # # # # #             self.screen.fill((0, 0, 0))
# # # # # #             m = self.font_small.render(msg, True, (255, 255, 255))
# # # # # #             self.screen.blit(m, (self.W // 2 - m.get_width() // 2, self.H // 2 - m.get_height() // 2))
# # # # # #             pygame.display.flip()
# # # # # #             self.clock.tick(self.fps)
# # # # # #
# # # # # #
# # # # # # def main() -> None:
# # # # # #     cfg = "/home/pi/sparc_lock/kiosk_config.yaml"
# # # # # #     ks = KioskShell(cfg)
# # # # # #     ks.run()
# # # # # #
# # # # # #
# # # # # # if __name__ == "__main__":
# # # # # #     main()
# # # # # #!/usr/bin/env python3
# # # # # # -*- coding: utf-8 -*-
# # # # # """
# # # # # kiosk_shell.py — Full file (drop-in replacement)
# # # # #
# # # # # Key change to eliminate the light-blue X11/WM title-bar flash:
# # # # # - Keep ONE SDL/Pygame window for the entire kiosk session.
# # # # # - Run puzzle_lock *in-process* on the SAME display Surface (no second process, no second window).
# # # # # """
# # # # #
# # # # # import os
# # # # # import sys
# # # # # import time
# # # # # import subprocess
# # # # # from typing import Optional, Tuple
# # # # #
# # # # # # Quiet pygame banner
# # # # # os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
# # # # #
# # # # # # Force X11 path
# # # # # os.environ.setdefault("SDL_VIDEODRIVER", "x11")
# # # # # os.environ.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")
# # # # # # Avoid accidental Wayland selection
# # # # # os.environ.pop("WAYLAND_DISPLAY", None)
# # # # # os.environ.pop("WAYLAND_SOCKET", None)
# # # # #
# # # # # import pygame  # noqa: E402
# # # # #
# # # # #
# # # # # BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# # # # # CFG_PATH = os.path.join(BASE_DIR, "kiosk_config.yaml")
# # # # #
# # # # # # If present, we’ll call this to launch Solaris (keeps your existing behavior)
# # # # # LAUNCH_SOLARIS_SH = os.path.join(BASE_DIR, "launch_solaris.sh")
# # # # #
# # # # # # Optional idle lock (seconds). You can tune or move this into kiosk_config.yaml later.
# # # # # IDLE_LOCK_S = 5 * 60
# # # # #
# # # # # # UI
# # # # # BG = (0, 0, 0)
# # # # # PANEL = (18, 18, 18)
# # # # # BORDER = (120, 120, 120)
# # # # # TXT = (245, 245, 245)
# # # # # MUTED = (215, 215, 215)
# # # # # ACCENT = (70, 185, 120)
# # # # #
# # # # #
# # # # # def _safe_read_post_unlock(cfg_path: str) -> str:
# # # # #     """
# # # # #     Reads feature_flags.post_unlock: "menu" | "solaris"
# # # # #     Defaults to "menu" if missing/invalid.
# # # # #     """
# # # # #     try:
# # # # #         import yaml  # type: ignore
# # # # #         if not os.path.isfile(cfg_path):
# # # # #             return "menu"
# # # # #         with open(cfg_path, "r", encoding="utf-8") as f:
# # # # #             cfg = yaml.safe_load(f) or {}
# # # # #         ff = cfg.get("feature_flags", {}) or {}
# # # # #         val = str(ff.get("post_unlock", "menu")).strip().lower()
# # # # #         return val if val in ("menu", "solaris") else "menu"
# # # # #     except Exception:
# # # # #         return "menu"
# # # # #
# # # # #
# # # # # def _fade_to_black(screen: pygame.Surface, clock: pygame.time.Clock, seconds: float = 0.18):
# # # # #     W, H = screen.get_size()
# # # # #     base = screen.copy()
# # # # #     t0 = time.time()
# # # # #     while True:
# # # # #         t = (time.time() - t0) / max(0.001, seconds)
# # # # #         if t >= 1.0:
# # # # #             break
# # # # #         for ev in pygame.event.get():
# # # # #             if ev.type == pygame.QUIT:
# # # # #                 raise SystemExit
# # # # #         screen.blit(base, (0, 0))
# # # # #         a = int(255 * min(1.0, t))
# # # # #         ov = pygame.Surface((W, H), pygame.SRCALPHA)
# # # # #         ov.fill((0, 0, 0, a))
# # # # #         screen.blit(ov, (0, 0))
# # # # #         pygame.display.flip()
# # # # #         clock.tick(60)
# # # # #     screen.fill((0, 0, 0))
# # # # #     pygame.display.flip()
# # # # #
# # # # #
# # # # # def _run_launch_solaris(display: str, xauth: str) -> int:
# # # # #     """
# # # # #     Runs your existing launcher script. Blocks until viewer exits.
# # # # #     Returns the exit code from the script (or 127 if missing).
# # # # #     """
# # # # #     if not os.path.isfile(LAUNCH_SOLARIS_SH):
# # # # #         return 127
# # # # #
# # # # #     env = os.environ.copy()
# # # # #     env["DISPLAY"] = display
# # # # #     env["XAUTHORITY"] = xauth
# # # # #     env["HOME"] = env.get("HOME", "/home/pi")
# # # # #     env["USER"] = env.get("USER", "pi")
# # # # #
# # # # #     try:
# # # # #         return subprocess.call([LAUNCH_SOLARIS_SH], env=env)
# # # # #     except Exception:
# # # # #         return 1
# # # # #
# # # # #
# # # # # class Button:
# # # # #     def __init__(self, rect: pygame.Rect, label: str):
# # # # #         self.rect = rect
# # # # #         self.label = label
# # # # #
# # # # #     def draw(self, screen: pygame.Surface, font: pygame.font.Font, small: pygame.font.Font, hover: bool):
# # # # #         pygame.draw.rect(screen, (28, 28, 28) if not hover else (40, 40, 40), self.rect, border_radius=18)
# # # # #         pygame.draw.rect(screen, BORDER, self.rect, 2, border_radius=18)
# # # # #
# # # # #         t = font.render(self.label, True, TXT)
# # # # #         screen.blit(t, (self.rect.centerx - t.get_width() // 2, self.rect.centery - t.get_height() // 2))
# # # # #
# # # # #         sub = small.render("Tap/Click", True, MUTED)
# # # # #         screen.blit(sub, (self.rect.centerx - sub.get_width() // 2, self.rect.bottom + 10))
# # # # #
# # # # #
# # # # # def main():
# # # # #     pygame.init()
# # # # #     try:
# # # # #         pygame.mixer.init()
# # # # #     except Exception:
# # # # #         pass
# # # # #
# # # # #     # IMPORTANT: Only create one display window for the entire kiosk lifetime.
# # # # #     try:
# # # # #         screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.NOFRAME, vsync=1)
# # # # #     except Exception:
# # # # #         try:
# # # # #             screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.NOFRAME)
# # # # #         except Exception:
# # # # #             screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
# # # # #
# # # # #     pygame.display.set_caption("SPARCstation Kiosk")
# # # # #     clock = pygame.time.Clock()
# # # # #     W, H = screen.get_size()
# # # # #
# # # # #     # Paint immediately to avoid any first-frame junk (within this single process)
# # # # #     screen.fill((0, 0, 0))
# # # # #     pygame.display.flip()
# # # # #     pygame.event.pump()
# # # # #
# # # # #     font_title = pygame.font.SysFont(None, 64)
# # # # #     font_btn = pygame.font.SysFont(None, 44)
# # # # #     font_small = pygame.font.SysFont(None, 26)
# # # # #
# # # # #     display = os.environ.get("DISPLAY", ":0")
# # # # #     xauth = os.environ.get("XAUTHORITY", "/home/pi/.Xauthority")
# # # # #
# # # # #     post_unlock = _safe_read_post_unlock(CFG_PATH)
# # # # #
# # # # #     # Buttons layout
# # # # #     btn_w = min(560, int(W * 0.58))
# # # # #     btn_h = 88
# # # # #     gap = 26
# # # # #     start_y = (H // 2) - (btn_h * 2 + gap) // 2
# # # # #
# # # # #     btn_solaris = Button(pygame.Rect((W - btn_w) // 2, start_y, btn_w, btn_h), "Solaris VM")
# # # # #     btn_lock = Button(pygame.Rect((W - btn_w) // 2, start_y + (btn_h + gap), btn_w, btn_h), "Lock Screen")
# # # # #     btn_quit = Button(pygame.Rect((W - btn_w) // 2, start_y + 2 * (btn_h + gap), btn_w, btn_h), "Quit")
# # # # #
# # # # #     last_input_t = time.time()
# # # # #
# # # # #     # Import puzzle_lock from same directory
# # # # #     sys.path.insert(0, BASE_DIR)
# # # # #     import puzzle_lock  # noqa: E402
# # # # #
# # # # #     while True:
# # # # #         mx, my = pygame.mouse.get_pos()
# # # # #
# # # # #         for ev in pygame.event.get():
# # # # #             if ev.type == pygame.QUIT:
# # # # #                 raise SystemExit
# # # # #
# # # # #             # Any interaction resets idle
# # # # #             if ev.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN, pygame.FINGERDOWN, pygame.FINGERMOTION):
# # # # #                 last_input_t = time.time()
# # # # #
# # # # #             if ev.type == pygame.KEYDOWN:
# # # # #                 if ev.key == pygame.K_ESCAPE:
# # # # #                     # Optional: ignore ESC to prevent accidental exit
# # # # #                     pass
# # # # #
# # # # #             if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
# # # # #                 # Touch/click hit-test
# # # # #                 if ev.type == pygame.FINGERDOWN:
# # # # #                     x, y = int(ev.x * W), int(ev.y * H)
# # # # #                 else:
# # # # #                     x, y = ev.pos
# # # # #
# # # # #                 if btn_solaris.rect.collidepoint((x, y)):
# # # # #                     _fade_to_black(screen, clock, 0.18)
# # # # #                     _run_launch_solaris(display, xauth)
# # # # #                     # After returning from viewer, repaint menu
# # # # #                     screen.fill((0, 0, 0))
# # # # #                     pygame.display.flip()
# # # # #                     last_input_t = time.time()
# # # # #
# # # # #                 elif btn_lock.rect.collidepoint((x, y)):
# # # # #                     _fade_to_black(screen, clock, 0.18)
# # # # #
# # # # #                     # CRITICAL: run lock in-process on the SAME window to avoid WM bar flash
# # # # #                     unlocked = puzzle_lock.run_lock_shared(screen=screen, clock=clock)
# # # # #
# # # # #                     # On unlock, optionally auto-launch Solaris depending on config
# # # # #                     if unlocked and post_unlock == "solaris":
# # # # #                         _fade_to_black(screen, clock, 0.18)
# # # # #                         _run_launch_solaris(display, xauth)
# # # # #
# # # # #                     # Back to menu (still same window)
# # # # #                     screen.fill((0, 0, 0))
# # # # #                     pygame.display.flip()
# # # # #                     last_input_t = time.time()
# # # # #
# # # # #                 elif btn_quit.rect.collidepoint((x, y)):
# # # # #                     _fade_to_black(screen, clock, 0.12)
# # # # #                     pygame.quit()
# # # # #                     sys.exit(0)
# # # # #
# # # # #         # Idle lock
# # # # #         if IDLE_LOCK_S > 0 and (time.time() - last_input_t) >= IDLE_LOCK_S:
# # # # #             _fade_to_black(screen, clock, 0.18)
# # # # #             unlocked = puzzle_lock.run_lock_shared(screen=screen, clock=clock)
# # # # #             if unlocked and post_unlock == "solaris":
# # # # #                 _fade_to_black(screen, clock, 0.18)
# # # # #                 _run_launch_solaris(display, xauth)
# # # # #             screen.fill((0, 0, 0))
# # # # #             pygame.display.flip()
# # # # #             last_input_t = time.time()
# # # # #
# # # # #         # Draw menu
# # # # #         screen.fill(BG)
# # # # #
# # # # #         title = font_title.render("SPARCstation Kiosk", True, TXT)
# # # # #         sub = font_small.render("Single-window mode (prevents X11 title-bar flashing).", True, MUTED)
# # # # #         screen.blit(title, (W // 2 - title.get_width() // 2, 90))
# # # # #         screen.blit(sub, (W // 2 - sub.get_width() // 2, 150))
# # # # #
# # # # #         panel = pygame.Rect(int(W * 0.12), int(H * 0.22), int(W * 0.76), int(H * 0.62))
# # # # #         pygame.draw.rect(screen, PANEL, panel, border_radius=28)
# # # # #         pygame.draw.rect(screen, (80, 80, 80), panel, 2, border_radius=28)
# # # # #
# # # # #         btn_solaris.draw(screen, font_btn, font_small, btn_solaris.rect.collidepoint((mx, my)))
# # # # #         btn_lock.draw(screen, font_btn, font_small, btn_lock.rect.collidepoint((mx, my)))
# # # # #         btn_quit.draw(screen, font_btn, font_small, btn_quit.rect.collidepoint((mx, my)))
# # # # #
# # # # #         hint = font_small.render("Tip: Lock uses the same fullscreen window to eliminate flashing.", True, MUTED)
# # # # #         screen.blit(hint, (W // 2 - hint.get_width() // 2, H - 42))
# # # # #
# # # # #         pygame.display.flip()
# # # # #         clock.tick(60)
# # # # #
# # # # #
# # # # # if __name__ == "__main__":
# # # # #     main()
# # # # #!/usr/bin/env python3
# # # # """
# # # # SPARCstation Kiosk Shell (X11 / pygame)
# # # #
# # # # Design:
# # # # - LightDM autologin starts one X session.
# # # # - Session script starts Openbox ONCE and execs start_lock.sh.
# # # # - start_lock.sh supervises kiosk_shell.py.
# # # # - kiosk_shell.py spawns puzzle_lock.py, then shows a menu.
# # # # - "Pi" and "Solaris" run INLINE (no LightDM logout / no greeter).
# # # # """
# # # #
# # # # import os
# # # # import sys
# # # # import time
# # # # import json
# # # # import yaml
# # # # import signal
# # # # import subprocess
# # # # from dataclasses import dataclass
# # # # from typing import Optional, TextIO, List, Dict, Any, Tuple
# # # # import fcntl
# # # #
# # # # # Hide pygame's banner BEFORE importing pygame
# # # # os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
# # # #
# # # # # ---- Environment hardening (X11-only kiosk) ----
# # # # def _runtime_dir_for_uid(uid: int) -> str:
# # # #     return os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{uid}"
# # # #
# # # #
# # # # def _force_x11_env_base() -> None:
# # # #     uid = os.getuid()
# # # #     os.environ.setdefault("DISPLAY", ":0")
# # # #     os.environ.setdefault("XAUTHORITY", "/home/pi/.Xauthority")
# # # #     os.environ.setdefault("XDG_RUNTIME_DIR", _runtime_dir_for_uid(uid))
# # # #
# # # #     # Force SDL to X11 to avoid Wayland/KMS/DRM paths
# # # #     os.environ.setdefault("SDL_VIDEODRIVER", "x11")
# # # #     os.environ.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")
# # # #
# # # #     # Reduce/avoid WM decoration flash: force window placement
# # # #     os.environ.setdefault("SDL_VIDEO_WINDOW_POS", "0,0")
# # # #     os.environ.setdefault("SDL_VIDEO_CENTERED", "0")
# # # #
# # # #     # Avoid SDL choosing Wayland paths
# # # #     os.environ.pop("WAYLAND_DISPLAY", None)
# # # #     os.environ.pop("WAYLAND_SOCKET", None)
# # # #
# # # #
# # # # _force_x11_env_base()
# # # #
# # # # import pygame  # noqa: E402
# # # #
# # # #
# # # # def _with_x_env(env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
# # # #     e = dict(env) if env else os.environ.copy()
# # # #     uid = os.getuid()
# # # #
# # # #     e.setdefault("DISPLAY", os.environ.get("DISPLAY", ":0"))
# # # #     e.setdefault("XAUTHORITY", os.environ.get("XAUTHORITY", "/home/pi/.Xauthority"))
# # # #     e.setdefault("XDG_RUNTIME_DIR", os.environ.get("XDG_RUNTIME_DIR", _runtime_dir_for_uid(uid)))
# # # #
# # # #     e.setdefault("SDL_VIDEODRIVER", "x11")
# # # #     e.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")
# # # #
# # # #     # Reduce/avoid WM decoration flash: force window placement
# # # #     e.setdefault("SDL_VIDEO_WINDOW_POS", "0,0")
# # # #     e.setdefault("SDL_VIDEO_CENTERED", "0")
# # # #
# # # #     e.pop("WAYLAND_DISPLAY", None)
# # # #     e.pop("WAYLAND_SOCKET", None)
# # # #
# # # #     # Keep pygame banner suppressed in subprocesses too
# # # #     e.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
# # # #     return e
# # # #
# # # #
# # # # # ------------------------------
# # # # # Utilities: logging
# # # # # ------------------------------
# # # # def log_line(path: str, msg: str) -> None:
# # # #     ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
# # # #     line = f"[{ts}] {msg}\n"
# # # #     try:
# # # #         d = os.path.dirname(path)
# # # #         if d:
# # # #             os.makedirs(d, exist_ok=True)
# # # #         with open(path, "a", buffering=1) as f:
# # # #             f.write(line)
# # # #     except Exception:
# # # #         sys.stderr.write(line)
# # # #
# # # #
# # # # # ------------------------------
# # # # # Utilities: singleton lock
# # # # # ------------------------------
# # # # def ensure_singleton(lock_path: Optional[str] = None) -> int:
# # # #     """
# # # #     Prevent multiple kiosk_shell instances.
# # # #
# # # #     If another instance is running, we BLOCK until the lock becomes free.
# # # #     This prevents start_lock.sh from spinning if it starts kiosk_shell twice.
# # # #     """
# # # #     uid = os.getuid()
# # # #     rdir = _runtime_dir_for_uid(uid)
# # # #     try:
# # # #         os.makedirs(rdir, exist_ok=True)
# # # #     except Exception:
# # # #         rdir = "/tmp"
# # # #
# # # #     if lock_path is None:
# # # #         lock_path = os.path.join(rdir, "sparc_kiosk_shell.lock")
# # # #
# # # #     fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
# # # #
# # # #     # Try non-blocking first, then block if held
# # # #     try:
# # # #         fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
# # # #     except BlockingIOError:
# # # #         fcntl.flock(fd, fcntl.LOCK_EX)
# # # #
# # # #     try:
# # # #         os.ftruncate(fd, 0)
# # # #         os.write(fd, f"{os.getpid()}\n".encode())
# # # #     except Exception:
# # # #         pass
# # # #
# # # #     return fd
# # # #
# # # #
# # # # # ------------------------------
# # # # # Utilities: xprintidle
# # # # # ------------------------------
# # # # def read_xprintidle_ms(xprintidle_bin: str = "xprintidle") -> Optional[int]:
# # # #     env = _with_x_env(os.environ.copy())
# # # #     try:
# # # #         out = subprocess.check_output([xprintidle_bin], text=True, env=env, timeout=0.8).strip()
# # # #         return int(out)
# # # #     except Exception:
# # # #         return None
# # # #
# # # #
# # # # # ------------------------------
# # # # # Utilities: process management
# # # # # ------------------------------
# # # # @dataclass
# # # # class ManagedProcess:
# # # #     name: str
# # # #     popen: subprocess.Popen
# # # #     log_handle: Optional[TextIO] = None
# # # #
# # # #
# # # # def kill_process_group(p: subprocess.Popen, log_path: str, name: str) -> None:
# # # #     if p.poll() is not None:
# # # #         return
# # # #
# # # #     try:
# # # #         pgid = os.getpgid(p.pid)
# # # #     except Exception:
# # # #         pgid = None
# # # #
# # # #     def _wait_brief(deadline_s: float) -> bool:
# # # #         end = time.monotonic() + deadline_s
# # # #         while time.monotonic() < end:
# # # #             if p.poll() is not None:
# # # #                 return True
# # # #             time.sleep(0.05)
# # # #         return p.poll() is not None
# # # #
# # # #     if not pgid or pgid <= 0:
# # # #         try:
# # # #             log_line(log_path, f"Killing {name}: SIGTERM pid={p.pid} (no pgid)")
# # # #             p.terminate()
# # # #         except Exception:
# # # #             pass
# # # #         if _wait_brief(2.0):
# # # #             return
# # # #         try:
# # # #             log_line(log_path, f"Killing {name}: SIGKILL pid={p.pid} (no pgid)")
# # # #             p.kill()
# # # #         except Exception:
# # # #             pass
# # # #         try:
# # # #             p.wait(timeout=1.0)
# # # #         except Exception:
# # # #             pass
# # # #         return
# # # #
# # # #     try:
# # # #         log_line(log_path, f"Killing {name}: SIGTERM pgid={pgid}")
# # # #         os.killpg(pgid, signal.SIGTERM)
# # # #     except Exception:
# # # #         pass
# # # #     if _wait_brief(2.0):
# # # #         return
# # # #     try:
# # # #         log_line(log_path, f"Killing {name}: SIGKILL pgid={pgid}")
# # # #         os.killpg(pgid, signal.SIGKILL)
# # # #     except Exception:
# # # #         pass
# # # #     try:
# # # #         p.wait(timeout=1.0)
# # # #     except Exception:
# # # #         pass
# # # #
# # # #
# # # # def spawn_process(
# # # #     name: str,
# # # #     argv: List[str],
# # # #     log_path: Optional[str],
# # # #     env: Optional[Dict[str, str]] = None,
# # # #     cwd: Optional[str] = None,
# # # # ) -> ManagedProcess:
# # # #     log_handle = None
# # # #     if log_path:
# # # #         d = os.path.dirname(log_path)
# # # #         if d:
# # # #             os.makedirs(d, exist_ok=True)
# # # #         log_handle = open(log_path, "ab", buffering=0)
# # # #
# # # #     stdout_target = log_handle if log_handle else subprocess.DEVNULL
# # # #
# # # #     p = subprocess.Popen(
# # # #         argv,
# # # #         env=_with_x_env(env),
# # # #         cwd=cwd,
# # # #         stdin=subprocess.DEVNULL,
# # # #         stdout=stdout_target,
# # # #         stderr=subprocess.STDOUT,
# # # #         start_new_session=True,
# # # #         close_fds=True,
# # # #     )
# # # #     return ManagedProcess(name=name, popen=p, log_handle=log_handle)
# # # #
# # # #
# # # # # ------------------------------
# # # # # Kiosk Shell
# # # # # ------------------------------
# # # # class KioskShell:
# # # #     def __init__(self, cfg_path: str):
# # # #         self.cfg_path = cfg_path
# # # #         self.cfg = self._load_cfg(cfg_path)
# # # #         self.log_path = self.cfg["logs"]["shell_log"]
# # # #
# # # #         self._singleton_fd = ensure_singleton()
# # # #         self._shutting_down = False
# # # #
# # # #         self.active_child: Optional[subprocess.Popen] = None
# # # #         self.in_external = False
# # # #
# # # #         # VM (QEMU) management
# # # #         self.vm_pidfile = self.cfg["vm"]["pidfile"]
# # # #         self.vm_start_cmd = self.cfg["vm"]["start_cmd"]
# # # #         self.vm_cwd = self.cfg["vm"]["cwd"]
# # # #         self.vm_autostart = bool(self.cfg["vm"]["enable_autostart"])
# # # #         self.vm_startup_grace_s = float(self.cfg["vm"]["startup_grace_s"])
# # # #
# # # #         # PINs
# # # #         self.pi_pin = str(self.cfg["security"]["pi_pin"])
# # # #
# # # #         def _handle_term(signum, frame):
# # # #             self._shutting_down = True
# # # #             log_line(self.log_path, f"Signal {signum} received; stopping active child and exiting")
# # # #             p = self.active_child
# # # #             if p and p.poll() is None:
# # # #                 kill_process_group(p, self.log_path, "active_child")
# # # #             try:
# # # #                 self._suspend_display("signal_exit")
# # # #             except Exception:
# # # #                 pass
# # # #             try:
# # # #                 pygame.quit()
# # # #             except Exception:
# # # #                 pass
# # # #             raise SystemExit(0)
# # # #
# # # #         signal.signal(signal.SIGTERM, _handle_term)
# # # #         signal.signal(signal.SIGINT, _handle_term)
# # # #
# # # #         pygame.init()
# # # #         try:
# # # #             pygame.font.init()
# # # #         except Exception:
# # # #             pass
# # # #
# # # #         self._init_display_with_retry()
# # # #
# # # #     def _xsetroot_black(self) -> None:
# # # #         try:
# # # #             subprocess.run(
# # # #                 ["xsetroot", "-solid", "black"],
# # # #                 env=_with_x_env(os.environ.copy()),
# # # #                 stdout=subprocess.DEVNULL,
# # # #                 stderr=subprocess.DEVNULL,
# # # #                 timeout=0.8,
# # # #                 check=False,
# # # #             )
# # # #         except Exception:
# # # #             pass
# # # #
# # # #     def _blackout_frame(self, delay_s: float = 0.05) -> None:
# # # #         """Paint a single black frame to reduce flashes during display teardown."""
# # # #         try:
# # # #             if pygame.display.get_init():
# # # #                 surf = pygame.display.get_surface()
# # # #                 if surf:
# # # #                     surf.fill((0, 0, 0))
# # # #                     pygame.display.flip()
# # # #                     if delay_s > 0:
# # # #                         time.sleep(delay_s)
# # # #         except Exception:
# # # #             pass
# # # #
# # # #     # --------------------------
# # # #     # X11 helpers / blanking
# # # #     # --------------------------
# # # #     def _xset(self, args: List[str]) -> bool:
# # # #         try:
# # # #             subprocess.run(
# # # #                 ["xset"] + args,
# # # #                 env=_with_x_env(os.environ.copy()),
# # # #                 stdout=subprocess.DEVNULL,
# # # #                 stderr=subprocess.DEVNULL,
# # # #                 timeout=1.0,
# # # #                 check=False,
# # # #             )
# # # #             return True
# # # #         except Exception:
# # # #             return False
# # # #
# # # #     def _wait_for_x_ready(self, retries: int = 60, sleep_s: float = 0.25) -> bool:
# # # #         env = _with_x_env(os.environ.copy())
# # # #         for _ in range(retries):
# # # #             try:
# # # #                 subprocess.run(
# # # #                     ["xset", "q"],
# # # #                     env=env,
# # # #                     stdout=subprocess.DEVNULL,
# # # #                     stderr=subprocess.DEVNULL,
# # # #                     timeout=1.0,
# # # #                     check=True,
# # # #                 )
# # # #                 return True
# # # #             except Exception:
# # # #                 time.sleep(sleep_s)
# # # #         return False
# # # #
# # # #     def _disable_screen_blanking(self) -> None:
# # # #         self._xset(["s", "off"])
# # # #         self._xset(["s", "noblank"])
# # # #         self._xset(["-dpms"])
# # # #
# # # #     def _release_pygame_completely(self, reason: str) -> None:
# # # #         try:
# # # #             self._set_input_mode(grab=False, show_cursor=True)
# # # #         except Exception:
# # # #             pass
# # # #         try:
# # # #             pygame.event.clear()
# # # #             pygame.event.pump()
# # # #         except Exception:
# # # #             pass
# # # #
# # # #         # black-out + root black before teardown
# # # #         self._blackout_frame(delay_s=0.04)
# # # #         self._xsetroot_black()
# # # #
# # # #         try:
# # # #             if pygame.display.get_init():
# # # #                 pygame.display.quit()
# # # #         except Exception:
# # # #             pass
# # # #         log_line(self.log_path, f"Released pygame display ({reason})")
# # # #
# # # #     # Legacy exit-code handoff (disabled unless explicitly allowed)
# # # #     def _hard_exit(self, code: int, reason: str) -> None:
# # # #         self._shutting_down = True
# # # #         log_line(self.log_path, f"Exiting kiosk_shell rc={code} ({reason})")
# # # #         try:
# # # #             self._release_pygame_completely(f"exit:{reason}")
# # # #         except Exception:
# # # #             pass
# # # #         try:
# # # #             pygame.quit()
# # # #         except Exception:
# # # #             pass
# # # #         raise SystemExit(code)
# # # #
# # # #     def _allow_exit_codes(self) -> bool:
# # # #         return os.environ.get("SPARC_ALLOW_EXIT_CODES", "0") == "1"
# # # #
# # # #     # --------------------------
# # # #     # Display lifecycle
# # # #     # --------------------------
# # # #     def _init_display_with_retry(self, retries: int = 40, sleep_s: float = 0.25) -> None:
# # # #         last_err: Optional[Exception] = None
# # # #         for _ in range(retries):
# # # #             try:
# # # #                 if not self._wait_for_x_ready(retries=6, sleep_s=0.2):
# # # #                     raise RuntimeError("X not ready (xset q failed)")
# # # #
# # # #                 pygame.display.init()
# # # #                 try:
# # # #                     if not pygame.font.get_init():
# # # #                         pygame.font.init()
# # # #                 except Exception:
# # # #                     pass
# # # #
# # # #                 self.init_display()
# # # #                 return
# # # #             except Exception as e:
# # # #                 last_err = e
# # # #                 time.sleep(sleep_s)
# # # #
# # # #         log_line(self.log_path, f"FATAL: unable to init display after retries: {last_err}")
# # # #         raise last_err if last_err else RuntimeError("unable to init display")
# # # #
# # # #     def init_display(self) -> None:
# # # #         ui = self.cfg.get("ui", {})
# # # #         self.title = ui.get("title", "SPARCstation")
# # # #
# # # #         pygame.display.set_caption(self.title)
# # # #
# # # #         # IMPORTANT: NOFRAME avoids Openbox title-bar flash seen during FULLSCREEN transitions.
# # # #         self.screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)
# # # #         self.W, self.H = self.screen.get_size()
# # # #
# # # #         # Paint black immediately
# # # #         self.screen.fill((0, 0, 0))
# # # #         pygame.display.flip()
# # # #         pygame.event.pump()
# # # #
# # # #         self.font = pygame.font.SysFont(None, int(ui.get("font_size", 54)))
# # # #         self.font_small = pygame.font.SysFont(None, int(ui.get("small_font_size", 28)))
# # # #
# # # #         self.fps = int(ui.get("fps", 60))
# # # #         self.clock = pygame.time.Clock()
# # # #
# # # #         self._set_input_mode(grab=True, show_cursor=True)
# # # #         self._blackout_frame(delay_s=0.02)
# # # #
# # # #     def _suspend_display(self, reason: str) -> None:
# # # #         try:
# # # #             self._set_input_mode(grab=False, show_cursor=False)
# # # #         except Exception:
# # # #             pass
# # # #
# # # #         self._blackout_frame(delay_s=0.04)
# # # #         self._xsetroot_black()
# # # #
# # # #         try:
# # # #             if pygame.display.get_init():
# # # #                 pygame.display.quit()
# # # #         except Exception:
# # # #             pass
# # # #         log_line(self.log_path, f"Suspend display ({reason})")
# # # #
# # # #     def _reclaim_fullscreen(self, reason: str = "return") -> None:
# # # #         if self._shutting_down:
# # # #             log_line(self.log_path, f"Skip reclaim during shutdown ({reason})")
# # # #             return
# # # #
# # # #         try:
# # # #             pygame.event.clear()
# # # #         except Exception:
# # # #             pass
# # # #
# # # #         # blackout + root black before reset cycle
# # # #         self._blackout_frame(delay_s=0.04)
# # # #         self._xsetroot_black()
# # # #
# # # #         try:
# # # #             if pygame.display.get_init():
# # # #                 pygame.display.quit()
# # # #         except Exception:
# # # #             pass
# # # #
# # # #         try:
# # # #             if not self._wait_for_x_ready(retries=12, sleep_s=0.25):
# # # #                 raise RuntimeError("X not ready on reclaim")
# # # #
# # # #             pygame.display.init()
# # # #             self.init_display()
# # # #             self._blackout_frame(delay_s=0.01)
# # # #             log_line(self.log_path, f"Reclaimed display ({reason})")
# # # #         except Exception as e:
# # # #             log_line(self.log_path, f"ERROR reclaiming display ({reason}): {e}")
# # # #             self._init_display_with_retry()
# # # #
# # # #     def _set_input_mode(self, grab: bool, show_cursor: bool) -> None:
# # # #         try:
# # # #             pygame.event.set_grab(bool(grab))
# # # #         except Exception:
# # # #             pass
# # # #         try:
# # # #             pygame.mouse.set_visible(bool(show_cursor))
# # # #         except Exception:
# # # #             pass
# # # #         try:
# # # #             pygame.event.pump()
# # # #         except Exception:
# # # #             pass
# # # #
# # # #     # --------------------------
# # # #     # Config
# # # #     # --------------------------
# # # #     def _load_cfg(self, path: str) -> Dict[str, Any]:
# # # #         with open(path, "r") as f:
# # # #             cfg = yaml.safe_load(f) or {}
# # # #
# # # #         cfg.setdefault("feature_flags", {})
# # # #         cfg.setdefault("idle", {})
# # # #         cfg.setdefault("ui", {})
# # # #         cfg.setdefault("paths", {})
# # # #         cfg.setdefault("logs", {})
# # # #         cfg.setdefault("vm", {})
# # # #         cfg.setdefault("security", {})
# # # #
# # # #         cfg["idle"].setdefault("menu_seconds", 120)
# # # #         cfg["idle"].setdefault("external_seconds", 300)
# # # #
# # # #         cfg["logs"].setdefault("shell_log", "/home/pi/sparc_lock/logs/kiosk_shell.log")
# # # #         cfg["logs"].setdefault("lock_child_log", "/home/pi/sparc_lock/logs/lock_child.log")
# # # #         cfg["logs"].setdefault("mpv_log", "/home/pi/sparc_lock/logs/mpv.log")
# # # #         cfg["logs"].setdefault("solaris_log", "/home/pi/sparc_lock/logs/solaris_vnc.log")
# # # #         cfg["logs"].setdefault("games_log_dir", "/home/pi/sparc_lock/logs/games")
# # # #
# # # #         cfg["paths"].setdefault("lock_py", "/home/pi/sparc_lock/puzzle_lock.py")
# # # #         cfg["paths"].setdefault("launch_solaris_sh", "/home/pi/sparc_lock/launch_solaris.sh")
# # # #         cfg["paths"].setdefault("start_pi_mode_sh", "/home/pi/sparc_lock/start_pi_mode.sh")
# # # #         cfg["paths"].setdefault("mpv_input_conf", "/home/pi/sparc_lock/mpv.input.conf")
# # # #         cfg["paths"].setdefault("media_images", "/home/pi/sparc_media/images")
# # # #         cfg["paths"].setdefault("media_music", "/home/pi/sparc_media/music")
# # # #         cfg["paths"].setdefault("media_videos", "/home/pi/sparc_media/videos")
# # # #         cfg["paths"].setdefault("games_root", "/home/pi/sparc_games/installed")
# # # #
# # # #         # VM defaults
# # # #         cfg["vm"].setdefault("enable_autostart", True)
# # # #         cfg["vm"].setdefault("pidfile", "/home/pi/sparc_vm/qemu-sparc.pid")
# # # #         cfg["vm"].setdefault("start_cmd", ["/home/pi/sparc_vm/run_sol8.sh"])
# # # #         cfg["vm"].setdefault("cwd", "/home/pi/sparc_vm")
# # # #         cfg["vm"].setdefault("startup_grace_s", 1.0)
# # # #
# # # #         # Feature flags (menu composition)
# # # #         cfg["feature_flags"].setdefault("enable_pi", True)
# # # #         cfg["feature_flags"].setdefault("enable_solaris", True)
# # # #         cfg["feature_flags"].setdefault("enable_games", True)
# # # #         cfg["feature_flags"].setdefault("enable_media", True)
# # # #         cfg["feature_flags"].setdefault("enable_power", True)
# # # #
# # # #         # Default to INLINE behavior
# # # #         cfg["feature_flags"].setdefault("solaris_via_exit_code", False)
# # # #         cfg["feature_flags"].setdefault("pi_via_exit_code", False)
# # # #
# # # #         # Security
# # # #         cfg["security"].setdefault("pi_pin", "1193")
# # # #
# # # #         return cfg
# # # #
# # # #     # --------------------------
# # # #     # VM management (QEMU)
# # # #     # --------------------------
# # # #     def _vm_is_running(self) -> bool:
# # # #         try:
# # # #             with open(self.vm_pidfile, "r") as f:
# # # #                 pid_str = f.read().strip()
# # # #             if not pid_str:
# # # #                 return False
# # # #             pid = int(pid_str)
# # # #             os.kill(pid, 0)
# # # #             return True
# # # #         except FileNotFoundError:
# # # #             return False
# # # #         except ProcessLookupError:
# # # #             try:
# # # #                 os.remove(self.vm_pidfile)
# # # #             except Exception:
# # # #                 pass
# # # #             return False
# # # #         except Exception:
# # # #             return False
# # # #
# # # #     def _ensure_vm_running(self) -> None:
# # # #         if not self.vm_autostart:
# # # #             return
# # # #         if self._vm_is_running():
# # # #             return
# # # #         try:
# # # #             log_line(self.log_path, f"Starting VM: {self.vm_start_cmd}")
# # # #             subprocess.Popen(
# # # #                 self.vm_start_cmd,
# # # #                 cwd=self.vm_cwd,
# # # #                 env=_with_x_env(),
# # # #                 stdout=subprocess.DEVNULL,
# # # #                 stderr=subprocess.DEVNULL,
# # # #                 start_new_session=True,
# # # #             )
# # # #             time.sleep(self.vm_startup_grace_s)
# # # #         except Exception as e:
# # # #             log_line(self.log_path, f"WARNING: failed to start VM: {e}")
# # # #
# # # #     # --------------------------
# # # #     # PIN UI
# # # #     # --------------------------
# # # #     def _pin_prompt(self, title: str, msg: str, expected_pin: str) -> bool:
# # # #         pin_input = ""
# # # #         err_msg = ""
# # # #         err_t0 = 0.0
# # # #
# # # #         keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "C", "0", "OK"]
# # # #         cols, rows = 3, 4
# # # #         cancel_rect = pygame.Rect(16, 16, 170, 52)
# # # #
# # # #         def draw():
# # # #             self.screen.fill((0, 0, 0))
# # # #             overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
# # # #             overlay.fill((0, 0, 0, 210))
# # # #             self.screen.blit(overlay, (0, 0))
# # # #
# # # #             pygame.draw.rect(self.screen, (40, 40, 40), cancel_rect, border_radius=14)
# # # #             pygame.draw.rect(self.screen, (200, 200, 200), cancel_rect, 2, border_radius=14)
# # # #             ct = self.font_small.render("CANCEL", True, (255, 255, 255))
# # # #             self.screen.blit(ct, (cancel_rect.centerx - ct.get_width() // 2, cancel_rect.centery - ct.get_height() // 2))
# # # #
# # # #             t = self.font.render(title, True, (255, 255, 255))
# # # #             self.screen.blit(t, (self.W // 2 - t.get_width() // 2, 90))
# # # #
# # # #             m = self.font_small.render(msg, True, (220, 220, 220))
# # # #             self.screen.blit(m, (self.W // 2 - m.get_width() // 2, 150))
# # # #
# # # #             masked = "*" * len(pin_input)
# # # #             e = self.font.render(masked, True, (255, 255, 0))
# # # #             self.screen.blit(e, (self.W // 2 - e.get_width() // 2, 190))
# # # #
# # # #             pad_w = min(520, int(self.W * 0.42))
# # # #             pad_h = min(520, int(self.H * 0.62))
# # # #             pad_x = (self.W - pad_w) // 2
# # # #             pad_y = (self.H - pad_h) // 2 + 40
# # # #             cell_w = pad_w // cols
# # # #             cell_h = pad_h // rows
# # # #
# # # #             pygame.draw.rect(self.screen, (35, 35, 35), pygame.Rect(pad_x, pad_y, pad_w, pad_h), border_radius=16)
# # # #             rects = []
# # # #             for r in range(rows):
# # # #                 for c in range(cols):
# # # #                     x = pad_x + c * cell_w + 10
# # # #                     y = pad_y + r * cell_h + 10
# # # #                     rects.append(pygame.Rect(x, y, cell_w - 20, cell_h - 20))
# # # #
# # # #             mx, my = pygame.mouse.get_pos()
# # # #             for i, r in enumerate(rects):
# # # #                 hot = r.collidepoint(mx, my)
# # # #                 bg = (70, 70, 70) if hot else (55, 55, 55)
# # # #                 pygame.draw.rect(self.screen, bg, r, border_radius=12)
# # # #                 pygame.draw.rect(self.screen, (170, 170, 170), r, 2, border_radius=12)
# # # #                 kt = self.font.render(keys[i], True, (255, 255, 255))
# # # #                 self.screen.blit(kt, (r.centerx - kt.get_width() // 2, r.centery - kt.get_height() // 2))
# # # #
# # # #             if err_msg and (time.time() - err_t0) < 2.0:
# # # #                 em = self.font_small.render(err_msg, True, (255, 90, 90))
# # # #                 self.screen.blit(em, (self.W // 2 - em.get_width() // 2, pad_y + pad_h + 18))
# # # #
# # # #             tip = self.font_small.render("Enter=submit, Backspace=delete, OK=submit. Esc/CANCEL=back.", True, (200, 200, 200))
# # # #             self.screen.blit(tip, (self.W // 2 - tip.get_width() // 2, pad_y + pad_h + 52))
# # # #
# # # #             pygame.display.flip()
# # # #
# # # #         def hit_key(x: int, y: int) -> Optional[str]:
# # # #             pad_w = min(520, int(self.W * 0.42))
# # # #             pad_h = min(520, int(self.H * 0.62))
# # # #             pad_x = (self.W - pad_w) // 2
# # # #             pad_y = (self.H - pad_h) // 2 + 40
# # # #             cell_w = pad_w // cols
# # # #             cell_h = pad_h // rows
# # # #
# # # #             idx = 0
# # # #             for r in range(rows):
# # # #                 for c in range(cols):
# # # #                     rx = pad_x + c * cell_w + 10
# # # #                     ry = pad_y + r * cell_h + 10
# # # #                     rect = pygame.Rect(rx, ry, cell_w - 20, cell_h - 20)
# # # #                     if rect.collidepoint(x, y):
# # # #                         return keys[idx]
# # # #                     idx += 1
# # # #             return None
# # # #
# # # #         self._set_input_mode(grab=True, show_cursor=True)
# # # #         pygame.event.clear()
# # # #         pygame.event.pump()
# # # #
# # # #         while True:
# # # #             for ev in pygame.event.get():
# # # #                 if ev.type == pygame.QUIT:
# # # #                     raise SystemExit(0)
# # # #
# # # #                 if ev.type == pygame.KEYDOWN:
# # # #                     if ev.key in (pygame.K_ESCAPE,):
# # # #                         return False
# # # #                     if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
# # # #                         if pin_input == expected_pin:
# # # #                             return True
# # # #                         err_msg = "Incorrect PIN"
# # # #                         err_t0 = time.time()
# # # #                         pin_input = ""
# # # #                     elif ev.key == pygame.K_BACKSPACE:
# # # #                         pin_input = pin_input[:-1]
# # # #                     else:
# # # #                         ch = ev.unicode
# # # #                         if ch.isdigit() and len(pin_input) < 12:
# # # #                             pin_input += ch
# # # #
# # # #                 if ev.type == pygame.MOUSEBUTTONDOWN:
# # # #                     x, y = ev.pos
# # # #                     if cancel_rect.collidepoint(x, y):
# # # #                         return False
# # # #                     k = hit_key(x, y)
# # # #                     if k:
# # # #                         if k == "C":
# # # #                             pin_input = ""
# # # #                         elif k == "OK":
# # # #                             if pin_input == expected_pin:
# # # #                                 return True
# # # #                             err_msg = "Incorrect PIN"
# # # #                             err_t0 = time.time()
# # # #                             pin_input = ""
# # # #                         else:
# # # #                             if len(pin_input) < 12:
# # # #                                 pin_input += k
# # # #
# # # #                 if ev.type == pygame.FINGERDOWN:
# # # #                     x = int(ev.x * self.W)
# # # #                     y = int(ev.y * self.H)
# # # #                     if cancel_rect.collidepoint(x, y):
# # # #                         return False
# # # #                     k = hit_key(x, y)
# # # #                     if k:
# # # #                         if k == "C":
# # # #                             pin_input = ""
# # # #                         elif k == "OK":
# # # #                             if pin_input == expected_pin:
# # # #                                 return True
# # # #                             err_msg = "Incorrect PIN"
# # # #                             err_t0 = time.time()
# # # #                             pin_input = ""
# # # #                         else:
# # # #                             if len(pin_input) < 12:
# # # #                                 pin_input += k
# # # #
# # # #             draw()
# # # #             self.clock.tick(self.fps)
# # # #
# # # #     # --------------------------
# # # #     # Main loop
# # # #     # --------------------------
# # # #     def run(self) -> None:
# # # #         log_line(self.log_path, "kiosk_shell starting")
# # # #         self._ensure_vm_running()
# # # #
# # # #         while True:
# # # #             rc = self.run_lock()
# # # #             if rc != 0:
# # # #                 log_line(self.log_path, f"Lock returned rc={rc} -> restarting lock")
# # # #                 continue
# # # #
# # # #             choice = self.menu_loop()
# # # #             log_line(self.log_path, f"Menu returned choice={choice}")
# # # #
# # # #             if choice == "relock":
# # # #                 continue
# # # #
# # # #             if choice == "pi":
# # # #                 ok = self._pin_prompt("PI DESKTOP", "Enter PIN to open Pi admin desktop", self.pi_pin)
# # # #                 if not ok:
# # # #                     log_line(self.log_path, "Pi PIN canceled/failed -> back to menu")
# # # #                     continue
# # # #
# # # #                 log_line(self.log_path, "Pi PIN accepted -> entering Pi mode (inline)")
# # # #
# # # #                 if bool(self.cfg["feature_flags"].get("pi_via_exit_code", False)) and self._allow_exit_codes():
# # # #                     self._suspend_display("exit_to_pi")
# # # #                     self._hard_exit(42, "pi_mode")
# # # #                 else:
# # # #                     self._run_pi_mode_inline()
# # # #                 continue
# # # #
# # # #             if choice == "solaris":
# # # #                 log_line(self.log_path, "Solaris selected")
# # # #
# # # #                 if bool(self.cfg["feature_flags"].get("solaris_via_exit_code", False)) and self._allow_exit_codes():
# # # #                     self._suspend_display("exit_to_solaris")
# # # #                     self._hard_exit(43, "solaris")
# # # #                 else:
# # # #                     self.run_solaris()
# # # #                 continue
# # # #
# # # #             if choice == "games":
# # # #                 self.run_games()
# # # #                 continue
# # # #
# # # #             if choice == "media":
# # # #                 self.run_media()
# # # #                 continue
# # # #
# # # #             if choice == "shutdown":
# # # #                 self.run_shutdown()
# # # #                 continue
# # # #
# # # #     # --------------------------
# # # #     # Lock runner
# # # #     # --------------------------
# # # #     def run_lock(self) -> int:
# # # #         lock_py = self.cfg["paths"]["lock_py"]
# # # #         env = _with_x_env(os.environ.copy())
# # # #
# # # #         log_line(self.log_path, "Starting lock (puzzle_lock.py)")
# # # #         mp: Optional[ManagedProcess] = None
# # # #
# # # #         self._suspend_display("before_lock")
# # # #
# # # #         try:
# # # #             mp = spawn_process(
# # # #                 name="lock",
# # # #                 argv=["python3", "-u", lock_py],
# # # #                 log_path=self.cfg["logs"]["lock_child_log"],
# # # #                 env=env,
# # # #                 cwd="/home/pi/sparc_lock",
# # # #             )
# # # #             self.active_child = mp.popen
# # # #             rc = mp.popen.wait()
# # # #             log_line(self.log_path, f"Lock exited rc={rc}")
# # # #             return rc
# # # #         finally:
# # # #             self.active_child = None
# # # #             if mp and mp.log_handle:
# # # #                 try:
# # # #                     mp.log_handle.close()
# # # #                 except Exception:
# # # #                     pass
# # # #             self._reclaim_fullscreen("after_lock")
# # # #
# # # #     # --------------------------
# # # #     # Menu UI
# # # #     # --------------------------
# # # #     def menu_loop(self) -> str:
# # # #         flags = self.cfg.get("feature_flags", {})
# # # #         enable_pi = bool(flags.get("enable_pi", True))
# # # #         enable_solaris = bool(flags.get("enable_solaris", True))
# # # #         enable_games = bool(flags.get("enable_games", True))
# # # #         enable_media = bool(flags.get("enable_media", True))
# # # #         enable_power = bool(flags.get("enable_power", True))
# # # #
# # # #         items: List[Tuple[str, str]] = []
# # # #         if enable_pi:
# # # #             items.append(("Pi", "pi"))
# # # #         if enable_solaris:
# # # #             items.append(("Solaris", "solaris"))
# # # #         if enable_games:
# # # #             items.append(("Games", "games"))
# # # #         if enable_media:
# # # #             items.append(("Media Library", "media"))
# # # #         if enable_power:
# # # #             items.append(("Shutdown", "shutdown"))
# # # #         items.append(("Re-lock", "relock"))
# # # #
# # # #         idle_limit = int(self.cfg["idle"]["menu_seconds"])
# # # #         last_input = time.time()
# # # #         sel = 0
# # # #
# # # #         self._set_input_mode(grab=True, show_cursor=True)
# # # #         self._disable_screen_blanking()
# # # #         try:
# # # #             pygame.event.clear()
# # # #             pygame.event.pump()
# # # #         except Exception:
# # # #             pass
# # # #
# # # #         while True:
# # # #             if (time.time() - last_input) >= idle_limit:
# # # #                 log_line(self.log_path, f"Menu idle >= {idle_limit}s -> relock")
# # # #                 return "relock"
# # # #
# # # #             for ev in pygame.event.get():
# # # #                 if ev.type == pygame.QUIT:
# # # #                     raise SystemExit(0)
# # # #
# # # #                 if ev.type in (
# # # #                     pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION,
# # # #                     pygame.KEYDOWN,
# # # #                     pygame.FINGERDOWN, pygame.FINGERMOTION
# # # #                 ):
# # # #                     last_input = time.time()
# # # #
# # # #                 if ev.type == pygame.KEYDOWN:
# # # #                     if ev.key in (pygame.K_ESCAPE, pygame.K_q):
# # # #                         return "relock"
# # # #                     if ev.key == pygame.K_UP:
# # # #                         sel = max(0, sel - 1)
# # # #                     elif ev.key == pygame.K_DOWN:
# # # #                         sel = min(len(items) - 1, sel + 1)
# # # #                     elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
# # # #                         action = items[sel][1]
# # # #                         log_line(self.log_path, f"Menu key select -> {action}")
# # # #                         return action
# # # #
# # # #                 if ev.type == pygame.MOUSEBUTTONDOWN:
# # # #                     hit = self._hit_test_menu(items, ev.pos[0], ev.pos[1])
# # # #                     if hit:
# # # #                         log_line(self.log_path, f"Menu click -> {hit}")
# # # #                         return hit
# # # #
# # # #                 if ev.type == pygame.FINGERDOWN:
# # # #                     x = int(ev.x * self.W)
# # # #                     y = int(ev.y * self.H)
# # # #                     hit = self._hit_test_menu(items, x, y)
# # # #                     if hit:
# # # #                         log_line(self.log_path, f"Menu touch -> {hit}")
# # # #                         return hit
# # # #
# # # #             self._draw_menu(items, sel=sel)
# # # #             pygame.display.flip()
# # # #             self.clock.tick(self.fps)
# # # #
# # # #     def _draw_menu(self, items: List[Tuple[str, str]], sel: int = 0) -> None:
# # # #         self.screen.fill((0, 0, 0))
# # # #
# # # #         title = self.font.render(self.title, True, (255, 255, 255))
# # # #         self.screen.blit(title, (self.W // 2 - title.get_width() // 2, 40))
# # # #
# # # #         btn_w = int(self.W * 0.70)
# # # #         btn_h = 90
# # # #         gap = 22
# # # #         start_y = 160
# # # #
# # # #         for i, (label, _action) in enumerate(items):
# # # #             x = self.W // 2 - btn_w // 2
# # # #             y = start_y + i * (btn_h + gap)
# # # #             rect = pygame.Rect(x, y, btn_w, btn_h)
# # # #
# # # #             is_sel = (i == sel)
# # # #             bg = (55, 55, 55) if is_sel else (30, 30, 30)
# # # #             border = (200, 200, 200) if is_sel else (120, 120, 120)
# # # #
# # # #             pygame.draw.rect(self.screen, bg, rect, border_radius=18)
# # # #             pygame.draw.rect(self.screen, border, rect, width=2, border_radius=18)
# # # #
# # # #             text = self.font.render(label, True, (240, 240, 240))
# # # #             self.screen.blit(text, (
# # # #                 rect.centerx - text.get_width() // 2,
# # # #                 rect.centery - text.get_height() // 2
# # # #             ))
# # # #
# # # #         hint = self.font_small.render("Click/tap or use Up/Down + Enter. Idle returns to lock.", True, (180, 180, 180))
# # # #         self.screen.blit(hint, (self.W // 2 - hint.get_width() // 2, self.H - 60))
# # # #
# # # #     def _hit_test_menu(self, items: List[Tuple[str, str]], x: int, y: int) -> Optional[str]:
# # # #         btn_w = int(self.W * 0.70)
# # # #         btn_h = 90
# # # #         gap = 22
# # # #         start_y = 160
# # # #         for i, (_label, action) in enumerate(items):
# # # #             rx = self.W // 2 - btn_w // 2
# # # #             ry = start_y + i * (btn_h + gap)
# # # #             rect = pygame.Rect(rx, ry, btn_w, btn_h)
# # # #             if rect.collidepoint(x, y):
# # # #                 return action
# # # #         return None
# # # #
# # # #     # --------------------------
# # # #     # Pi mode (INLINE)
# # # #     # --------------------------
# # # #     def _run_pi_mode_inline(self) -> None:
# # # #         sh = self.cfg["paths"]["start_pi_mode_sh"]
# # # #         logp = "/home/pi/sparc_lock/logs/pi_mode.log"
# # # #         self._run_external(
# # # #             name="pi_mode",
# # # #             argv=["/bin/bash", sh],
# # # #             log_path=logp,
# # # #             env=_with_x_env(os.environ.copy()),
# # # #             idle_seconds=int(self.cfg["idle"]["external_seconds"]),
# # # #             cwd="/home/pi",
# # # #         )
# # # #
# # # #     # --------------------------
# # # #     # Solaris (INLINE)
# # # #     # --------------------------
# # # #     def run_solaris(self) -> int:
# # # #         log_line(self.log_path, "run_solaris() entered")
# # # #         if self.in_external:
# # # #             log_line(self.log_path, "Ignoring Solaris launch: external already active")
# # # #             return 0
# # # #
# # # #         self._ensure_vm_running()
# # # #         self.in_external = True
# # # #         try:
# # # #             sh = self.cfg["paths"]["launch_solaris_sh"]
# # # #             idle_s = int(self.cfg["idle"]["external_seconds"])
# # # #             env = _with_x_env(os.environ.copy())
# # # #             env["SPARC_IDLE_MANAGED"] = "1"
# # # #             return self._run_external(
# # # #                 name="solaris",
# # # #                 argv=[sh],
# # # #                 log_path=self.cfg["logs"]["solaris_log"],
# # # #                 env=env,
# # # #                 idle_seconds=idle_s,
# # # #                 cwd="/home/pi",
# # # #             )
# # # #         finally:
# # # #             self.in_external = False
# # # #
# # # #     # --------------------------
# # # #     # Media
# # # #     # --------------------------
# # # #     def run_media(self) -> None:
# # # #         roots = [
# # # #             ("Images", self.cfg["paths"]["media_images"]),
# # # #             ("Music", self.cfg["paths"]["media_music"]),
# # # #             ("Videos", self.cfg["paths"]["media_videos"]),
# # # #         ]
# # # #         choice = self._simple_list_screen("Media Library", [r[0] for r in roots])
# # # #         if choice is None:
# # # #             return
# # # #         _label, path = roots[choice]
# # # #         self._browse_and_play(path)
# # # #
# # # #     def _browse_and_play(self, folder: str) -> None:
# # # #         try:
# # # #             files = sorted([f for f in os.listdir(folder) if not f.startswith(".")])
# # # #         except Exception:
# # # #             self._toast(f"Cannot open: {folder}")
# # # #             return
# # # #
# # # #         idx = self._simple_list_screen(os.path.basename(folder), files)
# # # #         if idx is None:
# # # #             return
# # # #
# # # #         target = os.path.join(folder, files[idx])
# # # #         self._play_with_mpv(target)
# # # #
# # # #     def _play_with_mpv(self, path: str) -> None:
# # # #         idle_s = int(self.cfg["idle"]["external_seconds"])
# # # #         mpv_conf = self.cfg["paths"]["mpv_input_conf"]
# # # #         argv = ["mpv", "--fs", "--input-conf=" + mpv_conf, path]
# # # #         self._run_external(
# # # #             name="mpv",
# # # #             argv=argv,
# # # #             log_path=self.cfg["logs"]["mpv_log"],
# # # #             env=_with_x_env(os.environ.copy()),
# # # #             idle_seconds=idle_s,
# # # #         )
# # # #
# # # #     # --------------------------
# # # #     # Games
# # # #     # --------------------------
# # # #     def run_games(self) -> None:
# # # #         games_root = self.cfg["paths"]["games_root"]
# # # #         games = self._discover_games(games_root)
# # # #         if not games:
# # # #             self._toast("No games installed.")
# # # #             return
# # # #
# # # #         labels = [g["title"] for g in games]
# # # #         idx = self._simple_list_screen("Games", labels)
# # # #         if idx is None:
# # # #             return
# # # #
# # # #         g = games[idx]
# # # #         argv = g["exec"]
# # # #         cwd = g.get("cwd") or g["dir"]
# # # #         name = f"game_{g['id']}"
# # # #
# # # #         log_dir = self.cfg["logs"]["games_log_dir"]
# # # #         os.makedirs(log_dir, exist_ok=True)
# # # #         log_path = os.path.join(log_dir, f"{g['id']}.log")
# # # #
# # # #         idle_s = int(self.cfg["idle"]["external_seconds"])
# # # #         self._run_external(name=name, argv=argv, log_path=log_path, env=_with_x_env(os.environ.copy()), idle_seconds=idle_s, cwd=cwd)
# # # #
# # # #     def _discover_games(self, root: str) -> List[Dict[str, Any]]:
# # # #         out: List[Dict[str, Any]] = []
# # # #         try:
# # # #             dirs = sorted([d for d in os.listdir(root) if not d.startswith(".")])
# # # #         except Exception:
# # # #             return out
# # # #
# # # #         for d in dirs:
# # # #             gdir = os.path.join(root, d)
# # # #             mpath = os.path.join(gdir, "manifest.json")
# # # #             if not os.path.isdir(gdir) or not os.path.isfile(mpath):
# # # #                 continue
# # # #             try:
# # # #                 with open(mpath, "r") as f:
# # # #                     m = json.load(f)
# # # #                 gid = str(m.get("id", d)).strip()
# # # #                 title = str(m.get("title", gid)).strip()
# # # #                 execv = m.get("exec")
# # # #                 if not isinstance(execv, list) or not execv:
# # # #                     continue
# # # #                 out.append({"id": gid, "title": title, "exec": execv, "cwd": m.get("cwd"), "dir": gdir})
# # # #             except Exception:
# # # #                 continue
# # # #         return out
# # # #
# # # #     # --------------------------
# # # #     # Shutdown
# # # #     # --------------------------
# # # #     def run_shutdown(self) -> None:
# # # #         ok = self._confirm("Shutdown", "Power off the system?")
# # # #         if not ok:
# # # #             return
# # # #         self._run_external(
# # # #             name="shutdown",
# # # #             argv=["sudo", "-n", "/usr/sbin/shutdown", "-h", "now"],
# # # #             log_path=os.path.join(os.path.dirname(self.log_path), "shutdown.log"),
# # # #             env=_with_x_env(os.environ.copy()),
# # # #             idle_seconds=999999,
# # # #         )
# # # #
# # # #     # --------------------------
# # # #     # External runner
# # # #     # --------------------------
# # # #     def _run_external(
# # # #         self,
# # # #         name: str,
# # # #         argv: List[str],
# # # #         log_path: str,
# # # #         env: Optional[Dict[str, str]],
# # # #         idle_seconds: int,
# # # #         cwd: Optional[str] = None,
# # # #     ) -> int:
# # # #         mp: Optional[ManagedProcess] = None
# # # #         try:
# # # #             self._disable_screen_blanking()
# # # #             self._suspend_display(f"before_external:{name}")
# # # #             time.sleep(0.08)
# # # #
# # # #             log_line(self.log_path, f"Starting external: {name} argv={argv}")
# # # #             mp = spawn_process(name=name, argv=argv, log_path=log_path, env=env, cwd=cwd)
# # # #             self.active_child = mp.popen
# # # #
# # # #             threshold_ms = int(idle_seconds * 1000)
# # # #             hard_start = time.monotonic()
# # # #             xprintidle_missing_since: Optional[float] = None
# # # #
# # # #             baseline_idle_ms = read_xprintidle_ms()
# # # #             if baseline_idle_ms is None:
# # # #                 baseline_idle_ms = 0
# # # #
# # # #             while True:
# # # #                 rc = mp.popen.poll()
# # # #                 if rc is not None:
# # # #                     log_line(self.log_path, f"External exited: {name} rc={rc}")
# # # #                     return rc
# # # #
# # # #                 idle_now = read_xprintidle_ms()
# # # #                 GRACE_S = 3.0
# # # #
# # # #                 if idle_now is None:
# # # #                     if xprintidle_missing_since is None:
# # # #                         xprintidle_missing_since = time.monotonic()
# # # #                         log_line(self.log_path, f"WARNING: xprintidle unavailable in {name}; using hard timeout={idle_seconds}s")
# # # #                     if (time.monotonic() - xprintidle_missing_since) < GRACE_S:
# # # #                         time.sleep(0.25)
# # # #                         continue
# # # #                     elapsed = time.monotonic() - hard_start
# # # #                     if elapsed >= float(idle_seconds):
# # # #                         log_line(self.log_path, f"Hard timeout {elapsed:.1f}s >= {idle_seconds}s in {name} -> kill and return")
# # # #                         kill_process_group(mp.popen, self.log_path, name)
# # # #                         return 0
# # # #                 else:
# # # #                     delta = max(0, int(idle_now) - int(baseline_idle_ms))
# # # #                     if delta >= threshold_ms:
# # # #                         log_line(self.log_path, f"Idle since launch {delta}ms >= {threshold_ms}ms in {name} -> kill and return")
# # # #                         kill_process_group(mp.popen, self.log_path, name)
# # # #                         return 0
# # # #
# # # #                 time.sleep(0.25)
# # # #
# # # #         finally:
# # # #             self.active_child = None
# # # #             if mp and mp.log_handle:
# # # #                 try:
# # # #                     mp.log_handle.close()
# # # #                 except Exception:
# # # #                     pass
# # # #             self._reclaim_fullscreen(f"after_external:{name}")
# # # #
# # # #     # --------------------------
# # # #     # Simple list screens / confirm / toast
# # # #     # --------------------------
# # # #     def _simple_list_screen(self, title: str, items: List[str]) -> Optional[int]:
# # # #         if not items:
# # # #             return None
# # # #
# # # #         idx = 0
# # # #         last_input = time.time()
# # # #         idle_limit = max(10, int(self.cfg["idle"]["menu_seconds"]))
# # # #
# # # #         self._set_input_mode(grab=True, show_cursor=True)
# # # #         self._disable_screen_blanking()
# # # #
# # # #         while True:
# # # #             if (time.time() - last_input) >= idle_limit:
# # # #                 return None
# # # #
# # # #             visible = min(8, len(items))
# # # #             start = max(0, min(idx - visible // 2, len(items) - visible))
# # # #
# # # #             for ev in pygame.event.get():
# # # #                 if ev.type == pygame.QUIT:
# # # #                     raise SystemExit(0)
# # # #
# # # #                 if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN, pygame.FINGERDOWN):
# # # #                     last_input = time.time()
# # # #
# # # #                 if ev.type == pygame.KEYDOWN:
# # # #                     if ev.key in (pygame.K_ESCAPE, pygame.K_q):
# # # #                         return None
# # # #                     if ev.key == pygame.K_UP:
# # # #                         idx = max(0, idx - 1)
# # # #                     elif ev.key == pygame.K_DOWN:
# # # #                         idx = min(len(items) - 1, idx + 1)
# # # #                     elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
# # # #                         return idx
# # # #
# # # #                 if ev.type == pygame.MOUSEBUTTONDOWN:
# # # #                     hit = self._hit_test_list(ev.pos[0], ev.pos[1], start, visible)
# # # #                     if hit is not None:
# # # #                         return hit
# # # #
# # # #                 if ev.type == pygame.FINGERDOWN:
# # # #                     x = int(ev.x * self.W)
# # # #                     y = int(ev.y * self.H)
# # # #                     hit = self._hit_test_list(x, y, start, visible)
# # # #                     if hit is not None:
# # # #                         return hit
# # # #
# # # #             self._draw_list(title, items, idx)
# # # #             pygame.display.flip()
# # # #             self.clock.tick(self.fps)
# # # #
# # # #     def _draw_list(self, title: str, items: List[str], sel: int) -> None:
# # # #         self.screen.fill((0, 0, 0))
# # # #         t = self.font.render(title, True, (255, 255, 255))
# # # #         self.screen.blit(t, (self.W // 2 - t.get_width() // 2, 40))
# # # #
# # # #         row_h = 70
# # # #         gap = 12
# # # #         start_y = 140
# # # #         visible = min(8, len(items))
# # # #         start = max(0, min(sel - visible // 2, len(items) - visible))
# # # #
# # # #         for vi, i in enumerate(range(start, min(len(items), start + visible))):
# # # #             y = start_y + vi * (row_h + gap)
# # # #             rect = pygame.Rect(int(self.W * 0.10), y, int(self.W * 0.80), row_h)
# # # #             is_sel = (i == sel)
# # # #             pygame.draw.rect(self.screen, (50, 50, 50) if is_sel else (25, 25, 25), rect, border_radius=14)
# # # #             pygame.draw.rect(self.screen, (140, 140, 140), rect, width=2, border_radius=14)
# # # #             text = self.font_small.render(items[i], True, (255, 255, 255))
# # # #             self.screen.blit(text, (rect.x + 18, rect.centery - text.get_height() // 2))
# # # #
# # # #         hint = self.font_small.render("Tap an item. ESC/Q to go back.", True, (180, 180, 180))
# # # #         self.screen.blit(hint, (self.W // 2 - hint.get_width() // 2, self.H - 60))
# # # #
# # # #     def _hit_test_list(self, x: int, y: int, start: int, visible: int) -> Optional[int]:
# # # #         row_h = 70
# # # #         gap = 12
# # # #         start_y = 140
# # # #         for vi in range(visible):
# # # #             ry = start_y + vi * (row_h + gap)
# # # #             rect = pygame.Rect(int(self.W * 0.10), ry, int(self.W * 0.80), row_h)
# # # #             if rect.collidepoint(x, y):
# # # #                 return start + vi
# # # #         return None
# # # #
# # # #     def _confirm(self, title: str, msg: str) -> bool:
# # # #         yes_rect = pygame.Rect(int(self.W * 0.15), int(self.H * 0.60), int(self.W * 0.30), 90)
# # # #         no_rect = pygame.Rect(int(self.W * 0.55), int(self.H * 0.60), int(self.W * 0.30), 90)
# # # #
# # # #         self._set_input_mode(grab=True, show_cursor=True)
# # # #         self._disable_screen_blanking()
# # # #
# # # #         while True:
# # # #             for ev in pygame.event.get():
# # # #                 if ev.type == pygame.QUIT:
# # # #                     raise SystemExit(0)
# # # #                 if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_q):
# # # #                     return False
# # # #                 if ev.type == pygame.MOUSEBUTTONDOWN:
# # # #                     x, y = ev.pos
# # # #                     if yes_rect.collidepoint(x, y):
# # # #                         return True
# # # #                     if no_rect.collidepoint(x, y):
# # # #                         return False
# # # #                 if ev.type == pygame.FINGERDOWN:
# # # #                     x = int(ev.x * self.W)
# # # #                     y = int(ev.y * self.H)
# # # #                     if yes_rect.collidepoint(x, y):
# # # #                         return True
# # # #                     if no_rect.collidepoint(x, y):
# # # #                         return False
# # # #
# # # #             self.screen.fill((0, 0, 0))
# # # #             t = self.font.render(title, True, (255, 255, 255))
# # # #             self.screen.blit(t, (self.W // 2 - t.get_width() // 2, 80))
# # # #
# # # #             m = self.font_small.render(msg, True, (220, 220, 220))
# # # #             self.screen.blit(m, (self.W // 2 - m.get_width() // 2, 200))
# # # #
# # # #             pygame.draw.rect(self.screen, (30, 30, 30), yes_rect, border_radius=18)
# # # #             pygame.draw.rect(self.screen, (120, 120, 120), yes_rect, width=2, border_radius=18)
# # # #             yt = self.font.render("YES", True, (255, 255, 255))
# # # #             self.screen.blit(yt, (yes_rect.centerx - yt.get_width() // 2, yes_rect.centery - yt.get_height() // 2))
# # # #
# # # #             pygame.draw.rect(self.screen, (30, 30, 30), no_rect, border_radius=18)
# # # #             pygame.draw.rect(self.screen, (120, 120, 120), no_rect, width=2, border_radius=18)
# # # #             nt = self.font.render("NO", True, (255, 255, 255))
# # # #             self.screen.blit(nt, (no_rect.centerx - nt.get_width() // 2, no_rect.centery - nt.get_height() // 2))
# # # #
# # # #             pygame.display.flip()
# # # #             self.clock.tick(self.fps)
# # # #
# # # #     def _toast(self, msg: str, seconds: float = 1.6) -> None:
# # # #         t0 = time.time()
# # # #         self._set_input_mode(grab=True, show_cursor=False)
# # # #         self._disable_screen_blanking()
# # # #         while (time.time() - t0) < seconds:
# # # #             for ev in pygame.event.get():
# # # #                 if ev.type == pygame.QUIT:
# # # #                     raise SystemExit(0)
# # # #             self.screen.fill((0, 0, 0))
# # # #             m = self.font_small.render(msg, True, (255, 255, 255))
# # # #             self.screen.blit(m, (self.W // 2 - m.get_width() // 2, self.H // 2 - m.get_height() // 2))
# # # #             pygame.display.flip()
# # # #             self.clock.tick(self.fps)
# # # #
# # # #
# # # # def main() -> None:
# # # #     cfg = "/home/pi/sparc_lock/kiosk_config.yaml"
# # # #     ks = KioskShell(cfg)
# # # #     ks.run()
# # # #
# # # #
# # # # if __name__ == "__main__":
# # # #     main()
# # # #!/usr/bin/env python3
# # # import os
# # # import sys
# # # import time
# # # import yaml
# # # import signal
# # # import subprocess
# # # from typing import Optional, Dict, Any, List, Tuple
# # #
# # # os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
# # # os.environ.setdefault("SDL_VIDEODRIVER", "x11")
# # # os.environ.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")
# # # os.environ.setdefault("SDL_VIDEO_WINDOW_POS", "0,0")
# # # os.environ.setdefault("SDL_VIDEO_CENTERED", "0")
# # #
# # # import pygame  # noqa: E402
# # #
# # #
# # # CFG_PATH = "/home/pi/sparc_lock/kiosk_config.yaml"
# # # LOG_PATH = "/home/pi/sparc_lock/logs/kiosk_shell.log"
# # #
# # #
# # # def log(msg: str) -> None:
# # #     ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
# # #     line = f"[{ts}] {msg}\n"
# # #     try:
# # #         os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
# # #         with open(LOG_PATH, "a", buffering=1) as f:
# # #             f.write(line)
# # #     except Exception:
# # #         sys.stderr.write(line)
# # #
# # #
# # # def load_cfg(path: str) -> Dict[str, Any]:
# # #     cfg: Dict[str, Any] = {}
# # #     try:
# # #         with open(path, "r") as f:
# # #             cfg = yaml.safe_load(f) or {}
# # #     except Exception:
# # #         cfg = {}
# # #
# # #     cfg.setdefault("idle", {})
# # #     cfg.setdefault("feature_flags", {})
# # #     cfg.setdefault("paths", {})
# # #     cfg.setdefault("ui", {})
# # #     cfg.setdefault("security", {})
# # #
# # #     cfg["idle"].setdefault("menu_seconds", 120)
# # #     cfg["idle"].setdefault("external_seconds", 300)
# # #
# # #     cfg["paths"].setdefault("start_pi_mode_sh", "/home/pi/sparc_lock/start_pi_mode.sh")
# # #     cfg["paths"].setdefault("launch_solaris_sh", "/home/pi/sparc_lock/launch_solaris.sh")
# # #
# # #     cfg["feature_flags"].setdefault("enable_pi", True)
# # #     cfg["feature_flags"].setdefault("enable_solaris", True)
# # #     cfg["feature_flags"].setdefault("enable_power", True)
# # #
# # #     cfg["security"].setdefault("pi_pin", "1193")
# # #
# # #     cfg["ui"].setdefault("title", "SPARCstation")
# # #     cfg["ui"].setdefault("fps", 60)
# # #     cfg["ui"].setdefault("font_size", 54)
# # #     cfg["ui"].setdefault("small_font_size", 28)
# # #
# # #     return cfg
# # #
# # #
# # # class KioskShell:
# # #     def __init__(self, cfg: Dict[str, Any]):
# # #         self.cfg = cfg
# # #         self.title = self.cfg["ui"]["title"]
# # #         self.fps = int(self.cfg["ui"]["fps"])
# # #         self.clock = pygame.time.Clock()
# # #
# # #         self._shutting_down = False
# # #
# # #         signal.signal(signal.SIGTERM, self._sig_exit)
# # #         signal.signal(signal.SIGINT, self._sig_exit)
# # #
# # #         pygame.init()
# # #         pygame.font.init()
# # #         pygame.display.set_caption(self.title)
# # #
# # #         # One continuous pygame window for BOTH lock + menu (no window switching).
# # #         self.screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)
# # #         self.W, self.H = self.screen.get_size()
# # #
# # #         self.font = pygame.font.SysFont(None, int(self.cfg["ui"]["font_size"]))
# # #         self.font_small = pygame.font.SysFont(None, int(self.cfg["ui"]["small_font_size"]))
# # #
# # #         self._set_input_mode(grab=True, show_cursor=True)
# # #         self._black_frame()
# # #
# # #         # Ensure we can import puzzle_lock from this directory
# # #         here = os.path.dirname(os.path.abspath(__file__))
# # #         if here not in sys.path:
# # #             sys.path.insert(0, here)
# # #
# # #         import puzzle_lock  # local module
# # #         self.puzzle_lock = puzzle_lock
# # #
# # #     def _sig_exit(self, signum, frame):
# # #         self._shutting_down = True
# # #         log(f"Signal {signum} received; exiting")
# # #         try:
# # #             pygame.quit()
# # #         except Exception:
# # #             pass
# # #         raise SystemExit(0)
# # #
# # #     def _set_input_mode(self, grab: bool, show_cursor: bool) -> None:
# # #         try:
# # #             pygame.event.set_grab(bool(grab))
# # #         except Exception:
# # #             pass
# # #         try:
# # #             pygame.mouse.set_visible(bool(show_cursor))
# # #         except Exception:
# # #             pass
# # #         try:
# # #             pygame.event.pump()
# # #         except Exception:
# # #             pass
# # #
# # #     def _black_frame(self) -> None:
# # #         try:
# # #             self.screen.fill((0, 0, 0))
# # #             pygame.display.flip()
# # #         except Exception:
# # #             pass
# # #
# # #     # ---------------- Lock (shared window) ----------------
# # #     def run_lock(self) -> bool:
# # #         """
# # #         Runs the lock UI IN-PROCESS on the existing pygame display.
# # #         This eliminates the Openbox title-bar flash caused by switching
# # #         between separate pygame windows/processes.
# # #         """
# # #         log("Entering lock (shared-screen mode; no subprocess)")
# # #         self._set_input_mode(grab=True, show_cursor=True)
# # #         pygame.event.clear()
# # #         pygame.event.pump()
# # #         self._black_frame()
# # #
# # #         ok = bool(self.puzzle_lock.run_lock_shared(self.screen, self.clock))
# # #
# # #         pygame.event.clear()
# # #         pygame.event.pump()
# # #         self._black_frame()
# # #
# # #         log(f"Lock returned ok={ok}")
# # #         return ok
# # #
# # #     # ---------------- Menu ----------------
# # #     def _menu_items(self) -> List[Tuple[str, str]]:
# # #         items: List[Tuple[str, str]] = []
# # #         if bool(self.cfg["feature_flags"].get("enable_pi", True)):
# # #             items.append(("Pi Admin", "pi"))
# # #         if bool(self.cfg["feature_flags"].get("enable_solaris", True)):
# # #             items.append(("Solaris", "solaris"))
# # #         if bool(self.cfg["feature_flags"].get("enable_power", True)):
# # #             items.append(("Shutdown", "shutdown"))
# # #         items.append(("Re-lock", "relock"))
# # #         return items
# # #
# # #     def menu_loop(self) -> str:
# # #         items = self._menu_items()
# # #         sel = 0
# # #         last_input = time.time()
# # #         idle_s = int(self.cfg["idle"]["menu_seconds"])
# # #
# # #         self._set_input_mode(grab=True, show_cursor=True)
# # #
# # #         while True:
# # #             if (time.time() - last_input) >= idle_s:
# # #                 return "relock"
# # #
# # #             for ev in pygame.event.get():
# # #                 if ev.type == pygame.QUIT:
# # #                     raise SystemExit(0)
# # #
# # #                 if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.KEYDOWN,
# # #                                pygame.FINGERDOWN, pygame.FINGERMOTION):
# # #                     last_input = time.time()
# # #
# # #                 if ev.type == pygame.KEYDOWN:
# # #                     if ev.key in (pygame.K_ESCAPE, pygame.K_q):
# # #                         return "relock"
# # #                     if ev.key == pygame.K_UP:
# # #                         sel = max(0, sel - 1)
# # #                     elif ev.key == pygame.K_DOWN:
# # #                         sel = min(len(items) - 1, sel + 1)
# # #                     elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
# # #                         return items[sel][1]
# # #
# # #                 if ev.type == pygame.MOUSEBUTTONDOWN:
# # #                     hit = self._hit_menu(items, ev.pos[0], ev.pos[1])
# # #                     if hit:
# # #                         return hit
# # #
# # #                 if ev.type == pygame.FINGERDOWN:
# # #                     x = int(ev.x * self.W)
# # #                     y = int(ev.y * self.H)
# # #                     hit = self._hit_menu(items, x, y)
# # #                     if hit:
# # #                         return hit
# # #
# # #             self._draw_menu(items, sel)
# # #             pygame.display.flip()
# # #             self.clock.tick(self.fps)
# # #
# # #     def _draw_menu(self, items: List[Tuple[str, str]], sel: int) -> None:
# # #         self.screen.fill((0, 0, 0))
# # #
# # #         t = self.font.render(self.title, True, (255, 255, 255))
# # #         self.screen.blit(t, (self.W // 2 - t.get_width() // 2, 40))
# # #
# # #         btn_w = int(self.W * 0.70)
# # #         btn_h = 90
# # #         gap = 22
# # #         start_y = 160
# # #
# # #         for i, (label, _act) in enumerate(items):
# # #             x = self.W // 2 - btn_w // 2
# # #             y = start_y + i * (btn_h + gap)
# # #             rect = pygame.Rect(x, y, btn_w, btn_h)
# # #
# # #             is_sel = (i == sel)
# # #             bg = (55, 55, 55) if is_sel else (30, 30, 30)
# # #             border = (200, 200, 200) if is_sel else (120, 120, 120)
# # #
# # #             pygame.draw.rect(self.screen, bg, rect, border_radius=18)
# # #             pygame.draw.rect(self.screen, border, rect, width=2, border_radius=18)
# # #
# # #             txt = self.font.render(label, True, (240, 240, 240))
# # #             self.screen.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))
# # #
# # #         hint = self.font_small.render("Up/Down + Enter, or tap. Idle re-locks.", True, (180, 180, 180))
# # #         self.screen.blit(hint, (self.W // 2 - hint.get_width() // 2, self.H - 60))
# # #
# # #     def _hit_menu(self, items: List[Tuple[str, str]], x: int, y: int) -> Optional[str]:
# # #         btn_w = int(self.W * 0.70)
# # #         btn_h = 90
# # #         gap = 22
# # #         start_y = 160
# # #
# # #         for i, (_label, action) in enumerate(items):
# # #             rx = self.W // 2 - btn_w // 2
# # #             ry = start_y + i * (btn_h + gap)
# # #             rect = pygame.Rect(rx, ry, btn_w, btn_h)
# # #             if rect.collidepoint(x, y):
# # #                 return action
# # #         return None
# # #
# # #     # ---------------- External helpers (unchanged behavior) ----------------
# # #     def _run_external(self, argv: List[str], log_path: str, cwd: Optional[str] = None, idle_seconds: int = 300) -> int:
# # #         """
# # #         NOTE: This still spawns an external program and waits.
# # #         We do NOT tear down the pygame window; the external app should raise itself.
# # #         """
# # #         os.makedirs(os.path.dirname(log_path), exist_ok=True)
# # #         with open(log_path, "ab", buffering=0) as lf:
# # #             p = subprocess.Popen(
# # #                 argv,
# # #                 cwd=cwd,
# # #                 stdin=subprocess.DEVNULL,
# # #                 stdout=lf,
# # #                 stderr=subprocess.STDOUT,
# # #                 start_new_session=True,
# # #                 close_fds=True,
# # #             )
# # #
# # #         # Simple wait (idle handling for externals is handled elsewhere in your stack)
# # #         return p.wait()
# # #
# # #     def run(self) -> None:
# # #         log("kiosk_shell starting (shared lock window)")
# # #
# # #         while True:
# # #             # Always go to lock first
# # #             ok = self.run_lock()
# # #             if not ok:
# # #                 # lock aborted -> relock
# # #                 continue
# # #
# # #             choice = self.menu_loop()
# # #             log(f"Menu choice={choice}")
# # #
# # #             if choice == "relock":
# # #                 continue
# # #
# # #             if choice == "pi":
# # #                 sh = self.cfg["paths"]["start_pi_mode_sh"]
# # #                 self._run_external(["/bin/bash", sh], "/home/pi/sparc_lock/logs/pi_mode.log", cwd="/home/pi")
# # #                 continue
# # #
# # #             if choice == "solaris":
# # #                 sh = self.cfg["paths"]["launch_solaris_sh"]
# # #                 self._run_external([sh], "/home/pi/sparc_lock/logs/solaris_vnc.log", cwd="/home/pi")
# # #                 continue
# # #
# # #             if choice == "shutdown":
# # #                 self._run_external(["sudo", "-n", "/usr/sbin/shutdown", "-h", "now"],
# # #                                    "/home/pi/sparc_lock/logs/shutdown.log")
# # #                 return
# # #
# # #
# # # def main() -> None:
# # #     cfg = load_cfg(CFG_PATH)
# # #     KioskShell(cfg).run()
# # #
# # #
# # # if __name__ == "__main__":
# # #     main()
# # #!/usr/bin/env python3
# # import os
# # import sys
# # import time
# # import signal
# # from typing import Dict, Any
# #
# # # Keep pygame quiet and consistent in X11
# # os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
# # os.environ.setdefault("SDL_VIDEODRIVER", "x11")
# # os.environ.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")
# # os.environ.setdefault("SDL_VIDEO_WINDOW_POS", "0,0")
# # os.environ.setdefault("SDL_VIDEO_CENTERED", "0")
# #
# # import pygame  # noqa: E402
# #
# # CFG_PATH = "/home/pi/sparc_lock/kiosk_config.yaml"
# # LOG_PATH = "/home/pi/sparc_lock/logs/kiosk_shell.log"
# #
# #
# # def log(msg: str) -> None:
# #     ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
# #     line = f"[{ts}] {msg}\n"
# #     try:
# #         os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
# #         with open(LOG_PATH, "a", buffering=1) as f:
# #             f.write(line)
# #     except Exception:
# #         sys.stderr.write(line)
# #
# #
# # def load_cfg(path: str) -> Dict[str, Any]:
# #     cfg: Dict[str, Any] = {}
# #     try:
# #         import yaml
# #         with open(path, "r") as f:
# #             cfg = yaml.safe_load(f) or {}
# #     except Exception:
# #         cfg = {}
# #
# #     # defaults
# #     cfg.setdefault("feature_flags", {})
# #     cfg.setdefault("idle", {})
# #     cfg.setdefault("security", {})
# #     cfg.setdefault("ui", {})
# #     cfg.setdefault("paths", {})
# #
# #     cfg["idle"].setdefault("menu_seconds", 120)
# #
# #     cfg["security"].setdefault("pi_pin", "1193")
# #
# #     cfg["feature_flags"].setdefault("enable_pi", True)
# #     cfg["feature_flags"].setdefault("enable_solaris", True)
# #     cfg["feature_flags"].setdefault("enable_power", True)
# #     cfg["feature_flags"].setdefault("enable_reboot", True)
# #
# #     cfg["ui"].setdefault("title", "SPARCstation")
# #     cfg["ui"].setdefault("fps", 60)
# #
# #     # Optional: user-defined menu list (if you want exact old menu restored without code edits)
# #     # cfg["ui"]["post_unlock_menu"] = [
# #     #   {"label":"Solaris","action":"solaris"},
# #     #   {"label":"Pi Admin","action":"pi"},
# #     #   {"label":"Re-lock","action":"relock"},
# #     #   {"label":"Shutdown","action":"shutdown"},
# #     #   {"label":"Reboot","action":"reboot"},
# #     # ]
# #
# #     return cfg
# #
# #
# # def main() -> None:
# #     cfg = load_cfg(CFG_PATH)
# #
# #     # Import local puzzle_lock
# #     here = os.path.dirname(os.path.abspath(__file__))
# #     if here not in sys.path:
# #         sys.path.insert(0, here)
# #
# #     import puzzle_lock  # noqa: E402
# #
# #     shutting_down = False
# #
# #     def _sig_exit(signum, frame):
# #         nonlocal shutting_down
# #         shutting_down = True
# #         log(f"Signal {signum} received; exiting")
# #         try:
# #             pygame.quit()
# #         except Exception:
# #             pass
# #         raise SystemExit(0)
# #
# #     signal.signal(signal.SIGTERM, _sig_exit)
# #     signal.signal(signal.SIGINT, _sig_exit)
# #
# #     log("kiosk_shell starting (single-window shared pygame)")
# #
# #     pygame.init()
# #     pygame.font.init()
# #
# #     pygame.display.set_caption(str(cfg["ui"]["title"]))
# #
# #     # One window only. FULLSCREEN prevents WM decorations.
# #     screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
# #     clock = pygame.time.Clock()
# #
# #     # Run lock + puzzles + post-unlock menu in-process.
# #     # Return codes are used by start_lock.sh to launch modes.
# #     rc = puzzle_lock.run_kiosk_flow_shared(screen=screen, clock=clock, cfg=cfg)
# #
# #     log(f"Exiting kiosk_shell with rc={rc}")
# #
# #     try:
# #         pygame.quit()
# #     except Exception:
# #         pass
# #
# #     # Exit code is the contract with start_lock.sh
# #     sys.exit(int(rc))
# #
# #
# # if __name__ == "__main__":
# #     main()
# #!/usr/bin/env python3
# import os
# import sys
# import time
# import yaml
# import signal
# from typing import Optional, Dict, Any, List, Tuple
#
# os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
# os.environ.setdefault("SDL_VIDEODRIVER", "x11")
# os.environ.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")
# os.environ.setdefault("SDL_VIDEO_WINDOW_POS", "0,0")
# os.environ.setdefault("SDL_VIDEO_CENTERED", "0")
#
# import pygame  # noqa: E402
#
# CFG_PATH = "/home/pi/sparc_lock/kiosk_config.yaml"
# LOG_PATH = "/home/pi/sparc_lock/logs/kiosk_shell.log"
#
#
# # Return codes expected by start_lock.sh
# RC_RELOCK = 0
# RC_PI_MODE = 42
# RC_SOLARIS = 43
# RC_SHUTDOWN = 44
# RC_REBOOT = 45
#
#
# def log(msg: str) -> None:
#     ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
#     line = f"[{ts}] {msg}\n"
#     try:
#         os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
#         with open(LOG_PATH, "a", buffering=1) as f:
#             f.write(line)
#     except Exception:
#         sys.stderr.write(line)
#
#
# def load_cfg(path: str) -> Dict[str, Any]:
#     cfg: Dict[str, Any] = {}
#     try:
#         with open(path, "r") as f:
#             cfg = yaml.safe_load(f) or {}
#     except Exception:
#         cfg = {}
#
#     cfg.setdefault("idle", {})
#     cfg.setdefault("feature_flags", {})
#     cfg.setdefault("paths", {})
#     cfg.setdefault("ui", {})
#     cfg.setdefault("security", {})
#
#     cfg["idle"].setdefault("menu_seconds", 120)
#     cfg["idle"].setdefault("external_seconds", 300)
#
#     cfg["paths"].setdefault("start_pi_mode_sh", "/home/pi/sparc_lock/start_pi_mode.sh")
#     cfg["paths"].setdefault("launch_solaris_sh", "/home/pi/sparc_lock/launch_solaris.sh")
#
#     cfg["feature_flags"].setdefault("enable_pi", True)
#     cfg["feature_flags"].setdefault("enable_solaris", True)
#     cfg["feature_flags"].setdefault("enable_power", True)
#
#     # Lock behavior (consumed by puzzle_lock via cfg we pass in)
#     cfg["feature_flags"].setdefault("unlock_levels", 1)                 # N square-puzzle clears to unlock menu
#     cfg["feature_flags"].setdefault("unlock_mode", "square")            # square | jigsaw | mixed (lock screen)
#     cfg["feature_flags"].setdefault("enable_endless_jigsaw", True)      # jigsaw button is endless levels by default
#
#     cfg["security"].setdefault("pi_pin", "1193")
#
#     cfg["ui"].setdefault("title", "SPARCstation")
#     cfg["ui"].setdefault("fps", 60)
#     cfg["ui"].setdefault("font_size", 54)
#     cfg["ui"].setdefault("small_font_size", 28)
#
#     return cfg
#
#
# class KioskShell:
#     def __init__(self, cfg: Dict[str, Any]):
#         self.cfg = cfg
#         self.title = str(self.cfg["ui"]["title"])
#         self.fps = int(self.cfg["ui"]["fps"])
#         self.clock = pygame.time.Clock()
#
#         self._shutting_down = False
#
#         signal.signal(signal.SIGTERM, self._sig_exit)
#         signal.signal(signal.SIGINT, self._sig_exit)
#
#         pygame.init()
#         pygame.font.init()
#         pygame.display.set_caption(self.title)
#
#         # One continuous pygame window for BOTH lock + menu
#         self.screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)
#         self.W, self.H = self.screen.get_size()
#
#         self.font = pygame.font.SysFont(None, int(self.cfg["ui"]["font_size"]))
#         self.font_small = pygame.font.SysFont(None, int(self.cfg["ui"]["small_font_size"]))
#
#         self._set_input_mode(grab=True, show_cursor=True)
#         self._black_frame()
#
#         # Ensure we can import puzzle_lock from this directory
#         here = os.path.dirname(os.path.abspath(__file__))
#         if here not in sys.path:
#             sys.path.insert(0, here)
#
#         import puzzle_lock  # local module
#         self.puzzle_lock = puzzle_lock
#
#     def _sig_exit(self, signum, frame):
#         self._shutting_down = True
#         log(f"Signal {signum} received; exiting")
#         try:
#             pygame.quit()
#         except Exception:
#             pass
#         raise SystemExit(0)
#
#     def _set_input_mode(self, grab: bool, show_cursor: bool) -> None:
#         try:
#             pygame.event.set_grab(bool(grab))
#         except Exception:
#             pass
#         try:
#             pygame.mouse.set_visible(bool(show_cursor))
#         except Exception:
#             pass
#         try:
#             pygame.event.pump()
#         except Exception:
#             pass
#
#     def _black_frame(self) -> None:
#         try:
#             self.screen.fill((0, 0, 0))
#             pygame.display.flip()
#         except Exception:
#             pass
#
#     def _exit_with_rc(self, rc: int) -> None:
#         # Clear frame so the user doesn't see stale UI behind external launch
#         try:
#             pygame.event.clear()
#             self._black_frame()
#         except Exception:
#             pass
#         try:
#             pygame.quit()
#         except Exception:
#             pass
#         raise SystemExit(rc)
#
#     # ---------------- Lock (shared window) ----------------
#     def run_lock(self) -> bool:
#         log("Entering lock (shared-screen mode)")
#         self._set_input_mode(grab=True, show_cursor=True)
#         pygame.event.clear()
#         pygame.event.pump()
#         self._black_frame()
#
#         ok = bool(self.puzzle_lock.run_lock_shared(self.screen, self.clock, cfg=self.cfg))
#
#         pygame.event.clear()
#         pygame.event.pump()
#         self._black_frame()
#
#         log(f"Lock returned ok={ok}")
#         return ok
#
#     # ---------------- Menu ----------------
#     def _menu_items(self) -> List[Tuple[str, str]]:
#         items: List[Tuple[str, str]] = []
#         if bool(self.cfg["feature_flags"].get("enable_pi", True)):
#             items.append(("Pi Admin", "pi"))
#         if bool(self.cfg["feature_flags"].get("enable_solaris", True)):
#             items.append(("Solaris", "solaris"))
#         if bool(self.cfg["feature_flags"].get("enable_power", True)):
#             items.append(("Reboot", "reboot"))
#             items.append(("Shutdown", "shutdown"))
#         items.append(("Re-lock", "relock"))
#         return items
#
#     def menu_loop(self) -> str:
#         items = self._menu_items()
#         sel = 0
#         last_input = time.time()
#         idle_s = int(self.cfg["idle"]["menu_seconds"])
#
#         self._set_input_mode(grab=True, show_cursor=True)
#
#         while True:
#             if (time.time() - last_input) >= idle_s:
#                 return "relock"
#
#             for ev in pygame.event.get():
#                 if ev.type == pygame.QUIT:
#                     self._exit_with_rc(0)
#
#                 if ev.type in (
#                     pygame.MOUSEBUTTONDOWN,
#                     pygame.MOUSEMOTION,
#                     pygame.KEYDOWN,
#                     pygame.FINGERDOWN,
#                     pygame.FINGERMOTION,
#                 ):
#                     last_input = time.time()
#
#                 if ev.type == pygame.KEYDOWN:
#                     if ev.key in (pygame.K_ESCAPE, pygame.K_q):
#                         return "relock"
#                     if ev.key == pygame.K_UP:
#                         sel = max(0, sel - 1)
#                     elif ev.key == pygame.K_DOWN:
#                         sel = min(len(items) - 1, sel + 1)
#                     elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
#                         return items[sel][1]
#
#                 if ev.type == pygame.MOUSEBUTTONDOWN:
#                     hit = self._hit_menu(items, ev.pos[0], ev.pos[1])
#                     if hit:
#                         return hit
#
#                 if ev.type == pygame.FINGERDOWN:
#                     x = int(ev.x * self.W)
#                     y = int(ev.y * self.H)
#                     hit = self._hit_menu(items, x, y)
#                     if hit:
#                         return hit
#
#             self._draw_menu(items, sel)
#             pygame.display.flip()
#             self.clock.tick(self.fps)
#
#     def _draw_menu(self, items: List[Tuple[str, str]], sel: int) -> None:
#         self.screen.fill((0, 0, 0))
#
#         t = self.font.render(self.title, True, (255, 255, 255))
#         self.screen.blit(t, (self.W // 2 - t.get_width() // 2, 40))
#
#         btn_w = int(self.W * 0.70)
#         btn_h = 90
#         gap = 22
#         start_y = 160
#
#         mx, my = pygame.mouse.get_pos()
#
#         for i, (label, _act) in enumerate(items):
#             x = self.W // 2 - btn_w // 2
#             y = start_y + i * (btn_h + gap)
#             rect = pygame.Rect(x, y, btn_w, btn_h)
#
#             hover = rect.collidepoint((mx, my))
#             is_sel = (i == sel) or hover
#
#             bg = (55, 55, 55) if is_sel else (30, 30, 30)
#             border = (220, 220, 220) if is_sel else (120, 120, 120)
#
#             pygame.draw.rect(self.screen, bg, rect, border_radius=18)
#             pygame.draw.rect(self.screen, border, rect, width=2, border_radius=18)
#
#             txt = self.font.render(label, True, (240, 240, 240))
#             self.screen.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))
#
#         hint = self.font_small.render("Up/Down + Enter, or tap. Idle re-locks.", True, (180, 180, 180))
#         self.screen.blit(hint, (self.W // 2 - hint.get_width() // 2, self.H - 60))
#
#     def _hit_menu(self, items: List[Tuple[str, str]], x: int, y: int) -> Optional[str]:
#         btn_w = int(self.W * 0.70)
#         btn_h = 90
#         gap = 22
#         start_y = 160
#
#         for i, (_label, action) in enumerate(items):
#             rx = self.W // 2 - btn_w // 2
#             ry = start_y + i * (btn_h + gap)
#             rect = pygame.Rect(rx, ry, btn_w, btn_h)
#             if rect.collidepoint(x, y):
#                 return action
#         return None
#
#     def run(self) -> None:
#         log("kiosk_shell starting")
#
#         while True:
#             ok = self.run_lock()
#             if not ok:
#                 continue
#
#             choice = self.menu_loop()
#             log(f"Menu choice={choice}")
#
#             if choice == "relock":
#                 continue
#
#             if choice == "pi":
#                 self._exit_with_rc(RC_PI_MODE)
#
#             if choice == "solaris":
#                 self._exit_with_rc(RC_SOLARIS)
#
#             if choice == "shutdown":
#                 self._exit_with_rc(RC_SHUTDOWN)
#
#             if choice == "reboot":
#                 self._exit_with_rc(RC_REBOOT)
#
#
# def main() -> None:
#     cfg = load_cfg(CFG_PATH)
#     KioskShell(cfg).run()
#
#
# if __name__ == "__main__":
#     main()
#!/usr/bin/env python3
import os
import sys
import time
import math
import yaml
import signal
from typing import Optional, Dict, Any, List, Tuple

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "x11")
os.environ.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")
os.environ.setdefault("SDL_VIDEO_WINDOW_POS", "0,0")
os.environ.setdefault("SDL_VIDEO_CENTERED", "0")

import pygame  # noqa: E402

CFG_PATH = "/home/pi/sparc_lock/kiosk_config.yaml"
LOG_PATH = "/home/pi/sparc_lock/logs/kiosk_shell.log"

# Return codes expected by start_lock.sh
RC_RELOCK = 0
RC_PI_MODE = 42
RC_SOLARIS = 43
RC_SHUTDOWN = 44
RC_REBOOT = 45
RC_GAMES = 46
RC_MEDIA = 47


def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    line = f"[{ts}] {msg}\n"
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a", buffering=1) as f:
            f.write(line)
    except Exception:
        sys.stderr.write(line)


def load_cfg(path: str) -> Dict[str, Any]:
    cfg: Dict[str, Any] = {}
    try:
        with open(path, "r") as f:
            cfg = yaml.safe_load(f) or {}
    except Exception:
        cfg = {}

    cfg.setdefault("idle", {})
    cfg.setdefault("feature_flags", {})
    cfg.setdefault("paths", {})
    cfg.setdefault("ui", {})
    cfg.setdefault("security", {})

    cfg["idle"].setdefault("menu_seconds", 120)
    cfg["idle"].setdefault("external_seconds", 300)

    cfg["paths"].setdefault("start_pi_mode_sh", "/home/pi/sparc_lock/start_pi_mode.sh")
    cfg["paths"].setdefault("launch_solaris_sh", "/home/pi/sparc_lock/launch_solaris.sh")
    cfg["paths"].setdefault("launch_games_sh", "/home/pi/sparc_lock/launch_games.sh")
    cfg["paths"].setdefault("launch_media_sh", "/home/pi/sparc_lock/launch_media.sh")

    cfg["feature_flags"].setdefault("enable_pi", True)
    cfg["feature_flags"].setdefault("enable_solaris", True)
    cfg["feature_flags"].setdefault("enable_power", True)
    cfg["feature_flags"].setdefault("enable_games", True)
    cfg["feature_flags"].setdefault("enable_media", True)

    # Lock behavior (consumed by puzzle_lock via cfg we pass in)
    cfg["feature_flags"].setdefault("unlock_levels", 1)
    cfg["feature_flags"].setdefault("unlock_mode", "square")        # square | jigsaw | mixed (lock screen)
    cfg["feature_flags"].setdefault("enable_endless_jigsaw", True)

    cfg["security"].setdefault("pi_pin", "1193")

    cfg["ui"].setdefault("title", "SPARCstation")
    cfg["ui"].setdefault("fps", 60)
    cfg["ui"].setdefault("font_size", 54)
    cfg["ui"].setdefault("small_font_size", 28)

    return cfg


class KioskShell:
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg
        self.title = str(self.cfg["ui"]["title"])
        self.fps = int(self.cfg["ui"]["fps"])
        self.clock = pygame.time.Clock()

        self._shutting_down = False

        signal.signal(signal.SIGTERM, self._sig_exit)
        signal.signal(signal.SIGINT, self._sig_exit)

        pygame.init()
        pygame.font.init()
        pygame.display.set_caption(self.title)

        # One continuous pygame window for BOTH lock + menu
        self.screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)
        self.W, self.H = self.screen.get_size()

        self.font = pygame.font.SysFont(None, int(self.cfg["ui"]["font_size"]))
        self.font_small = pygame.font.SysFont(None, int(self.cfg["ui"]["small_font_size"]))
        self.font_hint = pygame.font.SysFont(None, max(18, int(self.cfg["ui"]["small_font_size"]) - 6))

        self._set_input_mode(grab=True, show_cursor=True)
        self._black_frame()

        # Ensure we can import puzzle_lock from this directory
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.insert(0, here)

        import puzzle_lock  # local module
        self.puzzle_lock = puzzle_lock

        # Cached alpha surfaces for nicer buttons
        self._btn_layer = pygame.Surface((self.W, self.H), pygame.SRCALPHA)

    def _sig_exit(self, signum, frame):
        self._shutting_down = True
        log(f"Signal {signum} received; exiting")
        try:
            pygame.quit()
        except Exception:
            pass
        raise SystemExit(0)

    def _set_input_mode(self, grab: bool, show_cursor: bool) -> None:
        try:
            pygame.event.set_grab(bool(grab))
        except Exception:
            pass
        try:
            pygame.mouse.set_visible(bool(show_cursor))
        except Exception:
            pass
        try:
            pygame.event.pump()
        except Exception:
            pass

    def _black_frame(self) -> None:
        try:
            self.screen.fill((0, 0, 0))
            pygame.display.flip()
        except Exception:
            pass

    def _exit_with_rc(self, rc: int) -> None:
        # Clear frame so the user doesn't see stale UI behind external launch
        try:
            pygame.event.clear()
            self._black_frame()
        except Exception:
            pass
        try:
            pygame.quit()
        except Exception:
            pass
        raise SystemExit(rc)

    # ---------------- Lock (shared window) ----------------
    def run_lock(self) -> bool:
        log("Entering lock (shared-screen mode)")
        self._set_input_mode(grab=True, show_cursor=True)
        pygame.event.clear()
        pygame.event.pump()
        self._black_frame()

        ok = bool(self.puzzle_lock.run_lock_shared(self.screen, self.clock, cfg=self.cfg))

        pygame.event.clear()
        pygame.event.pump()
        self._black_frame()

        log(f"Lock returned ok={ok}")
        return ok

    # ---------------- Menu ----------------
    def _menu_items(self) -> List[Tuple[str, str]]:
        items: List[Tuple[str, str]] = []

        # New buttons requested
        if bool(self.cfg["feature_flags"].get("enable_games", True)):
            items.append(("Games", "games"))
        if bool(self.cfg["feature_flags"].get("enable_media", True)):
            items.append(("Media", "media"))

        # Existing buttons
        if bool(self.cfg["feature_flags"].get("enable_solaris", True)):
            items.append(("Solaris", "solaris"))
        if bool(self.cfg["feature_flags"].get("enable_pi", True)):
            items.append(("Pi Admin", "pi"))
        if bool(self.cfg["feature_flags"].get("enable_power", True)):
            items.append(("Reboot", "reboot"))
            items.append(("Shutdown", "shutdown"))
        items.append(("Re-lock", "relock"))
        return items

    def _accent_for(self, action: str) -> Tuple[int, int, int]:
        return {
            "games": (120, 200, 255),
            "media": (200, 160, 255),
            "solaris": (255, 200, 120),
            "pi": (120, 255, 190),
            "reboot": (255, 170, 170),
            "shutdown": (255, 130, 130),
            "relock": (200, 200, 200),
        }.get(action, (200, 200, 200))

    def _menu_layout(self, items: List[Tuple[str, str]]) -> List[Tuple[pygame.Rect, str, str]]:
        n = len(items)
        if n <= 0:
            return []

        cols = 2 if self.W < 1400 else 3
        cols = min(cols, n)
        rows = int(math.ceil(n / cols))

        gap = 26
        btn_h = 118
        max_area_w = int(self.W * 0.84)
        btn_w = (max_area_w - gap * (cols - 1)) // cols
        btn_w = max(320, min(btn_w, 560))

        area_w = cols * btn_w + (cols - 1) * gap
        start_x = (self.W - area_w) // 2

        # Vertical positioning
        top_reserved = 170
        bottom_reserved = 90
        total_h = rows * btn_h + (rows - 1) * gap
        avail_h = self.H - top_reserved - bottom_reserved
        start_y = top_reserved + max(0, (avail_h - total_h) // 2)

        out: List[Tuple[pygame.Rect, str, str]] = []
        for idx, (label, action) in enumerate(items):
            r = idx // cols
            c = idx % cols
            x = start_x + c * (btn_w + gap)
            y = start_y + r * (btn_h + gap)
            out.append((pygame.Rect(x, y, btn_w, btn_h), label, action))
        return out

    def menu_loop(self) -> str:
        items = self._menu_items()
        layout = self._menu_layout(items)
        sel = 0
        last_input = time.time()
        idle_s = int(self.cfg["idle"]["menu_seconds"])

        self._set_input_mode(grab=True, show_cursor=True)

        while True:
            if (time.time() - last_input) >= idle_s:
                return "relock"

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self._exit_with_rc(0)

                if ev.type in (
                    pygame.MOUSEBUTTONDOWN,
                    pygame.MOUSEMOTION,
                    pygame.KEYDOWN,
                    pygame.FINGERDOWN,
                    pygame.FINGERMOTION,
                ):
                    last_input = time.time()

                if ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_ESCAPE, pygame.K_q):
                        return "relock"

                    cols = 2 if self.W < 1400 else 3
                    cols = min(cols, max(1, len(layout)))

                    if ev.key == pygame.K_LEFT:
                        sel = max(0, sel - 1)
                    elif ev.key == pygame.K_RIGHT:
                        sel = min(len(layout) - 1, sel + 1)
                    elif ev.key == pygame.K_UP:
                        sel = max(0, sel - cols)
                    elif ev.key == pygame.K_DOWN:
                        sel = min(len(layout) - 1, sel + cols)
                    elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        return layout[sel][2]

                if ev.type == pygame.MOUSEBUTTONDOWN:
                    hit = self._hit_menu(layout, ev.pos[0], ev.pos[1])
                    if hit:
                        return hit

                if ev.type == pygame.FINGERDOWN:
                    x = int(ev.x * self.W)
                    y = int(ev.y * self.H)
                    hit = self._hit_menu(layout, x, y)
                    if hit:
                        return hit

            self._draw_menu(layout, sel)
            pygame.display.flip()
            self.clock.tick(self.fps)

    def _draw_menu_button(self, rect: pygame.Rect, label: str, action: str, active: bool, selected: bool) -> None:
        accent = self._accent_for(action)
        a = 255

        # Shadow
        shadow = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 120), shadow.get_rect(), border_radius=22)
        self.screen.blit(shadow, (rect.x, rect.y + (5 if not active else 3)))

        # Main body (alpha)
        body = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        base = (20, 20, 20, 235) if not (active or selected) else (32, 32, 32, 245)
        pygame.draw.rect(body, base, body.get_rect(), border_radius=22)

        # Accent strip
        strip_rect = pygame.Rect(16, rect.h - 12, rect.w - 32, 5)
        pygame.draw.rect(body, (accent[0], accent[1], accent[2], 220), strip_rect, border_radius=4)

        # Border
        border_col = (220, 220, 220, 160) if (active or selected) else (160, 160, 160, 110)
        pygame.draw.rect(body, border_col, body.get_rect(), width=2, border_radius=22)

        self.screen.blit(body, rect.topleft)

        # Text
        txt = self.font.render(label, True, (245, 245, 245))
        self.screen.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))

    def _draw_menu(self, layout: List[Tuple[pygame.Rect, str, str]], sel: int) -> None:
        self.screen.fill((0, 0, 0))

        title = self.font.render(self.title, True, (255, 255, 255))
        self.screen.blit(title, (self.W // 2 - title.get_width() // 2, 44))

        subtitle = self.font_small.render("Select a mode", True, (200, 200, 200))
        self.screen.blit(subtitle, (self.W // 2 - subtitle.get_width() // 2, 98))

        mx, my = pygame.mouse.get_pos()
        for i, (rect, label, action) in enumerate(layout):
            hover = rect.collidepoint((mx, my))
            selected = (i == sel)
            self._draw_menu_button(rect, label, action, active=hover, selected=selected)

        hint = self.font_hint.render("Arrow keys + Enter, or tap. Idle re-locks.", True, (170, 170, 170))
        self.screen.blit(hint, (self.W // 2 - hint.get_width() // 2, self.H - 54))

    def _hit_menu(self, layout: List[Tuple[pygame.Rect, str, str]], x: int, y: int) -> Optional[str]:
        for rect, _label, action in layout:
            if rect.collidepoint(x, y):
                return action
        return None

    def run(self) -> None:
        log("kiosk_shell starting")

        while True:
            ok = self.run_lock()
            if not ok:
                continue

            choice = self.menu_loop()
            log(f"Menu choice={choice}")

            if choice == "relock":
                continue

            if choice == "pi":
                self._exit_with_rc(RC_PI_MODE)

            if choice == "solaris":
                self._exit_with_rc(RC_SOLARIS)

            if choice == "games":
                self._exit_with_rc(RC_GAMES)

            if choice == "media":
                self._exit_with_rc(RC_MEDIA)

            if choice == "shutdown":
                self._exit_with_rc(RC_SHUTDOWN)

            if choice == "reboot":
                self._exit_with_rc(RC_REBOOT)


def main() -> None:
    cfg = load_cfg(CFG_PATH)
    KioskShell(cfg).run()


if __name__ == "__main__":
    main()
