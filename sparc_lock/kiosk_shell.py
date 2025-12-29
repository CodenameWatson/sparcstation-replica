
#!/usr/bin/env python3
import os
import sys
import time
import json
import yaml
import signal
import subprocess
from dataclasses import dataclass
from typing import Optional, TextIO, List, Dict, Any, Tuple
import fcntl
import pygame

# ---- Environment hardening (X11-only kiosk) ----
def _runtime_dir_for_uid(uid: int) -> str:
    return os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{uid}"

def _force_x11_env_base() -> None:
    uid = os.getuid()
    os.environ.setdefault("DISPLAY", ":0")
    os.environ.setdefault("XAUTHORITY", "/home/pi/.Xauthority")
    os.environ.setdefault("XDG_RUNTIME_DIR", _runtime_dir_for_uid(uid))
    os.environ.setdefault("SDL_VIDEODRIVER", "x11")
    os.environ.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")
    # Avoid SDL choosing Wayland/KMS paths
    os.environ.pop("WAYLAND_DISPLAY", None)
    os.environ.pop("WAYLAND_SOCKET", None)

_force_x11_env_base()

def ensure_singleton(lock_path: Optional[str] = None) -> int:
    """
    Prevent multiple kiosk_shell instances. Prefer per-user runtime dir over /tmp
    (more reliable if you ever started as root via sudo and created root-owned locks).
    """
    uid = os.getuid()
    rdir = _runtime_dir_for_uid(uid)
    try:
        os.makedirs(rdir, exist_ok=True)
    except Exception:
        # Fall back to /tmp if runtime dir isn't available
        rdir = "/tmp"

    if lock_path is None:
        lock_path = os.path.join(rdir, "sparc_kiosk_shell.lock")

    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        sys.exit(0)

    os.ftruncate(fd, 0)
    os.write(fd, f"{os.getpid()}\n".encode())
    return fd

# ------------------------------
# Utilities: logging
# ------------------------------
def log_line(path: str, msg: str) -> None:
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    line = f"[{ts}] {msg}\n"
    try:
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(path, "a", buffering=1) as f:
            f.write(line)
    except Exception:
        sys.stderr.write(line)

# ------------------------------
# Utilities: xprintidle
# ------------------------------
def read_xprintidle_ms(xprintidle_bin: str = "xprintidle") -> Optional[int]:
    env = _with_x_env(os.environ.copy())
    try:
        out = subprocess.check_output([xprintidle_bin], text=True, env=env, timeout=0.5).strip()
        return int(out)
    except Exception:
        return None

# ------------------------------
# Utilities: process management
# ------------------------------
@dataclass
class ManagedProcess:
    name: str
    popen: subprocess.Popen
    log_handle: Optional[TextIO] = None

def kill_process_group(p: subprocess.Popen, log_path: str, name: str) -> None:
    if p.poll() is not None:
        return

    try:
        pgid = os.getpgid(p.pid)
    except Exception:
        pgid = None

    def _wait_brief(deadline_s: float) -> bool:
        end = time.monotonic() + deadline_s
        while time.monotonic() < end:
            if p.poll() is not None:
                return True
            time.sleep(0.05)
        return p.poll() is not None

    if not pgid or pgid <= 0:
        try:
            log_line(log_path, f"Killing {name}: SIGTERM pid={p.pid} (no pgid)")
            p.terminate()
        except Exception:
            pass
        if _wait_brief(2.0):
            return
        try:
            log_line(log_path, f"Killing {name}: SIGKILL pid={p.pid} (no pgid)")
            p.kill()
        except Exception:
            pass
        try:
            p.wait(timeout=1.0)
        except Exception:
            pass
        return

    try:
        log_line(log_path, f"Killing {name}: SIGTERM pgid={pgid}")
        os.killpg(pgid, signal.SIGTERM)
    except Exception:
        pass
    if _wait_brief(2.0):
        return
    try:
        log_line(log_path, f"Killing {name}: SIGKILL pgid={pgid}")
        os.killpg(pgid, signal.SIGKILL)
    except Exception:
        pass
    try:
        p.wait(timeout=1.0)
    except Exception:
        pass

def _with_x_env(env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    e = dict(env) if env else os.environ.copy()
    uid = os.getuid()

    e.setdefault("DISPLAY", os.environ.get("DISPLAY", ":0"))
    e.setdefault("XAUTHORITY", os.environ.get("XAUTHORITY", "/home/pi/.Xauthority"))
    e.setdefault("XDG_RUNTIME_DIR", os.environ.get("XDG_RUNTIME_DIR", _runtime_dir_for_uid(uid)))

    # Force SDL to X11 to avoid KMS/DRM CRTC + pageflip errors
    e.setdefault("SDL_VIDEODRIVER", "x11")
    e.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")

    # Avoid Wayland selection
    e.pop("WAYLAND_DISPLAY", None)
    e.pop("WAYLAND_SOCKET", None)

    return e

def spawn_process(
    name: str,
    argv: List[str],
    log_path: Optional[str],
    env: Optional[Dict[str, str]] = None,
    cwd: Optional[str] = None,
) -> ManagedProcess:
    log_handle = None
    if log_path:
        d = os.path.dirname(log_path)
        if d:
            os.makedirs(d, exist_ok=True)
        log_handle = open(log_path, "ab", buffering=0)

    stdout_target = log_handle if log_handle else subprocess.DEVNULL

    p = subprocess.Popen(
        argv,
        env=_with_x_env(env),
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=stdout_target,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        close_fds=True,
    )
    return ManagedProcess(name=name, popen=p, log_handle=log_handle)

# ------------------------------
# Kiosk Shell
# ------------------------------
class KioskShell:
    def __init__(self, cfg_path: str):
        self.cfg_path = cfg_path
        self.cfg = self._load_cfg(cfg_path)
        self.log_path = self.cfg["logs"]["shell_log"]

        self.active_child: Optional[subprocess.Popen] = None
        self._singleton_fd = ensure_singleton()
        self.in_external = False

        # VM (QEMU) management
        self.vm_pidfile = self.cfg["vm"]["pidfile"]
        self.vm_start_cmd = self.cfg["vm"]["start_cmd"]
        self.vm_cwd = self.cfg["vm"]["cwd"]
        self.vm_autostart = bool(self.cfg["vm"]["enable_autostart"])
        self.vm_startup_grace_s = float(self.cfg["vm"]["startup_grace_s"])

        # PINs
        self.pi_pin = str(self.cfg["security"]["pi_pin"])

        def _handle_term(signum, frame):
            log_line(self.log_path, f"Signal {signum} received; stopping active child and exiting")
            p = self.active_child
            if p and p.poll() is None:
                kill_process_group(p, self.log_path, "active_child")
            try:
                pygame.quit()
            except Exception:
                pass
            raise SystemExit(0)

        signal.signal(signal.SIGTERM, _handle_term)
        signal.signal(signal.SIGINT, _handle_term)

        pygame.init()
        try:
            pygame.font.init()  
        except Exception:
            pass 
        self._init_display_with_retry()

    # --------------------------
    # Display lifecycle
    # --------------------------
    def _init_display_with_retry(self, retries: int = 40, sleep_s: float = 0.25) -> None:
        last_err: Optional[Exception] = None
        for _ in range(retries):
            try:
                pygame.display.init()
                try:
                    if not pygame.font.get_init():
                        pygame.font.init()
                except Exception:
                    pass
                self.init_display()
                return
            except Exception as e:
                last_err = e
                time.sleep(sleep_s)
        log_line(self.log_path, f"FATAL: unable to init display after retries: {last_err}")
        raise last_err if last_err else RuntimeError("unable to init display")

    def init_display(self) -> None:
        ui = self.cfg.get("ui", {})
        self.title = ui.get("title", "SPARCstation")
        try:
            if not pygame.font.get_init():
                pygame.font.init()
        except Exception:
            pass

        pygame.display.set_caption(self.title)
        # keep default fullscreen; env forces X11 driver
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.W, self.H = self.screen.get_size()

        self.font = pygame.font.SysFont(None, int(ui.get("font_size", 54)))
        self.font_small = pygame.font.SysFont(None, int(ui.get("small_font_size", 28)))

        self.fps = int(ui.get("fps", 60))
        self.clock = pygame.time.Clock()

        self._set_input_mode(grab=True, show_cursor=True)

        self.screen.fill((0, 0, 0))
        pygame.display.flip()
        pygame.event.pump()

    def _suspend_display(self, reason: str) -> None:
        try:
            self._set_input_mode(grab=False, show_cursor=False)
        except Exception:
            pass
        try:
            if pygame.display.get_init():
                self.screen.fill((0, 0, 0))
                pygame.display.flip()
        except Exception:
            pass
        try:
            pygame.display.quit()
        except Exception:
            pass
        log_line(self.log_path, f"Suspend display ({reason})")

    def _reclaim_fullscreen(self, reason: str = "return") -> None:
        try:
            pygame.event.clear()
        except Exception:
            pass
        try:
            pygame.display.quit()
        except Exception:
            pass

        try:
            pygame.display.init()
            self.init_display()
            log_line(self.log_path, f"Reclaimed fullscreen ({reason})")
        except Exception as e:
            log_line(self.log_path, f"ERROR reclaiming fullscreen ({reason}): {e}")
            self._init_display_with_retry()

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

    # --------------------------
    # Config
    # --------------------------
    def _load_cfg(self, path: str) -> Dict[str, Any]:
        with open(path, "r") as f:
            cfg = yaml.safe_load(f) or {}

        cfg.setdefault("feature_flags", {})
        cfg.setdefault("idle", {})
        cfg.setdefault("ui", {})
        cfg.setdefault("paths", {})
        cfg.setdefault("logs", {})
        cfg.setdefault("vm", {})
        cfg.setdefault("security", {})

        cfg["idle"].setdefault("menu_seconds", 120)
        cfg["idle"].setdefault("external_seconds", 300)

        cfg["logs"].setdefault("shell_log", "/home/pi/sparc_lock/logs/kiosk_shell.log")
        cfg["logs"].setdefault("mpv_log", "/home/pi/sparc_lock/logs/mpv.log")
        cfg["logs"].setdefault("solaris_log", "/home/pi/sparc_lock/logs/solaris_vnc.log")
        cfg["logs"].setdefault("games_log_dir", "/home/pi/sparc_lock/logs/games")

        cfg["paths"].setdefault("lock_py", "/home/pi/sparc_lock/puzzle_lock.py")
        cfg["paths"].setdefault("launch_solaris_sh", "/home/pi/sparc_lock/launch_solaris.sh")
        cfg["paths"].setdefault("mpv_input_conf", "/home/pi/sparc_lock/mpv.input.conf")
        cfg["paths"].setdefault("media_images", "/home/pi/sparc_media/images")
        cfg["paths"].setdefault("media_music", "/home/pi/sparc_media/music")
        cfg["paths"].setdefault("media_videos", "/home/pi/sparc_media/videos")
        cfg["paths"].setdefault("games_root", "/home/pi/sparc_games/installed")

        # VM defaults
        cfg["vm"].setdefault("enable_autostart", True)
        cfg["vm"].setdefault("pidfile", "/home/pi/sparc_vm/qemu-sparc.pid")
        cfg["vm"].setdefault("start_cmd", ["/home/pi/sparc_vm/run_sol8.sh"])
        cfg["vm"].setdefault("cwd", "/home/pi/sparc_vm")
        cfg["vm"].setdefault("startup_grace_s", 1.0)

        # Feature flags (menu composition)
        cfg["feature_flags"].setdefault("enable_pi", True)
        cfg["feature_flags"].setdefault("enable_solaris", True)
        cfg["feature_flags"].setdefault("enable_games", True)
        cfg["feature_flags"].setdefault("enable_media", True)
        cfg["feature_flags"].setdefault("enable_power", True)

        # Security
        cfg["security"].setdefault("pi_pin", "1193")

        return cfg

    # --------------------------
    # VM management (QEMU)
    # --------------------------
    def _vm_is_running(self) -> bool:
        try:
            with open(self.vm_pidfile, "r") as f:
                pid_str = f.read().strip()
            if not pid_str:
                return False
            pid = int(pid_str)
            os.kill(pid, 0)
            return True
        except FileNotFoundError:
            return False
        except ProcessLookupError:
            try:
                os.remove(self.vm_pidfile)
            except Exception:
                pass
            return False
        except Exception:
            return False

    def _ensure_vm_running(self) -> None:
        if not self.vm_autostart:
            return
        if self._vm_is_running():
            return
        try:
            log_line(self.log_path, f"Starting VM: {self.vm_start_cmd}")
            subprocess.Popen(
                self.vm_start_cmd,
                cwd=self.vm_cwd,
                env=_with_x_env(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            time.sleep(self.vm_startup_grace_s)
        except Exception as e:
            log_line(self.log_path, f"WARNING: failed to start VM: {e}")

    # --------------------------
    # PIN UI (unchanged)
    # --------------------------
    def _pin_prompt(self, title: str, msg: str, expected_pin: str) -> bool:
        pin_input = ""
        err_msg = ""
        err_t0 = 0.0

        keys = ["1","2","3","4","5","6","7","8","9","C","0","OK"]
        cols, rows = 3, 4
        cancel_rect = pygame.Rect(16, 16, 170, 52)

        def draw():
            self.screen.fill((0, 0, 0))
            overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 210))
            self.screen.blit(overlay, (0, 0))

            pygame.draw.rect(self.screen, (40,40,40), cancel_rect, border_radius=14)
            pygame.draw.rect(self.screen, (200,200,200), cancel_rect, 2, border_radius=14)
            ct = self.font_small.render("CANCEL", True, (255,255,255))
            self.screen.blit(ct, (cancel_rect.centerx - ct.get_width()//2, cancel_rect.centery - ct.get_height()//2))

            t = self.font.render(title, True, (255,255,255))
            self.screen.blit(t, (self.W//2 - t.get_width()//2, 90))

            m = self.font_small.render(msg, True, (220,220,220))
            self.screen.blit(m, (self.W//2 - m.get_width()//2, 150))

            masked = "*" * len(pin_input)
            e = self.font.render(masked, True, (255,255,0))
            self.screen.blit(e, (self.W//2 - e.get_width()//2, 190))

            pad_w = min(520, int(self.W * 0.42))
            pad_h = min(520, int(self.H * 0.62))
            pad_x = (self.W - pad_w) // 2
            pad_y = (self.H - pad_h) // 2 + 40
            cell_w = pad_w // cols
            cell_h = pad_h // rows

            pygame.draw.rect(self.screen, (35,35,35), pygame.Rect(pad_x, pad_y, pad_w, pad_h), border_radius=16)
            rects = []
            for r in range(rows):
                for c in range(cols):
                    x = pad_x + c*cell_w + 10
                    y = pad_y + r*cell_h + 10
                    rects.append(pygame.Rect(x, y, cell_w-20, cell_h-20))

            mx, my = pygame.mouse.get_pos()
            for i, r in enumerate(rects):
                hot = r.collidepoint(mx, my)
                bg = (70,70,70) if hot else (55,55,55)
                pygame.draw.rect(self.screen, bg, r, border_radius=12)
                pygame.draw.rect(self.screen, (170,170,170), r, 2, border_radius=12)
                kt = self.font.render(keys[i], True, (255,255,255))
                self.screen.blit(kt, (r.centerx - kt.get_width()//2, r.centery - kt.get_height()//2))

            if err_msg and (time.time() - err_t0) < 2.0:
                em = self.font_small.render(err_msg, True, (255,90,90))
                self.screen.blit(em, (self.W//2 - em.get_width()//2, pad_y + pad_h + 18))

            tip = self.font_small.render("Enter=submit, Backspace=delete, OK=submit. Esc/CANCEL=back.", True, (200,200,200))
            self.screen.blit(tip, (self.W//2 - tip.get_width()//2, pad_y + pad_h + 52))

            pygame.display.flip()

        def hit_key(x: int, y: int) -> Optional[str]:
            pad_w = min(520, int(self.W * 0.42))
            pad_h = min(520, int(self.H * 0.62))
            pad_x = (self.W - pad_w) // 2
            pad_y = (self.H - pad_h) // 2 + 40
            cell_w = pad_w // cols
            cell_h = pad_h // rows

            idx = 0
            for r in range(rows):
                for c in range(cols):
                    rx = pad_x + c*cell_w + 10
                    ry = pad_y + r*cell_h + 10
                    rect = pygame.Rect(rx, ry, cell_w-20, cell_h-20)
                    if rect.collidepoint(x, y):
                        return keys[idx]
                    idx += 1
            return None

        self._set_input_mode(grab=True, show_cursor=True)
        pygame.event.clear()
        pygame.event.pump()

        while True:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    raise SystemExit(0)

                if ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_ESCAPE,):
                        return False
                    if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if pin_input == expected_pin:
                            return True
                        err_msg = "Incorrect PIN"
                        err_t0 = time.time()
                        pin_input = ""
                    elif ev.key == pygame.K_BACKSPACE:
                        pin_input = pin_input[:-1]
                    else:
                        ch = ev.unicode
                        if ch.isdigit() and len(pin_input) < 12:
                            pin_input += ch

                if ev.type == pygame.MOUSEBUTTONDOWN:
                    x, y = ev.pos
                    if cancel_rect.collidepoint(x, y):
                        return False
                    k = hit_key(x, y)
                    if k:
                        if k == "C":
                            pin_input = ""
                        elif k == "OK":
                            if pin_input == expected_pin:
                                return True
                            err_msg = "Incorrect PIN"
                            err_t0 = time.time()
                            pin_input = ""
                        else:
                            if len(pin_input) < 12:
                                pin_input += k

                if ev.type == pygame.FINGERDOWN:
                    x = int(ev.x * self.W)
                    y = int(ev.y * self.H)
                    if cancel_rect.collidepoint(x, y):
                        return False
                    k = hit_key(x, y)
                    if k:
                        if k == "C":
                            pin_input = ""
                        elif k == "OK":
                            if pin_input == expected_pin:
                                return True
                            err_msg = "Incorrect PIN"
                            err_t0 = time.time()
                            pin_input = ""
                        else:
                            if len(pin_input) < 12:
                                pin_input += k

            draw()
            self.clock.tick(self.fps)

    # --------------------------
    # Main loop (unchanged control flow)
    # --------------------------
    def run(self) -> None:
        log_line(self.log_path, "kiosk_shell starting")
        self._ensure_vm_running()

        while True:
            rc = self.run_lock()
            if rc != 0:
                log_line(self.log_path, f"Lock returned rc={rc} -> restarting lock")
                continue

            choice = self.menu_loop()
            log_line(self.log_path, f"Menu returned choice={choice}")

            if choice == "relock":
                continue

            if choice == "pi":
                ok = self._pin_prompt("PI DESKTOP", "Enter PIN to exit kiosk and show Pi desktop", self.pi_pin)
                if ok:
                    log_line(self.log_path, "Pi PIN accepted -> exiting kiosk_shell rc=42")
                    self._suspend_display("exit_to_pi")
                    raise SystemExit(42)
                else:
                    log_line(self.log_path, "Pi PIN canceled/failed -> back to menu")
                    continue

            if choice == "solaris":
                self.run_solaris()
                continue

            if choice == "games":
                self.run_games()
                continue

            if choice == "media":
                self.run_media()
                continue

            if choice == "shutdown":
                self.run_shutdown()
                continue

    # --------------------------
    # Lock runner
    # --------------------------
    def run_lock(self) -> int:
        lock_py = self.cfg["paths"]["lock_py"]
        env = _with_x_env(os.environ.copy())

        log_line(self.log_path, "Starting lock (puzzle_lock.py)")
        mp: Optional[ManagedProcess] = None

        self._suspend_display("before_lock")

        try:
            mp = spawn_process(
                name="lock",
                argv=["python3", "-u", lock_py],
                log_path=os.path.join(os.path.dirname(self.log_path), "lock_child.log"),
                env=env,
                cwd="/home/pi/sparc_lock",
            )
            self.active_child = mp.popen
            rc = mp.popen.wait()
            log_line(self.log_path, f"Lock exited rc={rc}")
            return rc
        finally:
            self.active_child = None
            if mp and mp.log_handle:
                try:
                    mp.log_handle.close()
                except Exception:
                    pass
            self._reclaim_fullscreen("after_lock")

    # --------------------------
    # Menu UI (unchanged)
    # --------------------------
    def menu_loop(self) -> str:
        flags = self.cfg.get("feature_flags", {})
        enable_pi = bool(flags.get("enable_pi", True))
        enable_solaris = bool(flags.get("enable_solaris", True))
        enable_games = bool(flags.get("enable_games", True))
        enable_media = bool(flags.get("enable_media", True))
        enable_power = bool(flags.get("enable_power", True))

        items: List[Tuple[str, str]] = []
        if enable_pi:
            items.append(("Pi", "pi"))
        if enable_solaris:
            items.append(("Solaris", "solaris"))
        if enable_games:
            items.append(("Games", "games"))
        if enable_media:
            items.append(("Media Library", "media"))
        if enable_power:
            items.append(("Shutdown", "shutdown"))
        items.append(("Re-lock", "relock"))

        idle_limit = int(self.cfg["idle"]["menu_seconds"])
        last_input = time.time()
        sel = 0

        self._set_input_mode(grab=True, show_cursor=True)
        try:
            pygame.event.clear()
            pygame.event.pump()
        except Exception:
            pass

        while True:
            if (time.time() - last_input) >= idle_limit:
                log_line(self.log_path, f"Menu idle >= {idle_limit}s -> relock")
                return "relock"

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    raise SystemExit(0)

                if ev.type in (
                    pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION,
                    pygame.KEYDOWN,
                    pygame.FINGERDOWN, pygame.FINGERMOTION
                ):
                    last_input = time.time()

                if ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_ESCAPE, pygame.K_q):
                        return "relock"
                    if ev.key == pygame.K_UP:
                        sel = max(0, sel - 1)
                    elif ev.key == pygame.K_DOWN:
                        sel = min(len(items) - 1, sel + 1)
                    elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        action = items[sel][1]
                        log_line(self.log_path, f"Menu key select -> {action}")
                        return action

                if ev.type == pygame.MOUSEBUTTONDOWN:
                    hit = self._hit_test_menu(items, ev.pos[0], ev.pos[1])
                    if hit:
                        log_line(self.log_path, f"Menu click -> {hit}")
                        return hit

                if ev.type == pygame.FINGERDOWN:
                    x = int(ev.x * self.W)
                    y = int(ev.y * self.H)
                    hit = self._hit_test_menu(items, x, y)
                    if hit:
                        log_line(self.log_path, f"Menu touch -> {hit}")
                        return hit

            self._draw_menu(items, sel=sel)
            pygame.display.flip()
            self.clock.tick(self.fps)

    def _draw_menu(self, items: List[Tuple[str, str]], sel: int = 0) -> None:
        self.screen.fill((0, 0, 0))

        title = self.font.render(self.title, True, (255, 255, 255))
        self.screen.blit(title, (self.W // 2 - title.get_width() // 2, 40))

        btn_w = int(self.W * 0.70)
        btn_h = 90
        gap = 22
        start_y = 160

        for i, (label, _action) in enumerate(items):
            x = self.W // 2 - btn_w // 2
            y = start_y + i * (btn_h + gap)
            rect = pygame.Rect(x, y, btn_w, btn_h)

            is_sel = (i == sel)
            bg = (55, 55, 55) if is_sel else (30, 30, 30)
            border = (200, 200, 200) if is_sel else (120, 120, 120)

            pygame.draw.rect(self.screen, bg, rect, border_radius=18)
            pygame.draw.rect(self.screen, border, rect, width=2, border_radius=18)

            text = self.font.render(label, True, (240, 240, 240))
            self.screen.blit(text, (
                rect.centerx - text.get_width() // 2,
                rect.centery - text.get_height() // 2
            ))

        hint = self.font_small.render("Click/tap or use ?/? + Enter. Idle returns to lock.", True, (180, 180, 180))
        self.screen.blit(hint, (self.W // 2 - hint.get_width() // 2, self.H - 60))

    def _hit_test_menu(self, items: List[Tuple[str, str]], x: int, y: int) -> Optional[str]:
        btn_w = int(self.W * 0.70)
        btn_h = 90
        gap = 22
        start_y = 160
        for i, (_label, action) in enumerate(items):
            rx = self.W // 2 - btn_w // 2
            ry = start_y + i * (btn_h + gap)
            rect = pygame.Rect(rx, ry, btn_w, btn_h)
            if rect.collidepoint(x, y):
                return action
        return None
 # --------------------------
    # Solaris/media/games/shutdown/external unchanged from your version
    # --------------------------
    def run_solaris(self) -> int:
        log_line(self.log_path, "run_solaris() entered")
        if self.in_external:
            log_line(self.log_path, "Ignoring Solaris launch: external already active")
            return 0

        self._ensure_vm_running()
        self.in_external = True
        try:
            sh = self.cfg["paths"]["launch_solaris_sh"]
            idle_s = int(self.cfg["idle"]["external_seconds"])
            env = _with_x_env(os.environ.copy())
            env["SPARC_IDLE_MANAGED"] = "1"
            return self._run_external(
                name="solaris",
                argv=[sh],
                log_path=self.cfg["logs"]["solaris_log"],
                env=env,
                idle_seconds=idle_s,
            )
        finally:
            self.in_external = False
            self._reclaim_fullscreen("after_solaris")

    def run_media(self) -> None:
        roots = [
            ("Images", self.cfg["paths"]["media_images"]),
            ("Music", self.cfg["paths"]["media_music"]),
            ("Videos", self.cfg["paths"]["media_videos"]),
        ]
        choice = self._simple_list_screen("Media Library", [r[0] for r in roots])
        if choice is None:
            return
        _label, path = roots[choice]
        self._browse_and_play(path)

    def _browse_and_play(self, folder: str) -> None:
        try:
            files = sorted([f for f in os.listdir(folder) if not f.startswith(".")])
        except Exception:
            self._toast(f"Cannot open: {folder}")
            return

        idx = self._simple_list_screen(os.path.basename(folder), files)
        if idx is None:
            return

        target = os.path.join(folder, files[idx])
        self._play_with_mpv(target)

    def _play_with_mpv(self, path: str) -> None:
        idle_s = int(self.cfg["idle"]["external_seconds"])
        mpv_conf = self.cfg["paths"]["mpv_input_conf"]
        argv = ["mpv", "--fs", "--input-conf=" + mpv_conf, path]
        self._run_external(
            name="mpv",
            argv=argv,
            log_path=self.cfg["logs"]["mpv_log"],
            env=_with_x_env(),
            idle_seconds=idle_s
        )

    def run_games(self) -> None:
        games_root = self.cfg["paths"]["games_root"]
        games = self._discover_games(games_root)
        if not games:
            self._toast("No games installed.")
            return

        labels = [g["title"] for g in games]
        idx = self._simple_list_screen("Games", labels)
        if idx is None:
            return

        g = games[idx]
        argv = g["exec"]
        cwd = g.get("cwd") or g["dir"]
        name = f"game_{g['id']}"

        log_dir = self.cfg["logs"]["games_log_dir"]
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"{g['id']}.log")

        idle_s = int(self.cfg["idle"]["external_seconds"])
        self._run_external(name=name, argv=argv, log_path=log_path, env=_with_x_env(), idle_seconds=idle_s, cwd=cwd)

    def _discover_games(self, root: str) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        try:
            dirs = sorted([d for d in os.listdir(root) if not d.startswith(".")])
        except Exception:
            return out

        for d in dirs:
            gdir = os.path.join(root, d)
            mpath = os.path.join(gdir, "manifest.json")
            if not os.path.isdir(gdir) or not os.path.isfile(mpath):
                continue
            try:
                with open(mpath, "r") as f:
                    m = json.load(f)
                gid = str(m.get("id", d)).strip()
                title = str(m.get("title", gid)).strip()
                execv = m.get("exec")
                if not isinstance(execv, list) or not execv:
                    continue
                out.append({"id": gid, "title": title, "exec": execv, "cwd": m.get("cwd"), "dir": gdir})
            except Exception:
                continue
        return out

    def run_shutdown(self) -> None:
        ok = self._confirm("Shutdown", "Power off the system?")
        if not ok:
            return
        self._run_external(
            name="shutdown",
            argv=["sudo", "-n", "/usr/sbin/shutdown", "-h", "now"],
            log_path=os.path.join(os.path.dirname(self.log_path), "shutdown.log"),
            env=_with_x_env(),
            idle_seconds=999999,
        )

    def _run_external(
        self,
        name: str,
        argv: List[str],
        log_path: str,
        env: Optional[Dict[str, str]],
        idle_seconds: int,
        cwd: Optional[str] = None,
    ) -> int:
        mp: Optional[ManagedProcess] = None
        try:
            self._disable_screen_blanking()
            self._release_pygame_completely(f"before_external:{name}")

            log_line(self.log_path, f"Starting external: {name} argv={argv}")
            mp = spawn_process(name=name, argv=argv, log_path=log_path, env=env, cwd=cwd)
            self.active_child = mp.popen

            threshold_ms = int(idle_seconds * 1000)
            hard_start = time.monotonic()
            xprintidle_missing_since: Optional[float] = None

            while True:
                rc = mp.popen.poll()
                if rc is not None:
                    log_line(self.log_path, f"External exited: {name} rc={rc}")
                    return rc

                idle_ms = read_xprintidle_ms()
                GRACE_S = 3.0

                if idle_ms is None:
                    if xprintidle_missing_since is None:
                        xprintidle_missing_since = time.monotonic()
                        log_line(self.log_path, f"WARNING: xprintidle unavailable in {name}; using hard timeout={idle_seconds}s")
                    if (time.monotonic() - xprintidle_missing_since) < GRACE_S:
                        time.sleep(0.25)
                        continue
                    elapsed = time.monotonic() - hard_start
                    if elapsed >= float(idle_seconds):
                        log_line(self.log_path, f"Hard timeout {elapsed:.1f}s >= {idle_seconds}s in {name} -> kill and return")
                        kill_process_group(mp.popen, self.log_path, name)
                        return 0
                else:
                    if idle_ms >= threshold_ms:
                        log_line(self.log_path, f"Idle {idle_ms}ms >= {threshold_ms}ms in {name} -> kill and return")
                        kill_process_group(mp.popen, self.log_path, name)
                        return 0

                time.sleep(0.25)

        finally:
            self.active_child = None
            if mp and mp.log_handle:
                try:
                    mp.log_handle.close()
                except Exception:
                    pass
            self._reclaim_fullscreen(f"after_external:{name}")

    def _simple_list_screen(self, title: str, items: List[str]) -> Optional[int]:
        if not items:
            return None

        idx = 0
        last_input = time.time()
        idle_limit = max(10, int(self.cfg["idle"]["menu_seconds"]))

        self._set_input_mode(grab=True, show_cursor=True)
        self._disable_screen_blanking()

        while True:
            if (time.time() - last_input) >= idle_limit:
                return None

            visible = min(8, len(items))
            start = max(0, min(idx - visible // 2, len(items) - visible))

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    raise SystemExit(0)

                if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN, pygame.FINGERDOWN):
                    last_input = time.time()

                if ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_ESCAPE, pygame.K_q):
                        return None
                    if ev.key == pygame.K_UP:
                        idx = max(0, idx - 1)
                    elif ev.key == pygame.K_DOWN:
                        idx = min(len(items) - 1, idx + 1)
                    elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        return idx

                if ev.type == pygame.MOUSEBUTTONDOWN:
                    hit = self._hit_test_list(ev.pos[0], ev.pos[1], start, visible)
                    if hit is not None:
                        return hit

                if ev.type == pygame.FINGERDOWN:
                    x = int(ev.x * self.W)
                    y = int(ev.y * self.H)
                    hit = self._hit_test_list(x, y, start, visible)
                    if hit is not None:
                        return hit

            self._draw_list(title, items, idx)
            pygame.display.flip()
            self.clock.tick(self.fps)

    def _draw_list(self, title: str, items: List[str], sel: int) -> None:
        self.screen.fill((0, 0, 0))
        t = self.font.render(title, True, (255, 255, 255))
        self.screen.blit(t, (self.W // 2 - t.get_width() // 2, 40))

        row_h = 70
        gap = 12
        start_y = 140
        visible = min(8, len(items))
        start = max(0, min(sel - visible // 2, len(items) - visible))

        for vi, i in enumerate(range(start, min(len(items), start + visible))):
            y = start_y + vi * (row_h + gap)
            rect = pygame.Rect(int(self.W * 0.10), y, int(self.W * 0.80), row_h)
            is_sel = (i == sel)
            pygame.draw.rect(self.screen, (50, 50, 50) if is_sel else (25, 25, 25), rect, border_radius=14)
            pygame.draw.rect(self.screen, (140, 140, 140), rect, width=2, border_radius=14)
            text = self.font_small.render(items[i], True, (255, 255, 255))
            self.screen.blit(text, (rect.x + 18, rect.centery - text.get_height() // 2))

        hint = self.font_small.render("Tap an item. ESC/Q to go back.", True, (180, 180, 180))
        self.screen.blit(hint, (self.W // 2 - hint.get_width() // 2, self.H - 60))

    def _hit_test_list(self, x: int, y: int, start: int, visible: int) -> Optional[int]:
        row_h = 70
        gap = 12
        start_y = 140
        for vi in range(visible):
            ry = start_y + vi * (row_h + gap)
            rect = pygame.Rect(int(self.W * 0.10), ry, int(self.W * 0.80), row_h)
            if rect.collidepoint(x, y):
                return start + vi
        return None

    def _confirm(self, title: str, msg: str) -> bool:
        yes_rect = pygame.Rect(int(self.W * 0.15), int(self.H * 0.60), int(self.W * 0.30), 90)
        no_rect = pygame.Rect(int(self.W * 0.55), int(self.H * 0.60), int(self.W * 0.30), 90)

        self._set_input_mode(grab=True, show_cursor=True)
        self._disable_screen_blanking()

        while True:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    raise SystemExit(0)
                if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_q):
                    return False
                if ev.type == pygame.MOUSEBUTTONDOWN:
                    x, y = ev.pos
                    if yes_rect.collidepoint(x, y):
                        return True
                    if no_rect.collidepoint(x, y):
                        return False
                if ev.type == pygame.FINGERDOWN:
                    x = int(ev.x * self.W)
                    y = int(ev.y * self.H)
                    if yes_rect.collidepoint(x, y):
                        return True
                    if no_rect.collidepoint(x, y):
                        return False

            self.screen.fill((0, 0, 0))
            t = self.font.render(title, True, (255, 255, 255))
            self.screen.blit(t, (self.W // 2 - t.get_width() // 2, 80))

            m = self.font_small.render(msg, True, (220, 220, 220))
            self.screen.blit(m, (self.W // 2 - m.get_width() // 2, 200))

            pygame.draw.rect(self.screen, (30, 30, 30), yes_rect, border_radius=18)
            pygame.draw.rect(self.screen, (120, 120, 120), yes_rect, width=2, border_radius=18)
            yt = self.font.render("YES", True, (255, 255, 255))
            self.screen.blit(yt, (yes_rect.centerx - yt.get_width() // 2, yes_rect.centery - yt.get_height() // 2))

            pygame.draw.rect(self.screen, (30, 30, 30), no_rect, border_radius=18)
            pygame.draw.rect(self.screen, (120, 120, 120), no_rect, width=2, border_radius=18)
            nt = self.font.render("NO", True, (255, 255, 255))
            self.screen.blit(nt, (no_rect.centerx - nt.get_width() // 2, no_rect.centery - nt.get_height() // 2))

            pygame.display.flip()
            self.clock.tick(self.fps)

    def _toast(self, msg: str, seconds: float = 1.6) -> None:
        t0 = time.time()
        self._set_input_mode(grab=True, show_cursor=False)
        self._disable_screen_blanking()
        while (time.time() - t0) < seconds:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    raise SystemExit(0)
            self.screen.fill((0, 0, 0))
            m = self.font_small.render(msg, True, (255, 255, 255))
            self.screen.blit(m, (self.W // 2 - m.get_width() // 2, self.H // 2 - m.get_height() // 2))
            pygame.display.flip()
            self.clock.tick(self.fps)



def main():
    cfg = "/home/pi/sparc_lock/kiosk_config.yaml"
    ks = KioskShell(cfg)
    ks.run()


if __name__ == "__main__":
    main()