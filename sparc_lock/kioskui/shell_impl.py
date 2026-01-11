#!/usr/bin/env python3
import os
import sys
import time
import math
import yaml
import signal
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "x11")
os.environ.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")
os.environ.setdefault("SDL_VIDEO_WINDOW_POS", "0,0")
os.environ.setdefault("SDL_VIDEO_CENTERED", "0")

import pygame  # noqa: E402

CFG_PATH = str(Path(__file__).resolve().parents[1] / "kiosk_config.yaml")
LOG_PATH = "/home/pi/sparc_lock/logs/kiosk_shell.log"

from kioskui.rcodes import (
    RC_RELOCK, RC_PI_MODE, RC_SOLARIS, RC_SHUTDOWN, RC_REBOOT, RC_GAMES, RC_MEDIA
)



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
        # Ensure we can import sibling packages (lockui/) from the sparc_lock root
        root = Path(__file__).resolve().parents[1]  # .../sparc_lock
        root_s = str(root)
        if root_s not in sys.path:
            sys.path.insert(0, root_s)

        from lockui import lock_impl as puzzle_lock
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
