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

def ensure_singleton(lock_path="/tmp/sparc_kiosk_shell.lock") -> int:
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o644)
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
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", buffering=1) as f:
            f.write(line)
    except Exception:
        # last resort: stderr
        sys.stderr.write(line)


# ------------------------------
# Utilities: xprintidle
# ------------------------------

def read_xprintidle_ms(xprintidle_bin: str = "xprintidle") -> Optional[int]:
    env = os.environ.copy()
    env["DISPLAY"] = env.get("DISPLAY", ":0")
    env["XAUTHORITY"] = env.get("XAUTHORITY", "/home/pi/.Xauthority")

    try:
        out = subprocess.check_output(
            [xprintidle_bin],
            text=True,
            env=env,
            timeout=0.5,   # prevents rare stalls from blocking your loop
        ).strip()
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

    # If no pgid, fall back to terminating the single process, but still escalate.
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

    # Normal path: kill the whole process group.
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

def spawn_process(
    name: str,
    argv: List[str],
    log_path: Optional[str],
    env: Optional[Dict[str, str]] = None,
    cwd: Optional[str] = None
) -> ManagedProcess:
    log_handle = None
    stdout_target = subprocess.DEVNULL

    if log_path:
        d = os.path.dirname(log_path)
        if d:
            os.makedirs(d, exist_ok=True)
        log_handle = open(log_path, "ab", buffering=0)


    p = subprocess.Popen(
        argv,
        env=env,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=stdout_target,
        stderr=subprocess.STDOUT,
        start_new_session=True,   # replaces preexec_fn=os.setsid
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



        def _handle_term(signum, frame):
            log_line(self.log_path, f"Signal {signum} received; stopping active child and exiting")
            p = self.active_child
            if p and p.poll() is None:
                kill_process_group(p, self.log_path, "active_child")
            raise SystemExit(0)

        signal.signal(signal.SIGTERM, _handle_term)
        signal.signal(signal.SIGINT, _handle_term)


        
        pygame.init()
        pygame.mouse.set_visible(False)

        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.W, self.H = self.screen.get_size()

        ui = self.cfg.get("ui", {})
        self.font = pygame.font.SysFont(None, int(ui.get("font_size", 54)))
        self.font_small = pygame.font.SysFont(None, int(ui.get("small_font_size", 28)))

        self.fps = int(ui.get("fps", 60))
        self.clock = pygame.time.Clock()

        self.title = ui.get("title", "SPARCstation")

    def _load_cfg(self, path: str) -> Dict[str, Any]:
        with open(path, "r") as f:
            cfg = yaml.safe_load(f) or {}
        # minimal validation + defaults
        cfg.setdefault("feature_flags", {})
        cfg.setdefault("idle", {})
        cfg.setdefault("ui", {})
        cfg.setdefault("paths", {})
        cfg.setdefault("logs", {})
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
        return cfg

    # --------------------------
    # Main state machine
    # --------------------------
    def run(self) -> None:
        log_line(self.log_path, "kiosk_shell starting")
        while True:
            rc = self.run_lock()
            if rc == 42:
                # propagate admin request to session watchdog
                log_line(self.log_path, "Lock returned rc=42 -> exiting kiosk_shell rc=42 for PI MODE")
                raise SystemExit(42)
            if rc != 0:
                log_line(self.log_path, f"Lock returned rc={rc} -> restarting lock")
                continue

            # unlocked
            choice = self.menu_loop()
            if choice == "relock":
                continue
            elif choice == "solaris":
                self.run_solaris()
            elif choice == "games":
                self.run_games()
            elif choice == "media":
                self.run_media()
            elif choice == "shutdown":
                self.run_shutdown()
            else:
                # safety
                continue

    # --------------------------
    # Lock
    # --------------------------
    def run_lock(self) -> int:
        lock_py = self.cfg["paths"]["lock_py"]
        env = os.environ.copy()
        env["SPARC_POST_UNLOCK"] = "menu"  # required for lock->menu behavior

        log_line(self.log_path, "Starting lock (puzzle_lock.py)")
        mp = None
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
                try: mp.log_handle.close()
                except Exception: pass

    # --------------------------
    # Menu UI
    # --------------------------
    def menu_loop(self) -> str:
        flags = self.cfg.get("feature_flags", {})
        enable_media = bool(flags.get("enable_media", True))
        enable_games = bool(flags.get("enable_games", True))
        enable_power = bool(flags.get("enable_power", False))

        items = [("Solaris", "solaris")]
        if enable_games:
            items.append(("Games", "games"))
        if enable_media:
            items.append(("Media Library", "media"))
        if enable_power:
            items.append(("Shutdown", "shutdown"))
        items.append(("Re-lock", "relock"))

        idle_limit = int(self.cfg["idle"]["menu_seconds"])
        last_input = time.time()

        while True:
            now = time.time()
            if now - last_input >= idle_limit:
                log_line(self.log_path, f"Menu idle >= {idle_limit}s -> relock")
                return "relock"

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    raise SystemExit(0)
                if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.KEYDOWN, pygame.FINGERDOWN, pygame.FINGERMOTION):
                    last_input = time.time()

                if ev.type == pygame.MOUSEBUTTONDOWN:
                    x, y = ev.pos
                    hit = self._hit_test_menu(items, x, y)
                    if hit:
                        return hit

            self._draw_menu(items)
            pygame.display.flip()
            self.clock.tick(self.fps)

    def _draw_menu(self, items: List[Tuple[str, str]]) -> None:
        self.screen.fill((0, 0, 0))

        title = self.font.render(self.title, True, (255, 255, 255))
        self.screen.blit(title, (self.W // 2 - title.get_width() // 2, 40))

        # buttons
        btn_w = int(self.W * 0.70)
        btn_h = 90
        gap = 22
        start_y = 160

        for i, (label, action) in enumerate(items):
            x = self.W // 2 - btn_w // 2
            y = start_y + i * (btn_h + gap)
            rect = pygame.Rect(x, y, btn_w, btn_h)
            pygame.draw.rect(self.screen, (30, 30, 30), rect, border_radius=18)
            pygame.draw.rect(self.screen, (120, 120, 120), rect, width=2, border_radius=18)

            text = self.font.render(label, True, (240, 240, 240))
            self.screen.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))

        hint = self.font_small.render("Touch a button. Idle returns to lock.", True, (180, 180, 180))
        self.screen.blit(hint, (self.W // 2 - hint.get_width() // 2, self.H - 60))

        start_y = 160
        bx = self.W // 2 - btn_w // 2
        for i, (_label, action) in enumerate(items):
            by = start_y + i * (btn_h + gap)
            rect = pygame.Rect(bx, by, btn_w, btn_h)
            if rect.collidepoint(x, y):
                return action
        return None

    # --------------------------
    # Solaris launcher (managed)
    # --------------------------
    def run_solaris(self) -> None:
        if self.in_external:
            log_line(self.log_path, "Ignoring Solaris launch: external already active")
            return

        self.in_external = True
        try:
            sh = self.cfg["paths"]["launch_solaris_sh"]
            idle_s = int(self.cfg["idle"]["external_seconds"])
            env = os.environ.copy()
            env["SPARC_IDLE_MANAGED"] = "1"
            self._run_external(
                name="solaris",
                argv=[sh],
                log_path=self.cfg["logs"]["solaris_log"],
                env=env,
                idle_seconds=idle_s
            )
        finally:
            self.in_external = False


    # --------------------------
    # Media
    # --------------------------
    def run_media(self) -> None:
        # Minimal v1.1: show three folders and play selections using mpv.
        roots = [
            ("Images", self.cfg["paths"]["media_images"]),
            ("Music", self.cfg["paths"]["media_music"]),
            ("Videos", self.cfg["paths"]["media_videos"]),
        ]
        choice = self._simple_list_screen("Media Library", [r[0] for r in roots])
        if choice is None:
            return
        label, path = roots[choice]
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
        self._run_external(name="mpv", argv=argv, log_path=self.cfg["logs"]["mpv_log"], env=None, idle_seconds=idle_s)

    # --------------------------
    # Games
    # --------------------------
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
        self._run_external(name=name, argv=argv, log_path=log_path, env=None, idle_seconds=idle_s, cwd=cwd)

    def _discover_games(self, root: str) -> List[Dict[str, Any]]:
        out = []
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
                # strict-ish schema
                gid = str(m.get("id", d)).strip()
                title = str(m.get("title", gid)).strip()
                execv = m.get("exec")
                if not isinstance(execv, list) or not execv:
                    continue
                out.append({"id": gid, "title": title, "exec": execv, "cwd": m.get("cwd"), "dir": gdir})
            except Exception:
                continue
        return out

    # --------------------------
    # Shutdown (feature-flag guarded)
    # --------------------------
    def run_shutdown(self) -> None:
        # Minimal v1.1: confirmation screen then sudo shutdown.
        ok = self._confirm("Shutdown", "Power off the system?")
        if not ok:
            return
        self._run_external(
            name="shutdown",
            argv=["sudo", "-n", "/usr/sbin/shutdown", "-h", "now"],
            log_path=os.path.join(os.path.dirname(self.log_path), "shutdown.log"),
            env=None,
            idle_seconds=999999,
        )
    def run_reboot(self) -> None:
        ok = self._confirm("Reboot", "Reboot the system?")
        if not ok:
            return

        self._run_external(
            name="reboot",
            argv=["sudo", "-n", "/usr/sbin/shutdown", "-r", "now"],
            log_path=os.path.join(os.path.dirname(self.log_path), "reboot.log"),
            env=None,
            idle_seconds=999999,
        )
	

    # --------------------------
    # Common external runner
    # --------------------------
    def _run_external(self, name: str, argv: List[str], log_path: str, env: Optional[Dict[str, str]],
                      idle_seconds: int, cwd: Optional[str] = None) -> int:
        mp: Optional[ManagedProcess] = None
        try:
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
                        log_line(self.log_path, f"WARNING: xprintidle unavailable while running {name}; will use hard timeout={idle_seconds}s")
                    if (time.monotonic() - xprintidle_missing_since) < GRACE_S:
                        time.sleep(0.25)
                        continue
                    elapsed = time.monotonic() - hard_start
                    if elapsed >= float(idle_seconds):
                        log_line(self.log_path, f"Hard timeout {elapsed:.1f}s >= {idle_seconds}s in {name} -> kill and return")
                        kill_process_group(mp.popen, self.log_path, name)
                        return 0
                else:
                    # Normal idle policy
                    if idle_ms >= threshold_ms:
                        log_line(self.log_path, f"Idle {idle_ms}ms >= {threshold_ms}ms in {name} -> kill and return")
                        kill_process_group(mp.popen, self.log_path, name)
                        return 0


                time.sleep(0.25)

        finally:
            self.active_child = None
            if mp and mp.log_handle:
                try: mp.log_handle.close()
                except Exception: pass

    # --------------------------
    # Simple list UI (touch-friendly)
    # --------------------------
    def _simple_list_screen(self, title: str, items: List[str]) -> Optional[int]:
        if not items:
            return None

        idx = 0
        last_input = time.time()
        idle_limit = int(self.cfg["idle"]["menu_seconds"])

        while True:
            if time.time() - last_input >= idle_limit:
                return None

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
                    if ev.key == pygame.K_DOWN:
                        idx = min(len(items) - 1, idx + 1)
                    if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        return idx

                if ev.type == pygame.MOUSEBUTTONDOWN:
                    x, y = ev.pos
                    hit = self._hit_test_list(y, len(items))
                    if hit is not None:
                        idx = hit
                        return idx

            self._draw_list(title, items, idx)
            pygame.display.flip()
            self.clock.tick(self.fps)

    def _draw_list(self, title: str, items: List[str], sel: int) -> None:
        self.screen.fill((0, 0, 0))
        t = self.font.render(title, True, (255, 255, 255))
        self.screen.blit(t, (self.W // 2 - t.get_width() // 2, 40))

        row_h = 70
        start_y = 140
        visible = min(8, len(items))
        start = max(0, min(sel - visible // 2, len(items) - visible))

        for i in range(start, min(len(items), start + visible)):
            y = start_y + (i - start) * (row_h + 12)
            rect = pygame.Rect(int(self.W * 0.10), y, int(self.W * 0.80), row_h)
            is_sel = (i == sel)
            pygame.draw.rect(self.screen, (50, 50, 50) if is_sel else (25, 25, 25), rect, border_radius=14)
            pygame.draw.rect(self.screen, (140, 140, 140), rect, width=2, border_radius=14)
            text = self.font_small.render(items[i], True, (255, 255, 255))
            self.screen.blit(text, (rect.x + 18, rect.centery - text.get_height() // 2))

        hint = self.font_small.render("Tap an item. ESC/Q to go back.", True, (180, 180, 180))
        self.screen.blit(hint, (self.W // 2 - hint.get_width() // 2, self.H - 60))

    def _hit_test_list(self, y: int, n_items: int) -> Optional[int]:
        row_h = 70
        start_y = 140
        visible = min(8, n_items)

        # only hits visible rows; selection mapping handled by caller in current implementation
        for i in range(visible):
            ry = start_y + i * (row_h + 12)
            rect = pygame.Rect(int(self.W * 0.10), ry, int(self.W * 0.80), row_h)
            if rect.collidepoint(self.W // 2, y) or (rect.y <= y <= rect.y + rect.height):
                # this is approximate; list screen returns exact index via mapping
                return None
        return None

    def _confirm(self, title: str, msg: str) -> bool:
        # minimal confirmation: tap left/right
        yes_rect = pygame.Rect(int(self.W * 0.15), int(self.H * 0.60), int(self.W * 0.30), 90)
        no_rect = pygame.Rect(int(self.W * 0.55), int(self.H * 0.60), int(self.W * 0.30), 90)

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
        while time.time() - t0 < seconds:
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
    def _hit_test_menu(self, items: List[Tuple[str, str]], x: int, y: int) -> Optional[str]:
        btn_h = 90
        gap = 22

