# # # # # #!/usr/bin/env python3
# # # # # # -*- coding: utf-8 -*-
# # # # # """
# # # # # puzzle_lock.py — Full file (drop-in replacement)
# # # # #
# # # # # Anti-flash measures:
# # # # # - Paint a first black frame immediately after set_mode() (before heavy image/blur).
# # # # # - Avoid hard "screen.fill(black)" success cuts; use a captured background snapshot with an overlay.
# # # # # - Use vsync when supported.
# # # # # - Keep puzzle modes on a plain dark background (no fullscreen photo behind the puzzle UI).
# # # # # """
# # # # #
# # # # # import os
# # # # # import sys
# # # # # import time
# # # # # import math
# # # # # import random
# # # # # import datetime
# # # # # from typing import Optional, Tuple, List, Dict, Any
# # # # #
# # # # # # Reduce pygame console noise
# # # # # os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
# # # # #
# # # # # # Force X11 path and prevent minimize-on-focus-loss issues
# # # # # os.environ.setdefault("SDL_VIDEODRIVER", "x11")
# # # # # os.environ.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")
# # # # # os.environ.pop("WAYLAND_DISPLAY", None)
# # # # # os.environ.pop("WAYLAND_SOCKET", None)
# # # # #
# # # # # import pygame  # noqa: E402
# # # # #
# # # # #
# # # # # # ============================================================
# # # # # # Configuration
# # # # # # ============================================================
# # # # # BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# # # # # IMAGE_DIR = os.path.join(BASE_DIR, "images")
# # # # # SOUNDS_DIR = os.path.join(BASE_DIR, "sounds")
# # # # #
# # # # # BRAND_TEXT = "Glover SPARCstation"
# # # # # BRAND_SUB = "Puzzle Lock"
# # # # #
# # # # # # Admin PIN unlock (immediate unlock without solving)
# # # # # ADMIN_PIN = "1193"
# # # # # PIN_MAX_LEN = 12
# # # # #
# # # # # # Status bar
# # # # # SHOW_STATUS_BAR = True
# # # # # STATUS_BAR_H = 40
# # # # #
# # # # # # Lock UI visibility (dock auto-hide)
# # # # # LOCK_UI_START_HIDDEN = True
# # # # # LOCK_UI_AUTOHIDE_S = 6.0
# # # # # LOCK_UI_MOUSE_MOVE_THRESH = 10
# # # # # LOCK_UI_FADE_S = 0.18
# # # # #
# # # # # # Slideshow / effects
# # # # # LOCK_BG_CYCLE_S = 18.0
# # # # # LOCK_VISIBLE_SCALE_MODE = "contain"   # "contain" | "cover"
# # # # #
# # # # # LOCK_BG_PAN_RANGE_PX = 900
# # # # # LOCK_BG_PAN_SPEED_PX_S = 90.0
# # # # #
# # # # # LOCK_BG_BLUR_METHOD = "hq"           # "hq" (PIL if avail) | "downscale"
# # # # # LOCK_BG_HQ_DOWNSCALE = 2
# # # # # LOCK_BG_HQ_RADIUS = 10
# # # # #
# # # # # LOCK_BG_BLUR_DOWNSCALE = 12
# # # # # LOCK_BG_DIM_ALPHA = 60
# # # # #
# # # # # LOCK_TRANSITION_ENABLE = True
# # # # # LOCK_FADEIN_S = 0.55
# # # # #
# # # # # LOCK_TRANSITION_STYLES = ["shatter", "blinds", "explode", "drop"]
# # # # # LOCK_TRANSITION_STYLE = "random"
# # # # # LOCK_BREAK_DURATIONS = {
# # # # #     "shatter": 0.85,
# # # # #     "blinds":  0.95,
# # # # #     "explode": 0.80,
# # # # #     "drop":    0.90,
# # # # # }
# # # # # LOCK_SHATTER_TILE_TARGET = 180
# # # # # LOCK_SHATTER_GRAVITY = 1200.0
# # # # #
# # # # # LOCK_BG_RANDOM_START = True
# # # # # LOCK_BG_SHUFFLE = False
# # # # #
# # # # # # Colors
# # # # # COLOR_BG = (0, 0, 0)
# # # # # COLOR_PANEL = (16, 16, 16)
# # # # # COLOR_TRAY = (18, 18, 18)
# # # # # COLOR_LINE = (70, 70, 70)
# # # # #
# # # # # UI_TEXT = (240, 240, 240)
# # # # # UI_MUTED = (210, 210, 210)
# # # # #
# # # # # ACCENT_UNLOCK = (70, 185, 120)
# # # # # ACCENT_JIGSAW = (170, 170, 170)
# # # # # ACCENT_ADMIN = (120, 200, 255)
# # # # #
# # # # # # Sounds (optional wav files in ./sounds/)
# # # # # SND_PICK = "pick.wav"
# # # # # SND_DROP = "drop.wav"
# # # # # SND_SNAP = "snap.wav"
# # # # # SND_ERROR = "error.wav"
# # # # #
# # # # # # Square puzzle defaults
# # # # # GRID_X = 3
# # # # # GRID_Y = 4
# # # # # TRAY_H_FRAC = 0.28
# # # # # TRAY_MARGIN = 14
# # # # # SNAP_DIST = 190
# # # # #
# # # # # PUZ_INTRO_HOLD_S = 0.55
# # # # # PUZ_FALL_S = 0.85
# # # # # UNLOCK_SUCCESS_S = 0.85
# # # # #
# # # # # # Jigsaw defaults
# # # # # JIG_KNOB_FRAC = 0.22
# # # # # JIG_EDGE_OFF_FRAC = 0.18
# # # # #
# # # # # JIG_SNAP_FRAC = 0.55
# # # # # JIG_SNAP_MIN = 40
# # # # # JIG_SNAP_MAX = 140
# # # # #
# # # # # JIG_INTRO_HOLD_S = 0.55
# # # # # JIG_FALL_S = 0.85
# # # # # JIG_SOLVED_HOLD_S = 0.85
# # # # #
# # # # # JIG_BG_DIM_ALPHA = 130
# # # # #
# # # # # JIG_DIFFICULTY_CHOICES = [
# # # # #     ("Easy",    3, 2),
# # # # #     ("Normal",  4, 3),
# # # # #     ("Hard",    5, 4),
# # # # #     ("Expert",  6, 4),
# # # # #     ("Insane", 10, 5),
# # # # #     ("Extreme", 12, 5),
# # # # # ]
# # # # #
# # # # # PUZZLE_BOARD_SCALE_MODE = "cover"  # "cover" | "contain"
# # # # #
# # # # #
# # # # # # ============================================================
# # # # # # Helpers / utilities
# # # # # # ============================================================
# # # # # def clamp255(v: float) -> int:
# # # # #     return max(0, min(255, int(v)))
# # # # #
# # # # # def lighten(color, amt=22):
# # # # #     return (clamp255(color[0] + amt), clamp255(color[1] + amt), clamp255(color[2] + amt))
# # # # #
# # # # # def _ease_in_quad(t: float) -> float:
# # # # #     return t * t
# # # # #
# # # # # def _ease_out_cubic(t: float) -> float:
# # # # #     u = 1.0 - t
# # # # #     return 1.0 - (u * u * u)
# # # # #
# # # # # def dist2(a: Tuple[int, int], b: Tuple[int, int]) -> float:
# # # # #     dx = a[0] - b[0]
# # # # #     dy = a[1] - b[1]
# # # # #     return dx * dx + dy * dy
# # # # #
# # # # # def load_sound(name: str):
# # # # #     path = os.path.join(SOUNDS_DIR, name)
# # # # #     if os.path.exists(path):
# # # # #         try:
# # # # #             return pygame.mixer.Sound(path)
# # # # #         except Exception:
# # # # #             return None
# # # # #     return None
# # # # #
# # # # # def play(snd):
# # # # #     if snd:
# # # # #         try:
# # # # #             snd.play()
# # # # #         except Exception:
# # # # #             pass
# # # # #
# # # # # def event_pos(ev, W: int, H: int):
# # # # #     if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
# # # # #         return ev.pos
# # # # #     if ev.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
# # # # #         return (int(ev.x * W), int(ev.y * H))
# # # # #     return None
# # # # #
# # # # # def safe_load_image(path: str) -> pygame.Surface:
# # # # #     """
# # # # #     Fix EXIF orientation if Pillow is available; fallback to pygame loader otherwise.
# # # # #     """
# # # # #     try:
# # # # #         from PIL import Image, ImageOps  # type: ignore
# # # # #         img = Image.open(path)
# # # # #         img = ImageOps.exif_transpose(img)
# # # # #
# # # # #         if img.mode in ("RGBA", "LA") or ("transparency" in img.info):
# # # # #             img = img.convert("RGBA")
# # # # #             surf = pygame.image.frombuffer(img.tobytes(), img.size, "RGBA").convert_alpha()
# # # # #         else:
# # # # #             img = img.convert("RGB")
# # # # #             surf = pygame.image.frombuffer(img.tobytes(), img.size, "RGB").convert()
# # # # #         return surf
# # # # #     except Exception:
# # # # #         surf = pygame.image.load(path)
# # # # #         try:
# # # # #             return surf.convert_alpha() if surf.get_alpha() is not None else surf.convert()
# # # # #         except Exception:
# # # # #             return surf
# # # # #
# # # # # def scale_cover(src_surf: pygame.Surface, target_w: int, target_h: int) -> pygame.Surface:
# # # # #     sw, sh = src_surf.get_size()
# # # # #     if sw <= 0 or sh <= 0:
# # # # #         return pygame.Surface((target_w, target_h))
# # # # #     scale = max(target_w / sw, target_h / sh)
# # # # #     nw = int(sw * scale)
# # # # #     nh = int(sh * scale)
# # # # #     scaled = pygame.transform.smoothscale(src_surf, (nw, nh))
# # # # #     x = (nw - target_w) // 2
# # # # #     y = (nh - target_h) // 2
# # # # #     return scaled.subsurface(pygame.Rect(x, y, target_w, target_h)).copy()
# # # # #
# # # # # def scale_contain(src_surf: pygame.Surface, target_w: int, target_h: int):
# # # # #     """
# # # # #     Fit entire image within target (no cropping). Returns (scaled_surf, rect_to_blit_centered).
# # # # #     """
# # # # #     sw, sh = src_surf.get_size()
# # # # #     if sw <= 0 or sh <= 0:
# # # # #         blank = pygame.Surface((target_w, target_h))
# # # # #         return blank, blank.get_rect()
# # # # #     scale = min(target_w / sw, target_h / sh)
# # # # #     nw = max(1, int(sw * scale))
# # # # #     nh = max(1, int(sh * scale))
# # # # #     scaled = pygame.transform.smoothscale(src_surf, (nw, nh))
# # # # #     rect = scaled.get_rect(center=(target_w // 2, target_h // 2))
# # # # #     return scaled, rect
# # # # #
# # # # # def blur_surface_once(src: pygame.Surface, downscale: int = 12) -> pygame.Surface:
# # # # #     downscale = max(2, int(downscale))
# # # # #     w, h = src.get_size()
# # # # #     dw = max(2, w // downscale)
# # # # #     dh = max(2, h // downscale)
# # # # #     small = pygame.transform.smoothscale(src, (dw, dh))
# # # # #     return pygame.transform.smoothscale(small, (w, h))
# # # # #
# # # # # def blur_surface_hq(src: pygame.Surface, radius: int = 10, downscale: int = 2) -> pygame.Surface:
# # # # #     """
# # # # #     Higher-quality blur computed once per image swap.
# # # # #     Uses PIL GaussianBlur if available; falls back to blur_surface_once.
# # # # #     """
# # # # #     try:
# # # # #         from PIL import Image, ImageFilter  # type: ignore
# # # # #         w, h = src.get_size()
# # # # #         if w <= 2 or h <= 2:
# # # # #             return src
# # # # #
# # # # #         ds = max(1, int(downscale))
# # # # #         if ds > 1:
# # # # #             sw = max(2, w // ds)
# # # # #             sh = max(2, h // ds)
# # # # #             src_small = pygame.transform.smoothscale(src, (sw, sh))
# # # # #             raw = pygame.image.tostring(src_small, "RGB")
# # # # #             im = Image.frombytes("RGB", (sw, sh), raw)
# # # # #         else:
# # # # #             raw = pygame.image.tostring(src, "RGB")
# # # # #             im = Image.frombytes("RGB", (w, h), raw)
# # # # #
# # # # #         im = im.filter(ImageFilter.GaussianBlur(radius=max(0, int(radius))))
# # # # #
# # # # #         if ds > 1:
# # # # #             im = im.resize((w, h), resample=Image.LANCZOS)
# # # # #
# # # # #         out = pygame.image.frombuffer(im.tobytes(), (w, h), "RGB").convert()
# # # # #         return out
# # # # #     except Exception:
# # # # #         return blur_surface_once(src, LOCK_BG_BLUR_DOWNSCALE).convert()
# # # # #
# # # # #
# # # # # # ============================================================
# # # # # # Modern UI drawing
# # # # # # ============================================================
# # # # # def _draw_round_rect_alpha(dst, rect: pygame.Rect, rgb, alpha: int, radius: int):
# # # # #     alpha = clamp255(alpha)
# # # # #     s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
# # # # #     pygame.draw.rect(s, (rgb[0], rgb[1], rgb[2], alpha), pygame.Rect(0, 0, rect.w, rect.h), border_radius=radius)
# # # # #     dst.blit(s, rect.topleft)
# # # # #
# # # # # def _draw_round_rect_outline_alpha(dst, rect: pygame.Rect, rgb, alpha: int, radius: int, width: int = 2):
# # # # #     alpha = clamp255(alpha)
# # # # #     s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
# # # # #     pygame.draw.rect(s, (rgb[0], rgb[1], rgb[2], alpha), pygame.Rect(0, 0, rect.w, rect.h), width, border_radius=radius)
# # # # #     dst.blit(s, rect.topleft)
# # # # #
# # # # # def _draw_icon_lock(dst, center, color, alpha=255):
# # # # #     cx, cy = center
# # # # #     a = clamp255(alpha)
# # # # #     col = (color[0], color[1], color[2], a)
# # # # #     s = pygame.Surface((40, 40), pygame.SRCALPHA)
# # # # #     pygame.draw.arc(s, col, pygame.Rect(10, 6, 20, 18), math.pi, 0, 3)
# # # # #     pygame.draw.rect(s, col, pygame.Rect(10, 18, 20, 16), border_radius=5)
# # # # #     dst.blit(s, (cx - 20, cy - 20))
# # # # #
# # # # # def _draw_icon_jigsaw(dst, center, color, alpha=255):
# # # # #     cx, cy = center
# # # # #     a = clamp255(alpha)
# # # # #     col = (color[0], color[1], color[2], a)
# # # # #     s = pygame.Surface((40, 40), pygame.SRCALPHA)
# # # # #     pygame.draw.rect(s, col, pygame.Rect(10, 10, 18, 14), 2, border_radius=3)
# # # # #     pygame.draw.rect(s, col, pygame.Rect(14, 14, 18, 14), 2, border_radius=3)
# # # # #     pygame.draw.line(s, col, (16, 24), (22, 18), 2)
# # # # #     pygame.draw.line(s, col, (22, 18), (30, 26), 2)
# # # # #     dst.blit(s, (cx - 20, cy - 20))
# # # # #
# # # # # def _draw_icon_key(dst, center, color, alpha=255):
# # # # #     cx, cy = center
# # # # #     a = clamp255(alpha)
# # # # #     col = (color[0], color[1], color[2], a)
# # # # #     s = pygame.Surface((40, 40), pygame.SRCALPHA)
# # # # #     pygame.draw.circle(s, col, (14, 20), 6, 2)
# # # # #     pygame.draw.line(s, col, (20, 20), (34, 20), 2)
# # # # #     pygame.draw.line(s, col, (28, 20), (28, 26), 2)
# # # # #     pygame.draw.line(s, col, (32, 20), (32, 24), 2)
# # # # #     dst.blit(s, (cx - 20, cy - 20))
# # # # #
# # # # # def draw_modern_dock(dst, dock_rect: pygame.Rect, alpha: int):
# # # # #     _draw_round_rect_alpha(dst, dock_rect, (0, 0, 0), int(150 * (alpha / 255.0)), radius=22)
# # # # #     _draw_round_rect_outline_alpha(dst, dock_rect, (255, 255, 255), int(90 * (alpha / 255.0)), radius=22, width=2)
# # # # #
# # # # # def draw_modern_button(dst, rect: pygame.Rect, label: str, font, icon_fn, accent_rgb,
# # # # #                        active: bool, pressed: bool, alpha: int):
# # # # #     a = clamp255(alpha)
# # # # #
# # # # #     shadow_off = 3 if not pressed else 1
# # # # #     _draw_round_rect_alpha(dst, rect.move(0, shadow_off), (0, 0, 0), int(90 * (a / 255.0)), radius=16)
# # # # #
# # # # #     base = (18, 18, 18)
# # # # #     if active:
# # # # #         base = (26, 26, 26)
# # # # #     if pressed:
# # # # #         base = (12, 12, 12)
# # # # #
# # # # #     _draw_round_rect_alpha(dst, rect, base, int(210 * (a / 255.0)), radius=16)
# # # # #
# # # # #     strip = pygame.Rect(rect.x + 12, rect.y + rect.h - 10, rect.w - 24, 4)
# # # # #     _draw_round_rect_alpha(dst, strip, accent_rgb, int(200 * (a / 255.0)), radius=4)
# # # # #
# # # # #     _draw_round_rect_outline_alpha(dst, rect, (255, 255, 255), int(95 * (a / 255.0)), radius=16, width=2)
# # # # #
# # # # #     icon_center = (rect.x + 26, rect.centery)
# # # # #     icon_fn(dst, icon_center, accent_rgb, alpha=a)
# # # # #
# # # # #     txt = font.render(label, True, (240, 240, 240))
# # # # #     txt.set_alpha(a)
# # # # #     dst.blit(txt, (rect.x + 52, rect.centery - txt.get_height() // 2))
# # # # #
# # # # #
# # # # # # ============================================================
# # # # # # PIN overlay
# # # # # # ============================================================
# # # # # def make_button(rect: pygame.Rect, label: str, color=(90, 90, 90)):
# # # # #     return {"rect": rect, "label": label, "color": color}
# # # # #
# # # # # def draw_button(screen, btn, font_main, font_small, active=False, small=False):
# # # # #     r = btn["rect"]
# # # # #     base = btn.get("color", (90, 90, 90))
# # # # #     bg = base if not active else lighten(base, 28)
# # # # #
# # # # #     pygame.draw.rect(screen, bg, r, border_radius=16)
# # # # #     pygame.draw.rect(screen, (230, 230, 230), r, 2, border_radius=16)
# # # # #
# # # # #     f = font_small if small else font_main
# # # # #     t = f.render(btn["label"], True, (255, 255, 255))
# # # # #     screen.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))
# # # # #
# # # # # def pin_overlay_loop(screen, clock, W, H, bg_frame_surf, font, font_small, snd_error) -> bool:
# # # # #     pin_input = ""
# # # # #     pin_error = ""
# # # # #     pin_error_t0 = 0.0
# # # # #
# # # # #     cancel_btn = make_button(pygame.Rect(16, 16, 170, 48), "CANCEL", color=(120, 120, 120))
# # # # #
# # # # #     KEYPAD_COLS = 3
# # # # #     KEYPAD_ROWS = 4
# # # # #     KEYS = ["1", "2", "3",
# # # # #             "4", "5", "6",
# # # # #             "7", "8", "9",
# # # # #             "C", "0", "OK"]
# # # # #
# # # # #     def submit() -> bool:
# # # # #         nonlocal pin_input, pin_error, pin_error_t0
# # # # #         if pin_input == ADMIN_PIN:
# # # # #             return True
# # # # #         pin_error = "Incorrect PIN"
# # # # #         pin_error_t0 = time.time()
# # # # #         pin_input = ""
# # # # #         play(snd_error)
# # # # #         return False
# # # # #
# # # # #     while True:
# # # # #         for ev in pygame.event.get():
# # # # #             if ev.type == pygame.QUIT:
# # # # #                 raise SystemExit
# # # # #
# # # # #             if ev.type == pygame.KEYDOWN:
# # # # #                 if ev.key == pygame.K_ESCAPE:
# # # # #                     return False
# # # # #                 if ev.key == pygame.K_RETURN or ev.key == pygame.K_KP_ENTER:
# # # # #                     if submit():
# # # # #                         return True
# # # # #                 elif ev.key == pygame.K_BACKSPACE:
# # # # #                     pin_input = pin_input[:-1]
# # # # #                 else:
# # # # #                     if ev.unicode.isdigit() and len(pin_input) < PIN_MAX_LEN:
# # # # #                         pin_input += ev.unicode
# # # # #
# # # # #             if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
# # # # #                 pos = event_pos(ev, W, H)
# # # # #                 if not pos:
# # # # #                     continue
# # # # #
# # # # #                 if cancel_btn["rect"].collidepoint(pos):
# # # # #                     return False
# # # # #
# # # # #                 pad_w = min(520, int(W * 0.42))
# # # # #                 pad_h = min(520, int(H * 0.62))
# # # # #                 pad_x = (W - pad_w) // 2
# # # # #                 pad_y = (H - pad_h) // 2 + 40
# # # # #                 cell_w = pad_w // KEYPAD_COLS
# # # # #                 cell_h = pad_h // KEYPAD_ROWS
# # # # #
# # # # #                 idx = 0
# # # # #                 for r in range(KEYPAD_ROWS):
# # # # #                     for c in range(KEYPAD_COLS):
# # # # #                         x = pad_x + c * cell_w + 8
# # # # #                         y = pad_y + r * cell_h + 8
# # # # #                         rect = pygame.Rect(x, y, cell_w - 16, cell_h - 16)
# # # # #                         if rect.collidepoint(pos):
# # # # #                             key = KEYS[idx]
# # # # #                             if key == "C":
# # # # #                                 pin_input = ""
# # # # #                             elif key == "OK":
# # # # #                                 if submit():
# # # # #                                     return True
# # # # #                             else:
# # # # #                                 if len(pin_input) < PIN_MAX_LEN:
# # # # #                                     pin_input += key
# # # # #                             break
# # # # #                         idx += 1
# # # # #
# # # # #         screen.blit(bg_frame_surf, (0, 0))
# # # # #         overlay = pygame.Surface((W, H), pygame.SRCALPHA)
# # # # #         overlay.fill((0, 0, 0, 205))
# # # # #         screen.blit(overlay, (0, 0))
# # # # #
# # # # #         mx, my = pygame.mouse.get_pos()
# # # # #         draw_button(screen, cancel_btn, font, font_small, active=cancel_btn["rect"].collidepoint((mx, my)), small=True)
# # # # #
# # # # #         title = font.render("PIN UNLOCK", True, (255, 255, 255))
# # # # #         prompt = font_small.render("Enter PIN (keyboard or touchscreen keypad):", True, (230, 230, 230))
# # # # #         masked = "*" * len(pin_input)
# # # # #         entry = font.render(masked, True, (255, 255, 0))
# # # # #
# # # # #         screen.blit(title, (W // 2 - title.get_width() // 2, 80))
# # # # #         screen.blit(prompt, (W // 2 - prompt.get_width() // 2, 130))
# # # # #         screen.blit(entry, (W // 2 - entry.get_width() // 2, 165))
# # # # #
# # # # #         pad_w = min(520, int(W * 0.42))
# # # # #         pad_h = min(520, int(H * 0.62))
# # # # #         pad_x = (W - pad_w) // 2
# # # # #         pad_y = (H - pad_h) // 2 + 40
# # # # #         cell_w = pad_w // KEYPAD_COLS
# # # # #         cell_h = pad_h // KEYPAD_ROWS
# # # # #
# # # # #         pygame.draw.rect(screen, (35, 35, 35), pygame.Rect(pad_x, pad_y, pad_w, pad_h), border_radius=12)
# # # # #
# # # # #         rects = []
# # # # #         for r in range(KEYPAD_ROWS):
# # # # #             for c in range(KEYPAD_COLS):
# # # # #                 x = pad_x + c * cell_w + 8
# # # # #                 y = pad_y + r * cell_h + 8
# # # # #                 rects.append(pygame.Rect(x, y, cell_w - 16, cell_h - 16))
# # # # #
# # # # #         for i, r in enumerate(rects):
# # # # #             pygame.draw.rect(screen, (70, 70, 70), r, border_radius=10)
# # # # #             label = font.render(KEYS[i], True, (255, 255, 255))
# # # # #             screen.blit(label, (r.centerx - label.get_width() // 2, r.centery - label.get_height() // 2))
# # # # #
# # # # #         if pin_error and (time.time() - pin_error_t0) < 2.0:
# # # # #             err = font_small.render(pin_error, True, (255, 90, 90))
# # # # #             screen.blit(err, (W // 2 - err.get_width() // 2, pad_y + pad_h + 18))
# # # # #
# # # # #         tip = font_small.render("Enter/OK=submit, Backspace=delete, Esc/CANCEL=back.", True, (230, 230, 230))
# # # # #         screen.blit(tip, (W // 2 - tip.get_width() // 2, pad_y + pad_h + 50))
# # # # #
# # # # #         pygame.display.flip()
# # # # #         clock.tick(60)
# # # # #
# # # # #
# # # # # # ============================================================
# # # # # # Unlock success overlay (ANTI-FLASH)
# # # # # # ============================================================
# # # # # def unlock_success_overlay(screen, clock, W, H, font_brand, font_small, snd_snap,
# # # # #                           msg="UNLOCKED", sub="Returning to menu...", hold_s=UNLOCK_SUCCESS_S,
# # # # #                           bg_frame_surf: Optional[pygame.Surface] = None):
# # # # #     """
# # # # #     Anti-flash change:
# # # # #     - Do not clear to black first.
# # # # #     - Use a snapshot background (either provided or screen.copy()) and overlay on top.
# # # # #     """
# # # # #     if bg_frame_surf is None:
# # # # #         try:
# # # # #             bg_frame_surf = screen.copy()
# # # # #         except Exception:
# # # # #             bg_frame_surf = None
# # # # #
# # # # #     t0 = time.time()
# # # # #     play(snd_snap)
# # # # #     while time.time() - t0 < hold_s:
# # # # #         for ev in pygame.event.get():
# # # # #             if ev.type == pygame.QUIT:
# # # # #                 raise SystemExit
# # # # #
# # # # #         if bg_frame_surf is not None:
# # # # #             screen.blit(bg_frame_surf, (0, 0))
# # # # #         else:
# # # # #             screen.fill(COLOR_BG)
# # # # #
# # # # #         overlay = pygame.Surface((W, H), pygame.SRCALPHA)
# # # # #         overlay.fill((0, 0, 0, 180))
# # # # #         screen.blit(overlay, (0, 0))
# # # # #
# # # # #         m = font_brand.render(msg, True, (255, 255, 255))
# # # # #         s = font_small.render(sub, True, (230, 230, 230))
# # # # #         screen.blit(m, (W // 2 - m.get_width() // 2, H // 2 - 40))
# # # # #         screen.blit(s, (W // 2 - s.get_width() // 2, H // 2 + 20))
# # # # #         pygame.display.flip()
# # # # #         clock.tick(60)
# # # # #
# # # # # def fade_to_black(screen, clock, W, H, base: Optional[pygame.Surface] = None, seconds: float = 0.18):
# # # # #     if base is None:
# # # # #         try:
# # # # #             base = screen.copy()
# # # # #         except Exception:
# # # # #             base = None
# # # # #     t0 = time.time()
# # # # #     while True:
# # # # #         t = (time.time() - t0) / max(0.001, seconds)
# # # # #         if t >= 1.0:
# # # # #             break
# # # # #         for ev in pygame.event.get():
# # # # #             if ev.type == pygame.QUIT:
# # # # #                 raise SystemExit
# # # # #         if base is not None:
# # # # #             screen.blit(base, (0, 0))
# # # # #         else:
# # # # #             screen.fill((0, 0, 0))
# # # # #         a = int(255 * _ease_out_cubic(t))
# # # # #         ov = pygame.Surface((W, H), pygame.SRCALPHA)
# # # # #         ov.fill((0, 0, 0, a))
# # # # #         screen.blit(ov, (0, 0))
# # # # #         pygame.display.flip()
# # # # #         clock.tick(60)
# # # # #     screen.fill((0, 0, 0))
# # # # #     pygame.display.flip()
# # # # #
# # # # #
# # # # # # ============================================================
# # # # # # Jigsaw internals
# # # # # # ============================================================
# # # # # def calc_jig_snap_dist(W: int, BOARD_H: int, cols: int, rows: int) -> int:
# # # # #     cols = max(1, int(cols))
# # # # #     rows = max(1, int(rows))
# # # # #     cell_w = W // cols
# # # # #     cell_h = BOARD_H // rows
# # # # #     base = int(min(cell_w, cell_h) * JIG_SNAP_FRAC)
# # # # #     return max(JIG_SNAP_MIN, min(JIG_SNAP_MAX, base))
# # # # #
# # # # # def _make_jigsaw_edges(cols, rows):
# # # # #     h_edges = [
# # # # #         [{"dir": random.choice([-1, 1]), "off": random.uniform(-JIG_EDGE_OFF_FRAC, JIG_EDGE_OFF_FRAC)}
# # # # #          for _ in range(cols)]
# # # # #         for _ in range(rows - 1)
# # # # #     ]
# # # # #     v_edges = [
# # # # #         [{"dir": random.choice([-1, 1]), "off": random.uniform(-JIG_EDGE_OFF_FRAC, JIG_EDGE_OFF_FRAC)}
# # # # #          for _ in range(cols - 1)]
# # # # #         for _ in range(rows)
# # # # #     ]
# # # # #     return h_edges, v_edges
# # # # #
# # # # # def _apply_edge_circle(mask_surf, kind, center, radius):
# # # # #     if kind == 0:
# # # # #         return
# # # # #     if kind > 0:
# # # # #         pygame.draw.circle(mask_surf, (255, 255, 255, 255), center, radius)
# # # # #     else:
# # # # #         pygame.draw.circle(mask_surf, (255, 255, 255, 0), center, radius)
# # # # #
# # # # # def build_jigsaw_pieces(W, BOARD_H, board_surf, cols, rows):
# # # # #     cell_w = W // cols
# # # # #     cell_h = BOARD_H // rows
# # # # #
# # # # #     knob_r = int(min(cell_w, cell_h) * JIG_KNOB_FRAC)
# # # # #     margin = knob_r + 3
# # # # #
# # # # #     h_edges, v_edges = _make_jigsaw_edges(cols, rows)
# # # # #
# # # # #     pieces = []
# # # # #     for y in range(rows):
# # # # #         for x in range(cols):
# # # # #             if y == 0:
# # # # #                 top_kind, top_off = 0, 0.0
# # # # #             else:
# # # # #                 top_kind = -h_edges[y - 1][x]["dir"]
# # # # #                 top_off = h_edges[y - 1][x]["off"]
# # # # #
# # # # #             if y == rows - 1:
# # # # #                 bot_kind, bot_off = 0, 0.0
# # # # #             else:
# # # # #                 bot_kind = h_edges[y][x]["dir"]
# # # # #                 bot_off = h_edges[y][x]["off"]
# # # # #
# # # # #             if x == 0:
# # # # #                 left_kind, left_off = 0, 0.0
# # # # #             else:
# # # # #                 left_kind = -v_edges[y][x - 1]["dir"]
# # # # #                 left_off = v_edges[y][x - 1]["off"]
# # # # #
# # # # #             if x == cols - 1:
# # # # #                 right_kind, right_off = 0, 0.0
# # # # #             else:
# # # # #                 right_kind = v_edges[y][x]["dir"]
# # # # #                 right_off = v_edges[y][x]["off"]
# # # # #
# # # # #             pw = cell_w + 2 * margin
# # # # #             ph = cell_h + 2 * margin
# # # # #
# # # # #             mask_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
# # # # #             mask_surf.fill((255, 255, 255, 0))
# # # # #             pygame.draw.rect(mask_surf, (255, 255, 255, 255), pygame.Rect(margin, margin, cell_w, cell_h))
# # # # #
# # # # #             cx_top = margin + (cell_w // 2) + int(top_off * cell_w)
# # # # #             cy_top = margin
# # # # #             _apply_edge_circle(mask_surf, top_kind, (cx_top, cy_top), knob_r)
# # # # #
# # # # #             cx_bot = margin + (cell_w // 2) + int(bot_off * cell_w)
# # # # #             cy_bot = margin + cell_h
# # # # #             _apply_edge_circle(mask_surf, bot_kind, (cx_bot, cy_bot), knob_r)
# # # # #
# # # # #             cx_left = margin
# # # # #             cy_left = margin + (cell_h // 2) + int(left_off * cell_h)
# # # # #             _apply_edge_circle(mask_surf, left_kind, (cx_left, cy_left), knob_r)
# # # # #
# # # # #             cx_right = margin + cell_w
# # # # #             cy_right = margin + (cell_h // 2) + int(right_off * cell_h)
# # # # #             _apply_edge_circle(mask_surf, right_kind, (cx_right, cy_right), knob_r)
# # # # #
# # # # #             piece_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
# # # # #             piece_surf.blit(board_surf, (margin - x * cell_w, margin - y * cell_h))
# # # # #             piece_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
# # # # #
# # # # #             piece_mask = pygame.mask.from_surface(mask_surf)
# # # # #             correct_pos = (x * cell_w - margin, y * cell_h - margin)
# # # # #
# # # # #             pieces.append({
# # # # #                 "surf": piece_surf,
# # # # #                 "mask": piece_mask,
# # # # #                 "correct_pos": correct_pos,
# # # # #                 "pos": correct_pos,
# # # # #                 "locked": False,
# # # # #                 "fall_from": correct_pos,
# # # # #                 "fall_to": correct_pos,
# # # # #             })
# # # # #
# # # # #     return pieces
# # # # #
# # # # # def tray_random_pos_sized(W, tray_rect, obj_w, obj_h):
# # # # #     x0 = TRAY_MARGIN
# # # # #     x1 = W - TRAY_MARGIN - obj_w
# # # # #     y0 = tray_rect.top + TRAY_MARGIN
# # # # #     y1 = tray_rect.bottom - TRAY_MARGIN - obj_h
# # # # #     if x1 < x0:
# # # # #         x1 = x0
# # # # #     if y1 < y0:
# # # # #         y1 = y0
# # # # #     return (random.randint(x0, x1), random.randint(y0, y1))
# # # # #
# # # # # def jigsaw_all_locked(pieces):
# # # # #     return all(p.get("locked") for p in pieces)
# # # # #
# # # # #
# # # # # # ============================================================
# # # # # # App
# # # # # # ============================================================
# # # # # class LockApp:
# # # # #     STATE_LOCK = "LOCK"
# # # # #     STATE_SQUARE = "SQUARE"
# # # # #     STATE_JIG_SELECT = "JIG_SELECT"
# # # # #     STATE_JIGSAW = "JIGSAW"
# # # # #
# # # # #     PUZ_INTRO = "INTRO"
# # # # #     PUZ_FALL = "FALL"
# # # # #     PUZ_PLAY = "PLAY"
# # # # #
# # # # #     JIG_INTRO = "INTRO"
# # # # #     JIG_FALL = "FALL"
# # # # #     JIG_PLAY = "PLAY"
# # # # #     JIG_SOLVED = "SOLVED"
# # # # #
# # # # #     LOCK_TRANS_NONE = None
# # # # #     LOCK_TRANS_BREAK = "BREAK"
# # # # #     LOCK_TRANS_FADEIN = "FADEIN"
# # # # #
# # # # #     def __init__(self):
# # # # #         pygame.init()
# # # # #         try:
# # # # #             pygame.mixer.init()
# # # # #         except Exception:
# # # # #             pass
# # # # #
# # # # #         # Request vsync when supported.
# # # # #         try:
# # # # #             self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN, vsync=1)
# # # # #         except Exception:
# # # # #             self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
# # # # #
# # # # #         pygame.display.set_caption("SPARC Lock")
# # # # #         self.clock = pygame.time.Clock()
# # # # #         self.W, self.H = self.screen.get_size()
# # # # #
# # # # #         # ANTI-FLASH: immediate frame before heavy work
# # # # #         self.screen.fill((0, 0, 0))
# # # # #         pygame.display.flip()
# # # # #         pygame.event.pump()
# # # # #
# # # # #         pygame.mouse.set_visible(True)
# # # # #
# # # # #         self.font = pygame.font.SysFont(None, 52)
# # # # #         self.font_small = pygame.font.SysFont(None, 26)
# # # # #         self.font_brand = pygame.font.SysFont(None, 64)
# # # # #         self.font_brand2 = pygame.font.SysFont(None, 28)
# # # # #         self.font_dock = pygame.font.SysFont(None, 28)
# # # # #
# # # # #         self.snd_pick = load_sound(SND_PICK)
# # # # #         self.snd_drop = load_sound(SND_DROP)
# # # # #         self.snd_snap = load_sound(SND_SNAP)
# # # # #         self.snd_error = load_sound(SND_ERROR)
# # # # #
# # # # #         self.TRAY_H = int(self.H * TRAY_H_FRAC)
# # # # #         self.BOARD_H = self.H - self.TRAY_H
# # # # #         self.board_rect = pygame.Rect(0, 0, self.W, self.BOARD_H)
# # # # #         self.tray_rect = pygame.Rect(0, self.BOARD_H, self.W, self.TRAY_H)
# # # # #
# # # # #         self.images = self._load_images()
# # # # #         self.playlist = list(self.images)
# # # # #         if LOCK_BG_SHUFFLE:
# # # # #             random.shuffle(self.playlist)
# # # # #         else:
# # # # #             self.playlist.sort()
# # # # #         self.lock_idx = random.randrange(len(self.playlist)) if LOCK_BG_RANDOM_START else 0
# # # # #
# # # # #         # lock visuals
# # # # #         self.lock_bg_big: Optional[pygame.Surface] = None
# # # # #         self.lock_fg: Optional[pygame.Surface] = None
# # # # #         self.lock_fg_rect: Optional[pygame.Rect] = None
# # # # #         self.board_surf: Optional[pygame.Surface] = None
# # # # #         self.img_name = ""
# # # # #
# # # # #         self.pan_x = 0.0
# # # # #         self.pan_y = 0.0
# # # # #         self.pan_vx = 0.0
# # # # #         self.pan_vy = 0.0
# # # # #
# # # # #         self.lock_cycle_t0 = time.time()
# # # # #         self.lock_trans = self.LOCK_TRANS_NONE
# # # # #         self.lock_trans_t0 = 0.0
# # # # #
# # # # #         self.break_style = "shatter"
# # # # #         self.break_dur = float(LOCK_BREAK_DURATIONS.get("shatter", 0.85))
# # # # #         self.lock_snapshot = pygame.Surface((self.W, self.H))
# # # # #         self.break_pieces: List[Dict[str, Any]] = []
# # # # #
# # # # #         self._set_image_by_index(self.lock_idx)
# # # # #
# # # # #         now = time.time()
# # # # #         self.lock_ui_visible_until = (now + LOCK_UI_AUTOHIDE_S) if not LOCK_UI_START_HIDDEN else 0.0
# # # # #         self.last_mouse_pos = pygame.mouse.get_pos()
# # # # #         self.ui_alpha = 0.0 if LOCK_UI_START_HIDDEN else 255.0
# # # # #
# # # # #         self._layout_lock_dock()
# # # # #         self.lock_pressed: Optional[str] = None  # "unlock" | "jigsaw" | "admin"
# # # # #         self.state = self.STATE_LOCK
# # # # #
# # # # #         # square puzzle state
# # # # #         self.tiles: List[Dict[str, Any]] = []
# # # # #         self.tile_w = 0
# # # # #         self.tile_h = 0
# # # # #         self.slot_positions: List[Tuple[int, int]] = []
# # # # #         self.drag_tile: Optional[Dict[str, Any]] = None
# # # # #         self.drag_ox = 0
# # # # #         self.drag_oy = 0
# # # # #         self.puz_stage = self.PUZ_INTRO
# # # # #         self.puz_t0 = 0.0
# # # # #
# # # # #         # jigsaw state
# # # # #         self.jig_cols, self.jig_rows = JIG_DIFFICULTY_CHOICES[1][1], JIG_DIFFICULTY_CHOICES[1][2]
# # # # #         self.jig_snap_dist = calc_jig_snap_dist(self.W, self.BOARD_H, self.jig_cols, self.jig_rows)
# # # # #         self.jig_pieces: List[Dict[str, Any]] = []
# # # # #         self.jig_drag_piece: Optional[Dict[str, Any]] = None
# # # # #         self.jig_drag_ox = 0
# # # # #         self.jig_drag_oy = 0
# # # # #         self.jig_stage = self.JIG_INTRO
# # # # #         self.jig_t0 = 0.0
# # # # #
# # # # #         self.back_btn = make_button(pygame.Rect(16, 16, 160, 48), "BACK", color=(120, 120, 120))
# # # # #
# # # # #     # ------------------ lock layout ------------------
# # # # #     def _layout_lock_dock(self):
# # # # #         margin_bottom = 28
# # # # #         dock_w = min(780, int(self.W * 0.68))
# # # # #         dock_h = 96
# # # # #         dock_x = (self.W - dock_w) // 2
# # # # #         dock_y = self.H - dock_h - margin_bottom
# # # # #         self.dock_rect = pygame.Rect(dock_x, dock_y, dock_w, dock_h)
# # # # #
# # # # #         pad = 14
# # # # #         gap = 12
# # # # #         btn_h = 64
# # # # #         btn_y = dock_y + (dock_h - btn_h) // 2
# # # # #         btn_w = (dock_w - pad * 2 - gap * 2) // 3
# # # # #
# # # # #         self.btn_unlock = pygame.Rect(dock_x + pad + (btn_w + gap) * 0, btn_y, btn_w, btn_h)
# # # # #         self.btn_jigsaw = pygame.Rect(dock_x + pad + (btn_w + gap) * 1, btn_y, btn_w, btn_h)
# # # # #         self.btn_admin = pygame.Rect(dock_x + pad + (btn_w + gap) * 2, btn_y, btn_w, btn_h)
# # # # #
# # # # #     # ------------------ loading ------------------
# # # # #     def _load_images(self):
# # # # #         if not os.path.isdir(IMAGE_DIR):
# # # # #             print(f"Missing images dir: {IMAGE_DIR}", file=sys.stderr)
# # # # #             sys.exit(1)
# # # # #         imgs = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
# # # # #         if not imgs:
# # # # #             print(f"No images found in {IMAGE_DIR}", file=sys.stderr)
# # # # #             sys.exit(1)
# # # # #         return imgs
# # # # #
# # # # #     # ------------------ exit ------------------
# # # # #     def exit_unlocked(self):
# # # # #         # Return success (rc=0) to kiosk_shell
# # # # #         try:
# # # # #             pygame.quit()
# # # # #         except Exception:
# # # # #             pass
# # # # #         sys.exit(0)
# # # # #
# # # # #     # ------------------ UI visibility ------------------
# # # # #     def _touch_lock_ui(self):
# # # # #         self.lock_ui_visible_until = time.time() + LOCK_UI_AUTOHIDE_S
# # # # #
# # # # #     def _lock_ui_visible(self) -> bool:
# # # # #         return time.time() < self.lock_ui_visible_until
# # # # #
# # # # #     # ------------------ image setup ------------------
# # # # #     def _set_image_by_index(self, idx: int):
# # # # #         self.lock_idx = idx % len(self.playlist)
# # # # #         fname = self.playlist[self.lock_idx]
# # # # #         raw = safe_load_image(os.path.join(IMAGE_DIR, fname))
# # # # #         self.img_name = fname
# # # # #
# # # # #         # Foreground image (visible)
# # # # #         if LOCK_VISIBLE_SCALE_MODE.lower() == "cover":
# # # # #             self.lock_fg = scale_cover(raw, self.W, self.H)
# # # # #             self.lock_fg_rect = self.lock_fg.get_rect(topleft=(0, 0))
# # # # #         else:
# # # # #             self.lock_fg, self.lock_fg_rect = scale_contain(raw, self.W, self.H)
# # # # #
# # # # #         # Background image (blurred, panning)
# # # # #         big_w = self.W + LOCK_BG_PAN_RANGE_PX
# # # # #         big_h = self.H + LOCK_BG_PAN_RANGE_PX
# # # # #         bg = scale_cover(raw, big_w, big_h).convert()
# # # # #
# # # # #         if LOCK_BG_BLUR_METHOD.lower() == "hq":
# # # # #             bg = blur_surface_hq(bg, radius=LOCK_BG_HQ_RADIUS, downscale=LOCK_BG_HQ_DOWNSCALE)
# # # # #         else:
# # # # #             bg = blur_surface_once(bg, LOCK_BG_BLUR_DOWNSCALE).convert()
# # # # #
# # # # #         if LOCK_BG_DIM_ALPHA > 0:
# # # # #             dim = pygame.Surface((big_w, big_h), pygame.SRCALPHA)
# # # # #             dim.fill((0, 0, 0, clamp255(LOCK_BG_DIM_ALPHA)))
# # # # #             bg.blit(dim, (0, 0))
# # # # #
# # # # #         self.lock_bg_big = bg.convert()
# # # # #
# # # # #         # Board surf used to slice puzzle pieces (not used as fullscreen background in puzzle modes)
# # # # #         if PUZZLE_BOARD_SCALE_MODE.lower() == "contain":
# # # # #             board_fit, rect = scale_contain(raw, self.W, self.BOARD_H)
# # # # #             board = pygame.Surface((self.W, self.BOARD_H))
# # # # #             board.fill((0, 0, 0))
# # # # #             board.blit(board_fit, rect)
# # # # #             self.board_surf = board.convert()
# # # # #         else:
# # # # #             self.board_surf = scale_cover(raw, self.W, self.BOARD_H).convert()
# # # # #
# # # # #         max_x = max(0, self.lock_bg_big.get_width() - self.W)
# # # # #         max_y = max(0, self.lock_bg_big.get_height() - self.H)
# # # # #         self.pan_x = float(random.randint(0, max_x)) if max_x else 0.0
# # # # #         self.pan_y = float(random.randint(0, max_y)) if max_y else 0.0
# # # # #
# # # # #         ang = random.uniform(0, math.tau)
# # # # #         self.pan_vx = math.cos(ang) * LOCK_BG_PAN_SPEED_PX_S
# # # # #         self.pan_vy = math.sin(ang) * LOCK_BG_PAN_SPEED_PX_S
# # # # #
# # # # #         self.lock_cycle_t0 = time.time()
# # # # #
# # # # #     def _advance_image(self):
# # # # #         nxt = self.lock_idx + 1
# # # # #         if nxt >= len(self.playlist):
# # # # #             nxt = 0
# # # # #             if LOCK_BG_SHUFFLE:
# # # # #                 random.shuffle(self.playlist)
# # # # #         self._set_image_by_index(nxt)
# # # # #
# # # # #     def _update_pan(self, dt: float):
# # # # #         if not self.lock_bg_big:
# # # # #             return
# # # # #         max_x = max(0, self.lock_bg_big.get_width() - self.W)
# # # # #         max_y = max(0, self.lock_bg_big.get_height() - self.H)
# # # # #
# # # # #         self.pan_x += self.pan_vx * dt
# # # # #         self.pan_y += self.pan_vy * dt
# # # # #
# # # # #         if max_x > 0:
# # # # #             if self.pan_x < 0:
# # # # #                 self.pan_x = 0.0
# # # # #                 self.pan_vx = abs(self.pan_vx)
# # # # #             elif self.pan_x > max_x:
# # # # #                 self.pan_x = float(max_x)
# # # # #                 self.pan_vx = -abs(self.pan_vx)
# # # # #         else:
# # # # #             self.pan_x = 0.0
# # # # #
# # # # #         if max_y > 0:
# # # # #             if self.pan_y < 0:
# # # # #                 self.pan_y = 0.0
# # # # #                 self.pan_vy = abs(self.pan_vy)
# # # # #             elif self.pan_y > max_y:
# # # # #                 self.pan_y = float(max_y)
# # # # #                 self.pan_vy = -abs(self.pan_vy)
# # # # #         else:
# # # # #             self.pan_y = 0.0
# # # # #
# # # # #     def _draw_lock_frame_to(self, target_surf: pygame.Surface):
# # # # #         if self.lock_bg_big:
# # # # #             max_x = max(0, self.lock_bg_big.get_width() - self.W)
# # # # #             max_y = max(0, self.lock_bg_big.get_height() - self.H)
# # # # #             vx = int(max(0, min(max_x, self.pan_x)))
# # # # #             vy = int(max(0, min(max_y, self.pan_y)))
# # # # #             view = pygame.Rect(vx, vy, self.W, self.H)
# # # # #             target_surf.blit(self.lock_bg_big.subsurface(view), (0, 0))
# # # # #         else:
# # # # #             target_surf.fill((0, 0, 0))
# # # # #
# # # # #         if self.lock_fg and self.lock_fg_rect:
# # # # #             target_surf.blit(self.lock_fg, self.lock_fg_rect)
# # # # #
# # # # #     def _build_lock_frame_surface(self) -> pygame.Surface:
# # # # #         surf = pygame.Surface((self.W, self.H))
# # # # #         self._draw_lock_frame_to(surf)
# # # # #         return surf
# # # # #
# # # # #     # ------------------ status bar ------------------
# # # # #     def _draw_status_bar(self):
# # # # #         if not SHOW_STATUS_BAR:
# # # # #             return
# # # # #         bar = pygame.Surface((self.W, STATUS_BAR_H), pygame.SRCALPHA)
# # # # #         bar.fill((0, 0, 0, 140))
# # # # #         self.screen.blit(bar, (0, 0))
# # # # #
# # # # #         now = datetime.datetime.now()
# # # # #         txt = now.strftime("%a %b %d   %I:%M %p").lstrip("0")
# # # # #         t = self.font_small.render(txt, True, (230, 230, 230))
# # # # #         self.screen.blit(t, (self.W - t.get_width() - 16, (STATUS_BAR_H - t.get_height()) // 2))
# # # # #
# # # # #     # ============================================================
# # # # #     # Lock transitions (break + fadein)
# # # # #     # ============================================================
# # # # #     def _choose_break_style(self) -> str:
# # # # #         if LOCK_TRANSITION_STYLE == "random":
# # # # #             return random.choice(LOCK_TRANSITION_STYLES)
# # # # #         if LOCK_TRANSITION_STYLE in LOCK_TRANSITION_STYLES:
# # # # #             return LOCK_TRANSITION_STYLE
# # # # #         return "shatter"
# # # # #
# # # # #     def _begin_lock_transition(self):
# # # # #         # Capture snapshot of the current lock frame (not including dock)
# # # # #         self.lock_snapshot = self._build_lock_frame_surface()
# # # # #         self.break_style = self._choose_break_style()
# # # # #         self.break_dur = float(LOCK_BREAK_DURATIONS.get(self.break_style, 0.85))
# # # # #         self.lock_trans = self.LOCK_TRANS_BREAK
# # # # #         self.lock_trans_t0 = time.time()
# # # # #         self.break_pieces = self._make_break_pieces(self.lock_snapshot, self.break_style)
# # # # #
# # # # #     def _make_break_pieces(self, snap: pygame.Surface, style: str) -> List[Dict[str, Any]]:
# # # # #         pieces: List[Dict[str, Any]] = []
# # # # #         W, H = self.W, self.H
# # # # #
# # # # #         # Determine tiling
# # # # #         if style == "blinds":
# # # # #             n = 16
# # # # #             tile_w = max(16, W // n)
# # # # #             for i in range(n):
# # # # #                 x = i * tile_w
# # # # #                 w = tile_w if i < n - 1 else (W - x)
# # # # #                 rect = pygame.Rect(x, 0, w, H)
# # # # #                 surf = snap.subsurface(rect).copy()
# # # # #                 # slide alternately left/right
# # # # #                 dir_sign = -1 if (i % 2 == 0) else 1
# # # # #                 vx = dir_sign * random.uniform(250, 450)
# # # # #                 pieces.append({
# # # # #                     "surf": surf,
# # # # #                     "pos": [float(rect.x), float(rect.y)],
# # # # #                     "vel": [vx, random.uniform(-40, 40)],
# # # # #                     "rot": 0.0,
# # # # #                     "ang": random.uniform(-30, 30),
# # # # #                     "rect": rect,
# # # # #                 })
# # # # #             return pieces
# # # # #
# # # # #         # Shatter/explode/drop use grid tiles
# # # # #         target = LOCK_SHATTER_TILE_TARGET
# # # # #         cols = int(math.sqrt(target * (W / max(1.0, H))))
# # # # #         cols = max(6, min(30, cols))
# # # # #         rows = max(6, min(24, int(target / cols)))
# # # # #         tile_w = max(18, W // cols)
# # # # #         tile_h = max(18, H // rows)
# # # # #
# # # # #         for y in range(0, H, tile_h):
# # # # #             for x in range(0, W, tile_w):
# # # # #                 rect = pygame.Rect(x, y, min(tile_w, W - x), min(tile_h, H - y))
# # # # #                 surf = snap.subsurface(rect).copy()
# # # # #                 cx = rect.centerx - W / 2.0
# # # # #                 cy = rect.centery - H / 2.0
# # # # #
# # # # #                 if style == "explode":
# # # # #                     # outward velocity
# # # # #                     mag = random.uniform(220, 520)
# # # # #                     ang = math.atan2(cy, cx) + random.uniform(-0.25, 0.25)
# # # # #                     vx = math.cos(ang) * mag
# # # # #                     vy = math.sin(ang) * mag
# # # # #                     rot = random.uniform(-25, 25)
# # # # #                     pieces.append({
# # # # #                         "surf": surf,
# # # # #                         "pos": [float(rect.x), float(rect.y)],
# # # # #                         "vel": [vx, vy],
# # # # #                         "rot": 0.0,
# # # # #                         "ang": rot,
# # # # #                         "rect": rect,
# # # # #                     })
# # # # #                 elif style == "drop":
# # # # #                     # mostly downward
# # # # #                     vx = random.uniform(-80, 80)
# # # # #                     vy = random.uniform(50, 160)
# # # # #                     rot = random.uniform(-18, 18)
# # # # #                     pieces.append({
# # # # #                         "surf": surf,
# # # # #                         "pos": [float(rect.x), float(rect.y)],
# # # # #                         "vel": [vx, vy],
# # # # #                         "rot": 0.0,
# # # # #                         "ang": rot,
# # # # #                         "rect": rect,
# # # # #                     })
# # # # #                 else:
# # # # #                     # shatter
# # # # #                     vx = random.uniform(-260, 260) + (cx * 0.25)
# # # # #                     vy = random.uniform(-180, 120) + (cy * 0.20)
# # # # #                     rot = random.uniform(-35, 35)
# # # # #                     pieces.append({
# # # # #                         "surf": surf,
# # # # #                         "pos": [float(rect.x), float(rect.y)],
# # # # #                         "vel": [vx, vy],
# # # # #                         "rot": 0.0,
# # # # #                         "ang": rot,
# # # # #                         "rect": rect,
# # # # #                     })
# # # # #
# # # # #         return pieces
# # # # #
# # # # #     def _draw_break(self, t: float):
# # # # #         # t in [0,1]
# # # # #         self.screen.fill((0, 0, 0))
# # # # #         # update and draw pieces
# # # # #         dt = 1.0 / 60.0
# # # # #         grav = LOCK_SHATTER_GRAVITY
# # # # #
# # # # #         for p in self.break_pieces:
# # # # #             vx, vy = p["vel"]
# # # # #             if self.break_style in ("shatter", "drop"):
# # # # #                 vy += grav * dt * (0.70 if self.break_style == "drop" else 0.40)
# # # # #                 p["vel"][1] = vy
# # # # #
# # # # #             p["pos"][0] += vx * dt
# # # # #             p["pos"][1] += vy * dt
# # # # #
# # # # #             # slight damping towards end
# # # # #             damp = 1.0 - (0.12 * t)
# # # # #             p["vel"][0] *= damp
# # # # #             p["vel"][1] *= damp
# # # # #
# # # # #             # rotation
# # # # #             p["rot"] += p["ang"] * dt
# # # # #
# # # # #             surf = p["surf"]
# # # # #             if abs(p["rot"]) > 0.5:
# # # # #                 rs = pygame.transform.rotozoom(surf, p["rot"], 1.0)
# # # # #                 r = rs.get_rect(center=(p["pos"][0] + surf.get_width() / 2, p["pos"][1] + surf.get_height() / 2))
# # # # #                 self.screen.blit(rs, r.topleft)
# # # # #             else:
# # # # #                 self.screen.blit(surf, (p["pos"][0], p["pos"][1]))
# # # # #
# # # # #         # fade out as it breaks
# # # # #         ov = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
# # # # #         ov.fill((0, 0, 0, int(220 * _ease_in_quad(t))))
# # # # #         self.screen.blit(ov, (0, 0))
# # # # #
# # # # #     def _draw_fadein(self, t: float):
# # # # #         # t in [0,1]
# # # # #         self._draw_lock_frame_to(self.screen)
# # # # #         a = int(255 * (1.0 - _ease_out_cubic(t)))
# # # # #         ov = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
# # # # #         ov.fill((0, 0, 0, a))
# # # # #         self.screen.blit(ov, (0, 0))
# # # # #
# # # # #     # ============================================================
# # # # #     # Square puzzle
# # # # #     # ============================================================
# # # # #     def _square_setup(self):
# # # # #         if self.board_surf is None:
# # # # #             return
# # # # #
# # # # #         # Build slots within board area with margins so it looks cleaner
# # # # #         margin = 40
# # # # #         usable_w = self.W - margin * 2
# # # # #         usable_h = self.BOARD_H - margin * 2
# # # # #         cols, rows = GRID_X, GRID_Y
# # # # #
# # # # #         self.tile_w = usable_w // cols
# # # # #         self.tile_h = usable_h // rows
# # # # #
# # # # #         # Slot positions in board space
# # # # #         self.slot_positions = []
# # # # #         for j in range(rows):
# # # # #             for i in range(cols):
# # # # #                 sx = margin + i * self.tile_w
# # # # #                 sy = margin + j * self.tile_h
# # # # #                 self.slot_positions.append((sx, sy))
# # # # #
# # # # #         # Slice the board_surf into pieces
# # # # #         board_scaled = pygame.transform.smoothscale(self.board_surf, (usable_w, usable_h))
# # # # #         tiles: List[Dict[str, Any]] = []
# # # # #
# # # # #         for j in range(rows):
# # # # #             for i in range(cols):
# # # # #                 src_rect = pygame.Rect(i * self.tile_w, j * self.tile_h, self.tile_w, self.tile_h)
# # # # #                 surf = board_scaled.subsurface(src_rect).copy()
# # # # #                 # add a small border / rounding feel
# # # # #                 tile = pygame.Surface((self.tile_w, self.tile_h), pygame.SRCALPHA)
# # # # #                 tile.blit(surf, (0, 0))
# # # # #                 pygame.draw.rect(tile, (255, 255, 255, 70), pygame.Rect(0, 0, self.tile_w, self.tile_h), 2, border_radius=10)
# # # # #
# # # # #                 correct = self.slot_positions[j * cols + i]
# # # # #                 pos = tray_random_pos_sized(self.W, self.tray_rect, self.tile_w, self.tile_h)
# # # # #                 tiles.append({
# # # # #                     "surf": tile,
# # # # #                     "correct": correct,
# # # # #                     "pos": [float(pos[0]), float(pos[1])],
# # # # #                     "locked": False,
# # # # #                     "fall_from": [float(pos[0]), float(-self.tile_h - random.randint(20, 400))],
# # # # #                     "fall_to": [float(pos[0]), float(pos[1])],
# # # # #                 })
# # # # #
# # # # #         # Shuffle piece order so it’s not already in order
# # # # #         random.shuffle(tiles)
# # # # #
# # # # #         self.tiles = tiles
# # # # #         self.drag_tile = None
# # # # #         self.puz_stage = self.PUZ_INTRO
# # # # #         self.puz_t0 = time.time()
# # # # #
# # # # #     def _square_all_locked(self) -> bool:
# # # # #         return all(t["locked"] for t in self.tiles)
# # # # #
# # # # #     def _square_slot_occupied(self, slot_xy: Tuple[int, int]) -> bool:
# # # # #         for t in self.tiles:
# # # # #             if t["locked"] and tuple(map(int, t["pos"])) == slot_xy:
# # # # #                 return True
# # # # #         return False
# # # # #
# # # # #     def _square_find_tile_at(self, x: int, y: int) -> Optional[Dict[str, Any]]:
# # # # #         # topmost (iterate reverse)
# # # # #         for t in reversed(self.tiles):
# # # # #             if t["locked"]:
# # # # #                 continue
# # # # #             r = pygame.Rect(int(t["pos"][0]), int(t["pos"][1]), self.tile_w, self.tile_h)
# # # # #             if r.collidepoint((x, y)):
# # # # #                 return t
# # # # #         return None
# # # # #
# # # # #     def _square_draw(self):
# # # # #         # Plain background (no fullscreen image)
# # # # #         self.screen.fill(COLOR_BG)
# # # # #
# # # # #         # Top label
# # # # #         title = self.font_brand2.render("Unlock Puzzle", True, (230, 230, 230))
# # # # #         self.screen.blit(title, (self.W // 2 - title.get_width() // 2, 18))
# # # # #
# # # # #         # Board panel
# # # # #         board_panel = pygame.Rect(18, 60, self.W - 36, self.BOARD_H - 78)
# # # # #         pygame.draw.rect(self.screen, (10, 10, 10), board_panel, border_radius=22)
# # # # #         pygame.draw.rect(self.screen, (110, 110, 110), board_panel, 2, border_radius=22)
# # # # #
# # # # #         # Draw slots (empty outlines)
# # # # #         margin = 40
# # # # #         cols, rows = GRID_X, GRID_Y
# # # # #         usable_w = self.W - margin * 2
# # # # #         usable_h = self.BOARD_H - margin * 2
# # # # #         tile_w = usable_w // cols
# # # # #         tile_h = usable_h // rows
# # # # #
# # # # #         for j in range(rows):
# # # # #             for i in range(cols):
# # # # #                 sx = margin + i * tile_w
# # # # #                 sy = margin + j * tile_h
# # # # #                 slot_rect = pygame.Rect(sx, sy, tile_w, tile_h)
# # # # #                 pygame.draw.rect(self.screen, (55, 55, 55), slot_rect, 2, border_radius=10)
# # # # #
# # # # #         # Tray
# # # # #         pygame.draw.rect(self.screen, COLOR_TRAY, self.tray_rect)
# # # # #         pygame.draw.line(self.screen, COLOR_LINE, (0, self.BOARD_H), (self.W, self.BOARD_H), 2)
# # # # #
# # # # #         tray_label = self.font_small.render("Drag pieces into place.", True, (220, 220, 220))
# # # # #         self.screen.blit(tray_label, (18, self.BOARD_H + 10))
# # # # #
# # # # #         # Back button
# # # # #         mx, my = pygame.mouse.get_pos()
# # # # #         draw_button(self.screen, self.back_btn, self.font_small, self.font_small, active=self.back_btn["rect"].collidepoint((mx, my)), small=True)
# # # # #
# # # # #         # Draw tiles
# # # # #         for t in self.tiles:
# # # # #             self.screen.blit(t["surf"], (t["pos"][0], t["pos"][1]))
# # # # #
# # # # #         # Stage overlays
# # # # #         if self.puz_stage == self.PUZ_INTRO and self.board_surf is not None:
# # # # #             # Show a dimmed reference image on the board area only (not fullscreen background)
# # # # #             ref = pygame.transform.smoothscale(self.board_surf, (board_panel.w - 14, board_panel.h - 14))
# # # # #             ref_rect = ref.get_rect(center=board_panel.center)
# # # # #             overlay = pygame.Surface((ref.get_width(), ref.get_height()), pygame.SRCALPHA)
# # # # #             overlay.fill((0, 0, 0, 140))
# # # # #             self.screen.blit(ref, ref_rect.topleft)
# # # # #             self.screen.blit(overlay, ref_rect.topleft)
# # # # #
# # # # #             msg = self.font_small.render("Memorize the picture...", True, (240, 240, 240))
# # # # #             self.screen.blit(msg, (self.W // 2 - msg.get_width() // 2, board_panel.bottom - 34))
# # # # #
# # # # #     def _square_update_stage(self):
# # # # #         now = time.time()
# # # # #         if self.puz_stage == self.PUZ_INTRO:
# # # # #             if (now - self.puz_t0) >= PUZ_INTRO_HOLD_S:
# # # # #                 # Begin fall animation
# # # # #                 for t in self.tiles:
# # # # #                     # establish new random tray position
# # # # #                     pos = tray_random_pos_sized(self.W, self.tray_rect, self.tile_w, self.tile_h)
# # # # #                     t["fall_from"] = [float(pos[0]), float(-self.tile_h - random.randint(20, 400))]
# # # # #                     t["fall_to"] = [float(pos[0]), float(pos[1])]
# # # # #                     t["pos"] = [t["fall_from"][0], t["fall_from"][1]]
# # # # #                 self.puz_stage = self.PUZ_FALL
# # # # #                 self.puz_t0 = now
# # # # #
# # # # #         elif self.puz_stage == self.PUZ_FALL:
# # # # #             t = (now - self.puz_t0) / max(0.001, PUZ_FALL_S)
# # # # #             if t >= 1.0:
# # # # #                 for tile in self.tiles:
# # # # #                     tile["pos"] = [tile["fall_to"][0], tile["fall_to"][1]]
# # # # #                 self.puz_stage = self.PUZ_PLAY
# # # # #                 self.puz_t0 = now
# # # # #             else:
# # # # #                 tt = _ease_out_cubic(t)
# # # # #                 for tile in self.tiles:
# # # # #                     fx, fy = tile["fall_from"]
# # # # #                     tx, ty = tile["fall_to"]
# # # # #                     tile["pos"][0] = fx + (tx - fx) * tt
# # # # #                     tile["pos"][1] = fy + (ty - fy) * tt
# # # # #
# # # # #     def _square_handle_event(self, ev):
# # # # #         if ev.type == pygame.KEYDOWN:
# # # # #             if ev.key == pygame.K_ESCAPE:
# # # # #                 self.state = self.STATE_LOCK
# # # # #                 self.lock_pressed = None
# # # # #                 return
# # # # #
# # # # #         if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
# # # # #             pos = event_pos(ev, self.W, self.H)
# # # # #             if not pos:
# # # # #                 return
# # # # #             x, y = pos
# # # # #
# # # # #             if self.back_btn["rect"].collidepoint((x, y)):
# # # # #                 self.state = self.STATE_LOCK
# # # # #                 self.lock_pressed = None
# # # # #                 return
# # # # #
# # # # #             if self.puz_stage != self.PUZ_PLAY:
# # # # #                 return
# # # # #
# # # # #             t = self._square_find_tile_at(x, y)
# # # # #             if t:
# # # # #                 play(self.snd_pick)
# # # # #                 self.drag_tile = t
# # # # #                 self.drag_ox = x - int(t["pos"][0])
# # # # #                 self.drag_oy = y - int(t["pos"][1])
# # # # #                 # bring to top
# # # # #                 self.tiles.remove(t)
# # # # #                 self.tiles.append(t)
# # # # #
# # # # #         if ev.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
# # # # #             if self.drag_tile is None:
# # # # #                 return
# # # # #             pos = event_pos(ev, self.W, self.H)
# # # # #             if not pos:
# # # # #                 return
# # # # #             x, y = pos
# # # # #             self.drag_tile["pos"][0] = float(x - self.drag_ox)
# # # # #             self.drag_tile["pos"][1] = float(y - self.drag_oy)
# # # # #
# # # # #         if ev.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
# # # # #             if self.drag_tile is None:
# # # # #                 return
# # # # #             t = self.drag_tile
# # # # #             self.drag_tile = None
# # # # #             play(self.snd_drop)
# # # # #
# # # # #             # Snap to correct slot if close enough and slot not occupied
# # # # #             cx = int(t["pos"][0] + self.tile_w / 2)
# # # # #             cy = int(t["pos"][1] + self.tile_h / 2)
# # # # #
# # # # #             slot_x, slot_y = t["correct"]
# # # # #             slot_c = (slot_x + self.tile_w // 2, slot_y + self.tile_h // 2)
# # # # #
# # # # #             if dist2((cx, cy), slot_c) <= (SNAP_DIST * SNAP_DIST) and not self._square_slot_occupied((slot_x, slot_y)):
# # # # #                 t["pos"][0] = float(slot_x)
# # # # #                 t["pos"][1] = float(slot_y)
# # # # #                 t["locked"] = True
# # # # #                 play(self.snd_snap)
# # # # #
# # # # #                 if self._square_all_locked():
# # # # #                     bg = self.screen.copy()
# # # # #                     unlock_success_overlay(self.screen, self.clock, self.W, self.H, self.font_brand, self.font_small,
# # # # #                                           self.snd_snap, msg="UNLOCKED", sub="Returning to menu...", hold_s=UNLOCK_SUCCESS_S,
# # # # #                                           bg_frame_surf=bg)
# # # # #                     fade_to_black(self.screen, self.clock, self.W, self.H, base=bg, seconds=0.18)
# # # # #                     self.exit_unlocked()
# # # # #
# # # # #             # If not snapped, keep where dropped (no bounce-back)
# # # # #
# # # # #
# # # # # # ============================================================
# # # # #     # Jigsaw select + puzzle
# # # # # # ============================================================
# # # # #     def _draw_jig_select(self, selected: int):
# # # # #         self.screen.fill(COLOR_BG)
# # # # #
# # # # #         title = self.font_brand.render("Jigsaw Unlock", True, (255, 255, 255))
# # # # #         self.screen.blit(title, (self.W // 2 - title.get_width() // 2, 60))
# # # # #
# # # # #         sub = self.font_small.render("Select difficulty", True, (220, 220, 220))
# # # # #         self.screen.blit(sub, (self.W // 2 - sub.get_width() // 2, 120))
# # # # #
# # # # #         mx, my = pygame.mouse.get_pos()
# # # # #         draw_button(self.screen, self.back_btn, self.font_small, self.font_small, active=self.back_btn["rect"].collidepoint((mx, my)), small=True)
# # # # #
# # # # #         # List
# # # # #         row_h = 70
# # # # #         gap = 12
# # # # #         start_y = 170
# # # # #         for i, (name, c, r) in enumerate(JIG_DIFFICULTY_CHOICES):
# # # # #             rect = pygame.Rect(int(self.W * 0.18), start_y + i * (row_h + gap), int(self.W * 0.64), row_h)
# # # # #             active = rect.collidepoint((mx, my))
# # # # #             is_sel = (i == selected)
# # # # #             bg = (40, 40, 40) if is_sel else (22, 22, 22)
# # # # #             if active:
# # # # #                 bg = lighten(bg, 10)
# # # # #             pygame.draw.rect(self.screen, bg, rect, border_radius=16)
# # # # #             pygame.draw.rect(self.screen, (140, 140, 140), rect, 2, border_radius=16)
# # # # #
# # # # #             label = self.font.render(f"{name}", True, (240, 240, 240))
# # # # #             dims = self.font_small.render(f"{c} x {r}", True, (210, 210, 210))
# # # # #             self.screen.blit(label, (rect.x + 22, rect.centery - label.get_height() // 2))
# # # # #             self.screen.blit(dims, (rect.right - dims.get_width() - 22, rect.centery - dims.get_height() // 2))
# # # # #
# # # # #     def _hit_jig_choice(self, x: int, y: int) -> Optional[int]:
# # # # #         row_h = 70
# # # # #         gap = 12
# # # # #         start_y = 170
# # # # #         for i in range(len(JIG_DIFFICULTY_CHOICES)):
# # # # #             rect = pygame.Rect(int(self.W * 0.18), start_y + i * (row_h + gap), int(self.W * 0.64), row_h)
# # # # #             if rect.collidepoint((x, y)):
# # # # #                 return i
# # # # #         return None
# # # # #
# # # # #     def _jigsaw_setup(self, cols: int, rows: int):
# # # # #         if self.board_surf is None:
# # # # #             return
# # # # #
# # # # #         self.jig_cols, self.jig_rows = cols, rows
# # # # #         self.jig_snap_dist = calc_jig_snap_dist(self.W, self.BOARD_H, cols, rows)
# # # # #
# # # # #         pieces = build_jigsaw_pieces(self.W, self.BOARD_H, self.board_surf, cols, rows)
# # # # #
# # # # #         # Place pieces in tray area with fall animation
# # # # #         for p in pieces:
# # # # #             w, h = p["surf"].get_size()
# # # # #             pos = tray_random_pos_sized(self.W, self.tray_rect, w, h)
# # # # #             p["fall_from"] = [float(pos[0]), float(-h - random.randint(20, 400))]
# # # # #             p["fall_to"] = [float(pos[0]), float(pos[1])]
# # # # #             p["pos"] = [p["fall_from"][0], p["fall_from"][1]]
# # # # #             p["locked"] = False
# # # # #
# # # # #         random.shuffle(pieces)
# # # # #
# # # # #         self.jig_pieces = pieces
# # # # #         self.jig_drag_piece = None
# # # # #         self.jig_stage = self.JIG_INTRO
# # # # #         self.jig_t0 = time.time()
# # # # #
# # # # #     def _jigsaw_find_piece_at(self, x: int, y: int) -> Optional[Dict[str, Any]]:
# # # # #         # Topmost selection with mask hit-test
# # # # #         for p in reversed(self.jig_pieces):
# # # # #             if p.get("locked"):
# # # # #                 continue
# # # # #             px, py = int(p["pos"][0]), int(p["pos"][1])
# # # # #             lx, ly = x - px, y - py
# # # # #             if lx < 0 or ly < 0:
# # # # #                 continue
# # # # #             if lx >= p["surf"].get_width() or ly >= p["surf"].get_height():
# # # # #                 continue
# # # # #             if p["mask"].get_at((lx, ly)):
# # # # #                 return p
# # # # #         return None
# # # # #
# # # # #     def _jigsaw_update_stage(self):
# # # # #         now = time.time()
# # # # #         if self.jig_stage == self.JIG_INTRO:
# # # # #             if (now - self.jig_t0) >= JIG_INTRO_HOLD_S:
# # # # #                 self.jig_stage = self.JIG_FALL
# # # # #                 self.jig_t0 = now
# # # # #
# # # # #         elif self.jig_stage == self.JIG_FALL:
# # # # #             t = (now - self.jig_t0) / max(0.001, JIG_FALL_S)
# # # # #             if t >= 1.0:
# # # # #                 for p in self.jig_pieces:
# # # # #                     p["pos"] = [p["fall_to"][0], p["fall_to"][1]]
# # # # #                 self.jig_stage = self.JIG_PLAY
# # # # #                 self.jig_t0 = now
# # # # #             else:
# # # # #                 tt = _ease_out_cubic(t)
# # # # #                 for p in self.jig_pieces:
# # # # #                     fx, fy = p["fall_from"]
# # # # #                     tx, ty = p["fall_to"]
# # # # #                     p["pos"][0] = fx + (tx - fx) * tt
# # # # #                     p["pos"][1] = fy + (ty - fy) * tt
# # # # #
# # # # #     def _jigsaw_draw(self):
# # # # #         # Plain background
# # # # #         self.screen.fill(COLOR_BG)
# # # # #
# # # # #         title = self.font_brand2.render(f"Jigsaw {self.jig_cols} x {self.jig_rows}", True, (230, 230, 230))
# # # # #         self.screen.blit(title, (self.W // 2 - title.get_width() // 2, 18))
# # # # #
# # # # #         # Board panel
# # # # #         board_panel = pygame.Rect(18, 60, self.W - 36, self.BOARD_H - 78)
# # # # #         pygame.draw.rect(self.screen, (10, 10, 10), board_panel, border_radius=22)
# # # # #         pygame.draw.rect(self.screen, (110, 110, 110), board_panel, 2, border_radius=22)
# # # # #
# # # # #         # Optional faint reference in board area during intro
# # # # #         if self.jig_stage == self.JIG_INTRO and self.board_surf is not None:
# # # # #             ref = pygame.transform.smoothscale(self.board_surf, (board_panel.w - 14, board_panel.h - 14))
# # # # #             ref_rect = ref.get_rect(center=board_panel.center)
# # # # #             self.screen.blit(ref, ref_rect.topleft)
# # # # #             ov = pygame.Surface((ref.get_width(), ref.get_height()), pygame.SRCALPHA)
# # # # #             ov.fill((0, 0, 0, 155))
# # # # #             self.screen.blit(ov, ref_rect.topleft)
# # # # #             msg = self.font_small.render("Memorize the picture...", True, (240, 240, 240))
# # # # #             self.screen.blit(msg, (self.W // 2 - msg.get_width() // 2, board_panel.bottom - 34))
# # # # #
# # # # #         # Tray
# # # # #         pygame.draw.rect(self.screen, COLOR_TRAY, self.tray_rect)
# # # # #         pygame.draw.line(self.screen, COLOR_LINE, (0, self.BOARD_H), (self.W, self.BOARD_H), 2)
# # # # #
# # # # #         tray_label = self.font_small.render("Drag pieces into place (snaps when close).", True, (220, 220, 220))
# # # # #         self.screen.blit(tray_label, (18, self.BOARD_H + 10))
# # # # #
# # # # #         # Back button
# # # # #         mx, my = pygame.mouse.get_pos()
# # # # #         draw_button(self.screen, self.back_btn, self.font_small, self.font_small, active=self.back_btn["rect"].collidepoint((mx, my)), small=True)
# # # # #
# # # # #         # Draw pieces
# # # # #         for p in self.jig_pieces:
# # # # #             self.screen.blit(p["surf"], (p["pos"][0], p["pos"][1]))
# # # # #
# # # # #     def _jigsaw_handle_event(self, ev):
# # # # #         if ev.type == pygame.KEYDOWN:
# # # # #             if ev.key == pygame.K_ESCAPE:
# # # # #                 self.state = self.STATE_LOCK
# # # # #                 self.lock_pressed = None
# # # # #                 return
# # # # #
# # # # #         if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
# # # # #             pos = event_pos(ev, self.W, self.H)
# # # # #             if not pos:
# # # # #                 return
# # # # #             x, y = pos
# # # # #
# # # # #             if self.back_btn["rect"].collidepoint((x, y)):
# # # # #                 self.state = self.STATE_LOCK
# # # # #                 self.lock_pressed = None
# # # # #                 return
# # # # #
# # # # #             if self.jig_stage != self.JIG_PLAY:
# # # # #                 return
# # # # #
# # # # #             p = self._jigsaw_find_piece_at(x, y)
# # # # #             if p:
# # # # #                 play(self.snd_pick)
# # # # #                 self.jig_drag_piece = p
# # # # #                 self.jig_drag_ox = x - int(p["pos"][0])
# # # # #                 self.jig_drag_oy = y - int(p["pos"][1])
# # # # #                 # bring to top
# # # # #                 self.jig_pieces.remove(p)
# # # # #                 self.jig_pieces.append(p)
# # # # #
# # # # #         if ev.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
# # # # #             if self.jig_drag_piece is None:
# # # # #                 return
# # # # #             pos = event_pos(ev, self.W, self.H)
# # # # #             if not pos:
# # # # #                 return
# # # # #             x, y = pos
# # # # #             self.jig_drag_piece["pos"][0] = float(x - self.jig_drag_ox)
# # # # #             self.jig_drag_piece["pos"][1] = float(y - self.jig_drag_oy)
# # # # #
# # # # #         if ev.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
# # # # #             if self.jig_drag_piece is None:
# # # # #                 return
# # # # #             p = self.jig_drag_piece
# # # # #             self.jig_drag_piece = None
# # # # #             play(self.snd_drop)
# # # # #
# # # # #             # snap to correct
# # # # #             correct = p["correct_pos"]
# # # # #             px, py = p["pos"]
# # # # #             dx = (px - correct[0])
# # # # #             dy = (py - correct[1])
# # # # #             if (dx * dx + dy * dy) <= (self.jig_snap_dist * self.jig_snap_dist):
# # # # #                 p["pos"][0] = float(correct[0])
# # # # #                 p["pos"][1] = float(correct[1])
# # # # #                 p["locked"] = True
# # # # #                 play(self.snd_snap)
# # # # #
# # # # #                 if jigsaw_all_locked(self.jig_pieces):
# # # # #                     bg = self.screen.copy()
# # # # #                     unlock_success_overlay(self.screen, self.clock, self.W, self.H, self.font_brand, self.font_small,
# # # # #                                           self.snd_snap, msg="UNLOCKED", sub="Returning to menu...", hold_s=JIG_SOLVED_HOLD_S,
# # # # #                                           bg_frame_surf=bg)
# # # # #                     fade_to_black(self.screen, self.clock, self.W, self.H, base=bg, seconds=0.18)
# # # # #                     self.exit_unlocked()
# # # # #
# # # # #     # ============================================================
# # # # #     # Lock state input + draw
# # # # #     # ============================================================
# # # # #     def _draw_lock(self):
# # # # #         # Draw base lock frame or transition
# # # # #         if self.lock_trans == self.LOCK_TRANS_BREAK:
# # # # #             t = (time.time() - self.lock_trans_t0) / max(0.001, self.break_dur)
# # # # #             if t >= 1.0:
# # # # #                 # swap to next image and start fade-in
# # # # #                 self._advance_image()
# # # # #                 self.lock_trans = self.LOCK_TRANS_FADEIN
# # # # #                 self.lock_trans_t0 = time.time()
# # # # #                 self._draw_fadein(0.0)
# # # # #             else:
# # # # #                 self._draw_break(t)
# # # # #         elif self.lock_trans == self.LOCK_TRANS_FADEIN:
# # # # #             t = (time.time() - self.lock_trans_t0) / max(0.001, LOCK_FADEIN_S)
# # # # #             if t >= 1.0:
# # # # #                 self.lock_trans = self.LOCK_TRANS_NONE
# # # # #                 self.lock_trans_t0 = 0.0
# # # # #                 self._draw_lock_frame_to(self.screen)
# # # # #             else:
# # # # #                 self._draw_fadein(t)
# # # # #         else:
# # # # #             self._draw_lock_frame_to(self.screen)
# # # # #
# # # # #         # Brand
# # # # #         title = self.font_brand.render(BRAND_TEXT, True, (255, 255, 255))
# # # # #         subtitle = self.font_brand2.render(BRAND_SUB, True, (230, 230, 230))
# # # # #         self.screen.blit(title, (30, 70))
# # # # #         self.screen.blit(subtitle, (30, 135))
# # # # #
# # # # #         # Status bar
# # # # #         self._draw_status_bar()
# # # # #
# # # # #         # Dock fade alpha
# # # # #         target = 255.0 if self._lock_ui_visible() else 0.0
# # # # #         # exponential-ish approach
# # # # #         dt = 1.0 / 60.0
# # # # #         step = (255.0 / max(0.001, LOCK_UI_FADE_S)) * dt
# # # # #         if self.ui_alpha < target:
# # # # #             self.ui_alpha = min(target, self.ui_alpha + step)
# # # # #         elif self.ui_alpha > target:
# # # # #             self.ui_alpha = max(target, self.ui_alpha - step)
# # # # #
# # # # #         a = int(self.ui_alpha)
# # # # #         if a > 0:
# # # # #             draw_modern_dock(self.screen, self.dock_rect, a)
# # # # #
# # # # #             mx, my = pygame.mouse.get_pos()
# # # # #             over_unlock = self.btn_unlock.collidepoint((mx, my))
# # # # #             over_jigsaw = self.btn_jigsaw.collidepoint((mx, my))
# # # # #             over_admin = self.btn_admin.collidepoint((mx, my))
# # # # #
# # # # #             pressed_unlock = (self.lock_pressed == "unlock")
# # # # #             pressed_jigsaw = (self.lock_pressed == "jigsaw")
# # # # #             pressed_admin = (self.lock_pressed == "admin")
# # # # #
# # # # #             draw_modern_button(self.screen, self.btn_unlock, "Unlock", self.font_dock,
# # # # #                                _draw_icon_lock, ACCENT_UNLOCK, over_unlock, pressed_unlock, a)
# # # # #             draw_modern_button(self.screen, self.btn_jigsaw, "Jigsaw", self.font_dock,
# # # # #                                _draw_icon_jigsaw, ACCENT_JIGSAW, over_jigsaw, pressed_jigsaw, a)
# # # # #             draw_modern_button(self.screen, self.btn_admin, "PIN", self.font_dock,
# # # # #                                _draw_icon_key, ACCENT_ADMIN, over_admin, pressed_admin, a)
# # # # #
# # # # #         # tiny hint bottom-left
# # # # #         hint = self.font_small.render("Tap to show controls", True, (220, 220, 220))
# # # # #         hint.set_alpha(140)
# # # # #         self.screen.blit(hint, (24, self.H - 34))
# # # # #
# # # # #     def _lock_handle_event(self, ev):
# # # # #         if ev.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
# # # # #             pos = event_pos(ev, self.W, self.H)
# # # # #             if pos:
# # # # #                 x, y = pos
# # # # #                 lx, ly = self.last_mouse_pos
# # # # #                 if abs(x - lx) + abs(y - ly) >= LOCK_UI_MOUSE_MOVE_THRESH:
# # # # #                     self._touch_lock_ui()
# # # # #                 self.last_mouse_pos = (x, y)
# # # # #
# # # # #         if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
# # # # #             self._touch_lock_ui()
# # # # #             pos = event_pos(ev, self.W, self.H)
# # # # #             if not pos:
# # # # #                 return
# # # # #             x, y = pos
# # # # #
# # # # #             if self.ui_alpha >= 40:
# # # # #                 if self.btn_unlock.collidepoint((x, y)):
# # # # #                     self.lock_pressed = "unlock"
# # # # #                     play(self.snd_pick)
# # # # #                 elif self.btn_jigsaw.collidepoint((x, y)):
# # # # #                     self.lock_pressed = "jigsaw"
# # # # #                     play(self.snd_pick)
# # # # #                 elif self.btn_admin.collidepoint((x, y)):
# # # # #                     self.lock_pressed = "admin"
# # # # #                     play(self.snd_pick)
# # # # #                 else:
# # # # #                     self.lock_pressed = None
# # # # #
# # # # #         if ev.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
# # # # #             pos = event_pos(ev, self.W, self.H)
# # # # #             if not pos:
# # # # #                 self.lock_pressed = None
# # # # #                 return
# # # # #             x, y = pos
# # # # #
# # # # #             pressed = self.lock_pressed
# # # # #             self.lock_pressed = None
# # # # #             if pressed is None:
# # # # #                 return
# # # # #
# # # # #             # Button action
# # # # #             if pressed == "unlock" and self.btn_unlock.collidepoint((x, y)):
# # # # #                 self._square_setup()
# # # # #                 self.state = self.STATE_SQUARE
# # # # #                 return
# # # # #
# # # # #             if pressed == "jigsaw" and self.btn_jigsaw.collidepoint((x, y)):
# # # # #                 self.state = self.STATE_JIG_SELECT
# # # # #                 return
# # # # #
# # # # #             if pressed == "admin" and self.btn_admin.collidepoint((x, y)):
# # # # #                 # Admin PIN overlay
# # # # #                 bg = self.screen.copy()
# # # # #                 ok = pin_overlay_loop(self.screen, self.clock, self.W, self.H, bg, self.font, self.font_small, self.snd_error)
# # # # #                 if ok:
# # # # #                     bg2 = self.screen.copy()
# # # # #                     unlock_success_overlay(self.screen, self.clock, self.W, self.H, self.font_brand, self.font_small,
# # # # #                                           self.snd_snap, msg="UNLOCKED", sub="Returning to menu...", hold_s=UNLOCK_SUCCESS_S,
# # # # #                                           bg_frame_surf=bg2)
# # # # #                     fade_to_black(self.screen, self.clock, self.W, self.H, base=bg2, seconds=0.18)
# # # # #                     self.exit_unlocked()
# # # # #                 return
# # # # #
# # # # #         if ev.type == pygame.KEYDOWN:
# # # # #             self._touch_lock_ui()
# # # # #             if ev.key == pygame.K_ESCAPE:
# # # # #                 # stay locked, ignore
# # # # #                 return
# # # # #             if ev.key == pygame.K_RETURN or ev.key == pygame.K_KP_ENTER:
# # # # #                 # convenience: enter starts unlock
# # # # #                 self._square_setup()
# # # # #                 self.state = self.STATE_SQUARE
# # # # #                 return
# # # # #             if ev.key == pygame.K_j:
# # # # #                 self.state = self.STATE_JIG_SELECT
# # # # #                 return
# # # # #
# # # # #     # ============================================================
# # # # #     # Main loop
# # # # #     # ============================================================
# # # # #     def run(self):
# # # # #         selected_jig = 1  # default Normal
# # # # #
# # # # #         prev_time = time.time()
# # # # #         while True:
# # # # #             now = time.time()
# # # # #             dt = now - prev_time
# # # # #             prev_time = now
# # # # #
# # # # #             # Slide / pan updates only in lock mode and only when not in puzzles
# # # # #             if self.state == self.STATE_LOCK:
# # # # #                 self._update_pan(dt)
# # # # #
# # # # #                 # slideshow cycle when no transition playing
# # # # #                 if self.lock_trans == self.LOCK_TRANS_NONE and LOCK_TRANSITION_ENABLE:
# # # # #                     if (now - self.lock_cycle_t0) >= LOCK_BG_CYCLE_S:
# # # # #                         self._begin_lock_transition()
# # # # #
# # # # #             # handle events
# # # # #             for ev in pygame.event.get():
# # # # #                 if ev.type == pygame.QUIT:
# # # # #                     raise SystemExit
# # # # #
# # # # #                 if self.state == self.STATE_LOCK:
# # # # #                     self._lock_handle_event(ev)
# # # # #
# # # # #                 elif self.state == self.STATE_SQUARE:
# # # # #                     self._square_handle_event(ev)
# # # # #
# # # # #                 elif self.state == self.STATE_JIG_SELECT:
# # # # #                     if ev.type == pygame.KEYDOWN:
# # # # #                         if ev.key == pygame.K_ESCAPE:
# # # # #                             self.state = self.STATE_LOCK
# # # # #                             continue
# # # # #                         if ev.key == pygame.K_UP:
# # # # #                             selected_jig = max(0, selected_jig - 1)
# # # # #                         if ev.key == pygame.K_DOWN:
# # # # #                             selected_jig = min(len(JIG_DIFFICULTY_CHOICES) - 1, selected_jig + 1)
# # # # #                         if ev.key == pygame.K_RETURN or ev.key == pygame.K_KP_ENTER:
# # # # #                             name, c, r = JIG_DIFFICULTY_CHOICES[selected_jig]
# # # # #                             self._jigsaw_setup(c, r)
# # # # #                             self.state = self.STATE_JIGSAW
# # # # #                             continue
# # # # #                     if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
# # # # #                         pos = event_pos(ev, self.W, self.H)
# # # # #                         if pos:
# # # # #                             x, y = pos
# # # # #                             if self.back_btn["rect"].collidepoint((x, y)):
# # # # #                                 self.state = self.STATE_LOCK
# # # # #                                 continue
# # # # #                             hit = self._hit_jig_choice(x, y)
# # # # #                             if hit is not None:
# # # # #                                 selected_jig = hit
# # # # #                                 name, c, r = JIG_DIFFICULTY_CHOICES[selected_jig]
# # # # #                                 self._jigsaw_setup(c, r)
# # # # #                                 self.state = self.STATE_JIGSAW
# # # # #                                 continue
# # # # #
# # # # #                 elif self.state == self.STATE_JIGSAW:
# # # # #                     self._jigsaw_handle_event(ev)
# # # # #
# # # # #             # update puzzle stages
# # # # #             if self.state == self.STATE_SQUARE:
# # # # #                 self._square_update_stage()
# # # # #             if self.state == self.STATE_JIGSAW:
# # # # #                 self._jigsaw_update_stage()
# # # # #
# # # # #             # draw
# # # # #             if self.state == self.STATE_LOCK:
# # # # #                 self._draw_lock()
# # # # #             elif self.state == self.STATE_SQUARE:
# # # # #                 self._square_draw()
# # # # #             elif self.state == self.STATE_JIG_SELECT:
# # # # #                 self._draw_jig_select(selected_jig)
# # # # #             elif self.state == self.STATE_JIGSAW:
# # # # #                 self._jigsaw_draw()
# # # # #
# # # # #             pygame.display.flip()
# # # # #             self.clock.tick(60)
# # # # #
# # # # #
# # # # # # ============================================================
# # # # # # Entrypoint
# # # # # # ============================================================
# # # # # if __name__ == "__main__":
# # # # #     LockApp().run()
# # # # #!/usr/bin/env python3
# # # # # -*- coding: utf-8 -*-
# # # # """
# # # # puzzle_lock.py — Full file (drop-in replacement)
# # # #
# # # # Fix for “light blue pygame bar / WM title-bar flash between pygame files”:
# # # # - Support *shared window* mode: if a screen is passed in, DO NOT call pygame.display.set_mode().
# # # # - Return to caller instead of sys.exit() so kiosk_shell can keep the one SDL window alive.
# # # #
# # # # This eliminates the window creation/destruction cycle that causes Openbox/WM to flash a title bar.
# # # # """
# # # #
# # # # import os
# # # # import sys
# # # # import time
# # # # import math
# # # # import random
# # # # import datetime
# # # # from typing import Optional, Tuple, List, Dict, Any
# # # #
# # # # os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
# # # # os.environ.setdefault("SDL_VIDEODRIVER", "x11")
# # # # os.environ.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")
# # # # os.environ.pop("WAYLAND_DISPLAY", None)
# # # # os.environ.pop("WAYLAND_SOCKET", None)
# # # #
# # # # import pygame  # noqa: E402
# # # #
# # # #
# # # # # ============================================================
# # # # # Configuration
# # # # # ============================================================
# # # # BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# # # # IMAGE_DIR = os.path.join(BASE_DIR, "images")
# # # # SOUNDS_DIR = os.path.join(BASE_DIR, "sounds")
# # # #
# # # # BRAND_TEXT = "Glover SPARCstation"
# # # # BRAND_SUB = "Puzzle Lock"
# # # #
# # # # ADMIN_PIN = "1193"
# # # # PIN_MAX_LEN = 12
# # # #
# # # # SHOW_STATUS_BAR = True
# # # # STATUS_BAR_H = 40
# # # #
# # # # LOCK_UI_START_HIDDEN = True
# # # # LOCK_UI_AUTOHIDE_S = 6.0
# # # # LOCK_UI_MOUSE_MOVE_THRESH = 10
# # # # LOCK_UI_FADE_S = 0.18
# # # #
# # # # LOCK_BG_CYCLE_S = 18.0
# # # # LOCK_VISIBLE_SCALE_MODE = "contain"  # "contain" | "cover"
# # # #
# # # # LOCK_BG_PAN_RANGE_PX = 900
# # # # LOCK_BG_PAN_SPEED_PX_S = 90.0
# # # #
# # # # LOCK_BG_BLUR_METHOD = "hq"  # "hq" | "downscale"
# # # # LOCK_BG_HQ_DOWNSCALE = 2
# # # # LOCK_BG_HQ_RADIUS = 10
# # # #
# # # # LOCK_BG_BLUR_DOWNSCALE = 12
# # # # LOCK_BG_DIM_ALPHA = 60
# # # #
# # # # LOCK_TRANSITION_ENABLE = True
# # # # LOCK_FADEIN_S = 0.55
# # # #
# # # # LOCK_TRANSITION_STYLES = ["shatter", "blinds", "explode", "drop"]
# # # # LOCK_TRANSITION_STYLE = "random"
# # # # LOCK_BREAK_DURATIONS = {
# # # #     "shatter": 0.85,
# # # #     "blinds": 0.95,
# # # #     "explode": 0.80,
# # # #     "drop": 0.90,
# # # # }
# # # # LOCK_SHATTER_TILE_TARGET = 180
# # # # LOCK_SHATTER_GRAVITY = 1200.0
# # # #
# # # # LOCK_BG_RANDOM_START = True
# # # # LOCK_BG_SHUFFLE = False
# # # #
# # # # COLOR_BG = (0, 0, 0)
# # # # COLOR_TRAY = (18, 18, 18)
# # # # COLOR_LINE = (70, 70, 70)
# # # #
# # # # ACCENT_UNLOCK = (70, 185, 120)
# # # # ACCENT_JIGSAW = (170, 170, 170)
# # # # ACCENT_ADMIN = (120, 200, 255)
# # # #
# # # # SND_PICK = "pick.wav"
# # # # SND_DROP = "drop.wav"
# # # # SND_SNAP = "snap.wav"
# # # # SND_ERROR = "error.wav"
# # # #
# # # # GRID_X = 3
# # # # GRID_Y = 4
# # # # TRAY_H_FRAC = 0.28
# # # # TRAY_MARGIN = 14
# # # # SNAP_DIST = 190
# # # #
# # # # PUZ_INTRO_HOLD_S = 0.55
# # # # PUZ_FALL_S = 0.85
# # # # UNLOCK_SUCCESS_S = 0.85
# # # #
# # # # JIG_KNOB_FRAC = 0.22
# # # # JIG_EDGE_OFF_FRAC = 0.18
# # # #
# # # # JIG_SNAP_FRAC = 0.55
# # # # JIG_SNAP_MIN = 40
# # # # JIG_SNAP_MAX = 140
# # # #
# # # # JIG_INTRO_HOLD_S = 0.55
# # # # JIG_FALL_S = 0.85
# # # # JIG_SOLVED_HOLD_S = 0.85
# # # #
# # # # JIG_DIFFICULTY_CHOICES = [
# # # #     ("Easy", 3, 2),
# # # #     ("Normal", 4, 3),
# # # #     ("Hard", 5, 4),
# # # #     ("Expert", 6, 4),
# # # #     ("Insane", 10, 5),
# # # #     ("Extreme", 12, 5),
# # # # ]
# # # #
# # # # PUZZLE_BOARD_SCALE_MODE = "cover"  # "cover" | "contain"
# # # #
# # # #
# # # # # ============================================================
# # # # # Helpers
# # # # # ============================================================
# # # # def clamp255(v: float) -> int:
# # # #     return max(0, min(255, int(v)))
# # # #
# # # # def lighten(color, amt=22):
# # # #     return (clamp255(color[0] + amt), clamp255(color[1] + amt), clamp255(color[2] + amt))
# # # #
# # # # def _ease_in_quad(t: float) -> float:
# # # #     return t * t
# # # #
# # # # def _ease_out_cubic(t: float) -> float:
# # # #     u = 1.0 - t
# # # #     return 1.0 - (u * u * u)
# # # #
# # # # def dist2(a: Tuple[int, int], b: Tuple[int, int]) -> float:
# # # #     dx = a[0] - b[0]
# # # #     dy = a[1] - b[1]
# # # #     return dx * dx + dy * dy
# # # #
# # # # def load_sound(name: str):
# # # #     path = os.path.join(SOUNDS_DIR, name)
# # # #     if os.path.exists(path):
# # # #         try:
# # # #             return pygame.mixer.Sound(path)
# # # #         except Exception:
# # # #             return None
# # # #     return None
# # # #
# # # # def play(snd):
# # # #     if snd:
# # # #         try:
# # # #             snd.play()
# # # #         except Exception:
# # # #             pass
# # # #
# # # # def event_pos(ev, W: int, H: int):
# # # #     if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
# # # #         return ev.pos
# # # #     if ev.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
# # # #         return (int(ev.x * W), int(ev.y * H))
# # # #     return None
# # # #
# # # # def safe_load_image(path: str) -> pygame.Surface:
# # # #     try:
# # # #         from PIL import Image, ImageOps  # type: ignore
# # # #         img = Image.open(path)
# # # #         img = ImageOps.exif_transpose(img)
# # # #         if img.mode in ("RGBA", "LA") or ("transparency" in img.info):
# # # #             img = img.convert("RGBA")
# # # #             surf = pygame.image.frombuffer(img.tobytes(), img.size, "RGBA").convert_alpha()
# # # #         else:
# # # #             img = img.convert("RGB")
# # # #             surf = pygame.image.frombuffer(img.tobytes(), img.size, "RGB").convert()
# # # #         return surf
# # # #     except Exception:
# # # #         surf = pygame.image.load(path)
# # # #         try:
# # # #             return surf.convert_alpha() if surf.get_alpha() is not None else surf.convert()
# # # #         except Exception:
# # # #             return surf
# # # #
# # # # def scale_cover(src_surf: pygame.Surface, target_w: int, target_h: int) -> pygame.Surface:
# # # #     sw, sh = src_surf.get_size()
# # # #     if sw <= 0 or sh <= 0:
# # # #         return pygame.Surface((target_w, target_h))
# # # #     scale = max(target_w / sw, target_h / sh)
# # # #     nw = int(sw * scale)
# # # #     nh = int(sh * scale)
# # # #     scaled = pygame.transform.smoothscale(src_surf, (nw, nh))
# # # #     x = (nw - target_w) // 2
# # # #     y = (nh - target_h) // 2
# # # #     return scaled.subsurface(pygame.Rect(x, y, target_w, target_h)).copy()
# # # #
# # # # def scale_contain(src_surf: pygame.Surface, target_w: int, target_h: int):
# # # #     sw, sh = src_surf.get_size()
# # # #     if sw <= 0 or sh <= 0:
# # # #         blank = pygame.Surface((target_w, target_h))
# # # #         return blank, blank.get_rect()
# # # #     scale = min(target_w / sw, target_h / sh)
# # # #     nw = max(1, int(sw * scale))
# # # #     nh = max(1, int(sh * scale))
# # # #     scaled = pygame.transform.smoothscale(src_surf, (nw, nh))
# # # #     rect = scaled.get_rect(center=(target_w // 2, target_h // 2))
# # # #     return scaled, rect
# # # #
# # # # def blur_surface_once(src: pygame.Surface, downscale: int = 12) -> pygame.Surface:
# # # #     downscale = max(2, int(downscale))
# # # #     w, h = src.get_size()
# # # #     dw = max(2, w // downscale)
# # # #     dh = max(2, h // downscale)
# # # #     small = pygame.transform.smoothscale(src, (dw, dh))
# # # #     return pygame.transform.smoothscale(small, (w, h))
# # # #
# # # # def blur_surface_hq(src: pygame.Surface, radius: int = 10, downscale: int = 2) -> pygame.Surface:
# # # #     try:
# # # #         from PIL import Image, ImageFilter  # type: ignore
# # # #         w, h = src.get_size()
# # # #         if w <= 2 or h <= 2:
# # # #             return src
# # # #         ds = max(1, int(downscale))
# # # #         if ds > 1:
# # # #             sw = max(2, w // ds)
# # # #             sh = max(2, h // ds)
# # # #             src_small = pygame.transform.smoothscale(src, (sw, sh))
# # # #             raw = pygame.image.tostring(src_small, "RGB")
# # # #             im = Image.frombytes("RGB", (sw, sh), raw)
# # # #         else:
# # # #             raw = pygame.image.tostring(src, "RGB")
# # # #             im = Image.frombytes("RGB", (w, h), raw)
# # # #         im = im.filter(ImageFilter.GaussianBlur(radius=max(0, int(radius))))
# # # #         if ds > 1:
# # # #             im = im.resize((w, h), resample=Image.LANCZOS)
# # # #         out = pygame.image.frombuffer(im.tobytes(), (w, h), "RGB").convert()
# # # #         return out
# # # #     except Exception:
# # # #         return blur_surface_once(src, LOCK_BG_BLUR_DOWNSCALE).convert()
# # # #
# # # #
# # # # # ============================================================
# # # # # UI drawing helpers
# # # # # ============================================================
# # # # def _draw_round_rect_alpha(dst, rect: pygame.Rect, rgb, alpha: int, radius: int):
# # # #     alpha = clamp255(alpha)
# # # #     s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
# # # #     pygame.draw.rect(s, (rgb[0], rgb[1], rgb[2], alpha), pygame.Rect(0, 0, rect.w, rect.h), border_radius=radius)
# # # #     dst.blit(s, rect.topleft)
# # # #
# # # # def _draw_round_rect_outline_alpha(dst, rect: pygame.Rect, rgb, alpha: int, radius: int, width: int = 2):
# # # #     alpha = clamp255(alpha)
# # # #     s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
# # # #     pygame.draw.rect(s, (rgb[0], rgb[1], rgb[2], alpha), pygame.Rect(0, 0, rect.w, rect.h), width, border_radius=radius)
# # # #     dst.blit(s, rect.topleft)
# # # #
# # # # def _draw_icon_lock(dst, center, color, alpha=255):
# # # #     cx, cy = center
# # # #     a = clamp255(alpha)
# # # #     col = (color[0], color[1], color[2], a)
# # # #     s = pygame.Surface((40, 40), pygame.SRCALPHA)
# # # #     pygame.draw.arc(s, col, pygame.Rect(10, 6, 20, 18), math.pi, 0, 3)
# # # #     pygame.draw.rect(s, col, pygame.Rect(10, 18, 20, 16), border_radius=5)
# # # #     dst.blit(s, (cx - 20, cy - 20))
# # # #
# # # # def _draw_icon_jigsaw(dst, center, color, alpha=255):
# # # #     cx, cy = center
# # # #     a = clamp255(alpha)
# # # #     col = (color[0], color[1], color[2], a)
# # # #     s = pygame.Surface((40, 40), pygame.SRCALPHA)
# # # #     pygame.draw.rect(s, col, pygame.Rect(10, 10, 18, 14), 2, border_radius=3)
# # # #     pygame.draw.rect(s, col, pygame.Rect(14, 14, 18, 14), 2, border_radius=3)
# # # #     pygame.draw.line(s, col, (16, 24), (22, 18), 2)
# # # #     pygame.draw.line(s, col, (22, 18), (30, 26), 2)
# # # #     dst.blit(s, (cx - 20, cy - 20))
# # # #
# # # # def _draw_icon_key(dst, center, color, alpha=255):
# # # #     cx, cy = center
# # # #     a = clamp255(alpha)
# # # #     col = (color[0], color[1], color[2], a)
# # # #     s = pygame.Surface((40, 40), pygame.SRCALPHA)
# # # #     pygame.draw.circle(s, col, (14, 20), 6, 2)
# # # #     pygame.draw.line(s, col, (20, 20), (34, 20), 2)
# # # #     pygame.draw.line(s, col, (28, 20), (28, 26), 2)
# # # #     pygame.draw.line(s, col, (32, 20), (32, 24), 2)
# # # #     dst.blit(s, (cx - 20, cy - 20))
# # # #
# # # # def draw_modern_dock(dst, dock_rect: pygame.Rect, alpha: int):
# # # #     _draw_round_rect_alpha(dst, dock_rect, (0, 0, 0), int(150 * (alpha / 255.0)), radius=22)
# # # #     _draw_round_rect_outline_alpha(dst, dock_rect, (255, 255, 255), int(90 * (alpha / 255.0)), radius=22, width=2)
# # # #
# # # # def draw_modern_button(dst, rect: pygame.Rect, label: str, font, icon_fn, accent_rgb,
# # # #                        active: bool, pressed: bool, alpha: int):
# # # #     a = clamp255(alpha)
# # # #     shadow_off = 3 if not pressed else 1
# # # #     _draw_round_rect_alpha(dst, rect.move(0, shadow_off), (0, 0, 0), int(90 * (a / 255.0)), radius=16)
# # # #
# # # #     base = (18, 18, 18)
# # # #     if active:
# # # #         base = (26, 26, 26)
# # # #     if pressed:
# # # #         base = (12, 12, 12)
# # # #
# # # #     _draw_round_rect_alpha(dst, rect, base, int(210 * (a / 255.0)), radius=16)
# # # #
# # # #     strip = pygame.Rect(rect.x + 12, rect.y + rect.h - 10, rect.w - 24, 4)
# # # #     _draw_round_rect_alpha(dst, strip, accent_rgb, int(200 * (a / 255.0)), radius=4)
# # # #
# # # #     _draw_round_rect_outline_alpha(dst, rect, (255, 255, 255), int(95 * (a / 255.0)), radius=16, width=2)
# # # #
# # # #     icon_center = (rect.x + 26, rect.centery)
# # # #     icon_fn(dst, icon_center, accent_rgb, alpha=a)
# # # #
# # # #     txt = font.render(label, True, (240, 240, 240))
# # # #     txt.set_alpha(a)
# # # #     dst.blit(txt, (rect.x + 52, rect.centery - txt.get_height() // 2))
# # # #
# # # #
# # # # # ============================================================
# # # # # PIN overlay
# # # # # ============================================================
# # # # def make_button(rect: pygame.Rect, label: str, color=(90, 90, 90)):
# # # #     return {"rect": rect, "label": label, "color": color}
# # # #
# # # # def draw_button(screen, btn, font_main, font_small, active=False, small=False):
# # # #     r = btn["rect"]
# # # #     base = btn.get("color", (90, 90, 90))
# # # #     bg = base if not active else lighten(base, 28)
# # # #     pygame.draw.rect(screen, bg, r, border_radius=16)
# # # #     pygame.draw.rect(screen, (230, 230, 230), r, 2, border_radius=16)
# # # #     f = font_small if small else font_main
# # # #     t = f.render(btn["label"], True, (255, 255, 255))
# # # #     screen.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))
# # # #
# # # # def pin_overlay_loop(screen, clock, W, H, bg_frame_surf, font, font_small, snd_error) -> bool:
# # # #     pin_input = ""
# # # #     pin_error = ""
# # # #     pin_error_t0 = 0.0
# # # #
# # # #     cancel_btn = make_button(pygame.Rect(16, 16, 170, 48), "CANCEL", color=(120, 120, 120))
# # # #
# # # #     KEYPAD_COLS = 3
# # # #     KEYPAD_ROWS = 4
# # # #     KEYS = ["1", "2", "3",
# # # #             "4", "5", "6",
# # # #             "7", "8", "9",
# # # #             "C", "0", "OK"]
# # # #
# # # #     def submit() -> bool:
# # # #         nonlocal pin_input, pin_error, pin_error_t0
# # # #         if pin_input == ADMIN_PIN:
# # # #             return True
# # # #         pin_error = "Incorrect PIN"
# # # #         pin_error_t0 = time.time()
# # # #         pin_input = ""
# # # #         play(snd_error)
# # # #         return False
# # # #
# # # #     while True:
# # # #         for ev in pygame.event.get():
# # # #             if ev.type == pygame.QUIT:
# # # #                 return False
# # # #
# # # #             if ev.type == pygame.KEYDOWN:
# # # #                 if ev.key == pygame.K_ESCAPE:
# # # #                     return False
# # # #                 if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
# # # #                     if submit():
# # # #                         return True
# # # #                 elif ev.key == pygame.K_BACKSPACE:
# # # #                     pin_input = pin_input[:-1]
# # # #                 else:
# # # #                     if ev.unicode.isdigit() and len(pin_input) < PIN_MAX_LEN:
# # # #                         pin_input += ev.unicode
# # # #
# # # #             if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
# # # #                 pos = event_pos(ev, W, H)
# # # #                 if not pos:
# # # #                     continue
# # # #                 if cancel_btn["rect"].collidepoint(pos):
# # # #                     return False
# # # #
# # # #                 pad_w = min(520, int(W * 0.42))
# # # #                 pad_h = min(520, int(H * 0.62))
# # # #                 pad_x = (W - pad_w) // 2
# # # #                 pad_y = (H - pad_h) // 2 + 40
# # # #                 cell_w = pad_w // KEYPAD_COLS
# # # #                 cell_h = pad_h // KEYPAD_ROWS
# # # #
# # # #                 idx = 0
# # # #                 for r in range(KEYPAD_ROWS):
# # # #                     for c in range(KEYPAD_COLS):
# # # #                         x = pad_x + c * cell_w + 8
# # # #                         y = pad_y + r * cell_h + 8
# # # #                         rect = pygame.Rect(x, y, cell_w - 16, cell_h - 16)
# # # #                         if rect.collidepoint(pos):
# # # #                             key = KEYS[idx]
# # # #                             if key == "C":
# # # #                                 pin_input = ""
# # # #                             elif key == "OK":
# # # #                                 if submit():
# # # #                                     return True
# # # #                             else:
# # # #                                 if len(pin_input) < PIN_MAX_LEN:
# # # #                                     pin_input += key
# # # #                             break
# # # #                         idx += 1
# # # #
# # # #         screen.blit(bg_frame_surf, (0, 0))
# # # #         overlay = pygame.Surface((W, H), pygame.SRCALPHA)
# # # #         overlay.fill((0, 0, 0, 205))
# # # #         screen.blit(overlay, (0, 0))
# # # #
# # # #         mx, my = pygame.mouse.get_pos()
# # # #         draw_button(screen, cancel_btn, font, font_small, active=cancel_btn["rect"].collidepoint((mx, my)), small=True)
# # # #
# # # #         title = font.render("PIN UNLOCK", True, (255, 255, 255))
# # # #         prompt = font_small.render("Enter PIN:", True, (230, 230, 230))
# # # #         masked = "*" * len(pin_input)
# # # #         entry = font.render(masked, True, (255, 255, 0))
# # # #
# # # #         screen.blit(title, (W // 2 - title.get_width() // 2, 80))
# # # #         screen.blit(prompt, (W // 2 - prompt.get_width() // 2, 130))
# # # #         screen.blit(entry, (W // 2 - entry.get_width() // 2, 165))
# # # #
# # # #         pad_w = min(520, int(W * 0.42))
# # # #         pad_h = min(520, int(H * 0.62))
# # # #         pad_x = (W - pad_w) // 2
# # # #         pad_y = (H - pad_h) // 2 + 40
# # # #         cell_w = pad_w // KEYPAD_COLS
# # # #         cell_h = pad_h // KEYPAD_ROWS
# # # #
# # # #         pygame.draw.rect(screen, (35, 35, 35), pygame.Rect(pad_x, pad_y, pad_w, pad_h), border_radius=12)
# # # #
# # # #         rects = []
# # # #         for r in range(KEYPAD_ROWS):
# # # #             for c in range(KEYPAD_COLS):
# # # #                 x = pad_x + c * cell_w + 8
# # # #                 y = pad_y + r * cell_h + 8
# # # #                 rects.append(pygame.Rect(x, y, cell_w - 16, cell_h - 16))
# # # #
# # # #         for i, r in enumerate(rects):
# # # #             pygame.draw.rect(screen, (70, 70, 70), r, border_radius=10)
# # # #             label = font.render(KEYS[i], True, (255, 255, 255))
# # # #             screen.blit(label, (r.centerx - label.get_width() // 2, r.centery - label.get_height() // 2))
# # # #
# # # #         if pin_error and (time.time() - pin_error_t0) < 2.0:
# # # #             err = font_small.render(pin_error, True, (255, 90, 90))
# # # #             screen.blit(err, (W // 2 - err.get_width() // 2, pad_y + pad_h + 18))
# # # #
# # # #         pygame.display.flip()
# # # #         clock.tick(60)
# # # #
# # # #
# # # # # ============================================================
# # # # # Success overlay + fades
# # # # # ============================================================
# # # # def unlock_success_overlay(screen, clock, W, H, font_brand, font_small, snd_snap,
# # # #                           msg="UNLOCKED", sub="Returning to menu...", hold_s=UNLOCK_SUCCESS_S,
# # # #                           bg_frame_surf: Optional[pygame.Surface] = None):
# # # #     if bg_frame_surf is None:
# # # #         try:
# # # #             bg_frame_surf = screen.copy()
# # # #         except Exception:
# # # #             bg_frame_surf = None
# # # #
# # # #     t0 = time.time()
# # # #     play(snd_snap)
# # # #     while time.time() - t0 < hold_s:
# # # #         for ev in pygame.event.get():
# # # #             if ev.type == pygame.QUIT:
# # # #                 return
# # # #
# # # #         if bg_frame_surf is not None:
# # # #             screen.blit(bg_frame_surf, (0, 0))
# # # #         else:
# # # #             screen.fill(COLOR_BG)
# # # #
# # # #         overlay = pygame.Surface((W, H), pygame.SRCALPHA)
# # # #         overlay.fill((0, 0, 0, 180))
# # # #         screen.blit(overlay, (0, 0))
# # # #
# # # #         m = font_brand.render(msg, True, (255, 255, 255))
# # # #         s = font_small.render(sub, True, (230, 230, 230))
# # # #         screen.blit(m, (W // 2 - m.get_width() // 2, H // 2 - 40))
# # # #         screen.blit(s, (W // 2 - s.get_width() // 2, H // 2 + 20))
# # # #         pygame.display.flip()
# # # #         clock.tick(60)
# # # #
# # # # def fade_to_black(screen, clock, seconds: float = 0.18):
# # # #     W, H = screen.get_size()
# # # #     try:
# # # #         base = screen.copy()
# # # #     except Exception:
# # # #         base = None
# # # #     t0 = time.time()
# # # #     while True:
# # # #         t = (time.time() - t0) / max(0.001, seconds)
# # # #         if t >= 1.0:
# # # #             break
# # # #         for ev in pygame.event.get():
# # # #             if ev.type == pygame.QUIT:
# # # #                 return
# # # #         if base is not None:
# # # #             screen.blit(base, (0, 0))
# # # #         else:
# # # #             screen.fill((0, 0, 0))
# # # #         a = int(255 * _ease_out_cubic(t))
# # # #         ov = pygame.Surface((W, H), pygame.SRCALPHA)
# # # #         ov.fill((0, 0, 0, a))
# # # #         screen.blit(ov, (0, 0))
# # # #         pygame.display.flip()
# # # #         clock.tick(60)
# # # #     screen.fill((0, 0, 0))
# # # #     pygame.display.flip()
# # # #
# # # #
# # # # # ============================================================
# # # # # Jigsaw internals
# # # # # ============================================================
# # # # def calc_jig_snap_dist(W: int, BOARD_H: int, cols: int, rows: int) -> int:
# # # #     cols = max(1, int(cols))
# # # #     rows = max(1, int(rows))
# # # #     cell_w = W // cols
# # # #     cell_h = BOARD_H // rows
# # # #     base = int(min(cell_w, cell_h) * JIG_SNAP_FRAC)
# # # #     return max(JIG_SNAP_MIN, min(JIG_SNAP_MAX, base))
# # # #
# # # # def _make_jigsaw_edges(cols, rows):
# # # #     h_edges = [
# # # #         [{"dir": random.choice([-1, 1]), "off": random.uniform(-JIG_EDGE_OFF_FRAC, JIG_EDGE_OFF_FRAC)}
# # # #          for _ in range(cols)]
# # # #         for _ in range(rows - 1)
# # # #     ]
# # # #     v_edges = [
# # # #         [{"dir": random.choice([-1, 1]), "off": random.uniform(-JIG_EDGE_OFF_FRAC, JIG_EDGE_OFF_FRAC)}
# # # #          for _ in range(cols - 1)]
# # # #         for _ in range(rows)
# # # #     ]
# # # #     return h_edges, v_edges
# # # #
# # # # def _apply_edge_circle(mask_surf, kind, center, radius):
# # # #     if kind == 0:
# # # #         return
# # # #     if kind > 0:
# # # #         pygame.draw.circle(mask_surf, (255, 255, 255, 255), center, radius)
# # # #     else:
# # # #         pygame.draw.circle(mask_surf, (255, 255, 255, 0), center, radius)
# # # #
# # # # def build_jigsaw_pieces(W, BOARD_H, board_surf, cols, rows):
# # # #     cell_w = W // cols
# # # #     cell_h = BOARD_H // rows
# # # #     knob_r = int(min(cell_w, cell_h) * JIG_KNOB_FRAC)
# # # #     margin = knob_r + 3
# # # #     h_edges, v_edges = _make_jigsaw_edges(cols, rows)
# # # #
# # # #     pieces = []
# # # #     for y in range(rows):
# # # #         for x in range(cols):
# # # #             if y == 0:
# # # #                 top_kind, top_off = 0, 0.0
# # # #             else:
# # # #                 top_kind = -h_edges[y - 1][x]["dir"]
# # # #                 top_off = h_edges[y - 1][x]["off"]
# # # #
# # # #             if y == rows - 1:
# # # #                 bot_kind, bot_off = 0, 0.0
# # # #             else:
# # # #                 bot_kind = h_edges[y][x]["dir"]
# # # #                 bot_off = h_edges[y][x]["off"]
# # # #
# # # #             if x == 0:
# # # #                 left_kind, left_off = 0, 0.0
# # # #             else:
# # # #                 left_kind = -v_edges[y][x - 1]["dir"]
# # # #                 left_off = v_edges[y][x - 1]["off"]
# # # #
# # # #             if x == cols - 1:
# # # #                 right_kind, right_off = 0, 0.0
# # # #             else:
# # # #                 right_kind = v_edges[y][x]["dir"]
# # # #                 right_off = v_edges[y][x]["off"]
# # # #
# # # #             pw = cell_w + 2 * margin
# # # #             ph = cell_h + 2 * margin
# # # #
# # # #             mask_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
# # # #             mask_surf.fill((255, 255, 255, 0))
# # # #             pygame.draw.rect(mask_surf, (255, 255, 255, 255), pygame.Rect(margin, margin, cell_w, cell_h))
# # # #
# # # #             cx_top = margin + (cell_w // 2) + int(top_off * cell_w)
# # # #             cy_top = margin
# # # #             _apply_edge_circle(mask_surf, top_kind, (cx_top, cy_top), knob_r)
# # # #
# # # #             cx_bot = margin + (cell_w // 2) + int(bot_off * cell_w)
# # # #             cy_bot = margin + cell_h
# # # #             _apply_edge_circle(mask_surf, bot_kind, (cx_bot, cy_bot), knob_r)
# # # #
# # # #             cx_left = margin
# # # #             cy_left = margin + (cell_h // 2) + int(left_off * cell_h)
# # # #             _apply_edge_circle(mask_surf, left_kind, (cx_left, cy_left), knob_r)
# # # #
# # # #             cx_right = margin + cell_w
# # # #             cy_right = margin + (cell_h // 2) + int(right_off * cell_h)
# # # #             _apply_edge_circle(mask_surf, right_kind, (cx_right, cy_right), knob_r)
# # # #
# # # #             piece_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
# # # #             piece_surf.blit(board_surf, (margin - x * cell_w, margin - y * cell_h))
# # # #             piece_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
# # # #
# # # #             piece_mask = pygame.mask.from_surface(mask_surf)
# # # #             correct_pos = (x * cell_w - margin, y * cell_h - margin)
# # # #
# # # #             pieces.append({
# # # #                 "surf": piece_surf,
# # # #                 "mask": piece_mask,
# # # #                 "correct_pos": correct_pos,
# # # #                 "pos": list(correct_pos),
# # # #                 "locked": False,
# # # #                 "fall_from": list(correct_pos),
# # # #                 "fall_to": list(correct_pos),
# # # #             })
# # # #
# # # #     return pieces
# # # #
# # # # def tray_random_pos_sized(W, tray_rect, obj_w, obj_h):
# # # #     x0 = TRAY_MARGIN
# # # #     x1 = W - TRAY_MARGIN - obj_w
# # # #     y0 = tray_rect.top + TRAY_MARGIN
# # # #     y1 = tray_rect.bottom - TRAY_MARGIN - obj_h
# # # #     if x1 < x0:
# # # #         x1 = x0
# # # #     if y1 < y0:
# # # #         y1 = y0
# # # #     return (random.randint(x0, x1), random.randint(y0, y1))
# # # #
# # # # def jigsaw_all_locked(pieces):
# # # #     return all(p.get("locked") for p in pieces)
# # # #
# # # #
# # # # # ============================================================
# # # # # Lock App
# # # # # ============================================================
# # # # class LockApp:
# # # #     STATE_LOCK = "LOCK"
# # # #     STATE_SQUARE = "SQUARE"
# # # #     STATE_JIG_SELECT = "JIG_SELECT"
# # # #     STATE_JIGSAW = "JIGSAW"
# # # #
# # # #     PUZ_INTRO = "INTRO"
# # # #     PUZ_FALL = "FALL"
# # # #     PUZ_PLAY = "PLAY"
# # # #
# # # #     JIG_INTRO = "INTRO"
# # # #     JIG_FALL = "FALL"
# # # #     JIG_PLAY = "PLAY"
# # # #
# # # #     LOCK_TRANS_NONE = None
# # # #     LOCK_TRANS_BREAK = "BREAK"
# # # #     LOCK_TRANS_FADEIN = "FADEIN"
# # # #
# # # #     def __init__(self, screen: Optional[pygame.Surface] = None, clock: Optional[pygame.time.Clock] = None):
# # # #         # Only init if caller hasn’t already.
# # # #         if not pygame.get_init():
# # # #             pygame.init()
# # # #         if not pygame.font.get_init():
# # # #             pygame.font.init()
# # # #         try:
# # # #             if not pygame.mixer.get_init():
# # # #                 pygame.mixer.init()
# # # #         except Exception:
# # # #             pass
# # # #
# # # #         self.shared_screen = screen is not None
# # # #
# # # #         if screen is None:
# # # #             # Standalone mode (creates its own window)
# # # #             try:
# # # #                 self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.NOFRAME, vsync=1)
# # # #             except Exception:
# # # #                 try:
# # # #                     self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.NOFRAME)
# # # #                 except Exception:
# # # #                     self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
# # # #         else:
# # # #             # Shared mode: use existing display window to avoid WM/title-bar flash
# # # #             self.screen = screen
# # # #
# # # #         self.clock = clock or pygame.time.Clock()
# # # #         self.W, self.H = self.screen.get_size()
# # # #
# # # #         # First frame paint
# # # #         self.screen.fill((0, 0, 0))
# # # #         pygame.display.flip()
# # # #         pygame.event.pump()
# # # #
# # # #         self.font = pygame.font.SysFont(None, 52)
# # # #         self.font_small = pygame.font.SysFont(None, 26)
# # # #         self.font_brand = pygame.font.SysFont(None, 64)
# # # #         self.font_brand2 = pygame.font.SysFont(None, 28)
# # # #         self.font_dock = pygame.font.SysFont(None, 28)
# # # #
# # # #         self.snd_pick = load_sound(SND_PICK)
# # # #         self.snd_drop = load_sound(SND_DROP)
# # # #         self.snd_snap = load_sound(SND_SNAP)
# # # #         self.snd_error = load_sound(SND_ERROR)
# # # #
# # # #         self.TRAY_H = int(self.H * TRAY_H_FRAC)
# # # #         self.BOARD_H = self.H - self.TRAY_H
# # # #         self.board_rect = pygame.Rect(0, 0, self.W, self.BOARD_H)
# # # #         self.tray_rect = pygame.Rect(0, self.BOARD_H, self.W, self.TRAY_H)
# # # #
# # # #         self.images = self._load_images()
# # # #         self.playlist = list(self.images)
# # # #         if LOCK_BG_SHUFFLE:
# # # #             random.shuffle(self.playlist)
# # # #         else:
# # # #             self.playlist.sort()
# # # #         self.lock_idx = random.randrange(len(self.playlist)) if LOCK_BG_RANDOM_START else 0
# # # #
# # # #         self.lock_bg_big: Optional[pygame.Surface] = None
# # # #         self.lock_fg: Optional[pygame.Surface] = None
# # # #         self.lock_fg_rect: Optional[pygame.Rect] = None
# # # #         self.board_surf: Optional[pygame.Surface] = None
# # # #
# # # #         self.pan_x = 0.0
# # # #         self.pan_y = 0.0
# # # #         self.pan_vx = 0.0
# # # #         self.pan_vy = 0.0
# # # #
# # # #         self.lock_cycle_t0 = time.time()
# # # #         self.lock_trans = self.LOCK_TRANS_NONE
# # # #         self.lock_trans_t0 = 0.0
# # # #
# # # #         self.break_style = "shatter"
# # # #         self.break_dur = float(LOCK_BREAK_DURATIONS.get("shatter", 0.85))
# # # #         self.lock_snapshot = pygame.Surface((self.W, self.H))
# # # #         self.break_pieces: List[Dict[str, Any]] = []
# # # #
# # # #         self._set_image_by_index(self.lock_idx)
# # # #
# # # #         now = time.time()
# # # #         self.lock_ui_visible_until = (now + LOCK_UI_AUTOHIDE_S) if not LOCK_UI_START_HIDDEN else 0.0
# # # #         self.last_mouse_pos = pygame.mouse.get_pos()
# # # #         self.ui_alpha = 0.0 if LOCK_UI_START_HIDDEN else 255.0
# # # #
# # # #         self._layout_lock_dock()
# # # #         self.lock_pressed: Optional[str] = None
# # # #         self.state = self.STATE_LOCK
# # # #
# # # #         # square puzzle
# # # #         self.tiles: List[Dict[str, Any]] = []
# # # #         self.tile_w = 0
# # # #         self.tile_h = 0
# # # #         self.slot_positions: List[Tuple[int, int]] = []
# # # #         self.drag_tile: Optional[Dict[str, Any]] = None
# # # #         self.drag_ox = 0
# # # #         self.drag_oy = 0
# # # #         self.puz_stage = self.PUZ_INTRO
# # # #         self.puz_t0 = 0.0
# # # #
# # # #         # jigsaw
# # # #         self.jig_cols, self.jig_rows = JIG_DIFFICULTY_CHOICES[1][1], JIG_DIFFICULTY_CHOICES[1][2]
# # # #         self.jig_snap_dist = calc_jig_snap_dist(self.W, self.BOARD_H, self.jig_cols, self.jig_rows)
# # # #         self.jig_pieces: List[Dict[str, Any]] = []
# # # #         self.jig_drag_piece: Optional[Dict[str, Any]] = None
# # # #         self.jig_drag_ox = 0
# # # #         self.jig_drag_oy = 0
# # # #         self.jig_stage = self.JIG_INTRO
# # # #         self.jig_t0 = 0.0
# # # #
# # # #         self.back_btn = make_button(pygame.Rect(16, 16, 160, 48), "BACK", color=(120, 120, 120))
# # # #
# # # #         self._result_unlocked = False
# # # #         self._running = True
# # # #
# # # #     def _layout_lock_dock(self):
# # # #         margin_bottom = 28
# # # #         dock_w = min(780, int(self.W * 0.68))
# # # #         dock_h = 96
# # # #         dock_x = (self.W - dock_w) // 2
# # # #         dock_y = self.H - dock_h - margin_bottom
# # # #         self.dock_rect = pygame.Rect(dock_x, dock_y, dock_w, dock_h)
# # # #
# # # #         pad = 14
# # # #         gap = 12
# # # #         btn_h = 64
# # # #         btn_y = dock_y + (dock_h - btn_h) // 2
# # # #         btn_w = (dock_w - pad * 2 - gap * 2) // 3
# # # #
# # # #         self.btn_unlock = pygame.Rect(dock_x + pad + (btn_w + gap) * 0, btn_y, btn_w, btn_h)
# # # #         self.btn_jigsaw = pygame.Rect(dock_x + pad + (btn_w + gap) * 1, btn_y, btn_w, btn_h)
# # # #         self.btn_admin = pygame.Rect(dock_x + pad + (btn_w + gap) * 2, btn_y, btn_w, btn_h)
# # # #
# # # #     def _load_images(self):
# # # #         if not os.path.isdir(IMAGE_DIR):
# # # #             return []
# # # #         imgs = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
# # # #         return imgs
# # # #
# # # #     def _touch_lock_ui(self):
# # # #         self.lock_ui_visible_until = time.time() + LOCK_UI_AUTOHIDE_S
# # # #
# # # #     def _lock_ui_visible(self) -> bool:
# # # #         return time.time() < self.lock_ui_visible_until
# # # #
# # # #     def _set_image_by_index(self, idx: int):
# # # #         if not self.playlist:
# # # #             return
# # # #         self.lock_idx = idx % len(self.playlist)
# # # #         fname = self.playlist[self.lock_idx]
# # # #         raw = safe_load_image(os.path.join(IMAGE_DIR, fname))
# # # #
# # # #         if LOCK_VISIBLE_SCALE_MODE.lower() == "cover":
# # # #             self.lock_fg = scale_cover(raw, self.W, self.H)
# # # #             self.lock_fg_rect = self.lock_fg.get_rect(topleft=(0, 0))
# # # #         else:
# # # #             self.lock_fg, self.lock_fg_rect = scale_contain(raw, self.W, self.H)
# # # #
# # # #         big_w = self.W + LOCK_BG_PAN_RANGE_PX
# # # #         big_h = self.H + LOCK_BG_PAN_RANGE_PX
# # # #         bg = scale_cover(raw, big_w, big_h).convert()
# # # #
# # # #         if LOCK_BG_BLUR_METHOD.lower() == "hq":
# # # #             bg = blur_surface_hq(bg, radius=LOCK_BG_HQ_RADIUS, downscale=LOCK_BG_HQ_DOWNSCALE)
# # # #         else:
# # # #             bg = blur_surface_once(bg, LOCK_BG_BLUR_DOWNSCALE).convert()
# # # #
# # # #         if LOCK_BG_DIM_ALPHA > 0:
# # # #             dim = pygame.Surface((big_w, big_h), pygame.SRCALPHA)
# # # #             dim.fill((0, 0, 0, clamp255(LOCK_BG_DIM_ALPHA)))
# # # #             bg.blit(dim, (0, 0))
# # # #
# # # #         self.lock_bg_big = bg.convert()
# # # #
# # # #         if PUZZLE_BOARD_SCALE_MODE.lower() == "contain":
# # # #             board_fit, rect = scale_contain(raw, self.W, self.BOARD_H)
# # # #             board = pygame.Surface((self.W, self.BOARD_H))
# # # #             board.fill((0, 0, 0))
# # # #             board.blit(board_fit, rect)
# # # #             self.board_surf = board.convert()
# # # #         else:
# # # #             self.board_surf = scale_cover(raw, self.W, self.BOARD_H).convert()
# # # #
# # # #         max_x = max(0, self.lock_bg_big.get_width() - self.W)
# # # #         max_y = max(0, self.lock_bg_big.get_height() - self.H)
# # # #         self.pan_x = float(random.randint(0, max_x)) if max_x else 0.0
# # # #         self.pan_y = float(random.randint(0, max_y)) if max_y else 0.0
# # # #
# # # #         ang = random.uniform(0, math.tau)
# # # #         self.pan_vx = math.cos(ang) * LOCK_BG_PAN_SPEED_PX_S
# # # #         self.pan_vy = math.sin(ang) * LOCK_BG_PAN_SPEED_PX_S
# # # #
# # # #         self.lock_cycle_t0 = time.time()
# # # #
# # # #     def _advance_image(self):
# # # #         if not self.playlist:
# # # #             return
# # # #         nxt = self.lock_idx + 1
# # # #         if nxt >= len(self.playlist):
# # # #             nxt = 0
# # # #             if LOCK_BG_SHUFFLE:
# # # #                 random.shuffle(self.playlist)
# # # #         self._set_image_by_index(nxt)
# # # #
# # # #     def _update_pan(self, dt: float):
# # # #         if not self.lock_bg_big:
# # # #             return
# # # #         max_x = max(0, self.lock_bg_big.get_width() - self.W)
# # # #         max_y = max(0, self.lock_bg_big.get_height() - self.H)
# # # #
# # # #         self.pan_x += self.pan_vx * dt
# # # #         self.pan_y += self.pan_vy * dt
# # # #
# # # #         if max_x > 0:
# # # #             if self.pan_x < 0:
# # # #                 self.pan_x = 0.0
# # # #                 self.pan_vx = abs(self.pan_vx)
# # # #             elif self.pan_x > max_x:
# # # #                 self.pan_x = float(max_x)
# # # #                 self.pan_vx = -abs(self.pan_vx)
# # # #         else:
# # # #             self.pan_x = 0.0
# # # #
# # # #         if max_y > 0:
# # # #             if self.pan_y < 0:
# # # #                 self.pan_y = 0.0
# # # #                 self.pan_vy = abs(self.pan_vy)
# # # #             elif self.pan_y > max_y:
# # # #                 self.pan_y = float(max_y)
# # # #                 self.pan_vy = -abs(self.pan_vy)
# # # #         else:
# # # #             self.pan_y = 0.0
# # # #
# # # #     def _draw_lock_frame_to(self, target_surf: pygame.Surface):
# # # #         if self.lock_bg_big:
# # # #             max_x = max(0, self.lock_bg_big.get_width() - self.W)
# # # #             max_y = max(0, self.lock_bg_big.get_height() - self.H)
# # # #             vx = int(max(0, min(max_x, self.pan_x)))
# # # #             vy = int(max(0, min(max_y, self.pan_y)))
# # # #             view = pygame.Rect(vx, vy, self.W, self.H)
# # # #             target_surf.blit(self.lock_bg_big.subsurface(view), (0, 0))
# # # #         else:
# # # #             target_surf.fill((0, 0, 0))
# # # #
# # # #         if self.lock_fg and self.lock_fg_rect:
# # # #             target_surf.blit(self.lock_fg, self.lock_fg_rect)
# # # #
# # # #     def _build_lock_frame_surface(self) -> pygame.Surface:
# # # #         surf = pygame.Surface((self.W, self.H))
# # # #         self._draw_lock_frame_to(surf)
# # # #         return surf
# # # #
# # # #     def _draw_status_bar(self):
# # # #         if not SHOW_STATUS_BAR:
# # # #             return
# # # #         bar = pygame.Surface((self.W, STATUS_BAR_H), pygame.SRCALPHA)
# # # #         bar.fill((0, 0, 0, 140))
# # # #         self.screen.blit(bar, (0, 0))
# # # #         now = datetime.datetime.now()
# # # #         txt = now.strftime("%a %b %d   %I:%M %p").lstrip("0")
# # # #         t = self.font_small.render(txt, True, (230, 230, 230))
# # # #         self.screen.blit(t, (self.W - t.get_width() - 16, (STATUS_BAR_H - t.get_height()) // 2))
# # # #
# # # #     def _choose_break_style(self) -> str:
# # # #         if LOCK_TRANSITION_STYLE == "random":
# # # #             return random.choice(LOCK_TRANSITION_STYLES)
# # # #         if LOCK_TRANSITION_STYLE in LOCK_TRANSITION_STYLES:
# # # #             return LOCK_TRANSITION_STYLE
# # # #         return "shatter"
# # # #
# # # #     def _make_break_pieces(self, snap: pygame.Surface, style: str) -> List[Dict[str, Any]]:
# # # #         pieces: List[Dict[str, Any]] = []
# # # #         W, H = self.W, self.H
# # # #
# # # #         if style == "blinds":
# # # #             n = 16
# # # #             tile_w = max(16, W // n)
# # # #             for i in range(n):
# # # #                 x = i * tile_w
# # # #                 w = tile_w if i < n - 1 else (W - x)
# # # #                 rect = pygame.Rect(x, 0, w, H)
# # # #                 surf = snap.subsurface(rect).copy()
# # # #                 dir_sign = -1 if (i % 2 == 0) else 1
# # # #                 vx = dir_sign * random.uniform(250, 450)
# # # #                 pieces.append({
# # # #                     "surf": surf,
# # # #                     "pos": [float(rect.x), float(rect.y)],
# # # #                     "vel": [vx, random.uniform(-40, 40)],
# # # #                     "rot": 0.0,
# # # #                     "ang": random.uniform(-30, 30),
# # # #                 })
# # # #             return pieces
# # # #
# # # #         target = LOCK_SHATTER_TILE_TARGET
# # # #         cols = int(math.sqrt(target * (W / max(1.0, H))))
# # # #         cols = max(6, min(30, cols))
# # # #         rows = max(6, min(24, int(target / cols)))
# # # #         tile_w = max(18, W // cols)
# # # #         tile_h = max(18, H // rows)
# # # #
# # # #         for y in range(0, H, tile_h):
# # # #             for x in range(0, W, tile_w):
# # # #                 rect = pygame.Rect(x, y, min(tile_w, W - x), min(tile_h, H - y))
# # # #                 surf = snap.subsurface(rect).copy()
# # # #                 cx = rect.centerx - W / 2.0
# # # #                 cy = rect.centery - H / 2.0
# # # #
# # # #                 if style == "explode":
# # # #                     mag = random.uniform(220, 520)
# # # #                     ang = math.atan2(cy, cx) + random.uniform(-0.25, 0.25)
# # # #                     vx = math.cos(ang) * mag
# # # #                     vy = math.sin(ang) * mag
# # # #                 elif style == "drop":
# # # #                     vx = random.uniform(-80, 80)
# # # #                     vy = random.uniform(50, 160)
# # # #                 else:
# # # #                     vx = random.uniform(-260, 260) + (cx * 0.25)
# # # #                     vy = random.uniform(-180, 120) + (cy * 0.20)
# # # #
# # # #                 rot = random.uniform(-35, 35)
# # # #                 pieces.append({
# # # #                     "surf": surf,
# # # #                     "pos": [float(rect.x), float(rect.y)],
# # # #                     "vel": [vx, vy],
# # # #                     "rot": 0.0,
# # # #                     "ang": rot,
# # # #                 })
# # # #
# # # #         return pieces
# # # #
# # # #     def _begin_lock_transition(self):
# # # #         self.lock_snapshot = self._build_lock_frame_surface()
# # # #         self.break_style = self._choose_break_style()
# # # #         self.break_dur = float(LOCK_BREAK_DURATIONS.get(self.break_style, 0.85))
# # # #         self.lock_trans = self.LOCK_TRANS_BREAK
# # # #         self.lock_trans_t0 = time.time()
# # # #         self.break_pieces = self._make_break_pieces(self.lock_snapshot, self.break_style)
# # # #
# # # #     def _draw_break(self, t: float):
# # # #         self.screen.fill((0, 0, 0))
# # # #         dt = 1.0 / 60.0
# # # #         grav = LOCK_SHATTER_GRAVITY
# # # #
# # # #         for p in self.break_pieces:
# # # #             vx, vy = p["vel"]
# # # #             if self.break_style in ("shatter", "drop"):
# # # #                 vy += grav * dt * (0.70 if self.break_style == "drop" else 0.40)
# # # #                 p["vel"][1] = vy
# # # #
# # # #             p["pos"][0] += vx * dt
# # # #             p["pos"][1] += vy * dt
# # # #
# # # #             damp = 1.0 - (0.12 * t)
# # # #             p["vel"][0] *= damp
# # # #             p["vel"][1] *= damp
# # # #
# # # #             p["rot"] += p["ang"] * dt
# # # #
# # # #             surf = p["surf"]
# # # #             if abs(p["rot"]) > 0.5:
# # # #                 rs = pygame.transform.rotozoom(surf, p["rot"], 1.0)
# # # #                 r = rs.get_rect(center=(p["pos"][0] + surf.get_width() / 2, p["pos"][1] + surf.get_height() / 2))
# # # #                 self.screen.blit(rs, r.topleft)
# # # #             else:
# # # #                 self.screen.blit(surf, (p["pos"][0], p["pos"][1]))
# # # #
# # # #         ov = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
# # # #         ov.fill((0, 0, 0, int(220 * _ease_in_quad(t))))
# # # #         self.screen.blit(ov, (0, 0))
# # # #
# # # #     def _draw_fadein(self, t: float):
# # # #         self._draw_lock_frame_to(self.screen)
# # # #         a = int(255 * (1.0 - _ease_out_cubic(t)))
# # # #         ov = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
# # # #         ov.fill((0, 0, 0, a))
# # # #         self.screen.blit(ov, (0, 0))
# # # #
# # # #     # ---------- Square puzzle ----------
# # # #     def _square_setup(self):
# # # #         if self.board_surf is None:
# # # #             return
# # # #
# # # #         margin = 40
# # # #         usable_w = self.W - margin * 2
# # # #         usable_h = self.BOARD_H - margin * 2
# # # #         cols, rows = GRID_X, GRID_Y
# # # #
# # # #         self.tile_w = usable_w // cols
# # # #         self.tile_h = usable_h // rows
# # # #
# # # #         self.slot_positions = []
# # # #         for j in range(rows):
# # # #             for i in range(cols):
# # # #                 sx = margin + i * self.tile_w
# # # #                 sy = margin + j * self.tile_h
# # # #                 self.slot_positions.append((sx, sy))
# # # #
# # # #         board_scaled = pygame.transform.smoothscale(self.board_surf, (usable_w, usable_h))
# # # #         tiles: List[Dict[str, Any]] = []
# # # #         for j in range(rows):
# # # #             for i in range(cols):
# # # #                 src_rect = pygame.Rect(i * self.tile_w, j * self.tile_h, self.tile_w, self.tile_h)
# # # #                 surf = board_scaled.subsurface(src_rect).copy()
# # # #                 tile = pygame.Surface((self.tile_w, self.tile_h), pygame.SRCALPHA)
# # # #                 tile.blit(surf, (0, 0))
# # # #                 pygame.draw.rect(tile, (255, 255, 255, 70), pygame.Rect(0, 0, self.tile_w, self.tile_h), 2, border_radius=10)
# # # #
# # # #                 correct = self.slot_positions[j * cols + i]
# # # #                 pos = tray_random_pos_sized(self.W, self.tray_rect, self.tile_w, self.tile_h)
# # # #                 tiles.append({
# # # #                     "surf": tile,
# # # #                     "correct": correct,
# # # #                     "pos": [float(pos[0]), float(pos[1])],
# # # #                     "locked": False,
# # # #                     "fall_from": [float(pos[0]), float(-self.tile_h - random.randint(20, 400))],
# # # #                     "fall_to": [float(pos[0]), float(pos[1])],
# # # #                 })
# # # #
# # # #         random.shuffle(tiles)
# # # #         self.tiles = tiles
# # # #         self.drag_tile = None
# # # #         self.puz_stage = self.PUZ_INTRO
# # # #         self.puz_t0 = time.time()
# # # #
# # # #     def _square_all_locked(self) -> bool:
# # # #         return all(t["locked"] for t in self.tiles)
# # # #
# # # #     def _square_slot_occupied(self, slot_xy: Tuple[int, int]) -> bool:
# # # #         for t in self.tiles:
# # # #             if t["locked"] and tuple(map(int, t["pos"])) == slot_xy:
# # # #                 return True
# # # #         return False
# # # #
# # # #     def _square_find_tile_at(self, x: int, y: int) -> Optional[Dict[str, Any]]:
# # # #         for t in reversed(self.tiles):
# # # #             if t["locked"]:
# # # #                 continue
# # # #             r = pygame.Rect(int(t["pos"][0]), int(t["pos"][1]), self.tile_w, self.tile_h)
# # # #             if r.collidepoint((x, y)):
# # # #                 return t
# # # #         return None
# # # #
# # # #     def _square_update_stage(self):
# # # #         now = time.time()
# # # #         if self.puz_stage == self.PUZ_INTRO:
# # # #             if (now - self.puz_t0) >= PUZ_INTRO_HOLD_S:
# # # #                 for t in self.tiles:
# # # #                     pos = tray_random_pos_sized(self.W, self.tray_rect, self.tile_w, self.tile_h)
# # # #                     t["fall_from"] = [float(pos[0]), float(-self.tile_h - random.randint(20, 400))]
# # # #                     t["fall_to"] = [float(pos[0]), float(pos[1])]
# # # #                     t["pos"] = [t["fall_from"][0], t["fall_from"][1]]
# # # #                 self.puz_stage = self.PUZ_FALL
# # # #                 self.puz_t0 = now
# # # #
# # # #         elif self.puz_stage == self.PUZ_FALL:
# # # #             t = (now - self.puz_t0) / max(0.001, PUZ_FALL_S)
# # # #             if t >= 1.0:
# # # #                 for tile in self.tiles:
# # # #                     tile["pos"] = [tile["fall_to"][0], tile["fall_to"][1]]
# # # #                 self.puz_stage = self.PUZ_PLAY
# # # #                 self.puz_t0 = now
# # # #             else:
# # # #                 tt = _ease_out_cubic(t)
# # # #                 for tile in self.tiles:
# # # #                     fx, fy = tile["fall_from"]
# # # #                     tx, ty = tile["fall_to"]
# # # #                     tile["pos"][0] = fx + (tx - fx) * tt
# # # #                     tile["pos"][1] = fy + (ty - fy) * tt
# # # #
# # # #     def _square_draw(self):
# # # #         self.screen.fill(COLOR_BG)
# # # #
# # # #         title = self.font_brand2.render("Unlock Puzzle", True, (230, 230, 230))
# # # #         self.screen.blit(title, (self.W // 2 - title.get_width() // 2, 18))
# # # #
# # # #         board_panel = pygame.Rect(18, 60, self.W - 36, self.BOARD_H - 78)
# # # #         pygame.draw.rect(self.screen, (10, 10, 10), board_panel, border_radius=22)
# # # #         pygame.draw.rect(self.screen, (110, 110, 110), board_panel, 2, border_radius=22)
# # # #
# # # #         margin = 40
# # # #         cols, rows = GRID_X, GRID_Y
# # # #         usable_w = self.W - margin * 2
# # # #         usable_h = self.BOARD_H - margin * 2
# # # #         tile_w = usable_w // cols
# # # #         tile_h = usable_h // rows
# # # #
# # # #         for j in range(rows):
# # # #             for i in range(cols):
# # # #                 sx = margin + i * tile_w
# # # #                 sy = margin + j * tile_h
# # # #                 slot_rect = pygame.Rect(sx, sy, tile_w, tile_h)
# # # #                 pygame.draw.rect(self.screen, (55, 55, 55), slot_rect, 2, border_radius=10)
# # # #
# # # #         pygame.draw.rect(self.screen, COLOR_TRAY, self.tray_rect)
# # # #         pygame.draw.line(self.screen, COLOR_LINE, (0, self.BOARD_H), (self.W, self.BOARD_H), 2)
# # # #
# # # #         tray_label = self.font_small.render("Drag pieces into place.", True, (220, 220, 220))
# # # #         self.screen.blit(tray_label, (18, self.BOARD_H + 10))
# # # #
# # # #         mx, my = pygame.mouse.get_pos()
# # # #         draw_button(self.screen, self.back_btn, self.font_small, self.font_small, active=self.back_btn["rect"].collidepoint((mx, my)), small=True)
# # # #
# # # #         for t in self.tiles:
# # # #             self.screen.blit(t["surf"], (t["pos"][0], t["pos"][1]))
# # # #
# # # #         if self.puz_stage == self.PUZ_INTRO and self.board_surf is not None:
# # # #             ref = pygame.transform.smoothscale(self.board_surf, (board_panel.w - 14, board_panel.h - 14))
# # # #             ref_rect = ref.get_rect(center=board_panel.center)
# # # #             overlay = pygame.Surface((ref.get_width(), ref.get_height()), pygame.SRCALPHA)
# # # #             overlay.fill((0, 0, 0, 140))
# # # #             self.screen.blit(ref, ref_rect.topleft)
# # # #             self.screen.blit(overlay, ref_rect.topleft)
# # # #             msg = self.font_small.render("Memorize the picture...", True, (240, 240, 240))
# # # #             self.screen.blit(msg, (self.W // 2 - msg.get_width() // 2, board_panel.bottom - 34))
# # # #
# # # #     def _square_handle_event(self, ev):
# # # #         if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
# # # #             self.state = self.STATE_LOCK
# # # #             self.lock_pressed = None
# # # #             return
# # # #
# # # #         if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
# # # #             pos = event_pos(ev, self.W, self.H)
# # # #             if not pos:
# # # #                 return
# # # #             x, y = pos
# # # #
# # # #             if self.back_btn["rect"].collidepoint((x, y)):
# # # #                 self.state = self.STATE_LOCK
# # # #                 self.lock_pressed = None
# # # #                 return
# # # #
# # # #             if self.puz_stage != self.PUZ_PLAY:
# # # #                 return
# # # #
# # # #             t = self._square_find_tile_at(x, y)
# # # #             if t:
# # # #                 play(self.snd_pick)
# # # #                 self.drag_tile = t
# # # #                 self.drag_ox = x - int(t["pos"][0])
# # # #                 self.drag_oy = y - int(t["pos"][1])
# # # #                 self.tiles.remove(t)
# # # #                 self.tiles.append(t)
# # # #
# # # #         if ev.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
# # # #             if self.drag_tile is None:
# # # #                 return
# # # #             pos = event_pos(ev, self.W, self.H)
# # # #             if not pos:
# # # #                 return
# # # #             x, y = pos
# # # #             self.drag_tile["pos"][0] = float(x - self.drag_ox)
# # # #             self.drag_tile["pos"][1] = float(y - self.drag_oy)
# # # #
# # # #         if ev.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
# # # #             if self.drag_tile is None:
# # # #                 return
# # # #             t = self.drag_tile
# # # #             self.drag_tile = None
# # # #             play(self.snd_drop)
# # # #
# # # #             cx = int(t["pos"][0] + self.tile_w / 2)
# # # #             cy = int(t["pos"][1] + self.tile_h / 2)
# # # #
# # # #             slot_x, slot_y = t["correct"]
# # # #             slot_c = (slot_x + self.tile_w // 2, slot_y + self.tile_h // 2)
# # # #
# # # #             if dist2((cx, cy), slot_c) <= (SNAP_DIST * SNAP_DIST) and not self._square_slot_occupied((slot_x, slot_y)):
# # # #                 t["pos"][0] = float(slot_x)
# # # #                 t["pos"][1] = float(slot_y)
# # # #                 t["locked"] = True
# # # #                 play(self.snd_snap)
# # # #
# # # #                 if self._square_all_locked():
# # # #                     bg = self.screen.copy()
# # # #                     unlock_success_overlay(self.screen, self.clock, self.W, self.H, self.font_brand, self.font_small,
# # # #                                           self.snd_snap, bg_frame_surf=bg)
# # # #                     fade_to_black(self.screen, self.clock, 0.18)
# # # #                     self._result_unlocked = True
# # # #                     self._running = False
# # # #
# # # #     # ---------- Jigsaw ----------
# # # #     def _jigsaw_setup(self, cols: int, rows: int):
# # # #         if self.board_surf is None:
# # # #             return
# # # #         self.jig_cols, self.jig_rows = cols, rows
# # # #         self.jig_snap_dist = calc_jig_snap_dist(self.W, self.BOARD_H, cols, rows)
# # # #
# # # #         pieces = build_jigsaw_pieces(self.W, self.BOARD_H, self.board_surf, cols, rows)
# # # #         for p in pieces:
# # # #             w, h = p["surf"].get_size()
# # # #             pos = tray_random_pos_sized(self.W, self.tray_rect, w, h)
# # # #             p["fall_from"] = [float(pos[0]), float(-h - random.randint(20, 400))]
# # # #             p["fall_to"] = [float(pos[0]), float(pos[1])]
# # # #             p["pos"] = [p["fall_from"][0], p["fall_from"][1]]
# # # #             p["locked"] = False
# # # #         random.shuffle(pieces)
# # # #
# # # #         self.jig_pieces = pieces
# # # #         self.jig_drag_piece = None
# # # #         self.jig_stage = self.JIG_INTRO
# # # #         self.jig_t0 = time.time()
# # # #
# # # #     def _jigsaw_find_piece_at(self, x: int, y: int) -> Optional[Dict[str, Any]]:
# # # #         for p in reversed(self.jig_pieces):
# # # #             if p.get("locked"):
# # # #                 continue
# # # #             px, py = int(p["pos"][0]), int(p["pos"][1])
# # # #             lx, ly = x - px, y - py
# # # #             if lx < 0 or ly < 0:
# # # #                 continue
# # # #             if lx >= p["surf"].get_width() or ly >= p["surf"].get_height():
# # # #                 continue
# # # #             if p["mask"].get_at((lx, ly)):
# # # #                 return p
# # # #         return None
# # # #
# # # #     def _jigsaw_update_stage(self):
# # # #         now = time.time()
# # # #         if self.jig_stage == self.JIG_INTRO:
# # # #             if (now - self.jig_t0) >= JIG_INTRO_HOLD_S:
# # # #                 self.jig_stage = self.JIG_FALL
# # # #                 self.jig_t0 = now
# # # #
# # # #         elif self.jig_stage == self.JIG_FALL:
# # # #             t = (now - self.jig_t0) / max(0.001, JIG_FALL_S)
# # # #             if t >= 1.0:
# # # #                 for p in self.jig_pieces:
# # # #                     p["pos"] = [p["fall_to"][0], p["fall_to"][1]]
# # # #                 self.jig_stage = self.JIG_PLAY
# # # #                 self.jig_t0 = now
# # # #             else:
# # # #                 tt = _ease_out_cubic(t)
# # # #                 for p in self.jig_pieces:
# # # #                     fx, fy = p["fall_from"]
# # # #                     tx, ty = p["fall_to"]
# # # #                     p["pos"][0] = fx + (tx - fx) * tt
# # # #                     p["pos"][1] = fy + (ty - fy) * tt
# # # #
# # # #     def _jigsaw_draw(self):
# # # #         self.screen.fill(COLOR_BG)
# # # #
# # # #         title = self.font_brand2.render(f"Jigsaw {self.jig_cols} x {self.jig_rows}", True, (230, 230, 230))
# # # #         self.screen.blit(title, (self.W // 2 - title.get_width() // 2, 18))
# # # #
# # # #         board_panel = pygame.Rect(18, 60, self.W - 36, self.BOARD_H - 78)
# # # #         pygame.draw.rect(self.screen, (10, 10, 10), board_panel, border_radius=22)
# # # #         pygame.draw.rect(self.screen, (110, 110, 110), board_panel, 2, border_radius=22)
# # # #
# # # #         if self.jig_stage == self.JIG_INTRO and self.board_surf is not None:
# # # #             ref = pygame.transform.smoothscale(self.board_surf, (board_panel.w - 14, board_panel.h - 14))
# # # #             ref_rect = ref.get_rect(center=board_panel.center)
# # # #             self.screen.blit(ref, ref_rect.topleft)
# # # #             ov = pygame.Surface((ref.get_width(), ref.get_height()), pygame.SRCALPHA)
# # # #             ov.fill((0, 0, 0, 155))
# # # #             self.screen.blit(ov, ref_rect.topleft)
# # # #
# # # #         pygame.draw.rect(self.screen, COLOR_TRAY, self.tray_rect)
# # # #         pygame.draw.line(self.screen, COLOR_LINE, (0, self.BOARD_H), (self.W, self.BOARD_H), 2)
# # # #
# # # #         tray_label = self.font_small.render("Drag pieces into place (snaps when close).", True, (220, 220, 220))
# # # #         self.screen.blit(tray_label, (18, self.BOARD_H + 10))
# # # #
# # # #         mx, my = pygame.mouse.get_pos()
# # # #         draw_button(self.screen, self.back_btn, self.font_small, self.font_small, active=self.back_btn["rect"].collidepoint((mx, my)), small=True)
# # # #
# # # #         for p in self.jig_pieces:
# # # #             self.screen.blit(p["surf"], (p["pos"][0], p["pos"][1]))
# # # #
# # # #     def _jigsaw_handle_event(self, ev):
# # # #         if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
# # # #             self.state = self.STATE_LOCK
# # # #             self.lock_pressed = None
# # # #             return
# # # #
# # # #         if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
# # # #             pos = event_pos(ev, self.W, self.H)
# # # #             if not pos:
# # # #                 return
# # # #             x, y = pos
# # # #
# # # #             if self.back_btn["rect"].collidepoint((x, y)):
# # # #                 self.state = self.STATE_LOCK
# # # #                 self.lock_pressed = None
# # # #                 return
# # # #
# # # #             if self.jig_stage != self.JIG_PLAY:
# # # #                 return
# # # #
# # # #             p = self._jigsaw_find_piece_at(x, y)
# # # #             if p:
# # # #                 play(self.snd_pick)
# # # #                 self.jig_drag_piece = p
# # # #                 self.jig_drag_ox = x - int(p["pos"][0])
# # # #                 self.jig_drag_oy = y - int(p["pos"][1])
# # # #                 self.jig_pieces.remove(p)
# # # #                 self.jig_pieces.append(p)
# # # #
# # # #         if ev.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
# # # #             if self.jig_drag_piece is None:
# # # #                 return
# # # #             pos = event_pos(ev, self.W, self.H)
# # # #             if not pos:
# # # #                 return
# # # #             x, y = pos
# # # #             self.jig_drag_piece["pos"][0] = float(x - self.jig_drag_ox)
# # # #             self.jig_drag_piece["pos"][1] = float(y - self.jig_drag_oy)
# # # #
# # # #         if ev.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
# # # #             if self.jig_drag_piece is None:
# # # #                 return
# # # #             p = self.jig_drag_piece
# # # #             self.jig_drag_piece = None
# # # #             play(self.snd_drop)
# # # #
# # # #             correct = p["correct_pos"]
# # # #             px, py = p["pos"]
# # # #             dx = (px - correct[0])
# # # #             dy = (py - correct[1])
# # # #             if (dx * dx + dy * dy) <= (self.jig_snap_dist * self.jig_snap_dist):
# # # #                 p["pos"][0] = float(correct[0])
# # # #                 p["pos"][1] = float(correct[1])
# # # #                 p["locked"] = True
# # # #                 play(self.snd_snap)
# # # #
# # # #                 if jigsaw_all_locked(self.jig_pieces):
# # # #                     bg = self.screen.copy()
# # # #                     unlock_success_overlay(self.screen, self.clock, self.W, self.H, self.font_brand, self.font_small,
# # # #                                           self.snd_snap, hold_s=JIG_SOLVED_HOLD_S, bg_frame_surf=bg)
# # # #                     fade_to_black(self.screen, self.clock, 0.18)
# # # #                     self._result_unlocked = True
# # # #                     self._running = False
# # # #
# # # #     # ---------- Lock state ----------
# # # #     def _draw_lock(self):
# # # #         if self.lock_trans == self.LOCK_TRANS_BREAK:
# # # #             t = (time.time() - self.lock_trans_t0) / max(0.001, self.break_dur)
# # # #             if t >= 1.0:
# # # #                 self._advance_image()
# # # #                 self.lock_trans = self.LOCK_TRANS_FADEIN
# # # #                 self.lock_trans_t0 = time.time()
# # # #                 self._draw_fadein(0.0)
# # # #             else:
# # # #                 self._draw_break(t)
# # # #         elif self.lock_trans == self.LOCK_TRANS_FADEIN:
# # # #             t = (time.time() - self.lock_trans_t0) / max(0.001, LOCK_FADEIN_S)
# # # #             if t >= 1.0:
# # # #                 self.lock_trans = self.LOCK_TRANS_NONE
# # # #                 self._draw_lock_frame_to(self.screen)
# # # #             else:
# # # #                 self._draw_fadein(t)
# # # #         else:
# # # #             self._draw_lock_frame_to(self.screen)
# # # #
# # # #         title = self.font_brand.render(BRAND_TEXT, True, (255, 255, 255))
# # # #         subtitle = self.font_brand2.render(BRAND_SUB, True, (230, 230, 230))
# # # #         self.screen.blit(title, (30, 70))
# # # #         self.screen.blit(subtitle, (30, 135))
# # # #
# # # #         self._draw_status_bar()
# # # #
# # # #         target = 255.0 if self._lock_ui_visible() else 0.0
# # # #         dt = 1.0 / 60.0
# # # #         step = (255.0 / max(0.001, LOCK_UI_FADE_S)) * dt
# # # #         if self.ui_alpha < target:
# # # #             self.ui_alpha = min(target, self.ui_alpha + step)
# # # #         elif self.ui_alpha > target:
# # # #             self.ui_alpha = max(target, self.ui_alpha - step)
# # # #
# # # #         a = int(self.ui_alpha)
# # # #         if a > 0:
# # # #             draw_modern_dock(self.screen, self.dock_rect, a)
# # # #
# # # #             mx, my = pygame.mouse.get_pos()
# # # #             over_unlock = self.btn_unlock.collidepoint((mx, my))
# # # #             over_jigsaw = self.btn_jigsaw.collidepoint((mx, my))
# # # #             over_admin = self.btn_admin.collidepoint((mx, my))
# # # #
# # # #             pressed_unlock = (self.lock_pressed == "unlock")
# # # #             pressed_jigsaw = (self.lock_pressed == "jigsaw")
# # # #             pressed_admin = (self.lock_pressed == "admin")
# # # #
# # # #             draw_modern_button(self.screen, self.btn_unlock, "Unlock", self.font_dock,
# # # #                                _draw_icon_lock, ACCENT_UNLOCK, over_unlock, pressed_unlock, a)
# # # #             draw_modern_button(self.screen, self.btn_jigsaw, "Jigsaw", self.font_dock,
# # # #                                _draw_icon_jigsaw, ACCENT_JIGSAW, over_jigsaw, pressed_jigsaw, a)
# # # #             draw_modern_button(self.screen, self.btn_admin, "PIN", self.font_dock,
# # # #                                _draw_icon_key, ACCENT_ADMIN, over_admin, pressed_admin, a)
# # # #
# # # #     def _lock_handle_event(self, ev):
# # # #         if ev.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
# # # #             pos = event_pos(ev, self.W, self.H)
# # # #             if pos:
# # # #                 x, y = pos
# # # #                 lx, ly = self.last_mouse_pos
# # # #                 if abs(x - lx) + abs(y - ly) >= LOCK_UI_MOUSE_MOVE_THRESH:
# # # #                     self._touch_lock_ui()
# # # #                 self.last_mouse_pos = (x, y)
# # # #
# # # #         if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
# # # #             self._touch_lock_ui()
# # # #             pos = event_pos(ev, self.W, self.H)
# # # #             if not pos:
# # # #                 return
# # # #             x, y = pos
# # # #
# # # #             if self.ui_alpha >= 40:
# # # #                 if self.btn_unlock.collidepoint((x, y)):
# # # #                     self.lock_pressed = "unlock"
# # # #                     play(self.snd_pick)
# # # #                 elif self.btn_jigsaw.collidepoint((x, y)):
# # # #                     self.lock_pressed = "jigsaw"
# # # #                     play(self.snd_pick)
# # # #                 elif self.btn_admin.collidepoint((x, y)):
# # # #                     self.lock_pressed = "admin"
# # # #                     play(self.snd_pick)
# # # #                 else:
# # # #                     self.lock_pressed = None
# # # #
# # # #         if ev.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
# # # #             pos = event_pos(ev, self.W, self.H)
# # # #             if not pos:
# # # #                 self.lock_pressed = None
# # # #                 return
# # # #             x, y = pos
# # # #
# # # #             pressed = self.lock_pressed
# # # #             self.lock_pressed = None
# # # #             if pressed is None:
# # # #                 return
# # # #
# # # #             if pressed == "unlock" and self.btn_unlock.collidepoint((x, y)):
# # # #                 self._square_setup()
# # # #                 self.state = self.STATE_SQUARE
# # # #                 return
# # # #
# # # #             if pressed == "jigsaw" and self.btn_jigsaw.collidepoint((x, y)):
# # # #                 self.state = self.STATE_JIG_SELECT
# # # #                 return
# # # #
# # # #             if pressed == "admin" and self.btn_admin.collidepoint((x, y)):
# # # #                 bg = self.screen.copy()
# # # #                 ok = pin_overlay_loop(self.screen, self.clock, self.W, self.H, bg, self.font, self.font_small, self.snd_error)
# # # #                 if ok:
# # # #                     bg2 = self.screen.copy()
# # # #                     unlock_success_overlay(self.screen, self.clock, self.W, self.H, self.font_brand, self.font_small,
# # # #                                           self.snd_snap, bg_frame_surf=bg2)
# # # #                     fade_to_black(self.screen, self.clock, 0.18)
# # # #                     self._result_unlocked = True
# # # #                     self._running = False
# # # #                 return
# # # #
# # # #         if ev.type == pygame.KEYDOWN:
# # # #             self._touch_lock_ui()
# # # #             if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
# # # #                 self._square_setup()
# # # #                 self.state = self.STATE_SQUARE
# # # #                 return
# # # #             if ev.key == pygame.K_j:
# # # #                 self.state = self.STATE_JIG_SELECT
# # # #                 return
# # # #
# # # #     def run(self) -> bool:
# # # #         # If no images exist, still allow lock UI to operate (plain black)
# # # #         if not self.playlist:
# # # #             self.lock_trans = self.LOCK_TRANS_NONE
# # # #
# # # #         selected_jig = 1
# # # #         prev_time = time.time()
# # # #
# # # #         while self._running:
# # # #             now = time.time()
# # # #             dt = now - prev_time
# # # #             prev_time = now
# # # #
# # # #             if self.state == self.STATE_LOCK:
# # # #                 self._update_pan(dt)
# # # #                 if self.lock_trans == self.LOCK_TRANS_NONE and LOCK_TRANSITION_ENABLE and self.playlist:
# # # #                     if (now - self.lock_cycle_t0) >= LOCK_BG_CYCLE_S:
# # # #                         self._begin_lock_transition()
# # # #
# # # #             for ev in pygame.event.get():
# # # #                 if ev.type == pygame.QUIT:
# # # #                     self._running = False
# # # #                     break
# # # #
# # # #                 if self.state == self.STATE_LOCK:
# # # #                     self._lock_handle_event(ev)
# # # #
# # # #                 elif self.state == self.STATE_SQUARE:
# # # #                     self._square_handle_event(ev)
# # # #
# # # #                 elif self.state == self.STATE_JIG_SELECT:
# # # #                     if ev.type == pygame.KEYDOWN:
# # # #                         if ev.key == pygame.K_ESCAPE:
# # # #                             self.state = self.STATE_LOCK
# # # #                             continue
# # # #                         if ev.key == pygame.K_UP:
# # # #                             selected_jig = max(0, selected_jig - 1)
# # # #                         if ev.key == pygame.K_DOWN:
# # # #                             selected_jig = min(len(JIG_DIFFICULTY_CHOICES) - 1, selected_jig + 1)
# # # #                         if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
# # # #                             _, c, r = JIG_DIFFICULTY_CHOICES[selected_jig]
# # # #                             self._jigsaw_setup(c, r)
# # # #                             self.state = self.STATE_JIGSAW
# # # #                             continue
# # # #
# # # #                     if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
# # # #                         pos = event_pos(ev, self.W, self.H)
# # # #                         if pos:
# # # #                             x, y = pos
# # # #                             if self.back_btn["rect"].collidepoint((x, y)):
# # # #                                 self.state = self.STATE_LOCK
# # # #                                 continue
# # # #
# # # #                             row_h = 70
# # # #                             gap = 12
# # # #                             start_y = 170
# # # #                             for i in range(len(JIG_DIFFICULTY_CHOICES)):
# # # #                                 rect = pygame.Rect(int(self.W * 0.18), start_y + i * (row_h + gap), int(self.W * 0.64), row_h)
# # # #                                 if rect.collidepoint((x, y)):
# # # #                                     selected_jig = i
# # # #                                     _, c, r = JIG_DIFFICULTY_CHOICES[selected_jig]
# # # #                                     self._jigsaw_setup(c, r)
# # # #                                     self.state = self.STATE_JIGSAW
# # # #                                     break
# # # #
# # # #                 elif self.state == self.STATE_JIGSAW:
# # # #                     self._jigsaw_handle_event(ev)
# # # #
# # # #             if self.state == self.STATE_SQUARE:
# # # #                 self._square_update_stage()
# # # #             if self.state == self.STATE_JIGSAW:
# # # #                 self._jigsaw_update_stage()
# # # #
# # # #             if self.state == self.STATE_LOCK:
# # # #                 self._draw_lock()
# # # #             elif self.state == self.STATE_SQUARE:
# # # #                 self._square_draw()
# # # #             elif self.state == self.STATE_JIG_SELECT:
# # # #                 # simple select screen
# # # #                 self.screen.fill(COLOR_BG)
# # # #                 title = self.font_brand.render("Jigsaw Unlock", True, (255, 255, 255))
# # # #                 self.screen.blit(title, (self.W // 2 - title.get_width() // 2, 60))
# # # #                 sub = self.font_small.render("Select difficulty", True, (220, 220, 220))
# # # #                 self.screen.blit(sub, (self.W // 2 - sub.get_width() // 2, 120))
# # # #
# # # #                 mx, my = pygame.mouse.get_pos()
# # # #                 draw_button(self.screen, self.back_btn, self.font_small, self.font_small,
# # # #                             active=self.back_btn["rect"].collidepoint((mx, my)), small=True)
# # # #
# # # #                 row_h = 70
# # # #                 gap = 12
# # # #                 start_y = 170
# # # #                 for i, (name, c, r) in enumerate(JIG_DIFFICULTY_CHOICES):
# # # #                     rect = pygame.Rect(int(self.W * 0.18), start_y + i * (row_h + gap), int(self.W * 0.64), row_h)
# # # #                     active = rect.collidepoint((mx, my))
# # # #                     bg = (40, 40, 40) if (i == selected_jig) else (22, 22, 22)
# # # #                     if active:
# # # #                         bg = lighten(bg, 10)
# # # #                     pygame.draw.rect(self.screen, bg, rect, border_radius=16)
# # # #                     pygame.draw.rect(self.screen, (140, 140, 140), rect, 2, border_radius=16)
# # # #
# # # #                     label = self.font.render(f"{name}", True, (240, 240, 240))
# # # #                     dims = self.font_small.render(f"{c} x {r}", True, (210, 210, 210))
# # # #                     self.screen.blit(label, (rect.x + 22, rect.centery - label.get_height() // 2))
# # # #                     self.screen.blit(dims, (rect.right - dims.get_width() - 22, rect.centery - dims.get_height() // 2))
# # # #
# # # #             elif self.state == self.STATE_JIGSAW:
# # # #                 self._jigsaw_draw()
# # # #
# # # #             pygame.display.flip()
# # # #             self.clock.tick(60)
# # # #
# # # #         return bool(self._result_unlocked)
# # # #
# # # #
# # # # # ============================================================
# # # # # Public entrypoint for kiosk_shell shared-window use
# # # # # ============================================================
# # # # def run_lock_shared(screen: pygame.Surface, clock: Optional[pygame.time.Clock] = None) -> bool:
# # # #     """
# # # #     Runs the lock UI on an existing fullscreen pygame display (no new window).
# # # #     Returns True if unlocked.
# # # #     """
# # # #     app = LockApp(screen=screen, clock=clock)
# # # #     return app.run()
# # # #
# # # #
# # # # # Backward compatible alias (so your kiosk_shell call reads cleanly)
# # # # def run_lock_shared(screen: pygame.Surface, clock: Optional[pygame.time.Clock] = None) -> bool:
# # # #     app = LockApp(screen=screen, clock=clock)
# # # #     return app.run()
# # # #
# # # #
# # # # # Standalone execution (creates its own window)
# # # # if __name__ == "__main__":
# # # #     app = LockApp(screen=None, clock=None)
# # # #     ok = app.run()
# # # #     # In standalone mode, return codes are meaningful; in shared mode, caller handles it.
# # # #     sys.exit(0 if ok else 1)
# # # #!/usr/bin/env python3
# # # # -*- coding: utf-8 -*-
# # #
# # # import os
# # # import sys
# # # import time
# # # import math
# # # import random
# # # import datetime
# # # from typing import Optional, Tuple, List, Dict, Any
# # #
# # # # Must be set before importing pygame
# # # os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
# # # os.environ.setdefault("SDL_VIDEODRIVER", "x11")
# # # os.environ.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")
# # # os.environ.setdefault("SDL_VIDEO_WINDOW_POS", "0,0")
# # # os.environ.setdefault("SDL_VIDEO_CENTERED", "0")
# # #
# # # import pygame  # noqa: E402
# # #
# # #
# # # # ---------------- CONFIG ----------------
# # # GRID_X = 3
# # # GRID_Y = 4
# # #
# # # SNAP_DIST = 190
# # #
# # # BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# # # IMAGE_DIR = os.path.join(BASE_DIR, "images")
# # # SOUNDS_DIR = os.path.join(BASE_DIR, "sounds")
# # #
# # # BRAND_TEXT = "Glover SPARCstation"
# # # BRAND_SUB = "Puzzle Lock"
# # #
# # # ADMIN_PIN = "1193"
# # # PIN_MAX_LEN = 12
# # #
# # # SHOW_STATUS_BAR = True
# # # STATUS_BAR_H = 40
# # #
# # # LOCK_UI_START_HIDDEN = True
# # # LOCK_UI_AUTOHIDE_S = 6.0
# # # LOCK_UI_MOUSE_MOVE_THRESH = 10
# # # LOCK_UI_FADE_S = 0.18
# # #
# # # LOCK_BG_CYCLE_S = 18.0
# # # LOCK_VISIBLE_SCALE_MODE = "contain"
# # #
# # # LOCK_BG_PAN_RANGE_PX = 900
# # # LOCK_BG_PAN_SPEED_PX_S = 90.0
# # #
# # # LOCK_BG_BLUR_METHOD = "hq"
# # # LOCK_BG_HQ_DOWNSCALE = 2
# # # LOCK_BG_HQ_RADIUS = 10
# # #
# # # LOCK_BG_BLUR_DOWNSCALE = 12
# # # LOCK_BG_DIM_ALPHA = 60
# # #
# # # LOCK_TRANSITION_ENABLE = True
# # # LOCK_FADEIN_S = 0.55
# # #
# # # LOCK_TRANSITION_STYLES = ["shatter", "blinds", "explode", "drop"]
# # # LOCK_TRANSITION_STYLE = "random"
# # # LOCK_BREAK_DURATIONS = {
# # #     "shatter": 0.85,
# # #     "blinds":  0.95,
# # #     "explode": 0.80,
# # #     "drop":    0.90,
# # # }
# # #
# # # LOCK_SHATTER_TILE_TARGET = 180
# # # LOCK_SHATTER_GRAVITY = 1200.0
# # #
# # # LOCK_BG_RANDOM_START = True
# # # LOCK_BG_SHUFFLE = False
# # #
# # # COLOR_BG = (0, 0, 0)
# # # COLOR_TRAY = (18, 18, 18)
# # # COLOR_LINE = (70, 70, 70)
# # #
# # # UI_TEXT = (240, 240, 240)
# # # UI_MUTED = (210, 210, 210)
# # #
# # # ACCENT_UNLOCK = (70, 185, 120)
# # # ACCENT_JIGSAW = (170, 170, 170)
# # # ACCENT_ADMIN = (120, 200, 255)
# # #
# # # SND_PICK = "pick.wav"
# # # SND_DROP = "drop.wav"
# # # SND_SNAP = "snap.wav"
# # # SND_ERROR = "error.wav"
# # #
# # # TRAY_H_FRAC = 0.28
# # # TRAY_MARGIN = 14
# # #
# # # PUZ_INTRO_HOLD_S = 0.55
# # # PUZ_FALL_S = 0.85
# # # UNLOCK_SUCCESS_S = 0.85
# # #
# # # JIG_KNOB_FRAC = 0.22
# # # JIG_EDGE_OFF_FRAC = 0.18
# # #
# # # JIG_SNAP_FRAC = 0.55
# # # JIG_SNAP_MIN = 40
# # # JIG_SNAP_MAX = 140
# # #
# # # JIG_INTRO_HOLD_S = 0.55
# # # JIG_FALL_S = 0.85
# # # JIG_SOLVED_HOLD_S = 0.85
# # #
# # # JIG_BG_DIM_ALPHA = 130
# # #
# # # JIG_DIFFICULTY_CHOICES = [
# # #     ("Easy",    3, 2),
# # #     ("Normal",  4, 3),
# # #     ("Hard",    5, 4),
# # #     ("Expert",  6, 4),
# # #     ("Insane", 10, 5),
# # #     ("Extreme", 12, 5),
# # # ]
# # #
# # # PUZZLE_BOARD_SCALE_MODE = "cover"
# # #
# # #
# # # # ---------------- helpers ----------------
# # # def clamp255(v: float) -> int:
# # #     return max(0, min(255, int(v)))
# # #
# # #
# # # def lighten(color, amt=22):
# # #     return (clamp255(color[0] + amt), clamp255(color[1] + amt), clamp255(color[2] + amt))
# # #
# # #
# # # def _ease_in_quad(t: float) -> float:
# # #     return t * t
# # #
# # #
# # # def _ease_out_cubic(t: float) -> float:
# # #     u = 1.0 - t
# # #     return 1.0 - (u * u * u)
# # #
# # #
# # # def dist2(a, b) -> float:
# # #     dx = a[0] - b[0]
# # #     dy = a[1] - b[1]
# # #     return dx * dx + dy * dy
# # #
# # #
# # # def load_sound(name: str):
# # #     path = os.path.join(SOUNDS_DIR, name)
# # #     if os.path.exists(path):
# # #         try:
# # #             return pygame.mixer.Sound(path)
# # #         except Exception:
# # #             return None
# # #     return None
# # #
# # #
# # # def play(snd):
# # #     if snd:
# # #         try:
# # #             snd.play()
# # #         except Exception:
# # #             pass
# # #
# # #
# # # def event_pos(ev, W: int, H: int):
# # #     if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
# # #         return ev.pos
# # #     if ev.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
# # #         return (int(ev.x * W), int(ev.y * H))
# # #     return None
# # #
# # #
# # # def safe_load_image(path: str) -> pygame.Surface:
# # #     try:
# # #         from PIL import Image, ImageOps  # type: ignore
# # #         img = Image.open(path)
# # #         img = ImageOps.exif_transpose(img)
# # #         if img.mode in ("RGBA", "LA") or ("transparency" in img.info):
# # #             img = img.convert("RGBA")
# # #             surf = pygame.image.frombuffer(img.tobytes(), img.size, "RGBA").convert_alpha()
# # #         else:
# # #             img = img.convert("RGB")
# # #             surf = pygame.image.frombuffer(img.tobytes(), img.size, "RGB").convert()
# # #         return surf
# # #     except Exception:
# # #         surf = pygame.image.load(path)
# # #         try:
# # #             return surf.convert_alpha() if surf.get_alpha() is not None else surf.convert()
# # #         except Exception:
# # #             return surf
# # #
# # #
# # # def scale_cover(src_surf: pygame.Surface, target_w: int, target_h: int) -> pygame.Surface:
# # #     sw, sh = src_surf.get_size()
# # #     scale = max(target_w / sw, target_h / sh)
# # #     nw = max(1, int(sw * scale))
# # #     nh = max(1, int(sh * scale))
# # #     scaled = pygame.transform.smoothscale(src_surf, (nw, nh))
# # #     x = (nw - target_w) // 2
# # #     y = (nh - target_h) // 2
# # #     return scaled.subsurface(pygame.Rect(x, y, target_w, target_h)).copy()
# # #
# # #
# # # def scale_contain(src_surf: pygame.Surface, target_w: int, target_h: int):
# # #     sw, sh = src_surf.get_size()
# # #     scale = min(target_w / sw, target_h / sh)
# # #     nw = max(1, int(sw * scale))
# # #     nh = max(1, int(sh * scale))
# # #     scaled = pygame.transform.smoothscale(src_surf, (nw, nh))
# # #     rect = scaled.get_rect(center=(target_w // 2, target_h // 2))
# # #     return scaled, rect
# # #
# # #
# # # def blur_surface_once(src: pygame.Surface, downscale: int = 12) -> pygame.Surface:
# # #     downscale = max(2, int(downscale))
# # #     w, h = src.get_size()
# # #     dw = max(2, w // downscale)
# # #     dh = max(2, h // downscale)
# # #     small = pygame.transform.smoothscale(src, (dw, dh))
# # #     return pygame.transform.smoothscale(small, (w, h))
# # #
# # #
# # # def blur_surface_hq(src: pygame.Surface, radius: int = 10, downscale: int = 2) -> pygame.Surface:
# # #     try:
# # #         from PIL import Image, ImageFilter  # type: ignore
# # #         w, h = src.get_size()
# # #         ds = max(1, int(downscale))
# # #         if ds > 1:
# # #             sw = max(2, w // ds)
# # #             sh = max(2, h // ds)
# # #             src_small = pygame.transform.smoothscale(src, (sw, sh))
# # #             raw = pygame.image.tostring(src_small, "RGB")
# # #             im = Image.frombytes("RGB", (sw, sh), raw)
# # #         else:
# # #             raw = pygame.image.tostring(src, "RGB")
# # #             im = Image.frombytes("RGB", (w, h), raw)
# # #
# # #         im = im.filter(ImageFilter.GaussianBlur(radius=max(0, int(radius))))
# # #         if ds > 1:
# # #             im = im.resize((w, h), resample=Image.LANCZOS)
# # #
# # #         out = pygame.image.frombuffer(im.tobytes(), (w, h), "RGB").convert()
# # #         return out
# # #     except Exception:
# # #         return blur_surface_once(src, LOCK_BG_BLUR_DOWNSCALE)
# # #
# # #
# # # def _draw_round_rect_alpha(dst, rect: pygame.Rect, rgb, alpha: int, radius: int):
# # #     a = clamp255(alpha)
# # #     s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
# # #     pygame.draw.rect(s, (rgb[0], rgb[1], rgb[2], a), pygame.Rect(0, 0, rect.w, rect.h), border_radius=radius)
# # #     dst.blit(s, rect.topleft)
# # #
# # #
# # # def _draw_round_rect_outline_alpha(dst, rect: pygame.Rect, rgb, alpha: int, radius: int, width: int = 2):
# # #     a = clamp255(alpha)
# # #     s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
# # #     pygame.draw.rect(s, (rgb[0], rgb[1], rgb[2], a), pygame.Rect(0, 0, rect.w, rect.h), width, border_radius=radius)
# # #     dst.blit(s, rect.topleft)
# # #
# # #
# # # def _draw_icon_lock(dst, center, color, alpha=255):
# # #     cx, cy = center
# # #     a = clamp255(alpha)
# # #     col = (color[0], color[1], color[2], a)
# # #     s = pygame.Surface((40, 40), pygame.SRCALPHA)
# # #     pygame.draw.arc(s, col, pygame.Rect(10, 6, 20, 18), math.pi, 0, 3)
# # #     pygame.draw.rect(s, col, pygame.Rect(10, 18, 20, 16), border_radius=5)
# # #     dst.blit(s, (cx - 20, cy - 20))
# # #
# # #
# # # def _draw_icon_jigsaw(dst, center, color, alpha=255):
# # #     cx, cy = center
# # #     a = clamp255(alpha)
# # #     col = (color[0], color[1], color[2], a)
# # #     s = pygame.Surface((40, 40), pygame.SRCALPHA)
# # #     pygame.draw.rect(s, col, pygame.Rect(10, 10, 18, 14), 2, border_radius=3)
# # #     pygame.draw.rect(s, col, pygame.Rect(14, 14, 18, 14), 2, border_radius=3)
# # #     pygame.draw.line(s, col, (16, 24), (22, 18), 2)
# # #     pygame.draw.line(s, col, (22, 18), (30, 26), 2)
# # #     dst.blit(s, (cx - 20, cy - 20))
# # #
# # #
# # # def _draw_icon_key(dst, center, color, alpha=255):
# # #     cx, cy = center
# # #     a = clamp255(alpha)
# # #     col = (color[0], color[1], color[2], a)
# # #     s = pygame.Surface((40, 40), pygame.SRCALPHA)
# # #     pygame.draw.circle(s, col, (14, 20), 6, 2)
# # #     pygame.draw.line(s, col, (20, 20), (34, 20), 2)
# # #     pygame.draw.line(s, col, (28, 20), (28, 26), 2)
# # #     pygame.draw.line(s, col, (32, 20), (32, 24), 2)
# # #     dst.blit(s, (cx - 20, cy - 20))
# # #
# # #
# # # def draw_modern_dock(dst, dock_rect: pygame.Rect, alpha: int):
# # #     _draw_round_rect_alpha(dst, dock_rect, (0, 0, 0), int(150 * (alpha / 255.0)), radius=22)
# # #     _draw_round_rect_outline_alpha(dst, dock_rect, (255, 255, 255), int(90 * (alpha / 255.0)), radius=22, width=2)
# # #
# # #
# # # def draw_modern_button(dst, rect: pygame.Rect, label: str, font, icon_fn, accent_rgb,
# # #                        active: bool, pressed: bool, alpha: int):
# # #     a = clamp255(alpha)
# # #     shadow_off = 3 if not pressed else 1
# # #     _draw_round_rect_alpha(dst, rect.move(0, shadow_off), (0, 0, 0), int(90 * (a / 255.0)), radius=16)
# # #
# # #     base = (18, 18, 18)
# # #     if active:
# # #         base = (26, 26, 26)
# # #     if pressed:
# # #         base = (12, 12, 12)
# # #
# # #     _draw_round_rect_alpha(dst, rect, base, int(210 * (a / 255.0)), radius=16)
# # #
# # #     strip = pygame.Rect(rect.x + 12, rect.y + rect.h - 10, rect.w - 24, 4)
# # #     _draw_round_rect_alpha(dst, strip, accent_rgb, int(200 * (a / 255.0)), radius=4)
# # #
# # #     _draw_round_rect_outline_alpha(dst, rect, (255, 255, 255), int(95 * (a / 255.0)), radius=16, width=2)
# # #
# # #     icon_center = (rect.x + 26, rect.centery)
# # #     icon_fn(dst, icon_center, accent_rgb, alpha=a)
# # #
# # #     txt = font.render(label, True, (240, 240, 240))
# # #     txt.set_alpha(a)
# # #     dst.blit(txt, (rect.x + 52, rect.centery - txt.get_height() // 2))
# # #
# # #
# # # def make_button(rect: pygame.Rect, label: str, color=(90, 90, 90)):
# # #     return {"rect": rect, "label": label, "color": color}
# # #
# # #
# # # def draw_button(screen, btn, font_main, font_small, active=False, small=False):
# # #     r = btn["rect"]
# # #     base = btn.get("color", (90, 90, 90))
# # #     bg = base if not active else lighten(base, 28)
# # #
# # #     pygame.draw.rect(screen, bg, r, border_radius=16)
# # #     pygame.draw.rect(screen, (230, 230, 230), r, 2, border_radius=16)
# # #
# # #     f = font_small if small else font_main
# # #     t = f.render(btn["label"], True, (255, 255, 255))
# # #     screen.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))
# # #
# # #
# # # def fade_to_black(screen, clock, dur_s: float = 0.18):
# # #     t0 = time.time()
# # #     w, h = screen.get_size()
# # #     while True:
# # #         now = time.time()
# # #         t = (now - t0) / max(0.001, dur_s)
# # #         if t >= 1.0:
# # #             break
# # #         a = int(255 * t)
# # #         ov = pygame.Surface((w, h), pygame.SRCALPHA)
# # #         ov.fill((0, 0, 0, a))
# # #         screen.blit(ov, (0, 0))
# # #         pygame.display.flip()
# # #         clock.tick(60)
# # #     screen.fill((0, 0, 0))
# # #     pygame.display.flip()
# # #
# # #
# # # def unlock_success_overlay(screen, clock, W, H, font_brand, font_small, snd_snap,
# # #                           msg="UNLOCKED", sub="Returning to menu...", hold_s=UNLOCK_SUCCESS_S,
# # #                           bg_frame_surf: Optional[pygame.Surface] = None):
# # #     play(snd_snap)
# # #     t0 = time.time()
# # #     while time.time() - t0 < hold_s:
# # #         for ev in pygame.event.get():
# # #             if ev.type == pygame.QUIT:
# # #                 raise SystemExit
# # #
# # #         if bg_frame_surf is not None:
# # #             screen.blit(bg_frame_surf, (0, 0))
# # #         else:
# # #             screen.fill(COLOR_BG)
# # #
# # #         overlay = pygame.Surface((W, H), pygame.SRCALPHA)
# # #         overlay.fill((0, 0, 0, 180))
# # #         screen.blit(overlay, (0, 0))
# # #
# # #         m = font_brand.render(msg, True, (255, 255, 255))
# # #         s = font_small.render(sub, True, (230, 230, 230))
# # #         screen.blit(m, (W // 2 - m.get_width() // 2, H // 2 - 40))
# # #         screen.blit(s, (W // 2 - s.get_width() // 2, H // 2 + 20))
# # #         pygame.display.flip()
# # #         clock.tick(60)
# # #
# # #
# # # def pin_overlay_loop(screen, clock, W, H, bg_frame_surf, font, font_small, snd_error) -> bool:
# # #     pin_input = ""
# # #     pin_error = ""
# # #     pin_error_t0 = 0.0
# # #
# # #     cancel_btn = make_button(pygame.Rect(16, 16, 170, 48), "CANCEL", color=(120, 120, 120))
# # #
# # #     KEYPAD_COLS = 3
# # #     KEYPAD_ROWS = 4
# # #     KEYS = ["1", "2", "3",
# # #             "4", "5", "6",
# # #             "7", "8", "9",
# # #             "C", "0", "OK"]
# # #
# # #     def submit() -> bool:
# # #         nonlocal pin_input, pin_error, pin_error_t0
# # #         if pin_input == ADMIN_PIN:
# # #             return True
# # #         pin_error = "Incorrect PIN"
# # #         pin_error_t0 = time.time()
# # #         pin_input = ""
# # #         play(snd_error)
# # #         return False
# # #
# # #     while True:
# # #         for ev in pygame.event.get():
# # #             if ev.type == pygame.QUIT:
# # #                 raise SystemExit
# # #
# # #             if ev.type == pygame.KEYDOWN:
# # #                 if ev.key == pygame.K_ESCAPE:
# # #                     return False
# # #                 if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
# # #                     if submit():
# # #                         return True
# # #                 elif ev.key == pygame.K_BACKSPACE:
# # #                     pin_input = pin_input[:-1]
# # #                 else:
# # #                     if ev.unicode.isdigit() and len(pin_input) < PIN_MAX_LEN:
# # #                         pin_input += ev.unicode
# # #
# # #             if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
# # #                 pos = event_pos(ev, W, H)
# # #                 if not pos:
# # #                     continue
# # #
# # #                 if cancel_btn["rect"].collidepoint(pos):
# # #                     return False
# # #
# # #                 pad_w = min(520, int(W * 0.42))
# # #                 pad_h = min(520, int(H * 0.62))
# # #                 pad_x = (W - pad_w) // 2
# # #                 pad_y = (H - pad_h) // 2 + 40
# # #                 cell_w = pad_w // KEYPAD_COLS
# # #                 cell_h = pad_h // KEYPAD_ROWS
# # #
# # #                 idx = 0
# # #                 for r in range(KEYPAD_ROWS):
# # #                     for c in range(KEYPAD_COLS):
# # #                         x = pad_x + c * cell_w + 8
# # #                         y = pad_y + r * cell_h + 8
# # #                         rect = pygame.Rect(x, y, cell_w - 16, cell_h - 16)
# # #                         if rect.collidepoint(pos):
# # #                             key = KEYS[idx]
# # #                             if key == "C":
# # #                                 pin_input = ""
# # #                             elif key == "OK":
# # #                                 if submit():
# # #                                     return True
# # #                             else:
# # #                                 if len(pin_input) < PIN_MAX_LEN:
# # #                                     pin_input += key
# # #                             break
# # #                         idx += 1
# # #
# # #         screen.blit(bg_frame_surf, (0, 0))
# # #         overlay = pygame.Surface((W, H), pygame.SRCALPHA)
# # #         overlay.fill((0, 0, 0, 205))
# # #         screen.blit(overlay, (0, 0))
# # #
# # #         mx, my = pygame.mouse.get_pos()
# # #         draw_button(screen, cancel_btn, font, font_small, active=cancel_btn["rect"].collidepoint((mx, my)), small=True)
# # #
# # #         title = font.render("PIN UNLOCK", True, (255, 255, 255))
# # #         prompt = font_small.render("Enter PIN (keyboard or touchscreen keypad):", True, (230, 230, 230))
# # #         masked = "*" * len(pin_input)
# # #         entry = font.render(masked, True, (255, 255, 0))
# # #
# # #         screen.blit(title, (W // 2 - title.get_width() // 2, 80))
# # #         screen.blit(prompt, (W // 2 - prompt.get_width() // 2, 130))
# # #         screen.blit(entry, (W // 2 - entry.get_width() // 2, 165))
# # #
# # #         pad_w = min(520, int(W * 0.42))
# # #         pad_h = min(520, int(H * 0.62))
# # #         pad_x = (W - pad_w) // 2
# # #         pad_y = (H - pad_h) // 2 + 40
# # #         cell_w = pad_w // KEYPAD_COLS
# # #         cell_h = pad_h // KEYPAD_ROWS
# # #
# # #         pygame.draw.rect(screen, (35, 35, 35), pygame.Rect(pad_x, pad_y, pad_w, pad_h), border_radius=12)
# # #
# # #         rects = []
# # #         for r in range(KEYPAD_ROWS):
# # #             for c in range(KEYPAD_COLS):
# # #                 x = pad_x + c * cell_w + 8
# # #                 y = pad_y + r * cell_h + 8
# # #                 rects.append(pygame.Rect(x, y, cell_w - 16, cell_h - 16))
# # #
# # #         for i, r in enumerate(rects):
# # #             pygame.draw.rect(screen, (70, 70, 70), r, border_radius=10)
# # #             label = font.render(KEYS[i], True, (255, 255, 255))
# # #             screen.blit(label, (r.centerx - label.get_width() // 2, r.centery - label.get_height() // 2))
# # #
# # #         if pin_error and (time.time() - pin_error_t0) < 2.0:
# # #             err = font_small.render(pin_error, True, (255, 90, 90))
# # #             screen.blit(err, (W // 2 - err.get_width() // 2, pad_y + pad_h + 18))
# # #
# # #         tip = font_small.render("Enter/OK=submit, Backspace=delete, Esc/CANCEL=back.", True, (230, 230, 230))
# # #         screen.blit(tip, (W // 2 - tip.get_width() // 2, pad_y + pad_h + 50))
# # #
# # #         pygame.display.flip()
# # #         clock.tick(60)
# # #
# # #
# # # def calc_jig_snap_dist(W: int, BOARD_H: int, cols: int, rows: int) -> int:
# # #     cols = max(1, int(cols))
# # #     rows = max(1, int(rows))
# # #     cell_w = W // cols
# # #     cell_h = BOARD_H // rows
# # #     base = int(min(cell_w, cell_h) * JIG_SNAP_FRAC)
# # #     return max(JIG_SNAP_MIN, min(JIG_SNAP_MAX, base))
# # #
# # #
# # # def _make_jigsaw_edges(cols, rows):
# # #     h_edges = [
# # #         [{"dir": random.choice([-1, 1]), "off": random.uniform(-JIG_EDGE_OFF_FRAC, JIG_EDGE_OFF_FRAC)}
# # #          for _ in range(cols)]
# # #         for _ in range(rows - 1)
# # #     ]
# # #     v_edges = [
# # #         [{"dir": random.choice([-1, 1]), "off": random.uniform(-JIG_EDGE_OFF_FRAC, JIG_EDGE_OFF_FRAC)}
# # #          for _ in range(cols - 1)]
# # #         for _ in range(rows)
# # #     ]
# # #     return h_edges, v_edges
# # #
# # #
# # # def _apply_edge_circle(mask_surf, kind, center, radius):
# # #     if kind == 0:
# # #         return
# # #     if kind > 0:
# # #         pygame.draw.circle(mask_surf, (255, 255, 255, 255), center, radius)
# # #     else:
# # #         pygame.draw.circle(mask_surf, (255, 255, 255, 0), center, radius)
# # #
# # #
# # # def build_jigsaw_pieces(W, BOARD_H, board_surf, cols, rows):
# # #     cell_w = W // cols
# # #     cell_h = BOARD_H // rows
# # #
# # #     knob_r = int(min(cell_w, cell_h) * JIG_KNOB_FRAC)
# # #     margin = knob_r + 3
# # #
# # #     h_edges, v_edges = _make_jigsaw_edges(cols, rows)
# # #
# # #     pieces = []
# # #     for y in range(rows):
# # #         for x in range(cols):
# # #             if y == 0:
# # #                 top_kind, top_off = 0, 0.0
# # #             else:
# # #                 top_kind = -h_edges[y - 1][x]["dir"]
# # #                 top_off = h_edges[y - 1][x]["off"]
# # #
# # #             if y == rows - 1:
# # #                 bot_kind, bot_off = 0, 0.0
# # #             else:
# # #                 bot_kind = h_edges[y][x]["dir"]
# # #                 bot_off = h_edges[y][x]["off"]
# # #
# # #             if x == 0:
# # #                 left_kind, left_off = 0, 0.0
# # #             else:
# # #                 left_kind = -v_edges[y][x - 1]["dir"]
# # #                 left_off = v_edges[y][x - 1]["off"]
# # #
# # #             if x == cols - 1:
# # #                 right_kind, right_off = 0, 0.0
# # #             else:
# # #                 right_kind = v_edges[y][x]["dir"]
# # #                 right_off = v_edges[y][x]["off"]
# # #
# # #             pw = cell_w + 2 * margin
# # #             ph = cell_h + 2 * margin
# # #
# # #             mask_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
# # #             mask_surf.fill((255, 255, 255, 0))
# # #             pygame.draw.rect(mask_surf, (255, 255, 255, 255), pygame.Rect(margin, margin, cell_w, cell_h))
# # #
# # #             cx_top = margin + (cell_w // 2) + int(top_off * cell_w)
# # #             cy_top = margin
# # #             _apply_edge_circle(mask_surf, top_kind, (cx_top, cy_top), knob_r)
# # #
# # #             cx_bot = margin + (cell_w // 2) + int(bot_off * cell_w)
# # #             cy_bot = margin + cell_h
# # #             _apply_edge_circle(mask_surf, bot_kind, (cx_bot, cy_bot), knob_r)
# # #
# # #             cx_left = margin
# # #             cy_left = margin + (cell_h // 2) + int(left_off * cell_h)
# # #             _apply_edge_circle(mask_surf, left_kind, (cx_left, cy_left), knob_r)
# # #
# # #             cx_right = margin + cell_w
# # #             cy_right = margin + (cell_h // 2) + int(right_off * cell_h)
# # #             _apply_edge_circle(mask_surf, right_kind, (cx_right, cy_right), knob_r)
# # #
# # #             piece_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
# # #             piece_surf.blit(board_surf, (margin - x * cell_w, margin - y * cell_h))
# # #             piece_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
# # #
# # #             piece_mask = pygame.mask.from_surface(mask_surf)
# # #             correct_pos = (x * cell_w - margin, y * cell_h - margin)
# # #
# # #             pieces.append({
# # #                 "surf": piece_surf,
# # #                 "mask": piece_mask,
# # #                 "correct_pos": correct_pos,
# # #                 "pos": correct_pos,
# # #                 "locked": False,
# # #                 "fall_from": correct_pos,
# # #                 "fall_to": correct_pos,
# # #             })
# # #
# # #     return pieces
# # #
# # #
# # # def tray_random_pos_sized(W, tray_rect, obj_w, obj_h):
# # #     x0 = TRAY_MARGIN
# # #     x1 = W - TRAY_MARGIN - obj_w
# # #     y0 = tray_rect.top + TRAY_MARGIN
# # #     y1 = tray_rect.bottom - TRAY_MARGIN - obj_h
# # #     if x1 < x0:
# # #         x1 = x0
# # #     if y1 < y0:
# # #         y1 = y0
# # #     return (random.randint(x0, x1), random.randint(y0, y1))
# # #
# # #
# # # def jigsaw_all_locked(pieces):
# # #     return all(p.get("locked") for p in pieces)
# # #
# # #
# # # # ---------------- LockApp ----------------
# # # class LockApp:
# # #     STATE_LOCK = "LOCK"
# # #     STATE_SQUARE = "SQUARE"
# # #     STATE_JIG_SELECT = "JIG_SELECT"
# # #     STATE_JIGSAW = "JIGSAW"
# # #
# # #     PUZ_INTRO = "INTRO"
# # #     PUZ_FALL = "FALL"
# # #     PUZ_PLAY = "PLAY"
# # #
# # #     JIG_INTRO = "INTRO"
# # #     JIG_FALL = "FALL"
# # #     JIG_PLAY = "PLAY"
# # #     JIG_SOLVED = "SOLVED"
# # #
# # #     LOCK_TRANS_NONE = None
# # #     LOCK_TRANS_BREAK = "BREAK"
# # #     LOCK_TRANS_FADEIN = "FADEIN"
# # #
# # #     def __init__(self, screen: Optional[pygame.Surface] = None, clock: Optional[pygame.time.Clock] = None):
# # #         self._shared = (screen is not None)
# # #         if not pygame.get_init():
# # #             pygame.init()
# # #         try:
# # #             if not pygame.font.get_init():
# # #                 pygame.font.init()
# # #         except Exception:
# # #             pass
# # #
# # #         # Mixer best-effort
# # #         try:
# # #             if not pygame.mixer.get_init():
# # #                 pygame.mixer.init()
# # #         except Exception:
# # #             pass
# # #
# # #         if screen is None:
# # #             # Standalone mode (still NOFRAME to avoid decoration)
# # #             self.screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)
# # #             pygame.display.set_caption("SPARC Lock")
# # #         else:
# # #             # Shared-screen mode (DO NOT create a new window)
# # #             self.screen = screen
# # #
# # #         self.clock = clock or pygame.time.Clock()
# # #         self.W, self.H = self.screen.get_size()
# # #         pygame.mouse.set_visible(True)
# # #
# # #         self.font = pygame.font.SysFont(None, 52)
# # #         self.font_small = pygame.font.SysFont(None, 26)
# # #         self.font_brand = pygame.font.SysFont(None, 64)
# # #         self.font_brand2 = pygame.font.SysFont(None, 28)
# # #         self.font_dock = pygame.font.SysFont(None, 28)
# # #
# # #         self.snd_pick = load_sound(SND_PICK)
# # #         self.snd_drop = load_sound(SND_DROP)
# # #         self.snd_snap = load_sound(SND_SNAP)
# # #         self.snd_error = load_sound(SND_ERROR)
# # #
# # #         self.TRAY_H = int(self.H * TRAY_H_FRAC)
# # #         self.BOARD_H = self.H - self.TRAY_H
# # #         self.board_rect = pygame.Rect(0, 0, self.W, self.BOARD_H)
# # #         self.tray_rect = pygame.Rect(0, self.BOARD_H, self.W, self.TRAY_H)
# # #
# # #         self.images = self._load_images()
# # #         self.playlist = list(self.images)
# # #         if LOCK_BG_SHUFFLE:
# # #             random.shuffle(self.playlist)
# # #         else:
# # #             self.playlist.sort()
# # #         self.lock_idx = random.randrange(len(self.playlist)) if (LOCK_BG_RANDOM_START and self.playlist) else 0
# # #
# # #         self.lock_bg_big = None
# # #         self.lock_fg = None
# # #         self.lock_fg_rect = None
# # #         self.board_surf = None
# # #         self.img_name = ""
# # #
# # #         self.pan_x = 0.0
# # #         self.pan_y = 0.0
# # #         self.pan_vx = 0.0
# # #         self.pan_vy = 0.0
# # #
# # #         self.lock_cycle_t0 = time.time()
# # #         self.lock_trans = self.LOCK_TRANS_NONE
# # #         self.lock_trans_t0 = 0.0
# # #
# # #         self.break_style = "shatter"
# # #         self.break_dur = float(LOCK_BREAK_DURATIONS.get("shatter", 0.85))
# # #
# # #         self.lock_snapshot = pygame.Surface((self.W, self.H))
# # #         self.break_pieces: List[Dict[str, Any]] = []
# # #
# # #         if self.playlist:
# # #             self._set_image_by_index(self.lock_idx)
# # #
# # #         now = time.time()
# # #         self.lock_ui_visible_until = (now + LOCK_UI_AUTOHIDE_S) if not LOCK_UI_START_HIDDEN else 0.0
# # #         self.last_mouse_pos = pygame.mouse.get_pos()
# # #         self.ui_alpha = 0.0 if LOCK_UI_START_HIDDEN else 255.0
# # #
# # #         self._layout_lock_dock()
# # #         self.lock_pressed = None
# # #
# # #         self.state = self.STATE_LOCK
# # #
# # #         self.tiles: List[Dict[str, Any]] = []
# # #         self.tile_w = 0
# # #         self.tile_h = 0
# # #         self.slot_positions: List[Tuple[int, int]] = []
# # #         self.drag_tile: Optional[Dict[str, Any]] = None
# # #         self.drag_ox = 0
# # #         self.drag_oy = 0
# # #         self.puz_stage = self.PUZ_INTRO
# # #         self.puz_t0 = 0.0
# # #
# # #         self.jig_cols, self.jig_rows = JIG_DIFFICULTY_CHOICES[1][1], JIG_DIFFICULTY_CHOICES[1][2]
# # #         self.jig_snap_dist = calc_jig_snap_dist(self.W, self.BOARD_H, self.jig_cols, self.jig_rows)
# # #         self.jig_pieces: List[Dict[str, Any]] = []
# # #         self.jig_drag_piece: Optional[Dict[str, Any]] = None
# # #         self.jig_drag_ox = 0
# # #         self.jig_drag_oy = 0
# # #         self.jig_stage = self.JIG_INTRO
# # #         self.jig_t0 = 0.0
# # #
# # #         self.back_btn = make_button(pygame.Rect(16, 16, 160, 48), "BACK", color=(120, 120, 120))
# # #
# # #         self._running = True
# # #         self._result_unlocked = False
# # #
# # #     def _layout_lock_dock(self):
# # #         margin_bottom = 28
# # #         dock_w = min(780, int(self.W * 0.68))
# # #         dock_h = 96
# # #         dock_x = (self.W - dock_w) // 2
# # #         dock_y = self.H - dock_h - margin_bottom
# # #         self.dock_rect = pygame.Rect(dock_x, dock_y, dock_w, dock_h)
# # #
# # #         pad = 14
# # #         gap = 12
# # #         btn_h = 64
# # #         btn_y = dock_y + (dock_h - btn_h) // 2
# # #         btn_w = (dock_w - pad * 2 - gap * 2) // 3
# # #
# # #         self.btn_unlock = pygame.Rect(dock_x + pad + (btn_w + gap) * 0, btn_y, btn_w, btn_h)
# # #         self.btn_jigsaw = pygame.Rect(dock_x + pad + (btn_w + gap) * 1, btn_y, btn_w, btn_h)
# # #         self.btn_admin = pygame.Rect(dock_x + pad + (btn_w + gap) * 2, btn_y, btn_w, btn_h)
# # #
# # #     def _load_images(self):
# # #         if not os.path.isdir(IMAGE_DIR):
# # #             return []
# # #         imgs = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
# # #         return imgs
# # #
# # #     def _touch_lock_ui(self):
# # #         self.lock_ui_visible_until = time.time() + LOCK_UI_AUTOHIDE_S
# # #
# # #     def _lock_ui_visible(self) -> bool:
# # #         return time.time() < self.lock_ui_visible_until
# # #
# # #     def _set_image_by_index(self, idx: int):
# # #         self.lock_idx = idx % len(self.playlist)
# # #         fname = self.playlist[self.lock_idx]
# # #         raw = safe_load_image(os.path.join(IMAGE_DIR, fname))
# # #         self.img_name = fname
# # #
# # #         if LOCK_VISIBLE_SCALE_MODE.lower() == "cover":
# # #             self.lock_fg = scale_cover(raw, self.W, self.H)
# # #             self.lock_fg_rect = self.lock_fg.get_rect(topleft=(0, 0))
# # #         else:
# # #             self.lock_fg, self.lock_fg_rect = scale_contain(raw, self.W, self.H)
# # #
# # #         big_w = self.W + LOCK_BG_PAN_RANGE_PX
# # #         big_h = self.H + LOCK_BG_PAN_RANGE_PX
# # #         bg = scale_cover(raw, big_w, big_h).convert()
# # #
# # #         if LOCK_BG_BLUR_METHOD.lower() == "hq":
# # #             bg = blur_surface_hq(bg, radius=LOCK_BG_HQ_RADIUS, downscale=LOCK_BG_HQ_DOWNSCALE)
# # #         else:
# # #             bg = blur_surface_once(bg, LOCK_BG_BLUR_DOWNSCALE).convert()
# # #
# # #         if LOCK_BG_DIM_ALPHA > 0:
# # #             dim = pygame.Surface((big_w, big_h), pygame.SRCALPHA)
# # #             dim.fill((0, 0, 0, clamp255(LOCK_BG_DIM_ALPHA)))
# # #             bg.blit(dim, (0, 0))
# # #
# # #         self.lock_bg_big = bg.convert()
# # #
# # #         if PUZZLE_BOARD_SCALE_MODE.lower() == "contain":
# # #             board_fit, rect = scale_contain(raw, self.W, self.BOARD_H)
# # #             board = pygame.Surface((self.W, self.BOARD_H))
# # #             board.fill((0, 0, 0))
# # #             board.blit(board_fit, rect)
# # #             self.board_surf = board.convert()
# # #         else:
# # #             self.board_surf = scale_cover(raw, self.W, self.BOARD_H).convert()
# # #
# # #         max_x = max(0, self.lock_bg_big.get_width() - self.W)
# # #         max_y = max(0, self.lock_bg_big.get_height() - self.H)
# # #         self.pan_x = float(random.randint(0, max_x)) if max_x else 0.0
# # #         self.pan_y = float(random.randint(0, max_y)) if max_y else 0.0
# # #
# # #         ang = random.uniform(0, math.tau)
# # #         self.pan_vx = math.cos(ang) * LOCK_BG_PAN_SPEED_PX_S
# # #         self.pan_vy = math.sin(ang) * LOCK_BG_PAN_SPEED_PX_S
# # #
# # #         self.lock_cycle_t0 = time.time()
# # #
# # #     def _advance_image(self):
# # #         nxt = self.lock_idx + 1
# # #         if nxt >= len(self.playlist):
# # #             nxt = 0
# # #             if LOCK_BG_SHUFFLE:
# # #                 random.shuffle(self.playlist)
# # #         self._set_image_by_index(nxt)
# # #
# # #     def _update_pan(self, dt: float):
# # #         if not self.lock_bg_big:
# # #             return
# # #         max_x = max(0, self.lock_bg_big.get_width() - self.W)
# # #         max_y = max(0, self.lock_bg_big.get_height() - self.H)
# # #
# # #         self.pan_x += self.pan_vx * dt
# # #         self.pan_y += self.pan_vy * dt
# # #
# # #         if max_x > 0:
# # #             if self.pan_x < 0:
# # #                 self.pan_x = 0.0
# # #                 self.pan_vx = abs(self.pan_vx)
# # #             elif self.pan_x > max_x:
# # #                 self.pan_x = float(max_x)
# # #                 self.pan_vx = -abs(self.pan_vx)
# # #         else:
# # #             self.pan_x = 0.0
# # #
# # #         if max_y > 0:
# # #             if self.pan_y < 0:
# # #                 self.pan_y = 0.0
# # #                 self.pan_vy = abs(self.pan_vy)
# # #             elif self.pan_y > max_y:
# # #                 self.pan_y = float(max_y)
# # #                 self.pan_vy = -abs(self.pan_vy)
# # #         else:
# # #             self.pan_y = 0.0
# # #
# # #     # ---------------- YOUR REMAINDER (verbatim) ----------------
# # #     def _draw_lock_frame_to(self, target_surf: pygame.Surface):
# # #         if self.lock_bg_big:
# # #             max_x = max(0, self.lock_bg_big.get_width() - self.W)
# # #             max_y = max(0, self.lock_bg_big.get_height() - self.H)
# # #             vx = int(max(0, min(max_x, self.pan_x)))
# # #             vy = int(max(0, min(max_y, self.pan_y)))
# # #             view = pygame.Rect(vx, vy, self.W, self.H)
# # #             target_surf.blit(self.lock_bg_big.subsurface(view), (0, 0))
# # #         else:
# # #             target_surf.fill((0, 0, 0))
# # #
# # #         if self.lock_fg and self.lock_fg_rect:
# # #             target_surf.blit(self.lock_fg, self.lock_fg_rect)
# # #
# # #     def _build_lock_frame_surface(self) -> pygame.Surface:
# # #         surf = pygame.Surface((self.W, self.H))
# # #         self._draw_lock_frame_to(surf)
# # #         return surf
# # #
# # #     def _draw_status_bar(self):
# # #         if not SHOW_STATUS_BAR:
# # #             return
# # #         bar = pygame.Surface((self.W, STATUS_BAR_H), pygame.SRCALPHA)
# # #         bar.fill((0, 0, 0, 140))
# # #         self.screen.blit(bar, (0, 0))
# # #         now = datetime.datetime.now()
# # #         txt = now.strftime("%a %b %d   %I:%M %p").lstrip("0")
# # #         t = self.font_small.render(txt, True, (230, 230, 230))
# # #         self.screen.blit(t, (self.W - t.get_width() - 16, (STATUS_BAR_H - t.get_height()) // 2))
# # #
# # #     def _choose_break_style(self) -> str:
# # #         if LOCK_TRANSITION_STYLE == "random":
# # #             return random.choice(LOCK_TRANSITION_STYLES)
# # #         if LOCK_TRANSITION_STYLE in LOCK_TRANSITION_STYLES:
# # #             return LOCK_TRANSITION_STYLE
# # #         return "shatter"
# # #
# # #     def _make_break_pieces(self, snap: pygame.Surface, style: str) -> List[Dict[str, Any]]:
# # #         pieces: List[Dict[str, Any]] = []
# # #         W, H = self.W, self.H
# # #
# # #         if style == "blinds":
# # #             n = 16
# # #             tile_w = max(16, W // n)
# # #             for i in range(n):
# # #                 x = i * tile_w
# # #                 w = tile_w if i < n - 1 else (W - x)
# # #                 rect = pygame.Rect(x, 0, w, H)
# # #                 surf = snap.subsurface(rect).copy()
# # #                 dir_sign = -1 if (i % 2 == 0) else 1
# # #                 vx = dir_sign * random.uniform(250, 450)
# # #                 pieces.append({
# # #                     "surf": surf,
# # #                     "pos": [float(rect.x), float(rect.y)],
# # #                     "vel": [vx, random.uniform(-40, 40)],
# # #                     "rot": 0.0,
# # #                     "ang": random.uniform(-30, 30),
# # #                 })
# # #             return pieces
# # #
# # #         target = LOCK_SHATTER_TILE_TARGET
# # #         cols = int(math.sqrt(target * (W / max(1.0, H))))
# # #         cols = max(6, min(30, cols))
# # #         rows = max(6, min(24, int(target / cols)))
# # #         tile_w = max(18, W // cols)
# # #         tile_h = max(18, H // rows)
# # #
# # #         for y in range(0, H, tile_h):
# # #             for x in range(0, W, tile_w):
# # #                 rect = pygame.Rect(x, y, min(tile_w, W - x), min(tile_h, H - y))
# # #                 surf = snap.subsurface(rect).copy()
# # #                 cx = rect.centerx - W / 2.0
# # #                 cy = rect.centery - H / 2.0
# # #
# # #                 if style == "explode":
# # #                     mag = random.uniform(220, 520)
# # #                     ang = math.atan2(cy, cx) + random.uniform(-0.25, 0.25)
# # #                     vx = math.cos(ang) * mag
# # #                     vy = math.sin(ang) * mag
# # #                 elif style == "drop":
# # #                     vx = random.uniform(-80, 80)
# # #                     vy = random.uniform(50, 160)
# # #                 else:
# # #                     vx = random.uniform(-260, 260) + (cx * 0.25)
# # #                     vy = random.uniform(-180, 120) + (cy * 0.20)
# # #
# # #                 rot = random.uniform(-35, 35)
# # #                 pieces.append({
# # #                     "surf": surf,
# # #                     "pos": [float(rect.x), float(rect.y)],
# # #                     "vel": [vx, vy],
# # #                     "rot": 0.0,
# # #                     "ang": rot,
# # #                 })
# # #
# # #         return pieces
# # #
# # #     def _begin_lock_transition(self):
# # #         self.lock_snapshot = self._build_lock_frame_surface()
# # #         self.break_style = self._choose_break_style()
# # #         self.break_dur = float(LOCK_BREAK_DURATIONS.get(self.break_style, 0.85))
# # #         self.lock_trans = self.LOCK_TRANS_BREAK
# # #         self.lock_trans_t0 = time.time()
# # #         self.break_pieces = self._make_break_pieces(self.lock_snapshot, self.break_style)
# # #
# # #     def _draw_break(self, t: float):
# # #         self.screen.fill((0, 0, 0))
# # #         dt = 1.0 / 60.0
# # #         grav = LOCK_SHATTER_GRAVITY
# # #
# # #         for p in self.break_pieces:
# # #             vx, vy = p["vel"]
# # #             if self.break_style in ("shatter", "drop"):
# # #                 vy += grav * dt * (0.70 if self.break_style == "drop" else 0.40)
# # #                 p["vel"][1] = vy
# # #
# # #             p["pos"][0] += vx * dt
# # #             p["pos"][1] += vy * dt
# # #
# # #             damp = 1.0 - (0.12 * t)
# # #             p["vel"][0] *= damp
# # #             p["vel"][1] *= damp
# # #
# # #             p["rot"] += p["ang"] * dt
# # #
# # #             surf = p["surf"]
# # #             if abs(p["rot"]) > 0.5:
# # #                 rs = pygame.transform.rotozoom(surf, p["rot"], 1.0)
# # #                 r = rs.get_rect(center=(p["pos"][0] + surf.get_width() / 2, p["pos"][1] + surf.get_height() / 2))
# # #                 self.screen.blit(rs, r.topleft)
# # #             else:
# # #                 self.screen.blit(surf, (p["pos"][0], p["pos"][1]))
# # #
# # #         ov = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
# # #         ov.fill((0, 0, 0, int(220 * _ease_in_quad(t))))
# # #         self.screen.blit(ov, (0, 0))
# # #
# # #     def _draw_fadein(self, t: float):
# # #         self._draw_lock_frame_to(self.screen)
# # #         a = int(255 * (1.0 - _ease_out_cubic(t)))
# # #         ov = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
# # #         ov.fill((0, 0, 0, a))
# # #         self.screen.blit(ov, (0, 0))
# # #
# # #     # ---------- Square puzzle ----------
# # #     def _square_setup(self):
# # #         if self.board_surf is None:
# # #             return
# # #
# # #         margin = 40
# # #         usable_w = self.W - margin * 2
# # #         usable_h = self.BOARD_H - margin * 2
# # #         cols, rows = GRID_X, GRID_Y
# # #
# # #         self.tile_w = usable_w // cols
# # #         self.tile_h = usable_h // rows
# # #
# # #         self.slot_positions = []
# # #         for j in range(rows):
# # #             for i in range(cols):
# # #                 sx = margin + i * self.tile_w
# # #                 sy = margin + j * self.tile_h
# # #                 self.slot_positions.append((sx, sy))
# # #
# # #         board_scaled = pygame.transform.smoothscale(self.board_surf, (usable_w, usable_h))
# # #         tiles: List[Dict[str, Any]] = []
# # #         for j in range(rows):
# # #             for i in range(cols):
# # #                 src_rect = pygame.Rect(i * self.tile_w, j * self.tile_h, self.tile_w, self.tile_h)
# # #                 surf = board_scaled.subsurface(src_rect).copy()
# # #                 tile = pygame.Surface((self.tile_w, self.tile_h), pygame.SRCALPHA)
# # #                 tile.blit(surf, (0, 0))
# # #                 pygame.draw.rect(tile, (255, 255, 255, 70), pygame.Rect(0, 0, self.tile_w, self.tile_h), 2, border_radius=10)
# # #
# # #                 correct = self.slot_positions[j * cols + i]
# # #                 pos = tray_random_pos_sized(self.W, self.tray_rect, self.tile_w, self.tile_h)
# # #                 tiles.append({
# # #                     "surf": tile,
# # #                     "correct": correct,
# # #                     "pos": [float(pos[0]), float(pos[1])],
# # #                     "locked": False,
# # #                     "fall_from": [float(pos[0]), float(-self.tile_h - random.randint(20, 400))],
# # #                     "fall_to": [float(pos[0]), float(pos[1])],
# # #                 })
# # #
# # #         random.shuffle(tiles)
# # #         self.tiles = tiles
# # #         self.drag_tile = None
# # #         self.puz_stage = self.PUZ_INTRO
# # #         self.puz_t0 = time.time()
# # #
# # #     def _square_all_locked(self) -> bool:
# # #         return all(t["locked"] for t in self.tiles)
# # #
# # #     def _square_slot_occupied(self, slot_xy: Tuple[int, int]) -> bool:
# # #         for t in self.tiles:
# # #             if t["locked"] and tuple(map(int, t["pos"])) == slot_xy:
# # #                 return True
# # #         return False
# # #
# # #     def _square_find_tile_at(self, x: int, y: int) -> Optional[Dict[str, Any]]:
# # #         for t in reversed(self.tiles):
# # #             if t["locked"]:
# # #                 continue
# # #             r = pygame.Rect(int(t["pos"][0]), int(t["pos"][1]), self.tile_w, self.tile_h)
# # #             if r.collidepoint((x, y)):
# # #                 return t
# # #         return None
# # #
# # #     def _square_update_stage(self):
# # #         now = time.time()
# # #         if self.puz_stage == self.PUZ_INTRO:
# # #             if (now - self.puz_t0) >= PUZ_INTRO_HOLD_S:
# # #                 for t in self.tiles:
# # #                     pos = tray_random_pos_sized(self.W, self.tray_rect, self.tile_w, self.tile_h)
# # #                     t["fall_from"] = [float(pos[0]), float(-self.tile_h - random.randint(20, 400))]
# # #                     t["fall_to"] = [float(pos[0]), float(pos[1])]
# # #                     t["pos"] = [t["fall_from"][0], t["fall_from"][1]]
# # #                 self.puz_stage = self.PUZ_FALL
# # #                 self.puz_t0 = now
# # #
# # #         elif self.puz_stage == self.PUZ_FALL:
# # #             t = (now - self.puz_t0) / max(0.001, PUZ_FALL_S)
# # #             if t >= 1.0:
# # #                 for tile in self.tiles:
# # #                     tile["pos"] = [tile["fall_to"][0], tile["fall_to"][1]]
# # #                 self.puz_stage = self.PUZ_PLAY
# # #                 self.puz_t0 = now
# # #             else:
# # #                 tt = _ease_out_cubic(t)
# # #                 for tile in self.tiles:
# # #                     fx, fy = tile["fall_from"]
# # #                     tx, ty = tile["fall_to"]
# # #                     tile["pos"][0] = fx + (tx - fx) * tt
# # #                     tile["pos"][1] = fy + (ty - fy) * tt
# # #
# # #     def _square_draw(self):
# # #         self.screen.fill(COLOR_BG)
# # #
# # #         title = self.font_brand2.render("Unlock Puzzle", True, (230, 230, 230))
# # #         self.screen.blit(title, (self.W // 2 - title.get_width() // 2, 18))
# # #
# # #         board_panel = pygame.Rect(18, 60, self.W - 36, self.BOARD_H - 78)
# # #         pygame.draw.rect(self.screen, (10, 10, 10), board_panel, border_radius=22)
# # #         pygame.draw.rect(self.screen, (110, 110, 110), board_panel, 2, border_radius=22)
# # #
# # #         margin = 40
# # #         cols, rows = GRID_X, GRID_Y
# # #         usable_w = self.W - margin * 2
# # #         usable_h = self.BOARD_H - margin * 2
# # #         tile_w = usable_w // cols
# # #         tile_h = usable_h // rows
# # #
# # #         for j in range(rows):
# # #             for i in range(cols):
# # #                 sx = margin + i * tile_w
# # #                 sy = margin + j * tile_h
# # #                 slot_rect = pygame.Rect(sx, sy, tile_w, tile_h)
# # #                 pygame.draw.rect(self.screen, (55, 55, 55), slot_rect, 2, border_radius=10)
# # #
# # #         pygame.draw.rect(self.screen, COLOR_TRAY, self.tray_rect)
# # #         pygame.draw.line(self.screen, COLOR_LINE, (0, self.BOARD_H), (self.W, self.BOARD_H), 2)
# # #
# # #         tray_label = self.font_small.render("Drag pieces into place.", True, (220, 220, 220))
# # #         self.screen.blit(tray_label, (18, self.BOARD_H + 10))
# # #
# # #         mx, my = pygame.mouse.get_pos()
# # #         draw_button(self.screen, self.back_btn, self.font_small, self.font_small, active=self.back_btn["rect"].collidepoint((mx, my)), small=True)
# # #
# # #         for t in self.tiles:
# # #             self.screen.blit(t["surf"], (t["pos"][0], t["pos"][1]))
# # #
# # #         if self.puz_stage == self.PUZ_INTRO and self.board_surf is not None:
# # #             ref = pygame.transform.smoothscale(self.board_surf, (board_panel.w - 14, board_panel.h - 14))
# # #             ref_rect = ref.get_rect(center=board_panel.center)
# # #             overlay = pygame.Surface((ref.get_width(), ref.get_height()), pygame.SRCALPHA)
# # #             overlay.fill((0, 0, 0, 140))
# # #             self.screen.blit(ref, ref_rect.topleft)
# # #             self.screen.blit(overlay, ref_rect.topleft)
# # #             msg = self.font_small.render("Memorize the picture...", True, (240, 240, 240))
# # #             self.screen.blit(msg, (self.W // 2 - msg.get_width() // 2, board_panel.bottom - 34))
# # #
# # #     def _square_handle_event(self, ev):
# # #         if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
# # #             self.state = self.STATE_LOCK
# # #             self.lock_pressed = None
# # #             return
# # #
# # #         if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
# # #             pos = event_pos(ev, self.W, self.H)
# # #             if not pos:
# # #                 return
# # #             x, y = pos
# # #
# # #             if self.back_btn["rect"].collidepoint((x, y)):
# # #                 self.state = self.STATE_LOCK
# # #                 self.lock_pressed = None
# # #                 return
# # #
# # #             if self.puz_stage != self.PUZ_PLAY:
# # #                 return
# # #
# # #             t = self._square_find_tile_at(x, y)
# # #             if t:
# # #                 play(self.snd_pick)
# # #                 self.drag_tile = t
# # #                 self.drag_ox = x - int(t["pos"][0])
# # #                 self.drag_oy = y - int(t["pos"][1])
# # #                 self.tiles.remove(t)
# # #                 self.tiles.append(t)
# # #
# # #         if ev.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
# # #             if self.drag_tile is None:
# # #                 return
# # #             pos = event_pos(ev, self.W, self.H)
# # #             if not pos:
# # #                 return
# # #             x, y = pos
# # #             self.drag_tile["pos"][0] = float(x - self.drag_ox)
# # #             self.drag_tile["pos"][1] = float(y - self.drag_oy)
# # #
# # #         if ev.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
# # #             if self.drag_tile is None:
# # #                 return
# # #             t = self.drag_tile
# # #             self.drag_tile = None
# # #             play(self.snd_drop)
# # #
# # #             cx = int(t["pos"][0] + self.tile_w / 2)
# # #             cy = int(t["pos"][1] + self.tile_h / 2)
# # #
# # #             slot_x, slot_y = t["correct"]
# # #             slot_c = (slot_x + self.tile_w // 2, slot_y + self.tile_h // 2)
# # #
# # #             if dist2((cx, cy), slot_c) <= (SNAP_DIST * SNAP_DIST) and not self._square_slot_occupied((slot_x, slot_y)):
# # #                 t["pos"][0] = float(slot_x)
# # #                 t["pos"][1] = float(slot_y)
# # #                 t["locked"] = True
# # #                 play(self.snd_snap)
# # #
# # #                 if self._square_all_locked():
# # #                     bg = self.screen.copy()
# # #                     unlock_success_overlay(self.screen, self.clock, self.W, self.H, self.font_brand, self.font_small,
# # #                                           self.snd_snap, bg_frame_surf=bg)
# # #                     fade_to_black(self.screen, self.clock, 0.18)
# # #                     self._result_unlocked = True
# # #                     self._running = False
# # #
# # #     # ---------- Jigsaw ----------
# # #     def _jigsaw_setup(self, cols: int, rows: int):
# # #         if self.board_surf is None:
# # #             return
# # #         self.jig_cols, self.jig_rows = cols, rows
# # #         self.jig_snap_dist = calc_jig_snap_dist(self.W, self.BOARD_H, cols, rows)
# # #
# # #         pieces = build_jigsaw_pieces(self.W, self.BOARD_H, self.board_surf, cols, rows)
# # #         for p in pieces:
# # #             w, h = p["surf"].get_size()
# # #             pos = tray_random_pos_sized(self.W, self.tray_rect, w, h)
# # #             p["fall_from"] = [float(pos[0]), float(-h - random.randint(20, 400))]
# # #             p["fall_to"] = [float(pos[0]), float(pos[1])]
# # #             p["pos"] = [p["fall_from"][0], p["fall_from"][1]]
# # #             p["locked"] = False
# # #         random.shuffle(pieces)
# # #
# # #         self.jig_pieces = pieces
# # #         self.jig_drag_piece = None
# # #         self.jig_stage = self.JIG_INTRO
# # #         self.jig_t0 = time.time()
# # #
# # #     def _jigsaw_find_piece_at(self, x: int, y: int) -> Optional[Dict[str, Any]]:
# # #         for p in reversed(self.jig_pieces):
# # #             if p.get("locked"):
# # #                 continue
# # #             px, py = int(p["pos"][0]), int(p["pos"][1])
# # #             lx, ly = x - px, y - py
# # #             if lx < 0 or ly < 0:
# # #                 continue
# # #             if lx >= p["surf"].get_width() or ly >= p["surf"].get_height():
# # #                 continue
# # #             if p["mask"].get_at((lx, ly)):
# # #                 return p
# # #         return None
# # #
# # #     def _jigsaw_update_stage(self):
# # #         now = time.time()
# # #         if self.jig_stage == self.JIG_INTRO:
# # #             if (now - self.jig_t0) >= JIG_INTRO_HOLD_S:
# # #                 self.jig_stage = self.JIG_FALL
# # #                 self.jig_t0 = now
# # #
# # #         elif self.jig_stage == self.JIG_FALL:
# # #             t = (now - self.jig_t0) / max(0.001, JIG_FALL_S)
# # #             if t >= 1.0:
# # #                 for p in self.jig_pieces:
# # #                     p["pos"] = [p["fall_to"][0], p["fall_to"][1]]
# # #                 self.jig_stage = self.JIG_PLAY
# # #                 self.jig_t0 = now
# # #             else:
# # #                 tt = _ease_out_cubic(t)
# # #                 for p in self.jig_pieces:
# # #                     fx, fy = p["fall_from"]
# # #                     tx, ty = p["fall_to"]
# # #                     p["pos"][0] = fx + (tx - fx) * tt
# # #                     p["pos"][1] = fy + (ty - fy) * tt
# # #
# # #     def _jigsaw_draw(self):
# # #         self.screen.fill(COLOR_BG)
# # #
# # #         title = self.font_brand2.render(f"Jigsaw {self.jig_cols} x {self.jig_rows}", True, (230, 230, 230))
# # #         self.screen.blit(title, (self.W // 2 - title.get_width() // 2, 18))
# # #
# # #         board_panel = pygame.Rect(18, 60, self.W - 36, self.BOARD_H - 78)
# # #         pygame.draw.rect(self.screen, (10, 10, 10), board_panel, border_radius=22)
# # #         pygame.draw.rect(self.screen, (110, 110, 110), board_panel, 2, border_radius=22)
# # #
# # #         if self.jig_stage == self.JIG_INTRO and self.board_surf is not None:
# # #             ref = pygame.transform.smoothscale(self.board_surf, (board_panel.w - 14, board_panel.h - 14))
# # #             ref_rect = ref.get_rect(center=board_panel.center)
# # #             self.screen.blit(ref, ref_rect.topleft)
# # #             ov = pygame.Surface((ref.get_width(), ref.get_height()), pygame.SRCALPHA)
# # #             ov.fill((0, 0, 0, 155))
# # #             self.screen.blit(ov, ref_rect.topleft)
# # #
# # #         pygame.draw.rect(self.screen, COLOR_TRAY, self.tray_rect)
# # #         pygame.draw.line(self.screen, COLOR_LINE, (0, self.BOARD_H), (self.W, self.BOARD_H), 2)
# # #
# # #         tray_label = self.font_small.render("Drag pieces into place (snaps when close).", True, (220, 220, 220))
# # #         self.screen.blit(tray_label, (18, self.BOARD_H + 10))
# # #
# # #         mx, my = pygame.mouse.get_pos()
# # #         draw_button(self.screen, self.back_btn, self.font_small, self.font_small, active=self.back_btn["rect"].collidepoint((mx, my)), small=True)
# # #
# # #         for p in self.jig_pieces:
# # #             self.screen.blit(p["surf"], (p["pos"][0], p["pos"][1]))
# # #
# # #     def _jigsaw_handle_event(self, ev):
# # #         if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
# # #             self.state = self.STATE_LOCK
# # #             self.lock_pressed = None
# # #             return
# # #
# # #         if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
# # #             pos = event_pos(ev, self.W, self.H)
# # #             if not pos:
# # #                 return
# # #             x, y = pos
# # #
# # #             if self.back_btn["rect"].collidepoint((x, y)):
# # #                 self.state = self.STATE_LOCK
# # #                 self.lock_pressed = None
# # #                 return
# # #
# # #             if self.jig_stage != self.JIG_PLAY:
# # #                 return
# # #
# # #             p = self._jigsaw_find_piece_at(x, y)
# # #             if p:
# # #                 play(self.snd_pick)
# # #                 self.jig_drag_piece = p
# # #                 self.jig_drag_ox = x - int(p["pos"][0])
# # #                 self.jig_drag_oy = y - int(p["pos"][1])
# # #                 self.jig_pieces.remove(p)
# # #                 self.jig_pieces.append(p)
# # #
# # #         if ev.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
# # #             if self.jig_drag_piece is None:
# # #                 return
# # #             pos = event_pos(ev, self.W, self.H)
# # #             if not pos:
# # #                 return
# # #             x, y = pos
# # #             self.jig_drag_piece["pos"][0] = float(x - self.jig_drag_ox)
# # #             self.jig_drag_piece["pos"][1] = float(y - self.jig_drag_oy)
# # #
# # #         if ev.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
# # #             if self.jig_drag_piece is None:
# # #                 return
# # #             p = self.jig_drag_piece
# # #             self.jig_drag_piece = None
# # #             play(self.snd_drop)
# # #
# # #             correct = p["correct_pos"]
# # #             px, py = p["pos"]
# # #             dx = (px - correct[0])
# # #             dy = (py - correct[1])
# # #             if (dx * dx + dy * dy) <= (self.jig_snap_dist * self.jig_snap_dist):
# # #                 p["pos"][0] = float(correct[0])
# # #                 p["pos"][1] = float(correct[1])
# # #                 p["locked"] = True
# # #                 play(self.snd_snap)
# # #
# # #                 if jigsaw_all_locked(self.jig_pieces):
# # #                     bg = self.screen.copy()
# # #                     unlock_success_overlay(self.screen, self.clock, self.W, self.H, self.font_brand, self.font_small,
# # #                                           self.snd_snap, hold_s=JIG_SOLVED_HOLD_S, bg_frame_surf=bg)
# # #                     fade_to_black(self.screen, self.clock, 0.18)
# # #                     self._result_unlocked = True
# # #                     self._running = False
# # #
# # #     # ---------- Lock state ----------
# # #     def _draw_lock(self):
# # #         if self.lock_trans == self.LOCK_TRANS_BREAK:
# # #             t = (time.time() - self.lock_trans_t0) / max(0.001, self.break_dur)
# # #             if t >= 1.0:
# # #                 self._advance_image()
# # #                 self.lock_trans = self.LOCK_TRANS_FADEIN
# # #                 self.lock_trans_t0 = time.time()
# # #                 self._draw_fadein(0.0)
# # #             else:
# # #                 self._draw_break(t)
# # #         elif self.lock_trans == self.LOCK_TRANS_FADEIN:
# # #             t = (time.time() - self.lock_trans_t0) / max(0.001, LOCK_FADEIN_S)
# # #             if t >= 1.0:
# # #                 self.lock_trans = self.LOCK_TRANS_NONE
# # #                 self._draw_lock_frame_to(self.screen)
# # #             else:
# # #                 self._draw_fadein(t)
# # #         else:
# # #             self._draw_lock_frame_to(self.screen)
# # #
# # #         title = self.font_brand.render(BRAND_TEXT, True, (255, 255, 255))
# # #         subtitle = self.font_brand2.render(BRAND_SUB, True, (230, 230, 230))
# # #         self.screen.blit(title, (30, 70))
# # #         self.screen.blit(subtitle, (30, 135))
# # #
# # #         self._draw_status_bar()
# # #
# # #         target = 255.0 if self._lock_ui_visible() else 0.0
# # #         dt = 1.0 / 60.0
# # #         step = (255.0 / max(0.001, LOCK_UI_FADE_S)) * dt
# # #         if self.ui_alpha < target:
# # #             self.ui_alpha = min(target, self.ui_alpha + step)
# # #         elif self.ui_alpha > target:
# # #             self.ui_alpha = max(target, self.ui_alpha - step)
# # #
# # #         a = int(self.ui_alpha)
# # #         if a > 0:
# # #             draw_modern_dock(self.screen, self.dock_rect, a)
# # #
# # #             mx, my = pygame.mouse.get_pos()
# # #             over_unlock = self.btn_unlock.collidepoint((mx, my))
# # #             over_jigsaw = self.btn_jigsaw.collidepoint((mx, my))
# # #             over_admin = self.btn_admin.collidepoint((mx, my))
# # #
# # #             pressed_unlock = (self.lock_pressed == "unlock")
# # #             pressed_jigsaw = (self.lock_pressed == "jigsaw")
# # #             pressed_admin = (self.lock_pressed == "admin")
# # #
# # #             draw_modern_button(self.screen, self.btn_unlock, "Unlock", self.font_dock,
# # #                                _draw_icon_lock, ACCENT_UNLOCK, over_unlock, pressed_unlock, a)
# # #             draw_modern_button(self.screen, self.btn_jigsaw, "Jigsaw", self.font_dock,
# # #                                _draw_icon_jigsaw, ACCENT_JIGSAW, over_jigsaw, pressed_jigsaw, a)
# # #             draw_modern_button(self.screen, self.btn_admin, "PIN", self.font_dock,
# # #                                _draw_icon_key, ACCENT_ADMIN, over_admin, pressed_admin, a)
# # #
# # #     def _lock_handle_event(self, ev):
# # #         if ev.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
# # #             pos = event_pos(ev, self.W, self.H)
# # #             if pos:
# # #                 x, y = pos
# # #                 lx, ly = self.last_mouse_pos
# # #                 if abs(x - lx) + abs(y - ly) >= LOCK_UI_MOUSE_MOVE_THRESH:
# # #                     self._touch_lock_ui()
# # #                 self.last_mouse_pos = (x, y)
# # #
# # #         if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
# # #             self._touch_lock_ui()
# # #             pos = event_pos(ev, self.W, self.H)
# # #             if not pos:
# # #                 return
# # #             x, y = pos
# # #
# # #             if self.ui_alpha >= 40:
# # #                 if self.btn_unlock.collidepoint((x, y)):
# # #                     self.lock_pressed = "unlock"
# # #                     play(self.snd_pick)
# # #                 elif self.btn_jigsaw.collidepoint((x, y)):
# # #                     self.lock_pressed = "jigsaw"
# # #                     play(self.snd_pick)
# # #                 elif self.btn_admin.collidepoint((x, y)):
# # #                     self.lock_pressed = "admin"
# # #                     play(self.snd_pick)
# # #                 else:
# # #                     self.lock_pressed = None
# # #
# # #         if ev.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
# # #             pos = event_pos(ev, self.W, self.H)
# # #             if not pos:
# # #                 self.lock_pressed = None
# # #                 return
# # #             x, y = pos
# # #
# # #             pressed = self.lock_pressed
# # #             self.lock_pressed = None
# # #             if pressed is None:
# # #                 return
# # #
# # #             if pressed == "unlock" and self.btn_unlock.collidepoint((x, y)):
# # #                 self._square_setup()
# # #                 self.state = self.STATE_SQUARE
# # #                 return
# # #
# # #             if pressed == "jigsaw" and self.btn_jigsaw.collidepoint((x, y)):
# # #                 self.state = self.STATE_JIG_SELECT
# # #                 return
# # #
# # #             if pressed == "admin" and self.btn_admin.collidepoint((x, y)):
# # #                 bg = self.screen.copy()
# # #                 ok = pin_overlay_loop(self.screen, self.clock, self.W, self.H, bg, self.font, self.font_small, self.snd_error)
# # #                 if ok:
# # #                     bg2 = self.screen.copy()
# # #                     unlock_success_overlay(self.screen, self.clock, self.W, self.H, self.font_brand, self.font_small,
# # #                                           self.snd_snap, bg_frame_surf=bg2)
# # #                     fade_to_black(self.screen, self.clock, 0.18)
# # #                     self._result_unlocked = True
# # #                     self._running = False
# # #                 return
# # #
# # #         if ev.type == pygame.KEYDOWN:
# # #             self._touch_lock_ui()
# # #             if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
# # #                 self._square_setup()
# # #                 self.state = self.STATE_SQUARE
# # #                 return
# # #             if ev.key == pygame.K_j:
# # #                 self.state = self.STATE_JIG_SELECT
# # #                 return
# # #
# # #     def run(self) -> bool:
# # #         # If no images exist, still allow lock UI to operate (plain black)
# # #         if not self.playlist:
# # #             self.lock_trans = self.LOCK_TRANS_NONE
# # #
# # #         selected_jig = 1
# # #         prev_time = time.time()
# # #
# # #         while self._running:
# # #             now = time.time()
# # #             dt = now - prev_time
# # #             prev_time = now
# # #
# # #             if self.state == self.STATE_LOCK:
# # #                 self._update_pan(dt)
# # #                 if self.lock_trans == self.LOCK_TRANS_NONE and LOCK_TRANSITION_ENABLE and self.playlist:
# # #                     if (now - self.lock_cycle_t0) >= LOCK_BG_CYCLE_S:
# # #                         self._begin_lock_transition()
# # #
# # #             for ev in pygame.event.get():
# # #                 if ev.type == pygame.QUIT:
# # #                     self._running = False
# # #                     break
# # #
# # #                 if self.state == self.STATE_LOCK:
# # #                     self._lock_handle_event(ev)
# # #
# # #                 elif self.state == self.STATE_SQUARE:
# # #                     self._square_handle_event(ev)
# # #
# # #                 elif self.state == self.STATE_JIG_SELECT:
# # #                     if ev.type == pygame.KEYDOWN:
# # #                         if ev.key == pygame.K_ESCAPE:
# # #                             self.state = self.STATE_LOCK
# # #                             continue
# # #                         if ev.key == pygame.K_UP:
# # #                             selected_jig = max(0, selected_jig - 1)
# # #                         if ev.key == pygame.K_DOWN:
# # #                             selected_jig = min(len(JIG_DIFFICULTY_CHOICES) - 1, selected_jig + 1)
# # #                         if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
# # #                             _, c, r = JIG_DIFFICULTY_CHOICES[selected_jig]
# # #                             self._jigsaw_setup(c, r)
# # #                             self.state = self.STATE_JIGSAW
# # #                             continue
# # #
# # #                     if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
# # #                         pos = event_pos(ev, self.W, self.H)
# # #                         if pos:
# # #                             x, y = pos
# # #                             if self.back_btn["rect"].collidepoint((x, y)):
# # #                                 self.state = self.STATE_LOCK
# # #                                 continue
# # #
# # #                             row_h = 70
# # #                             gap = 12
# # #                             start_y = 170
# # #                             for i in range(len(JIG_DIFFICULTY_CHOICES)):
# # #                                 rect = pygame.Rect(int(self.W * 0.18), start_y + i * (row_h + gap), int(self.W * 0.64), row_h)
# # #                                 if rect.collidepoint((x, y)):
# # #                                     selected_jig = i
# # #                                     _, c, r = JIG_DIFFICULTY_CHOICES[selected_jig]
# # #                                     self._jigsaw_setup(c, r)
# # #                                     self.state = self.STATE_JIGSAW
# # #                                     break
# # #
# # #                 elif self.state == self.STATE_JIGSAW:
# # #                     self._jigsaw_handle_event(ev)
# # #
# # #             if self.state == self.STATE_SQUARE:
# # #                 self._square_update_stage()
# # #             if self.state == self.STATE_JIGSAW:
# # #                 self._jigsaw_update_stage()
# # #
# # #             if self.state == self.STATE_LOCK:
# # #                 self._draw_lock()
# # #             elif self.state == self.STATE_SQUARE:
# # #                 self._square_draw()
# # #             elif self.state == self.STATE_JIG_SELECT:
# # #                 # simple select screen
# # #                 self.screen.fill(COLOR_BG)
# # #                 title = self.font_brand.render("Jigsaw Unlock", True, (255, 255, 255))
# # #                 self.screen.blit(title, (self.W // 2 - title.get_width() // 2, 60))
# # #                 sub = self.font_small.render("Select difficulty", True, (220, 220, 220))
# # #                 self.screen.blit(sub, (self.W // 2 - sub.get_width() // 2, 120))
# # #
# # #                 mx, my = pygame.mouse.get_pos()
# # #                 draw_button(self.screen, self.back_btn, self.font_small, self.font_small,
# # #                             active=self.back_btn["rect"].collidepoint((mx, my)), small=True)
# # #
# # #                 row_h = 70
# # #                 gap = 12
# # #                 start_y = 170
# # #                 for i, (name, c, r) in enumerate(JIG_DIFFICULTY_CHOICES):
# # #                     rect = pygame.Rect(int(self.W * 0.18), start_y + i * (row_h + gap), int(self.W * 0.64), row_h)
# # #                     active = rect.collidepoint((mx, my))
# # #                     bg = (40, 40, 40) if (i == selected_jig) else (22, 22, 22)
# # #                     if active:
# # #                         bg = lighten(bg, 10)
# # #                     pygame.draw.rect(self.screen, bg, rect, border_radius=16)
# # #                     pygame.draw.rect(self.screen, (140, 140, 140), rect, 2, border_radius=16)
# # #
# # #                     label = self.font.render(f"{name}", True, (240, 240, 240))
# # #                     dims = self.font_small.render(f"{c} x {r}", True, (210, 210, 210))
# # #                     self.screen.blit(label, (rect.x + 22, rect.centery - label.get_height() // 2))
# # #                     self.screen.blit(dims, (rect.right - dims.get_width() - 22, rect.centery - dims.get_height() // 2))
# # #
# # #             elif self.state == self.STATE_JIGSAW:
# # #                 self._jigsaw_draw()
# # #
# # #             pygame.display.flip()
# # #             self.clock.tick(60)
# # #
# # #         return bool(self._result_unlocked)
# # #
# # #
# # # # ============================================================
# # # # Public entrypoint for kiosk_shell shared-window use
# # # # ============================================================
# # # def run_lock_shared(screen: pygame.Surface, clock: Optional[pygame.time.Clock] = None) -> bool:
# # #     """
# # #     Runs the lock UI on an existing fullscreen pygame display (no new window).
# # #     Returns True if unlocked.
# # #     """
# # #     app = LockApp(screen=screen, clock=clock)
# # #     return app.run()
# # #
# # #
# # # # Backward compatible alias (so your kiosk_shell call reads cleanly)
# # # def run_lock_shared(screen: pygame.Surface, clock: Optional[pygame.time.Clock] = None) -> bool:
# # #     app = LockApp(screen=screen, clock=clock)
# # #     return app.run()
# # #
# # #
# # # # Standalone execution (creates its own window)
# # # if __name__ == "__main__":
# # #     app = LockApp(screen=None, clock=None)
# # #     ok = app.run()
# # #     # In standalone mode, return codes are meaningful; in shared mode, caller handles it.
# # #     sys.exit(0 if ok else 1)
# # #!/usr/bin/env python3
# # # -*- coding: utf-8 -*-
# #
# # import os
# # import sys
# # import time
# # import math
# # import random
# # import datetime
# # from typing import Optional, Tuple, List, Dict, Any
# #
# # # Must be set before importing pygame
# # os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
# # os.environ.setdefault("SDL_VIDEODRIVER", "x11")
# # os.environ.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")
# # os.environ.setdefault("SDL_VIDEO_WINDOW_POS", "0,0")
# # os.environ.setdefault("SDL_VIDEO_CENTERED", "0")
# #
# # import pygame  # noqa: E402
# #
# #
# # # ============================================================
# # # Return codes (match your historical contract)
# # # ============================================================
# # RC_RELOCK   = 0
# # RC_PI_MODE  = 42
# # RC_SOLARIS  = 43
# # RC_SHUTDOWN = 44
# # RC_REBOOT   = 45
# #
# #
# # # ---------------- CONFIG ----------------
# # GRID_X = 3
# # GRID_Y = 4
# #
# # SNAP_DIST = 190
# #
# # BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# # IMAGE_DIR = os.path.join(BASE_DIR, "images")
# # SOUNDS_DIR = os.path.join(BASE_DIR, "sounds")
# #
# # BRAND_TEXT = "Glover SPARCstation"
# # BRAND_SUB = "Puzzle Lock"
# #
# # # If cfg is passed, this will be overridden
# # ADMIN_PIN_DEFAULT = "1193"
# # PIN_MAX_LEN = 12
# #
# # SHOW_STATUS_BAR = True
# # STATUS_BAR_H = 40
# #
# # LOCK_UI_START_HIDDEN = True
# # LOCK_UI_AUTOHIDE_S = 6.0
# # LOCK_UI_MOUSE_MOVE_THRESH = 10
# # LOCK_UI_FADE_S = 0.18
# #
# # LOCK_BG_CYCLE_S = 18.0
# # LOCK_VISIBLE_SCALE_MODE = "contain"
# #
# # LOCK_BG_PAN_RANGE_PX = 900
# # LOCK_BG_PAN_SPEED_PX_S = 90.0
# #
# # LOCK_BG_BLUR_METHOD = "hq"
# # LOCK_BG_HQ_DOWNSCALE = 2
# # LOCK_BG_HQ_RADIUS = 10
# #
# # LOCK_BG_BLUR_DOWNSCALE = 12
# # LOCK_BG_DIM_ALPHA = 60
# #
# # LOCK_TRANSITION_ENABLE = True
# # LOCK_FADEIN_S = 0.55
# #
# # LOCK_TRANSITION_STYLES = ["shatter", "blinds", "explode", "drop"]
# # LOCK_TRANSITION_STYLE = "random"
# # LOCK_BREAK_DURATIONS = {
# #     "shatter": 0.85,
# #     "blinds":  0.95,
# #     "explode": 0.80,
# #     "drop":    0.90,
# # }
# #
# # LOCK_SHATTER_TILE_TARGET = 180
# # LOCK_SHATTER_GRAVITY = 1200.0
# #
# # LOCK_BG_RANDOM_START = True
# # LOCK_BG_SHUFFLE = False
# #
# # COLOR_BG = (0, 0, 0)
# # COLOR_TRAY = (18, 18, 18)
# # COLOR_LINE = (70, 70, 70)
# #
# # ACCENT_UNLOCK = (70, 185, 120)
# # ACCENT_JIGSAW = (170, 170, 170)
# # ACCENT_ADMIN = (120, 200, 255)
# #
# # SND_PICK = "pick.wav"
# # SND_DROP = "drop.wav"
# # SND_SNAP = "snap.wav"
# # SND_ERROR = "error.wav"
# #
# # TRAY_H_FRAC = 0.28
# # TRAY_MARGIN = 14
# #
# # # We remove the "reference image intro overlay" by making intro durations zero-ish,
# # # but we also remove the drawing overlay entirely below.
# # PUZ_INTRO_HOLD_S = 0.0
# # PUZ_FALL_S = 0.75
# # UNLOCK_SUCCESS_S = 0.85
# #
# # JIG_KNOB_FRAC = 0.22
# # JIG_EDGE_OFF_FRAC = 0.18
# #
# # JIG_SNAP_FRAC = 0.55
# # JIG_SNAP_MIN = 40
# # JIG_SNAP_MAX = 140
# #
# # JIG_INTRO_HOLD_S = 0.0
# # JIG_FALL_S = 0.75
# # JIG_SOLVED_HOLD_S = 0.85
# #
# # JIG_DIFFICULTY_CHOICES = [
# #     ("Easy",    3, 2),
# #     ("Normal",  4, 3),
# #     ("Hard",    5, 4),
# #     ("Expert",  6, 4),
# #     ("Insane", 10, 5),
# #     ("Extreme", 12, 5),
# # ]
# #
# # PUZZLE_BOARD_SCALE_MODE = "cover"
# #
# #
# # # ---------------- helpers ----------------
# # def clamp255(v: float) -> int:
# #     return max(0, min(255, int(v)))
# #
# #
# # def lighten(color, amt=22):
# #     return (clamp255(color[0] + amt), clamp255(color[1] + amt), clamp255(color[2] + amt))
# #
# #
# # def _ease_in_quad(t: float) -> float:
# #     return t * t
# #
# #
# # def _ease_out_cubic(t: float) -> float:
# #     u = 1.0 - t
# #     return 1.0 - (u * u * u)
# #
# #
# # def dist2(a, b) -> float:
# #     dx = a[0] - b[0]
# #     dy = a[1] - b[1]
# #     return dx * dx + dy * dy
# #
# #
# # def load_sound(name: str):
# #     path = os.path.join(SOUNDS_DIR, name)
# #     if os.path.exists(path):
# #         try:
# #             return pygame.mixer.Sound(path)
# #         except Exception:
# #             return None
# #     return None
# #
# #
# # def play(snd):
# #     if snd:
# #         try:
# #             snd.play()
# #         except Exception:
# #             pass
# #
# #
# # def event_pos(ev, W: int, H: int):
# #     if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
# #         return ev.pos
# #     if ev.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
# #         return (int(ev.x * W), int(ev.y * H))
# #     return None
# #
# #
# # def safe_load_image(path: str) -> pygame.Surface:
# #     try:
# #         from PIL import Image, ImageOps  # type: ignore
# #         img = Image.open(path)
# #         img = ImageOps.exif_transpose(img)
# #         if img.mode in ("RGBA", "LA") or ("transparency" in img.info):
# #             img = img.convert("RGBA")
# #             surf = pygame.image.frombuffer(img.tobytes(), img.size, "RGBA").convert_alpha()
# #         else:
# #             img = img.convert("RGB")
# #             surf = pygame.image.frombuffer(img.tobytes(), img.size, "RGB").convert()
# #         return surf
# #     except Exception:
# #         surf = pygame.image.load(path)
# #         try:
# #             return surf.convert_alpha() if surf.get_alpha() is not None else surf.convert()
# #         except Exception:
# #             return surf
# #
# #
# # def scale_cover(src_surf: pygame.Surface, target_w: int, target_h: int) -> pygame.Surface:
# #     sw, sh = src_surf.get_size()
# #     scale = max(target_w / sw, target_h / sh)
# #     nw = max(1, int(sw * scale))
# #     nh = max(1, int(sh * scale))
# #     scaled = pygame.transform.smoothscale(src_surf, (nw, nh))
# #     x = (nw - target_w) // 2
# #     y = (nh - target_h) // 2
# #     return scaled.subsurface(pygame.Rect(x, y, target_w, target_h)).copy()
# #
# #
# # def scale_contain(src_surf: pygame.Surface, target_w: int, target_h: int):
# #     sw, sh = src_surf.get_size()
# #     scale = min(target_w / sw, target_h / sh)
# #     nw = max(1, int(sw * scale))
# #     nh = max(1, int(sh * scale))
# #     scaled = pygame.transform.smoothscale(src_surf, (nw, nh))
# #     rect = scaled.get_rect(center=(target_w // 2, target_h // 2))
# #     return scaled, rect
# #
# #
# # def blur_surface_once(src: pygame.Surface, downscale: int = 12) -> pygame.Surface:
# #     downscale = max(2, int(downscale))
# #     w, h = src.get_size()
# #     dw = max(2, w // downscale)
# #     dh = max(2, h // downscale)
# #     small = pygame.transform.smoothscale(src, (dw, dh))
# #     return pygame.transform.smoothscale(small, (w, h))
# #
# #
# # def blur_surface_hq(src: pygame.Surface, radius: int = 10, downscale: int = 2) -> pygame.Surface:
# #     try:
# #         from PIL import Image, ImageFilter  # type: ignore
# #         w, h = src.get_size()
# #         ds = max(1, int(downscale))
# #         if ds > 1:
# #             sw = max(2, w // ds)
# #             sh = max(2, h // ds)
# #             src_small = pygame.transform.smoothscale(src, (sw, sh))
# #             raw = pygame.image.tostring(src_small, "RGB")
# #             im = Image.frombytes("RGB", (sw, sh), raw)
# #         else:
# #             raw = pygame.image.tostring(src, "RGB")
# #             im = Image.frombytes("RGB", (w, h), raw)
# #
# #         im = im.filter(ImageFilter.GaussianBlur(radius=max(0, int(radius))))
# #         if ds > 1:
# #             im = im.resize((w, h), resample=Image.LANCZOS)
# #
# #         out = pygame.image.frombuffer(im.tobytes(), (w, h), "RGB").convert()
# #         return out
# #     except Exception:
# #         return blur_surface_once(src, LOCK_BG_BLUR_DOWNSCALE)
# #
# #
# # def _draw_round_rect_alpha(dst, rect: pygame.Rect, rgb, alpha: int, radius: int):
# #     a = clamp255(alpha)
# #     s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
# #     pygame.draw.rect(s, (rgb[0], rgb[1], rgb[2], a), pygame.Rect(0, 0, rect.w, rect.h), border_radius=radius)
# #     dst.blit(s, rect.topleft)
# #
# #
# # def _draw_round_rect_outline_alpha(dst, rect: pygame.Rect, rgb, alpha: int, radius: int, width: int = 2):
# #     a = clamp255(alpha)
# #     s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
# #     pygame.draw.rect(s, (rgb[0], rgb[1], rgb[2], a), pygame.Rect(0, 0, rect.w, rect.h), width, border_radius=radius)
# #     dst.blit(s, rect.topleft)
# #
# #
# # def _draw_icon_lock(dst, center, color, alpha=255):
# #     cx, cy = center
# #     a = clamp255(alpha)
# #     col = (color[0], color[1], color[2], a)
# #     s = pygame.Surface((40, 40), pygame.SRCALPHA)
# #     pygame.draw.arc(s, col, pygame.Rect(10, 6, 20, 18), math.pi, 0, 3)
# #     pygame.draw.rect(s, col, pygame.Rect(10, 18, 20, 16), border_radius=5)
# #     dst.blit(s, (cx - 20, cy - 20))
# #
# #
# # def _draw_icon_jigsaw(dst, center, color, alpha=255):
# #     cx, cy = center
# #     a = clamp255(alpha)
# #     col = (color[0], color[1], color[2], a)
# #     s = pygame.Surface((40, 40), pygame.SRCALPHA)
# #     pygame.draw.rect(s, col, pygame.Rect(10, 10, 18, 14), 2, border_radius=3)
# #     pygame.draw.rect(s, col, pygame.Rect(14, 14, 18, 14), 2, border_radius=3)
# #     pygame.draw.line(s, col, (16, 24), (22, 18), 2)
# #     pygame.draw.line(s, col, (22, 18), (30, 26), 2)
# #     dst.blit(s, (cx - 20, cy - 20))
# #
# #
# # def _draw_icon_key(dst, center, color, alpha=255):
# #     cx, cy = center
# #     a = clamp255(alpha)
# #     col = (color[0], color[1], color[2], a)
# #     s = pygame.Surface((40, 40), pygame.SRCALPHA)
# #     pygame.draw.circle(s, col, (14, 20), 6, 2)
# #     pygame.draw.line(s, col, (20, 20), (34, 20), 2)
# #     pygame.draw.line(s, col, (28, 20), (28, 26), 2)
# #     pygame.draw.line(s, col, (32, 20), (32, 24), 2)
# #     dst.blit(s, (cx - 20, cy - 20))
# #
# #
# # def draw_modern_dock(dst, dock_rect: pygame.Rect, alpha: int):
# #     _draw_round_rect_alpha(dst, dock_rect, (0, 0, 0), int(150 * (alpha / 255.0)), radius=22)
# #     _draw_round_rect_outline_alpha(dst, dock_rect, (255, 255, 255), int(90 * (alpha / 255.0)), radius=22, width=2)
# #
# #
# # def draw_modern_button(dst, rect: pygame.Rect, label: str, font, icon_fn, accent_rgb,
# #                        active: bool, pressed: bool, alpha: int):
# #     a = clamp255(alpha)
# #     shadow_off = 3 if not pressed else 1
# #     _draw_round_rect_alpha(dst, rect.move(0, shadow_off), (0, 0, 0), int(90 * (a / 255.0)), radius=16)
# #
# #     base = (18, 18, 18)
# #     if active:
# #         base = (26, 26, 26)
# #     if pressed:
# #         base = (12, 12, 12)
# #
# #     _draw_round_rect_alpha(dst, rect, base, int(210 * (a / 255.0)), radius=16)
# #
# #     strip = pygame.Rect(rect.x + 12, rect.y + rect.h - 10, rect.w - 24, 4)
# #     _draw_round_rect_alpha(dst, strip, accent_rgb, int(200 * (a / 255.0)), radius=4)
# #
# #     _draw_round_rect_outline_alpha(dst, rect, (255, 255, 255), int(95 * (a / 255.0)), radius=16, width=2)
# #
# #     icon_center = (rect.x + 26, rect.centery)
# #     icon_fn(dst, icon_center, accent_rgb, alpha=a)
# #
# #     txt = font.render(label, True, (240, 240, 240))
# #     txt.set_alpha(a)
# #     dst.blit(txt, (rect.x + 52, rect.centery - txt.get_height() // 2))
# #
# #
# # def make_button(rect: pygame.Rect, label: str, color=(90, 90, 90)):
# #     return {"rect": rect, "label": label, "color": color}
# #
# #
# # def draw_button(screen, btn, font_main, font_small, active=False, small=False):
# #     r = btn["rect"]
# #     base = btn.get("color", (90, 90, 90))
# #     bg = base if not active else lighten(base, 28)
# #
# #     pygame.draw.rect(screen, bg, r, border_radius=16)
# #     pygame.draw.rect(screen, (230, 230, 230), r, 2, border_radius=16)
# #
# #     f = font_small if small else font_main
# #     t = f.render(btn["label"], True, (255, 255, 255))
# #     screen.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))
# #
# #
# # def fade_to_black(screen, clock, dur_s: float = 0.18):
# #     t0 = time.time()
# #     w, h = screen.get_size()
# #     while True:
# #         now = time.time()
# #         t = (now - t0) / max(0.001, dur_s)
# #         if t >= 1.0:
# #             break
# #         a = int(255 * t)
# #         ov = pygame.Surface((w, h), pygame.SRCALPHA)
# #         ov.fill((0, 0, 0, a))
# #         screen.blit(ov, (0, 0))
# #         pygame.display.flip()
# #         clock.tick(60)
# #     screen.fill((0, 0, 0))
# #     pygame.display.flip()
# #
# #
# # def unlock_success_overlay(screen, clock, W, H, font_brand, font_small, snd_snap,
# #                           msg="UNLOCKED", sub="Returning to menu...", hold_s=UNLOCK_SUCCESS_S,
# #                           bg_frame_surf: Optional[pygame.Surface] = None):
# #     play(snd_snap)
# #     t0 = time.time()
# #     while time.time() - t0 < hold_s:
# #         for ev in pygame.event.get():
# #             if ev.type == pygame.QUIT:
# #                 raise SystemExit
# #
# #         if bg_frame_surf is not None:
# #             screen.blit(bg_frame_surf, (0, 0))
# #         else:
# #             screen.fill(COLOR_BG)
# #
# #         overlay = pygame.Surface((W, H), pygame.SRCALPHA)
# #         overlay.fill((0, 0, 0, 180))
# #         screen.blit(overlay, (0, 0))
# #
# #         m = font_brand.render(msg, True, (255, 255, 255))
# #         s = font_small.render(sub, True, (230, 230, 230))
# #         screen.blit(m, (W // 2 - m.get_width() // 2, H // 2 - 40))
# #         screen.blit(s, (W // 2 - s.get_width() // 2, H // 2 + 20))
# #         pygame.display.flip()
# #         clock.tick(60)
# #
# #
# # def pin_overlay_loop(screen, clock, W, H, bg_frame_surf, font, font_small, snd_error, admin_pin: str) -> bool:
# #     pin_input = ""
# #     pin_error = ""
# #     pin_error_t0 = 0.0
# #
# #     cancel_btn = make_button(pygame.Rect(16, 16, 170, 48), "CANCEL", color=(120, 120, 120))
# #
# #     KEYPAD_COLS = 3
# #     KEYPAD_ROWS = 4
# #     KEYS = ["1", "2", "3",
# #             "4", "5", "6",
# #             "7", "8", "9",
# #             "C", "0", "OK"]
# #
# #     def submit() -> bool:
# #         nonlocal pin_input, pin_error, pin_error_t0
# #         if pin_input == admin_pin:
# #             return True
# #         pin_error = "Incorrect PIN"
# #         pin_error_t0 = time.time()
# #         pin_input = ""
# #         play(snd_error)
# #         return False
# #
# #     while True:
# #         for ev in pygame.event.get():
# #             if ev.type == pygame.QUIT:
# #                 raise SystemExit
# #
# #             if ev.type == pygame.KEYDOWN:
# #                 if ev.key == pygame.K_ESCAPE:
# #                     return False
# #                 if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
# #                     if submit():
# #                         return True
# #                 elif ev.key == pygame.K_BACKSPACE:
# #                     pin_input = pin_input[:-1]
# #                 else:
# #                     if ev.unicode.isdigit() and len(pin_input) < PIN_MAX_LEN:
# #                         pin_input += ev.unicode
# #
# #             if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
# #                 pos = event_pos(ev, W, H)
# #                 if not pos:
# #                     continue
# #
# #                 if cancel_btn["rect"].collidepoint(pos):
# #                     return False
# #
# #                 pad_w = min(520, int(W * 0.42))
# #                 pad_h = min(520, int(H * 0.62))
# #                 pad_x = (W - pad_w) // 2
# #                 pad_y = (H - pad_h) // 2 + 40
# #                 cell_w = pad_w // KEYPAD_COLS
# #                 cell_h = pad_h // KEYPAD_ROWS
# #
# #                 idx = 0
# #                 for r in range(KEYPAD_ROWS):
# #                     for c in range(KEYPAD_COLS):
# #                         x = pad_x + c * cell_w + 8
# #                         y = pad_y + r * cell_h + 8
# #                         rect = pygame.Rect(x, y, cell_w - 16, cell_h - 16)
# #                         if rect.collidepoint(pos):
# #                             key = KEYS[idx]
# #                             if key == "C":
# #                                 pin_input = ""
# #                             elif key == "OK":
# #                                 if submit():
# #                                     return True
# #                             else:
# #                                 if len(pin_input) < PIN_MAX_LEN:
# #                                     pin_input += key
# #                             break
# #                         idx += 1
# #
# #         screen.blit(bg_frame_surf, (0, 0))
# #         overlay = pygame.Surface((W, H), pygame.SRCALPHA)
# #         overlay.fill((0, 0, 0, 205))
# #         screen.blit(overlay, (0, 0))
# #
# #         mx, my = pygame.mouse.get_pos()
# #         draw_button(screen, cancel_btn, font, font_small, active=cancel_btn["rect"].collidepoint((mx, my)), small=True)
# #
# #         title = font.render("PIN UNLOCK", True, (255, 255, 255))
# #         prompt = font_small.render("Enter PIN (keyboard or touchscreen keypad):", True, (230, 230, 230))
# #         masked = "*" * len(pin_input)
# #         entry = font.render(masked, True, (255, 255, 0))
# #
# #         screen.blit(title, (W // 2 - title.get_width() // 2, 80))
# #         screen.blit(prompt, (W // 2 - prompt.get_width() // 2, 130))
# #         screen.blit(entry, (W // 2 - entry.get_width() // 2, 165))
# #
# #         pad_w = min(520, int(W * 0.42))
# #         pad_h = min(520, int(H * 0.62))
# #         pad_x = (W - pad_w) // 2
# #         pad_y = (H - pad_h) // 2 + 40
# #         cell_w = pad_w // KEYPAD_COLS
# #         cell_h = pad_h // KEYPAD_ROWS
# #
# #         pygame.draw.rect(screen, (35, 35, 35), pygame.Rect(pad_x, pad_y, pad_w, pad_h), border_radius=12)
# #
# #         rects = []
# #         for r in range(KEYPAD_ROWS):
# #             for c in range(KEYPAD_COLS):
# #                 x = pad_x + c * cell_w + 8
# #                 y = pad_y + r * cell_h + 8
# #                 rects.append(pygame.Rect(x, y, cell_w - 16, cell_h - 16))
# #
# #         for i, r in enumerate(rects):
# #             pygame.draw.rect(screen, (70, 70, 70), r, border_radius=10)
# #             label = font.render(KEYS[i], True, (255, 255, 255))
# #             screen.blit(label, (r.centerx - label.get_width() // 2, r.centery - label.get_height() // 2))
# #
# #         if pin_error and (time.time() - pin_error_t0) < 2.0:
# #             err = font_small.render(pin_error, True, (255, 90, 90))
# #             screen.blit(err, (W // 2 - err.get_width() // 2, pad_y + pad_h + 18))
# #
# #         tip = font_small.render("Enter/OK=submit, Backspace=delete, Esc/CANCEL=back.", True, (230, 230, 230))
# #         screen.blit(tip, (W // 2 - tip.get_width() // 2, pad_y + pad_h + 50))
# #
# #         pygame.display.flip()
# #         clock.tick(60)
# #
# #
# # def calc_jig_snap_dist(W: int, BOARD_H: int, cols: int, rows: int) -> int:
# #     cols = max(1, int(cols))
# #     rows = max(1, int(rows))
# #     cell_w = W // cols
# #     cell_h = BOARD_H // rows
# #     base = int(min(cell_w, cell_h) * JIG_SNAP_FRAC)
# #     return max(JIG_SNAP_MIN, min(JIG_SNAP_MAX, base))
# #
# #
# # def _make_jigsaw_edges(cols, rows):
# #     h_edges = [
# #         [{"dir": random.choice([-1, 1]), "off": random.uniform(-JIG_EDGE_OFF_FRAC, JIG_EDGE_OFF_FRAC)}
# #          for _ in range(cols)]
# #         for _ in range(rows - 1)
# #     ]
# #     v_edges = [
# #         [{"dir": random.choice([-1, 1]), "off": random.uniform(-JIG_EDGE_OFF_FRAC, JIG_EDGE_OFF_FRAC)}
# #          for _ in range(cols - 1)]
# #         for _ in range(rows)
# #     ]
# #     return h_edges, v_edges
# #
# #
# # def _apply_edge_circle(mask_surf, kind, center, radius):
# #     if kind == 0:
# #         return
# #     if kind > 0:
# #         pygame.draw.circle(mask_surf, (255, 255, 255, 255), center, radius)
# #     else:
# #         pygame.draw.circle(mask_surf, (255, 255, 255, 0), center, radius)
# #
# #
# # def build_jigsaw_pieces(W, BOARD_H, board_surf, cols, rows):
# #     cell_w = W // cols
# #     cell_h = BOARD_H // rows
# #
# #     knob_r = int(min(cell_w, cell_h) * JIG_KNOB_FRAC)
# #     margin = knob_r + 3
# #
# #     h_edges, v_edges = _make_jigsaw_edges(cols, rows)
# #
# #     pieces = []
# #     for y in range(rows):
# #         for x in range(cols):
# #             if y == 0:
# #                 top_kind, top_off = 0, 0.0
# #             else:
# #                 top_kind = -h_edges[y - 1][x]["dir"]
# #                 top_off = h_edges[y - 1][x]["off"]
# #
# #             if y == rows - 1:
# #                 bot_kind, bot_off = 0, 0.0
# #             else:
# #                 bot_kind = h_edges[y][x]["dir"]
# #                 bot_off = h_edges[y][x]["off"]
# #
# #             if x == 0:
# #                 left_kind, left_off = 0, 0.0
# #             else:
# #                 left_kind = -v_edges[y][x - 1]["dir"]
# #                 left_off = v_edges[y][x - 1]["off"]
# #
# #             if x == cols - 1:
# #                 right_kind, right_off = 0, 0.0
# #             else:
# #                 right_kind = v_edges[y][x]["dir"]
# #                 right_off = v_edges[y][x]["off"]
# #
# #             pw = cell_w + 2 * margin
# #             ph = cell_h + 2 * margin
# #
# #             mask_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
# #             mask_surf.fill((255, 255, 255, 0))
# #             pygame.draw.rect(mask_surf, (255, 255, 255, 255), pygame.Rect(margin, margin, cell_w, cell_h))
# #
# #             cx_top = margin + (cell_w // 2) + int(top_off * cell_w)
# #             cy_top = margin
# #             _apply_edge_circle(mask_surf, top_kind, (cx_top, cy_top), knob_r)
# #
# #             cx_bot = margin + (cell_w // 2) + int(bot_off * cell_w)
# #             cy_bot = margin + cell_h
# #             _apply_edge_circle(mask_surf, bot_kind, (cx_bot, cy_bot), knob_r)
# #
# #             cx_left = margin
# #             cy_left = margin + (cell_h // 2) + int(left_off * cell_h)
# #             _apply_edge_circle(mask_surf, left_kind, (cx_left, cy_left), knob_r)
# #
# #             cx_right = margin + cell_w
# #             cy_right = margin + (cell_h // 2) + int(right_off * cell_h)
# #             _apply_edge_circle(mask_surf, right_kind, (cx_right, cy_right), knob_r)
# #
# #             piece_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
# #             piece_surf.blit(board_surf, (margin - x * cell_w, margin - y * cell_h))
# #             piece_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
# #
# #             piece_mask = pygame.mask.from_surface(mask_surf)
# #             correct_pos = (x * cell_w - margin, y * cell_h - margin)
# #
# #             pieces.append({
# #                 "surf": piece_surf,
# #                 "mask": piece_mask,
# #                 "correct_pos": correct_pos,
# #                 "pos": [float(correct_pos[0]), float(correct_pos[1])],
# #                 "locked": False,
# #                 "fall_from": [float(correct_pos[0]), float(correct_pos[1])],
# #                 "fall_to": [float(correct_pos[0]), float(correct_pos[1])],
# #             })
# #
# #     return pieces
# #
# #
# # def tray_random_pos_sized(W, tray_rect, obj_w, obj_h):
# #     x0 = TRAY_MARGIN
# #     x1 = W - TRAY_MARGIN - obj_w
# #     y0 = tray_rect.top + TRAY_MARGIN
# #     y1 = tray_rect.bottom - TRAY_MARGIN - obj_h
# #     if x1 < x0:
# #         x1 = x0
# #     if y1 < y0:
# #         y1 = y0
# #     return (random.randint(x0, x1), random.randint(y0, y1))
# #
# #
# # def jigsaw_all_locked(pieces):
# #     return all(p.get("locked") for p in pieces)
# #
# #
# # # ============================================================
# # # Post-unlock menu (restores "other selections")
# # # ============================================================
# # def post_unlock_menu(screen: pygame.Surface, clock: pygame.time.Clock, cfg: Dict[str, Any]) -> int:
# #     W, H = screen.get_size()
# #     font = pygame.font.SysFont(None, 54)
# #     font_small = pygame.font.SysFont(None, 26)
# #
# #     idle_s = int(cfg.get("idle", {}).get("menu_seconds", 120))
# #     flags = cfg.get("feature_flags", {}) or {}
# #
# #     # Allow exact override from config if you want it identical to your old menu
# #     custom = (cfg.get("ui", {}) or {}).get("post_unlock_menu")
# #     if isinstance(custom, list) and custom:
# #         raw_items = []
# #         for it in custom:
# #             if isinstance(it, dict) and "label" in it and "action" in it:
# #                 raw_items.append((str(it["label"]), str(it["action"])))
# #     else:
# #         raw_items = []
# #         if bool(flags.get("enable_solaris", True)):
# #             raw_items.append(("Solaris", "solaris"))
# #         if bool(flags.get("enable_pi", True)):
# #             raw_items.append(("Pi Admin", "pi"))
# #         raw_items.append(("Re-lock", "relock"))
# #         if bool(flags.get("enable_power", True)):
# #             raw_items.append(("Shutdown", "shutdown"))
# #         if bool(flags.get("enable_reboot", True)):
# #             raw_items.append(("Reboot", "reboot"))
# #
# #     # Map action -> rc
# #     action_to_rc = {
# #         "relock": RC_RELOCK,
# #         "pi": RC_PI_MODE,
# #         "pi_mode": RC_PI_MODE,
# #         "solaris": RC_SOLARIS,
# #         "shutdown": RC_SHUTDOWN,
# #         "poweroff": RC_SHUTDOWN,
# #         "reboot": RC_REBOOT,
# #     }
# #
# #     items = [(lbl, action_to_rc.get(act, RC_RELOCK)) for (lbl, act) in raw_items]
# #     if not items:
# #         items = [("Re-lock", RC_RELOCK)]
# #
# #     sel = 0
# #     last_input = time.time()
# #
# #     btn_w = int(W * 0.70)
# #     btn_h = 90
# #     gap = 22
# #     start_y = 180
# #
# #     def hit(x: int, y: int) -> Optional[int]:
# #         for i in range(len(items)):
# #             rx = W // 2 - btn_w // 2
# #             ry = start_y + i * (btn_h + gap)
# #             rect = pygame.Rect(rx, ry, btn_w, btn_h)
# #             if rect.collidepoint(x, y):
# #                 return i
# #         return None
# #
# #     while True:
# #         if (time.time() - last_input) >= idle_s:
# #             return RC_RELOCK
# #
# #         for ev in pygame.event.get():
# #             if ev.type == pygame.QUIT:
# #                 return RC_RELOCK
# #
# #             if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.KEYDOWN,
# #                            pygame.FINGERDOWN, pygame.FINGERMOTION):
# #                 last_input = time.time()
# #
# #             if ev.type == pygame.KEYDOWN:
# #                 if ev.key in (pygame.K_ESCAPE, pygame.K_q):
# #                     return RC_RELOCK
# #                 if ev.key == pygame.K_UP:
# #                     sel = max(0, sel - 1)
# #                 elif ev.key == pygame.K_DOWN:
# #                     sel = min(len(items) - 1, sel + 1)
# #                 elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
# #                     return items[sel][1]
# #
# #             if ev.type == pygame.MOUSEBUTTONDOWN:
# #                 i = hit(ev.pos[0], ev.pos[1])
# #                 if i is not None:
# #                     return items[i][1]
# #
# #             if ev.type == pygame.FINGERDOWN:
# #                 x = int(ev.x * W)
# #                 y = int(ev.y * H)
# #                 i = hit(x, y)
# #                 if i is not None:
# #                     return items[i][1]
# #
# #         # draw
# #         screen.fill((0, 0, 0))
# #         title = font.render("Select Mode", True, (255, 255, 255))
# #         screen.blit(title, (W // 2 - title.get_width() // 2, 70))
# #
# #         mx, my = pygame.mouse.get_pos()
# #         for i, (label, _rc) in enumerate(items):
# #             rx = W // 2 - btn_w // 2
# #             ry = start_y + i * (btn_h + gap)
# #             rect = pygame.Rect(rx, ry, btn_w, btn_h)
# #
# #             active = rect.collidepoint((mx, my))
# #             is_sel = (i == sel)
# #
# #             bg = (55, 55, 55) if is_sel else (30, 30, 30)
# #             if active:
# #                 bg = lighten(bg, 18)
# #
# #             pygame.draw.rect(screen, bg, rect, border_radius=18)
# #             pygame.draw.rect(screen, (200, 200, 200) if is_sel else (120, 120, 120), rect, 2, border_radius=18)
# #
# #             txt = font.render(label, True, (240, 240, 240))
# #             screen.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))
# #
# #         hint = font_small.render("Up/Down + Enter, or tap. Esc re-locks.", True, (180, 180, 180))
# #         screen.blit(hint, (W // 2 - hint.get_width() // 2, H - 60))
# #
# #         pygame.display.flip()
# #         clock.tick(60)
# #
# #
# # # ---------------- LockApp ----------------
# # class LockApp:
# #     STATE_LOCK = "LOCK"
# #     STATE_SQUARE = "SQUARE"
# #     STATE_JIG_SELECT = "JIG_SELECT"
# #     STATE_JIGSAW = "JIGSAW"
# #
# #     PUZ_INTRO = "INTRO"
# #     PUZ_FALL = "FALL"
# #     PUZ_PLAY = "PLAY"
# #
# #     JIG_INTRO = "INTRO"
# #     JIG_FALL = "FALL"
# #     JIG_PLAY = "PLAY"
# #
# #     LOCK_TRANS_NONE = None
# #     LOCK_TRANS_BREAK = "BREAK"
# #     LOCK_TRANS_FADEIN = "FADEIN"
# #
# #     def __init__(self, screen: pygame.Surface, clock: pygame.time.Clock, cfg: Dict[str, Any]):
# #         self.cfg = cfg
# #         self.admin_pin = str((cfg.get("security", {}) or {}).get("pi_pin", ADMIN_PIN_DEFAULT))
# #
# #         self.screen = screen
# #         self.clock = clock
# #         self.W, self.H = self.screen.get_size()
# #
# #         # Mixer best-effort
# #         try:
# #             if not pygame.mixer.get_init():
# #                 pygame.mixer.init()
# #         except Exception:
# #             pass
# #
# #         self.font = pygame.font.SysFont(None, 52)
# #         self.font_small = pygame.font.SysFont(None, 26)
# #         self.font_brand = pygame.font.SysFont(None, 64)
# #         self.font_brand2 = pygame.font.SysFont(None, 28)
# #         self.font_dock = pygame.font.SysFont(None, 28)
# #
# #         self.snd_pick = load_sound(SND_PICK)
# #         self.snd_drop = load_sound(SND_DROP)
# #         self.snd_snap = load_sound(SND_SNAP)
# #         self.snd_error = load_sound(SND_ERROR)
# #
# #         self.TRAY_H = int(self.H * TRAY_H_FRAC)
# #         self.BOARD_H = self.H - self.TRAY_H
# #         self.tray_rect = pygame.Rect(0, self.BOARD_H, self.W, self.TRAY_H)
# #
# #         self.playlist = self._load_playlist()
# #         if LOCK_BG_SHUFFLE:
# #             random.shuffle(self.playlist)
# #         else:
# #             self.playlist.sort()
# #
# #         self.lock_idx = random.randrange(len(self.playlist)) if (LOCK_BG_RANDOM_START and self.playlist) else 0
# #
# #         self.lock_bg_big = None
# #         self.lock_fg = None
# #         self.lock_fg_rect = None
# #         self.board_surf = None
# #
# #         self.pan_x = 0.0
# #         self.pan_y = 0.0
# #         self.pan_vx = 0.0
# #         self.pan_vy = 0.0
# #
# #         self.lock_cycle_t0 = time.time()
# #         self.lock_trans = self.LOCK_TRANS_NONE
# #         self.lock_trans_t0 = 0.0
# #         self.break_style = "shatter"
# #         self.break_dur = float(LOCK_BREAK_DURATIONS.get("shatter", 0.85))
# #         self.lock_snapshot = pygame.Surface((self.W, self.H))
# #         self.break_pieces: List[Dict[str, Any]] = []
# #
# #         if self.playlist:
# #             self._set_image_by_index(self.lock_idx)
# #
# #         now = time.time()
# #         self.lock_ui_visible_until = (now + LOCK_UI_AUTOHIDE_S) if not LOCK_UI_START_HIDDEN else 0.0
# #         self.last_mouse_pos = pygame.mouse.get_pos()
# #         self.ui_alpha = 0.0 if LOCK_UI_START_HIDDEN else 255.0
# #
# #         self._layout_lock_dock()
# #         self.lock_pressed = None
# #         self.state = self.STATE_LOCK
# #
# #         # Square puzzle
# #         self.tiles: List[Dict[str, Any]] = []
# #         self.tile_w = 0
# #         self.tile_h = 0
# #         self.slot_positions: List[Tuple[int, int]] = []
# #         self.drag_tile: Optional[Dict[str, Any]] = None
# #         self.drag_ox = 0
# #         self.drag_oy = 0
# #         self.puz_stage = self.PUZ_PLAY  # no reference-image intro overlay
# #         self.puz_t0 = 0.0
# #
# #         # Jigsaw
# #         self.jig_cols, self.jig_rows = JIG_DIFFICULTY_CHOICES[1][1], JIG_DIFFICULTY_CHOICES[1][2]
# #         self.jig_snap_dist = calc_jig_snap_dist(self.W, self.BOARD_H, self.jig_cols, self.jig_rows)
# #         self.jig_pieces: List[Dict[str, Any]] = []
# #         self.jig_drag_piece: Optional[Dict[str, Any]] = None
# #         self.jig_drag_ox = 0
# #         self.jig_drag_oy = 0
# #         self.jig_stage = self.JIG_PLAY  # no intro overlay
# #         self.jig_t0 = 0.0
# #
# #         self.back_btn = make_button(pygame.Rect(16, 16, 160, 48), "BACK", color=(120, 120, 120))
# #
# #         self._running = True
# #         self._result_unlocked = False
# #
# #     def _load_playlist(self) -> List[str]:
# #         if not os.path.isdir(IMAGE_DIR):
# #             return []
# #         return [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
# #
# #     def _layout_lock_dock(self):
# #         margin_bottom = 28
# #         dock_w = min(780, int(self.W * 0.68))
# #         dock_h = 96
# #         dock_x = (self.W - dock_w) // 2
# #         dock_y = self.H - dock_h - margin_bottom
# #         self.dock_rect = pygame.Rect(dock_x, dock_y, dock_w, dock_h)
# #
# #         pad = 14
# #         gap = 12
# #         btn_h = 64
# #         btn_y = dock_y + (dock_h - btn_h) // 2
# #         btn_w = (dock_w - pad * 2 - gap * 2) // 3
# #
# #         self.btn_unlock = pygame.Rect(dock_x + pad + (btn_w + gap) * 0, btn_y, btn_w, btn_h)
# #         self.btn_jigsaw = pygame.Rect(dock_x + pad + (btn_w + gap) * 1, btn_y, btn_w, btn_h)
# #         self.btn_admin = pygame.Rect(dock_x + pad + (btn_w + gap) * 2, btn_y, btn_w, btn_h)
# #
# #     def _touch_lock_ui(self):
# #         self.lock_ui_visible_until = time.time() + LOCK_UI_AUTOHIDE_S
# #
# #     def _lock_ui_visible(self) -> bool:
# #         return time.time() < self.lock_ui_visible_until
# #
# #     def _set_image_by_index(self, idx: int):
# #         self.lock_idx = idx % len(self.playlist)
# #         fname = self.playlist[self.lock_idx]
# #         raw = safe_load_image(os.path.join(IMAGE_DIR, fname))
# #
# #         if LOCK_VISIBLE_SCALE_MODE.lower() == "cover":
# #             self.lock_fg = scale_cover(raw, self.W, self.H)
# #             self.lock_fg_rect = self.lock_fg.get_rect(topleft=(0, 0))
# #         else:
# #             self.lock_fg, self.lock_fg_rect = scale_contain(raw, self.W, self.H)
# #
# #         big_w = self.W + LOCK_BG_PAN_RANGE_PX
# #         big_h = self.H + LOCK_BG_PAN_RANGE_PX
# #         bg = scale_cover(raw, big_w, big_h).convert()
# #
# #         if LOCK_BG_BLUR_METHOD.lower() == "hq":
# #             bg = blur_surface_hq(bg, radius=LOCK_BG_HQ_RADIUS, downscale=LOCK_BG_HQ_DOWNSCALE)
# #         else:
# #             bg = blur_surface_once(bg, LOCK_BG_BLUR_DOWNSCALE).convert()
# #
# #         if LOCK_BG_DIM_ALPHA > 0:
# #             dim = pygame.Surface((big_w, big_h), pygame.SRCALPHA)
# #             dim.fill((0, 0, 0, clamp255(LOCK_BG_DIM_ALPHA)))
# #             bg.blit(dim, (0, 0))
# #
# #         self.lock_bg_big = bg.convert()
# #
# #         if PUZZLE_BOARD_SCALE_MODE.lower() == "contain":
# #             board_fit, rect = scale_contain(raw, self.W, self.BOARD_H)
# #             board = pygame.Surface((self.W, self.BOARD_H))
# #             board.fill((0, 0, 0))
# #             board.blit(board_fit, rect)
# #             self.board_surf = board.convert()
# #         else:
# #             self.board_surf = scale_cover(raw, self.W, self.BOARD_H).convert()
# #
# #         max_x = max(0, self.lock_bg_big.get_width() - self.W)
# #         max_y = max(0, self.lock_bg_big.get_height() - self.H)
# #         self.pan_x = float(random.randint(0, max_x)) if max_x else 0.0
# #         self.pan_y = float(random.randint(0, max_y)) if max_y else 0.0
# #
# #         ang = random.uniform(0, math.tau)
# #         self.pan_vx = math.cos(ang) * LOCK_BG_PAN_SPEED_PX_S
# #         self.pan_vy = math.sin(ang) * LOCK_BG_PAN_SPEED_PX_S
# #
# #         self.lock_cycle_t0 = time.time()
# #
# #     def _advance_image(self):
# #         nxt = self.lock_idx + 1
# #         if nxt >= len(self.playlist):
# #             nxt = 0
# #             if LOCK_BG_SHUFFLE:
# #                 random.shuffle(self.playlist)
# #         self._set_image_by_index(nxt)
# #
# #     def _update_pan(self, dt: float):
# #         if not self.lock_bg_big:
# #             return
# #         max_x = max(0, self.lock_bg_big.get_width() - self.W)
# #         max_y = max(0, self.lock_bg_big.get_height() - self.H)
# #
# #         self.pan_x += self.pan_vx * dt
# #         self.pan_y += self.pan_vy * dt
# #
# #         if max_x > 0:
# #             if self.pan_x < 0:
# #                 self.pan_x = 0.0
# #                 self.pan_vx = abs(self.pan_vx)
# #             elif self.pan_x > max_x:
# #                 self.pan_x = float(max_x)
# #                 self.pan_vx = -abs(self.pan_vx)
# #         else:
# #             self.pan_x = 0.0
# #
# #         if max_y > 0:
# #             if self.pan_y < 0:
# #                 self.pan_y = 0.0
# #                 self.pan_vy = abs(self.pan_vy)
# #             elif self.pan_y > max_y:
# #                 self.pan_y = float(max_y)
# #                 self.pan_vy = -abs(self.pan_vy)
# #         else:
# #             self.pan_y = 0.0
# #
# #     # ---------- Frame + status ----------
# #     def _draw_lock_frame_to(self, target_surf: pygame.Surface):
# #         if self.lock_bg_big:
# #             max_x = max(0, self.lock_bg_big.get_width() - self.W)
# #             max_y = max(0, self.lock_bg_big.get_height() - self.H)
# #             vx = int(max(0, min(max_x, self.pan_x)))
# #             vy = int(max(0, min(max_y, self.pan_y)))
# #             view = pygame.Rect(vx, vy, self.W, self.H)
# #             target_surf.blit(self.lock_bg_big.subsurface(view), (0, 0))
# #         else:
# #             target_surf.fill((0, 0, 0))
# #
# #         if self.lock_fg and self.lock_fg_rect:
# #             target_surf.blit(self.lock_fg, self.lock_fg_rect)
# #
# #     def _build_lock_frame_surface(self) -> pygame.Surface:
# #         surf = pygame.Surface((self.W, self.H))
# #         self._draw_lock_frame_to(surf)
# #         return surf
# #
# #     def _draw_status_bar(self):
# #         if not SHOW_STATUS_BAR:
# #             return
# #         bar = pygame.Surface((self.W, STATUS_BAR_H), pygame.SRCALPHA)
# #         bar.fill((0, 0, 0, 140))
# #         self.screen.blit(bar, (0, 0))
# #         now = datetime.datetime.now()
# #         txt = now.strftime("%a %b %d   %I:%M %p").lstrip("0")
# #         t = self.font_small.render(txt, True, (230, 230, 230))
# #         self.screen.blit(t, (self.W - t.get_width() - 16, (STATUS_BAR_H - t.get_height()) // 2))
# #
# #     # ---------- transitions ----------
# #     def _choose_break_style(self) -> str:
# #         if LOCK_TRANSITION_STYLE == "random":
# #             return random.choice(LOCK_TRANSITION_STYLES)
# #         if LOCK_TRANSITION_STYLE in LOCK_TRANSITION_STYLES:
# #             return LOCK_TRANSITION_STYLE
# #         return "shatter"
# #
# #     def _make_break_pieces(self, snap: pygame.Surface, style: str) -> List[Dict[str, Any]]:
# #         pieces: List[Dict[str, Any]] = []
# #         W, H = self.W, self.H
# #
# #         if style == "blinds":
# #             n = 16
# #             tile_w = max(16, W // n)
# #             for i in range(n):
# #                 x = i * tile_w
# #                 w = tile_w if i < n - 1 else (W - x)
# #                 rect = pygame.Rect(x, 0, w, H)
# #                 surf = snap.subsurface(rect).copy()
# #                 dir_sign = -1 if (i % 2 == 0) else 1
# #                 vx = dir_sign * random.uniform(250, 450)
# #                 pieces.append({
# #                     "surf": surf,
# #                     "pos": [float(rect.x), float(rect.y)],
# #                     "vel": [vx, random.uniform(-40, 40)],
# #                     "rot": 0.0,
# #                     "ang": random.uniform(-30, 30),
# #                 })
# #             return pieces
# #
# #         target = LOCK_SHATTER_TILE_TARGET
# #         cols = int(math.sqrt(target * (W / max(1.0, H))))
# #         cols = max(6, min(30, cols))
# #         rows = max(6, min(24, int(target / cols)))
# #         tile_w = max(18, W // cols)
# #         tile_h = max(18, H // rows)
# #
# #         for y in range(0, H, tile_h):
# #             for x in range(0, W, tile_w):
# #                 rect = pygame.Rect(x, y, min(tile_w, W - x), min(tile_h, H - y))
# #                 surf = snap.subsurface(rect).copy()
# #                 cx = rect.centerx - W / 2.0
# #                 cy = rect.centery - H / 2.0
# #
# #                 if style == "explode":
# #                     mag = random.uniform(220, 520)
# #                     ang = math.atan2(cy, cx) + random.uniform(-0.25, 0.25)
# #                     vx = math.cos(ang) * mag
# #                     vy = math.sin(ang) * mag
# #                 elif style == "drop":
# #                     vx = random.uniform(-80, 80)
# #                     vy = random.uniform(50, 160)
# #                 else:
# #                     vx = random.uniform(-260, 260) + (cx * 0.25)
# #                     vy = random.uniform(-180, 120) + (cy * 0.20)
# #
# #                 rot = random.uniform(-35, 35)
# #                 pieces.append({
# #                     "surf": surf,
# #                     "pos": [float(rect.x), float(rect.y)],
# #                     "vel": [vx, vy],
# #                     "rot": 0.0,
# #                     "ang": rot,
# #                 })
# #
# #         return pieces
# #
# #     def _begin_lock_transition(self):
# #         self.lock_snapshot = self._build_lock_frame_surface()
# #         self.break_style = self._choose_break_style()
# #         self.break_dur = float(LOCK_BREAK_DURATIONS.get(self.break_style, 0.85))
# #         self.lock_trans = self.LOCK_TRANS_BREAK
# #         self.lock_trans_t0 = time.time()
# #         self.break_pieces = self._make_break_pieces(self.lock_snapshot, self.break_style)
# #
# #     def _draw_break(self, t: float):
# #         self.screen.fill((0, 0, 0))
# #         dt = 1.0 / 60.0
# #         grav = LOCK_SHATTER_GRAVITY
# #
# #         for p in self.break_pieces:
# #             vx, vy = p["vel"]
# #             if self.break_style in ("shatter", "drop"):
# #                 vy += grav * dt * (0.70 if self.break_style == "drop" else 0.40)
# #                 p["vel"][1] = vy
# #
# #             p["pos"][0] += vx * dt
# #             p["pos"][1] += vy * dt
# #
# #             damp = 1.0 - (0.12 * t)
# #             p["vel"][0] *= damp
# #             p["vel"][1] *= damp
# #
# #             p["rot"] += p["ang"] * dt
# #
# #             surf = p["surf"]
# #             if abs(p["rot"]) > 0.5:
# #                 rs = pygame.transform.rotozoom(surf, p["rot"], 1.0)
# #                 r = rs.get_rect(center=(p["pos"][0] + surf.get_width() / 2, p["pos"][1] + surf.get_height() / 2))
# #                 self.screen.blit(rs, r.topleft)
# #             else:
# #                 self.screen.blit(surf, (p["pos"][0], p["pos"][1]))
# #
# #         ov = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
# #         ov.fill((0, 0, 0, int(220 * _ease_in_quad(t))))
# #         self.screen.blit(ov, (0, 0))
# #
# #     def _draw_fadein(self, t: float):
# #         self._draw_lock_frame_to(self.screen)
# #         a = int(255 * (1.0 - _ease_out_cubic(t)))
# #         ov = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
# #         ov.fill((0, 0, 0, a))
# #         self.screen.blit(ov, (0, 0))
# #
# #     # ---------- Square puzzle ----------
# #     def _square_setup(self):
# #         if self.board_surf is None:
# #             return
# #
# #         margin = 40
# #         usable_w = self.W - margin * 2
# #         usable_h = self.BOARD_H - margin * 2
# #         cols, rows = GRID_X, GRID_Y
# #
# #         self.tile_w = usable_w // cols
# #         self.tile_h = usable_h // rows
# #
# #         self.slot_positions = []
# #         for j in range(rows):
# #             for i in range(cols):
# #                 sx = margin + i * self.tile_w
# #                 sy = margin + j * self.tile_h
# #                 self.slot_positions.append((sx, sy))
# #
# #         board_scaled = pygame.transform.smoothscale(self.board_surf, (usable_w, usable_h))
# #         tiles: List[Dict[str, Any]] = []
# #         for j in range(rows):
# #             for i in range(cols):
# #                 src_rect = pygame.Rect(i * self.tile_w, j * self.tile_h, self.tile_w, self.tile_h)
# #                 surf = board_scaled.subsurface(src_rect).copy()
# #                 tile = pygame.Surface((self.tile_w, self.tile_h), pygame.SRCALPHA)
# #                 tile.blit(surf, (0, 0))
# #                 pygame.draw.rect(tile, (255, 255, 255, 70), pygame.Rect(0, 0, self.tile_w, self.tile_h), 2, border_radius=10)
# #
# #                 correct = self.slot_positions[j * cols + i]
# #                 pos = tray_random_pos_sized(self.W, self.tray_rect, self.tile_w, self.tile_h)
# #                 tiles.append({
# #                     "surf": tile,
# #                     "correct": correct,
# #                     "pos": [float(pos[0]), float(pos[1])],
# #                     "locked": False,
# #                 })
# #
# #         random.shuffle(tiles)
# #         self.tiles = tiles
# #         self.drag_tile = None
# #         self.puz_stage = self.PUZ_PLAY  # no reference overlay
# #         self.puz_t0 = time.time()
# #
# #     def _square_all_locked(self) -> bool:
# #         return all(t["locked"] for t in self.tiles)
# #
# #     def _square_slot_occupied(self, slot_xy: Tuple[int, int]) -> bool:
# #         for t in self.tiles:
# #             if t["locked"] and tuple(map(int, t["pos"])) == slot_xy:
# #                 return True
# #         return False
# #
# #     def _square_find_tile_at(self, x: int, y: int) -> Optional[Dict[str, Any]]:
# #         for t in reversed(self.tiles):
# #             if t["locked"]:
# #                 continue
# #             r = pygame.Rect(int(t["pos"][0]), int(t["pos"][1]), self.tile_w, self.tile_h)
# #             if r.collidepoint((x, y)):
# #                 return t
# #         return None
# #
# #     def _square_draw(self):
# #         # Remove the “weird rounded panel” and any reference image overlay.
# #         self.screen.fill(COLOR_BG)
# #
# #         title = self.font_brand2.render("Unlock Puzzle", True, (230, 230, 230))
# #         self.screen.blit(title, (self.W // 2 - title.get_width() // 2, 18))
# #
# #         # Draw slots only
# #         for (sx, sy) in self.slot_positions:
# #             slot_rect = pygame.Rect(sx, sy, self.tile_w, self.tile_h)
# #             pygame.draw.rect(self.screen, (55, 55, 55), slot_rect, 2, border_radius=10)
# #
# #         pygame.draw.rect(self.screen, COLOR_TRAY, self.tray_rect)
# #         pygame.draw.line(self.screen, COLOR_LINE, (0, self.BOARD_H), (self.W, self.BOARD_H), 2)
# #
# #         tray_label = self.font_small.render("Drag pieces into place.", True, (220, 220, 220))
# #         self.screen.blit(tray_label, (18, self.BOARD_H + 10))
# #
# #         mx, my = pygame.mouse.get_pos()
# #         draw_button(self.screen, self.back_btn, self.font_small, self.font_small,
# #                     active=self.back_btn["rect"].collidepoint((mx, my)), small=True)
# #
# #         for t in self.tiles:
# #             self.screen.blit(t["surf"], (t["pos"][0], t["pos"][1]))
# #
# #     def _square_handle_event(self, ev):
# #         if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
# #             self.state = self.STATE_LOCK
# #             self.lock_pressed = None
# #             return
# #
# #         if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
# #             pos = event_pos(ev, self.W, self.H)
# #             if not pos:
# #                 return
# #             x, y = pos
# #
# #             if self.back_btn["rect"].collidepoint((x, y)):
# #                 self.state = self.STATE_LOCK
# #                 self.lock_pressed = None
# #                 return
# #
# #             t = self._square_find_tile_at(x, y)
# #             if t:
# #                 play(self.snd_pick)
# #                 self.drag_tile = t
# #                 self.drag_ox = x - int(t["pos"][0])
# #                 self.drag_oy = y - int(t["pos"][1])
# #                 self.tiles.remove(t)
# #                 self.tiles.append(t)
# #
# #         if ev.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
# #             if self.drag_tile is None:
# #                 return
# #             pos = event_pos(ev, self.W, self.H)
# #             if not pos:
# #                 return
# #             x, y = pos
# #             self.drag_tile["pos"][0] = float(x - self.drag_ox)
# #             self.drag_tile["pos"][1] = float(y - self.drag_oy)
# #
# #         if ev.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
# #             if self.drag_tile is None:
# #                 return
# #             t = self.drag_tile
# #             self.drag_tile = None
# #             play(self.snd_drop)
# #
# #             cx = int(t["pos"][0] + self.tile_w / 2)
# #             cy = int(t["pos"][1] + self.tile_h / 2)
# #
# #             slot_x, slot_y = t["correct"]
# #             slot_c = (slot_x + self.tile_w // 2, slot_y + self.tile_h // 2)
# #
# #             if dist2((cx, cy), slot_c) <= (SNAP_DIST * SNAP_DIST) and not self._square_slot_occupied((slot_x, slot_y)):
# #                 t["pos"][0] = float(slot_x)
# #                 t["pos"][1] = float(slot_y)
# #                 t["locked"] = True
# #                 play(self.snd_snap)
# #
# #                 if self._square_all_locked():
# #                     bg = self.screen.copy()
# #                     unlock_success_overlay(self.screen, self.clock, self.W, self.H, self.font_brand, self.font_small,
# #                                           self.snd_snap, bg_frame_surf=bg)
# #                     fade_to_black(self.screen, self.clock, 0.18)
# #                     self._result_unlocked = True
# #                     self._running = False
# #
# #     # ---------- Jigsaw ----------
# #     def _jigsaw_setup(self, cols: int, rows: int):
# #         if self.board_surf is None:
# #             return
# #         self.jig_cols, self.jig_rows = cols, rows
# #         self.jig_snap_dist = calc_jig_snap_dist(self.W, self.BOARD_H, cols, rows)
# #
# #         pieces = build_jigsaw_pieces(self.W, self.BOARD_H, self.board_surf, cols, rows)
# #         for p in pieces:
# #             w, h = p["surf"].get_size()
# #             pos = tray_random_pos_sized(self.W, self.tray_rect, w, h)
# #             p["pos"] = [float(pos[0]), float(pos[1])]
# #             p["locked"] = False
# #         random.shuffle(pieces)
# #
# #         self.jig_pieces = pieces
# #         self.jig_drag_piece = None
# #         self.jig_stage = self.JIG_PLAY
# #         self.jig_t0 = time.time()
# #
# #     def _jigsaw_find_piece_at(self, x: int, y: int) -> Optional[Dict[str, Any]]:
# #         for p in reversed(self.jig_pieces):
# #             if p.get("locked"):
# #                 continue
# #             px, py = int(p["pos"][0]), int(p["pos"][1])
# #             lx, ly = x - px, y - py
# #             if lx < 0 or ly < 0:
# #                 continue
# #             if lx >= p["surf"].get_width() or ly >= p["surf"].get_height():
# #                 continue
# #             if p["mask"].get_at((lx, ly)):
# #                 return p
# #         return None
# #
# #     def _jigsaw_draw(self):
# #         # Remove the “rounded panel” and any intro overlay.
# #         self.screen.fill(COLOR_BG)
# #
# #         title = self.font_brand2.render(f"Jigsaw {self.jig_cols} x {self.jig_rows}", True, (230, 230, 230))
# #         self.screen.blit(title, (self.W // 2 - title.get_width() // 2, 18))
# #
# #         pygame.draw.rect(self.screen, COLOR_TRAY, self.tray_rect)
# #         pygame.draw.line(self.screen, COLOR_LINE, (0, self.BOARD_H), (self.W, self.BOARD_H), 2)
# #
# #         tray_label = self.font_small.render("Drag pieces into place (snaps when close).", True, (220, 220, 220))
# #         self.screen.blit(tray_label, (18, self.BOARD_H + 10))
# #
# #         mx, my = pygame.mouse.get_pos()
# #         draw_button(self.screen, self.back_btn, self.font_small, self.font_small,
# #                     active=self.back_btn["rect"].collidepoint((mx, my)), small=True)
# #
# #         for p in self.jig_pieces:
# #             self.screen.blit(p["surf"], (p["pos"][0], p["pos"][1]))
# #
# #     def _jigsaw_handle_event(self, ev):
# #         if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
# #             self.state = self.STATE_LOCK
# #             self.lock_pressed = None
# #             return
# #
# #         if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
# #             pos = event_pos(ev, self.W, self.H)
# #             if not pos:
# #                 return
# #             x, y = pos
# #
# #             if self.back_btn["rect"].collidepoint((x, y)):
# #                 self.state = self.STATE_LOCK
# #                 self.lock_pressed = None
# #                 return
# #
# #             p = self._jigsaw_find_piece_at(x, y)
# #             if p:
# #                 play(self.snd_pick)
# #                 self.jig_drag_piece = p
# #                 self.jig_drag_ox = x - int(p["pos"][0])
# #                 self.jig_drag_oy = y - int(p["pos"][1])
# #                 self.jig_pieces.remove(p)
# #                 self.jig_pieces.append(p)
# #
# #         if ev.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
# #             if self.jig_drag_piece is None:
# #                 return
# #             pos = event_pos(ev, self.W, self.H)
# #             if not pos:
# #                 return
# #             x, y = pos
# #             self.jig_drag_piece["pos"][0] = float(x - self.jig_drag_ox)
# #             self.jig_drag_piece["pos"][1] = float(y - self.jig_drag_oy)
# #
# #         if ev.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
# #             if self.jig_drag_piece is None:
# #                 return
# #             p = self.jig_drag_piece
# #             self.jig_drag_piece = None
# #             play(self.snd_drop)
# #
# #             correct = p["correct_pos"]
# #             px, py = p["pos"]
# #             dx = (px - correct[0])
# #             dy = (py - correct[1])
# #             if (dx * dx + dy * dy) <= (self.jig_snap_dist * self.jig_snap_dist):
# #                 p["pos"][0] = float(correct[0])
# #                 p["pos"][1] = float(correct[1])
# #                 p["locked"] = True
# #                 play(self.snd_snap)
# #
# #                 # IMPORTANT: this only unlocks when ALL pieces are locked
# #                 if jigsaw_all_locked(self.jig_pieces):
# #                     bg = self.screen.copy()
# #                     unlock_success_overlay(self.screen, self.clock, self.W, self.H, self.font_brand, self.font_small,
# #                                           self.snd_snap, hold_s=JIG_SOLVED_HOLD_S, bg_frame_surf=bg)
# #                     fade_to_black(self.screen, self.clock, 0.18)
# #                     self._result_unlocked = True
# #                     self._running = False
# #
# #     # ---------- Lock state ----------
# #     def _draw_lock(self):
# #         if self.lock_trans == self.LOCK_TRANS_BREAK:
# #             t = (time.time() - self.lock_trans_t0) / max(0.001, self.break_dur)
# #             if t >= 1.0:
# #                 self._advance_image()
# #                 self.lock_trans = self.LOCK_TRANS_FADEIN
# #                 self.lock_trans_t0 = time.time()
# #                 self._draw_fadein(0.0)
# #             else:
# #                 self._draw_break(t)
# #         elif self.lock_trans == self.LOCK_TRANS_FADEIN:
# #             t = (time.time() - self.lock_trans_t0) / max(0.001, LOCK_FADEIN_S)
# #             if t >= 1.0:
# #                 self.lock_trans = self.LOCK_TRANS_NONE
# #                 self._draw_lock_frame_to(self.screen)
# #             else:
# #                 self._draw_fadein(t)
# #         else:
# #             self._draw_lock_frame_to(self.screen)
# #
# #         title = self.font_brand.render(BRAND_TEXT, True, (255, 255, 255))
# #         subtitle = self.font_brand2.render(BRAND_SUB, True, (230, 230, 230))
# #         self.screen.blit(title, (30, 70))
# #         self.screen.blit(subtitle, (30, 135))
# #
# #         self._draw_status_bar()
# #
# #         target = 255.0 if self._lock_ui_visible() else 0.0
# #         dt = 1.0 / 60.0
# #         step = (255.0 / max(0.001, LOCK_UI_FADE_S)) * dt
# #         if self.ui_alpha < target:
# #             self.ui_alpha = min(target, self.ui_alpha + step)
# #         elif self.ui_alpha > target:
# #             self.ui_alpha = max(target, self.ui_alpha - step)
# #
# #         a = int(self.ui_alpha)
# #         if a > 0:
# #             draw_modern_dock(self.screen, self.dock_rect, a)
# #
# #             mx, my = pygame.mouse.get_pos()
# #             over_unlock = self.btn_unlock.collidepoint((mx, my))
# #             over_jigsaw = self.btn_jigsaw.collidepoint((mx, my))
# #             over_admin = self.btn_admin.collidepoint((mx, my))
# #
# #             pressed_unlock = (self.lock_pressed == "unlock")
# #             pressed_jigsaw = (self.lock_pressed == "jigsaw")
# #             pressed_admin = (self.lock_pressed == "admin")
# #
# #             draw_modern_button(self.screen, self.btn_unlock, "Unlock", self.font_dock,
# #                                _draw_icon_lock, ACCENT_UNLOCK, over_unlock, pressed_unlock, a)
# #             draw_modern_button(self.screen, self.btn_jigsaw, "Jigsaw", self.font_dock,
# #                                _draw_icon_jigsaw, ACCENT_JIGSAW, over_jigsaw, pressed_jigsaw, a)
# #             draw_modern_button(self.screen, self.btn_admin, "PIN", self.font_dock,
# #                                _draw_icon_key, ACCENT_ADMIN, over_admin, pressed_admin, a)
# #
# #     def _lock_handle_event(self, ev):
# #         if ev.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
# #             pos = event_pos(ev, self.W, self.H)
# #             if pos:
# #                 x, y = pos
# #                 lx, ly = self.last_mouse_pos
# #                 if abs(x - lx) + abs(y - ly) >= LOCK_UI_MOUSE_MOVE_THRESH:
# #                     self._touch_lock_ui()
# #                 self.last_mouse_pos = (x, y)
# #
# #         if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
# #             self._touch_lock_ui()
# #             pos = event_pos(ev, self.W, self.H)
# #             if not pos:
# #                 return
# #             x, y = pos
# #
# #             if self.ui_alpha >= 40:
# #                 if self.btn_unlock.collidepoint((x, y)):
# #                     self.lock_pressed = "unlock"
# #                     play(self.snd_pick)
# #                 elif self.btn_jigsaw.collidepoint((x, y)):
# #                     self.lock_pressed = "jigsaw"
# #                     play(self.snd_pick)
# #                 elif self.btn_admin.collidepoint((x, y)):
# #                     self.lock_pressed = "admin"
# #                     play(self.snd_pick)
# #                 else:
# #                     self.lock_pressed = None
# #
# #         if ev.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
# #             pos = event_pos(ev, self.W, self.H)
# #             if not pos:
# #                 self.lock_pressed = None
# #                 return
# #             x, y = pos
# #
# #             pressed = self.lock_pressed
# #             self.lock_pressed = None
# #             if pressed is None:
# #                 return
# #
# #             if pressed == "unlock" and self.btn_unlock.collidepoint((x, y)):
# #                 self._square_setup()
# #                 self.state = self.STATE_SQUARE
# #                 return
# #
# #             if pressed == "jigsaw" and self.btn_jigsaw.collidepoint((x, y)):
# #                 self.state = self.STATE_JIG_SELECT
# #                 return
# #
# #             if pressed == "admin" and self.btn_admin.collidepoint((x, y)):
# #                 bg = self.screen.copy()
# #                 ok = pin_overlay_loop(self.screen, self.clock, self.W, self.H, bg, self.font, self.font_small,
# #                                       self.snd_error, admin_pin=self.admin_pin)
# #                 if ok:
# #                     bg2 = self.screen.copy()
# #                     unlock_success_overlay(self.screen, self.clock, self.W, self.H, self.font_brand, self.font_small,
# #                                           self.snd_snap, bg_frame_surf=bg2)
# #                     fade_to_black(self.screen, self.clock, 0.18)
# #                     self._result_unlocked = True
# #                     self._running = False
# #                 return
# #
# #         if ev.type == pygame.KEYDOWN:
# #             self._touch_lock_ui()
# #             if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
# #                 self._square_setup()
# #                 self.state = self.STATE_SQUARE
# #                 return
# #             if ev.key == pygame.K_j:
# #                 self.state = self.STATE_JIG_SELECT
# #                 return
# #
# #     def run(self) -> bool:
# #         if not self.playlist:
# #             self.lock_trans = self.LOCK_TRANS_NONE
# #
# #         selected_jig = 1
# #         prev_time = time.time()
# #
# #         while self._running:
# #             now = time.time()
# #             dt = now - prev_time
# #             prev_time = now
# #
# #             if self.state == self.STATE_LOCK:
# #                 self._update_pan(dt)
# #                 if self.lock_trans == self.LOCK_TRANS_NONE and LOCK_TRANSITION_ENABLE and self.playlist:
# #                     if (now - self.lock_cycle_t0) >= LOCK_BG_CYCLE_S:
# #                         self._begin_lock_transition()
# #
# #             for ev in pygame.event.get():
# #                 if ev.type == pygame.QUIT:
# #                     self._running = False
# #                     break
# #
# #                 if self.state == self.STATE_LOCK:
# #                     self._lock_handle_event(ev)
# #
# #                 elif self.state == self.STATE_SQUARE:
# #                     self._square_handle_event(ev)
# #
# #                 elif self.state == self.STATE_JIG_SELECT:
# #                     if ev.type == pygame.KEYDOWN:
# #                         if ev.key == pygame.K_ESCAPE:
# #                             self.state = self.STATE_LOCK
# #                             continue
# #                         if ev.key == pygame.K_UP:
# #                             selected_jig = max(0, selected_jig - 1)
# #                         if ev.key == pygame.K_DOWN:
# #                             selected_jig = min(len(JIG_DIFFICULTY_CHOICES) - 1, selected_jig + 1)
# #                         if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
# #                             _, c, r = JIG_DIFFICULTY_CHOICES[selected_jig]
# #                             self._jigsaw_setup(c, r)
# #                             self.state = self.STATE_JIGSAW
# #                             continue
# #
# #                     if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
# #                         pos = event_pos(ev, self.W, self.H)
# #                         if pos:
# #                             x, y = pos
# #                             if self.back_btn["rect"].collidepoint((x, y)):
# #                                 self.state = self.STATE_LOCK
# #                                 continue
# #
# #                             row_h = 70
# #                             gap = 12
# #                             start_y = 170
# #                             for i in range(len(JIG_DIFFICULTY_CHOICES)):
# #                                 rect = pygame.Rect(int(self.W * 0.18), start_y + i * (row_h + gap),
# #                                                    int(self.W * 0.64), row_h)
# #                                 if rect.collidepoint((x, y)):
# #                                     selected_jig = i
# #                                     _, c, r = JIG_DIFFICULTY_CHOICES[selected_jig]
# #                                     self._jigsaw_setup(c, r)
# #                                     self.state = self.STATE_JIGSAW
# #                                     break
# #
# #                 elif self.state == self.STATE_JIGSAW:
# #                     self._jigsaw_handle_event(ev)
# #
# #             if self.state == self.STATE_LOCK:
# #                 self._draw_lock()
# #
# #             elif self.state == self.STATE_SQUARE:
# #                 self._square_draw()
# #
# #             elif self.state == self.STATE_JIG_SELECT:
# #                 self.screen.fill(COLOR_BG)
# #                 title = self.font_brand.render("Jigsaw Unlock", True, (255, 255, 255))
# #                 self.screen.blit(title, (self.W // 2 - title.get_width() // 2, 60))
# #                 sub = self.font_small.render("Select difficulty", True, (220, 220, 220))
# #                 self.screen.blit(sub, (self.W // 2 - sub.get_width() // 2, 120))
# #
# #                 mx, my = pygame.mouse.get_pos()
# #                 draw_button(self.screen, self.back_btn, self.font_small, self.font_small,
# #                             active=self.back_btn["rect"].collidepoint((mx, my)), small=True)
# #
# #                 row_h = 70
# #                 gap = 12
# #                 start_y = 170
# #                 for i, (name, c, r) in enumerate(JIG_DIFFICULTY_CHOICES):
# #                     rect = pygame.Rect(int(self.W * 0.18), start_y + i * (row_h + gap),
# #                                        int(self.W * 0.64), row_h)
# #                     active = rect.collidepoint((mx, my))
# #                     bg = (40, 40, 40) if (i == selected_jig) else (22, 22, 22)
# #                     if active:
# #                         bg = lighten(bg, 10)
# #                     pygame.draw.rect(self.screen, bg, rect, border_radius=16)
# #                     pygame.draw.rect(self.screen, (140, 140, 140), rect, 2, border_radius=16)
# #
# #                     label = self.font.render(f"{name}", True, (240, 240, 240))
# #                     dims = self.font_small.render(f"{c} x {r}", True, (210, 210, 210))
# #                     self.screen.blit(label, (rect.x + 22, rect.centery - label.get_height() // 2))
# #                     self.screen.blit(dims, (rect.right - dims.get_width() - 22, rect.centery - dims.get_height() // 2))
# #
# #             elif self.state == self.STATE_JIGSAW:
# #                 self._jigsaw_draw()
# #
# #             pygame.display.flip()
# #             self.clock.tick(60)
# #
# #         return bool(self._result_unlocked)
# #
# #
# # # ============================================================
# # # Public entrypoint used by kiosk_shell (single window)
# # # ============================================================
# # def run_kiosk_flow_shared(screen: pygame.Surface, clock: pygame.time.Clock, cfg: Dict[str, Any]) -> int:
# #     """
# #     Runs lock + puzzles. If unlocked, shows post-unlock menu and RETURNS an rc
# #     (42 Pi mode, 43 Solaris, etc.) so start_lock.sh can launch external modes.
# #     """
# #     app = LockApp(screen=screen, clock=clock, cfg=cfg)
# #     ok = app.run()
# #     if not ok:
# #         return RC_RELOCK
# #     return post_unlock_menu(screen=screen, clock=clock, cfg=cfg)
# #
# #
# # # Standalone execution (useful for testing)
# # if __name__ == "__main__":
# #     pygame.init()
# #     pygame.font.init()
# #     screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
# #     clock = pygame.time.Clock()
# #     cfg = {"security": {"pi_pin": ADMIN_PIN_DEFAULT}, "feature_flags": {}, "idle": {"menu_seconds": 120}, "ui": {}}
# #     rc = run_kiosk_flow_shared(screen, clock, cfg)
# #     pygame.quit()
# #     sys.exit(int(rc))
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
#
# import os
# import sys
# import time
# import math
# import random
# import datetime
# from typing import Optional, Tuple, List, Dict, Any
#
# os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
# os.environ.setdefault("SDL_VIDEODRIVER", "x11")
# os.environ.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")
# os.environ.setdefault("SDL_VIDEO_WINDOW_POS", "0,0")
# os.environ.setdefault("SDL_VIDEO_CENTERED", "0")
#
# import pygame  # noqa: E402
#
#
# # ---------------- CONFIG (defaults; can be overridden via cfg passed from kiosk_shell) ----------------
# GRID_X = 3
# GRID_Y = 4
#
# SNAP_DIST = 190
#
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# IMAGE_DIR = os.path.join(BASE_DIR, "images")
# SOUNDS_DIR = os.path.join(BASE_DIR, "sounds")
#
# BRAND_TEXT = "Glover SPARCstation"
# BRAND_SUB = "Puzzle Lock"
#
# ADMIN_PIN_DEFAULT = "1193"
# PIN_MAX_LEN = 12
#
# SHOW_STATUS_BAR = True
# STATUS_BAR_H = 40
#
# LOCK_UI_START_HIDDEN = True
# LOCK_UI_AUTOHIDE_S = 6.0
# LOCK_UI_MOUSE_MOVE_THRESH = 10
# LOCK_UI_FADE_S = 0.18
#
# LOCK_BG_CYCLE_S = 18.0
# LOCK_VISIBLE_SCALE_MODE = "contain"
#
# LOCK_BG_PAN_RANGE_PX = 900
# LOCK_BG_PAN_SPEED_PX_S = 90.0
#
# LOCK_BG_BLUR_METHOD = "hq"
# LOCK_BG_HQ_DOWNSCALE = 2
# LOCK_BG_HQ_RADIUS = 10
#
# LOCK_BG_BLUR_DOWNSCALE = 12
# LOCK_BG_DIM_ALPHA = 60
#
# LOCK_TRANSITION_ENABLE = True
# LOCK_FADEIN_S = 0.55
#
# LOCK_TRANSITION_STYLES = ["shatter", "blinds", "explode", "drop"]
# LOCK_TRANSITION_STYLE = "random"
# LOCK_BREAK_DURATIONS = {
#     "shatter": 0.85,
#     "blinds":  0.95,
#     "explode": 0.80,
#     "drop":    0.90,
# }
#
# LOCK_SHATTER_TILE_TARGET = 180
# LOCK_SHATTER_GRAVITY = 1200.0
#
# LOCK_BG_RANDOM_START = True
# LOCK_BG_SHUFFLE = False
#
# COLOR_BG = (0, 0, 0)
# COLOR_TRAY = (18, 18, 18)
# COLOR_LINE = (70, 70, 70)
#
# ACCENT_UNLOCK = (70, 185, 120)
# ACCENT_JIGSAW = (170, 170, 170)
# ACCENT_ADMIN = (120, 200, 255)
#
# SND_PICK = "pick.wav"
# SND_DROP = "drop.wav"
# SND_SNAP = "snap.wav"
# SND_ERROR = "error.wav"
#
# TRAY_H_FRAC = 0.28
# TRAY_MARGIN = 14
#
# PUZ_INTRO_HOLD_S = 0.55
# PUZ_FALL_S = 0.85
# UNLOCK_SUCCESS_S = 0.85
#
# JIG_KNOB_FRAC = 0.22
# JIG_EDGE_OFF_FRAC = 0.18
#
# JIG_SNAP_FRAC = 0.55
# JIG_SNAP_MIN = 40
# JIG_SNAP_MAX = 140
#
# JIG_INTRO_HOLD_S = 0.55
# JIG_FALL_S = 0.85
# JIG_SOLVED_HOLD_S = 0.85
#
# JIG_BG_DIM_ALPHA = 130
#
# JIG_DIFFICULTY_CHOICES = [
#     ("Easy",    3, 2),
#     ("Normal",  4, 3),
#     ("Hard",    5, 4),
#     ("Expert",  6, 4),
#     ("Insane", 10, 5),
#     ("Extreme", 12, 5),
# ]
#
# PUZZLE_BOARD_SCALE_MODE = "cover"
#
#
# # ---------------- helpers ----------------
# def clamp255(v: float) -> int:
#     return max(0, min(255, int(v)))
#
#
# def lighten(color, amt=22):
#     return (clamp255(color[0] + amt), clamp255(color[1] + amt), clamp255(color[2] + amt))
#
#
# def _ease_in_quad(t: float) -> float:
#     return t * t
#
#
# def _ease_out_cubic(t: float) -> float:
#     u = 1.0 - t
#     return 1.0 - (u * u * u)
#
#
# def dist2(a, b) -> float:
#     dx = a[0] - b[0]
#     dy = a[1] - b[1]
#     return dx * dx + dy * dy
#
#
# def load_sound(name: str):
#     path = os.path.join(SOUNDS_DIR, name)
#     if os.path.exists(path):
#         try:
#             return pygame.mixer.Sound(path)
#         except Exception:
#             return None
#     return None
#
#
# def play(snd):
#     if snd:
#         try:
#             snd.play()
#         except Exception:
#             pass
#
#
# def event_pos(ev, W: int, H: int):
#     if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
#         return ev.pos
#     if ev.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
#         return (int(ev.x * W), int(ev.y * H))
#     return None
#
#
# def safe_load_image(path: str) -> pygame.Surface:
#     try:
#         from PIL import Image, ImageOps  # type: ignore
#         img = Image.open(path)
#         img = ImageOps.exif_transpose(img)
#         if img.mode in ("RGBA", "LA") or ("transparency" in img.info):
#             img = img.convert("RGBA")
#             surf = pygame.image.frombuffer(img.tobytes(), img.size, "RGBA").convert_alpha()
#         else:
#             img = img.convert("RGB")
#             surf = pygame.image.frombuffer(img.tobytes(), img.size, "RGB").convert()
#         return surf
#     except Exception:
#         surf = pygame.image.load(path)
#         try:
#             return surf.convert_alpha() if surf.get_alpha() is not None else surf.convert()
#         except Exception:
#             return surf
#
#
# def scale_cover(src_surf: pygame.Surface, target_w: int, target_h: int) -> pygame.Surface:
#     sw, sh = src_surf.get_size()
#     scale = max(target_w / sw, target_h / sh)
#     nw = max(1, int(sw * scale))
#     nh = max(1, int(sh * scale))
#     scaled = pygame.transform.smoothscale(src_surf, (nw, nh))
#     x = (nw - target_w) // 2
#     y = (nh - target_h) // 2
#     return scaled.subsurface(pygame.Rect(x, y, target_w, target_h)).copy()
#
#
# def scale_contain(src_surf: pygame.Surface, target_w: int, target_h: int):
#     sw, sh = src_surf.get_size()
#     scale = min(target_w / sw, target_h / sh)
#     nw = max(1, int(sw * scale))
#     nh = max(1, int(sh * scale))
#     scaled = pygame.transform.smoothscale(src_surf, (nw, nh))
#     rect = scaled.get_rect(center=(target_w // 2, target_h // 2))
#     return scaled, rect
#
#
# def blur_surface_once(src: pygame.Surface, downscale: int = 12) -> pygame.Surface:
#     downscale = max(2, int(downscale))
#     w, h = src.get_size()
#     dw = max(2, w // downscale)
#     dh = max(2, h // downscale)
#     small = pygame.transform.smoothscale(src, (dw, dh))
#     return pygame.transform.smoothscale(small, (w, h))
#
#
# def blur_surface_hq(src: pygame.Surface, radius: int = 10, downscale: int = 2) -> pygame.Surface:
#     try:
#         from PIL import Image, ImageFilter  # type: ignore
#         w, h = src.get_size()
#         ds = max(1, int(downscale))
#         if ds > 1:
#             sw = max(2, w // ds)
#             sh = max(2, h // ds)
#             src_small = pygame.transform.smoothscale(src, (sw, sh))
#             raw = pygame.image.tostring(src_small, "RGB")
#             im = Image.frombytes("RGB", (sw, sh), raw)
#         else:
#             raw = pygame.image.tostring(src, "RGB")
#             im = Image.frombytes("RGB", (w, h), raw)
#
#         im = im.filter(ImageFilter.GaussianBlur(radius=max(0, int(radius))))
#         if ds > 1:
#             im = im.resize((w, h), resample=Image.LANCZOS)
#
#         out = pygame.image.frombuffer(im.tobytes(), (w, h), "RGB").convert()
#         return out
#     except Exception:
#         return blur_surface_once(src, LOCK_BG_BLUR_DOWNSCALE)
#
#
# def _draw_round_rect_alpha(dst, rect: pygame.Rect, rgb, alpha: int, radius: int):
#     a = clamp255(alpha)
#     s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
#     pygame.draw.rect(s, (rgb[0], rgb[1], rgb[2], a), pygame.Rect(0, 0, rect.w, rect.h), border_radius=radius)
#     dst.blit(s, rect.topleft)
#
#
# def _draw_round_rect_outline_alpha(dst, rect: pygame.Rect, rgb, alpha: int, radius: int, width: int = 2):
#     a = clamp255(alpha)
#     s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
#     pygame.draw.rect(s, (rgb[0], rgb[1], rgb[2], a), pygame.Rect(0, 0, rect.w, rect.h), width, border_radius=radius)
#     dst.blit(s, rect.topleft)
#
#
# def _draw_icon_lock(dst, center, color, alpha=255):
#     cx, cy = center
#     a = clamp255(alpha)
#     col = (color[0], color[1], color[2], a)
#     s = pygame.Surface((40, 40), pygame.SRCALPHA)
#     pygame.draw.arc(s, col, pygame.Rect(10, 6, 20, 18), math.pi, 0, 3)
#     pygame.draw.rect(s, col, pygame.Rect(10, 18, 20, 16), border_radius=5)
#     dst.blit(s, (cx - 20, cy - 20))
#
#
# def _draw_icon_jigsaw(dst, center, color, alpha=255):
#     cx, cy = center
#     a = clamp255(alpha)
#     col = (color[0], color[1], color[2], a)
#     s = pygame.Surface((40, 40), pygame.SRCALPHA)
#     pygame.draw.rect(s, col, pygame.Rect(10, 10, 18, 14), 2, border_radius=3)
#     pygame.draw.rect(s, col, pygame.Rect(14, 14, 18, 14), 2, border_radius=3)
#     pygame.draw.line(s, col, (16, 24), (22, 18), 2)
#     pygame.draw.line(s, col, (22, 18), (30, 26), 2)
#     dst.blit(s, (cx - 20, cy - 20))
#
#
# def _draw_icon_key(dst, center, color, alpha=255):
#     cx, cy = center
#     a = clamp255(alpha)
#     col = (color[0], color[1], color[2], a)
#     s = pygame.Surface((40, 40), pygame.SRCALPHA)
#     pygame.draw.circle(s, col, (14, 20), 6, 2)
#     pygame.draw.line(s, col, (20, 20), (34, 20), 2)
#     pygame.draw.line(s, col, (28, 20), (28, 26), 2)
#     pygame.draw.line(s, col, (32, 20), (32, 24), 2)
#     dst.blit(s, (cx - 20, cy - 20))
#
#
# def draw_modern_dock(dst, dock_rect: pygame.Rect, alpha: int):
#     _draw_round_rect_alpha(dst, dock_rect, (0, 0, 0), int(150 * (alpha / 255.0)), radius=22)
#     _draw_round_rect_outline_alpha(dst, dock_rect, (255, 255, 255), int(90 * (alpha / 255.0)), radius=22, width=2)
#
#
# def draw_modern_button(dst, rect: pygame.Rect, label: str, font, icon_fn, accent_rgb,
#                        active: bool, pressed: bool, alpha: int):
#     a = clamp255(alpha)
#     shadow_off = 3 if not pressed else 1
#     _draw_round_rect_alpha(dst, rect.move(0, shadow_off), (0, 0, 0), int(90 * (a / 255.0)), radius=16)
#
#     base = (18, 18, 18)
#     if active:
#         base = (26, 26, 26)
#     if pressed:
#         base = (12, 12, 12)
#
#     _draw_round_rect_alpha(dst, rect, base, int(210 * (a / 255.0)), radius=16)
#
#     strip = pygame.Rect(rect.x + 12, rect.y + rect.h - 10, rect.w - 24, 4)
#     _draw_round_rect_alpha(dst, strip, accent_rgb, int(200 * (a / 255.0)), radius=4)
#
#     _draw_round_rect_outline_alpha(dst, rect, (255, 255, 255), int(95 * (a / 255.0)), radius=16, width=2)
#
#     icon_center = (rect.x + 26, rect.centery)
#     icon_fn(dst, icon_center, accent_rgb, alpha=a)
#
#     txt = font.render(label, True, (240, 240, 240))
#     txt.set_alpha(a)
#     dst.blit(txt, (rect.x + 52, rect.centery - txt.get_height() // 2))
#
#
# def make_button(rect: pygame.Rect, label: str, color=(90, 90, 90)):
#     return {"rect": rect, "label": label, "color": color}
#
#
# def draw_button(screen, btn, font_main, font_small, active=False, small=False):
#     r = btn["rect"]
#     base = btn.get("color", (90, 90, 90))
#     bg = base if not active else lighten(base, 28)
#
#     pygame.draw.rect(screen, bg, r, border_radius=16)
#     pygame.draw.rect(screen, (230, 230, 230), r, 2, border_radius=16)
#
#     f = font_small if small else font_main
#     t = f.render(btn["label"], True, (255, 255, 255))
#     screen.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))
#
#
# def fade_to_black(screen, clock, dur_s: float = 0.18):
#     t0 = time.time()
#     w, h = screen.get_size()
#     ov = pygame.Surface((w, h), pygame.SRCALPHA)
#     while True:
#         now = time.time()
#         t = (now - t0) / max(0.001, dur_s)
#         if t >= 1.0:
#             break
#         a = int(255 * t)
#         ov.fill((0, 0, 0, a))
#         screen.blit(ov, (0, 0))
#         pygame.display.flip()
#         clock.tick(60)
#     screen.fill((0, 0, 0))
#     pygame.display.flip()
#
#
# def unlock_success_overlay(screen, clock, W, H, font_brand, font_small, snd_snap,
#                           msg="UNLOCKED", sub="Returning to menu...", hold_s=UNLOCK_SUCCESS_S,
#                           bg_frame_surf: Optional[pygame.Surface] = None):
#     play(snd_snap)
#     t0 = time.time()
#     overlay = pygame.Surface((W, H), pygame.SRCALPHA)
#     overlay.fill((0, 0, 0, 180))
#     while time.time() - t0 < hold_s:
#         for ev in pygame.event.get():
#             if ev.type == pygame.QUIT:
#                 raise SystemExit
#
#         if bg_frame_surf is not None:
#             screen.blit(bg_frame_surf, (0, 0))
#         else:
#             screen.fill(COLOR_BG)
#
#         screen.blit(overlay, (0, 0))
#
#         m = font_brand.render(msg, True, (255, 255, 255))
#         s = font_small.render(sub, True, (230, 230, 230))
#         screen.blit(m, (W // 2 - m.get_width() // 2, H // 2 - 40))
#         screen.blit(s, (W // 2 - s.get_width() // 2, H // 2 + 20))
#         pygame.display.flip()
#         clock.tick(60)
#
#
# def pin_overlay_loop(screen, clock, W, H, bg_frame_surf, font, font_small, snd_error, admin_pin: str) -> bool:
#     pin_input = ""
#     pin_error = ""
#     pin_error_t0 = 0.0
#
#     cancel_btn = make_button(pygame.Rect(16, 16, 170, 48), "CANCEL", color=(120, 120, 120))
#
#     KEYPAD_COLS = 3
#     KEYPAD_ROWS = 4
#     KEYS = ["1", "2", "3",
#             "4", "5", "6",
#             "7", "8", "9",
#             "C", "0", "OK"]
#
#     def submit() -> bool:
#         nonlocal pin_input, pin_error, pin_error_t0
#         if pin_input == admin_pin:
#             return True
#         pin_error = "Incorrect PIN"
#         pin_error_t0 = time.time()
#         pin_input = ""
#         play(snd_error)
#         return False
#
#     dim = pygame.Surface((W, H), pygame.SRCALPHA)
#     dim.fill((0, 0, 0, 205))
#
#     while True:
#         for ev in pygame.event.get():
#             if ev.type == pygame.QUIT:
#                 raise SystemExit
#
#             if ev.type == pygame.KEYDOWN:
#                 if ev.key == pygame.K_ESCAPE:
#                     return False
#                 if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
#                     if submit():
#                         return True
#                 elif ev.key == pygame.K_BACKSPACE:
#                     pin_input = pin_input[:-1]
#                 else:
#                     if ev.unicode.isdigit() and len(pin_input) < PIN_MAX_LEN:
#                         pin_input += ev.unicode
#
#             if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
#                 pos = event_pos(ev, W, H)
#                 if not pos:
#                     continue
#
#                 if cancel_btn["rect"].collidepoint(pos):
#                     return False
#
#                 pad_w = min(520, int(W * 0.42))
#                 pad_h = min(520, int(H * 0.62))
#                 pad_x = (W - pad_w) // 2
#                 pad_y = (H - pad_h) // 2 + 40
#                 cell_w = pad_w // KEYPAD_COLS
#                 cell_h = pad_h // KEYPAD_ROWS
#
#                 idx = 0
#                 for r in range(KEYPAD_ROWS):
#                     for c in range(KEYPAD_COLS):
#                         x = pad_x + c * cell_w + 8
#                         y = pad_y + r * cell_h + 8
#                         rect = pygame.Rect(x, y, cell_w - 16, cell_h - 16)
#                         if rect.collidepoint(pos):
#                             key = KEYS[idx]
#                             if key == "C":
#                                 pin_input = ""
#                             elif key == "OK":
#                                 if submit():
#                                     return True
#                             else:
#                                 if len(pin_input) < PIN_MAX_LEN:
#                                     pin_input += key
#                             break
#                         idx += 1
#
#         screen.blit(bg_frame_surf, (0, 0))
#         screen.blit(dim, (0, 0))
#
#         mx, my = pygame.mouse.get_pos()
#         draw_button(screen, cancel_btn, font, font_small, active=cancel_btn["rect"].collidepoint((mx, my)), small=True)
#
#         title = font.render("PIN UNLOCK", True, (255, 255, 255))
#         prompt = font_small.render("Enter PIN (keyboard or touchscreen keypad):", True, (230, 230, 230))
#         masked = "*" * len(pin_input)
#         entry = font.render(masked, True, (255, 255, 0))
#
#         screen.blit(title, (W // 2 - title.get_width() // 2, 80))
#         screen.blit(prompt, (W // 2 - prompt.get_width() // 2, 130))
#         screen.blit(entry, (W // 2 - entry.get_width() // 2, 165))
#
#         pad_w = min(520, int(W * 0.42))
#         pad_h = min(520, int(H * 0.62))
#         pad_x = (W - pad_w) // 2
#         pad_y = (H - pad_h) // 2 + 40
#         cell_w = pad_w // KEYPAD_COLS
#         cell_h = pad_h // KEYPAD_ROWS
#
#         pygame.draw.rect(screen, (35, 35, 35), pygame.Rect(pad_x, pad_y, pad_w, pad_h), border_radius=12)
#
#         rects = []
#         for r in range(KEYPAD_ROWS):
#             for c in range(KEYPAD_COLS):
#                 x = pad_x + c * cell_w + 8
#                 y = pad_y + r * cell_h + 8
#                 rects.append(pygame.Rect(x, y, cell_w - 16, cell_h - 16))
#
#         for i, r in enumerate(rects):
#             pygame.draw.rect(screen, (70, 70, 70), r, border_radius=10)
#             label = font.render(KEYS[i], True, (255, 255, 255))
#             screen.blit(label, (r.centerx - label.get_width() // 2, r.centery - label.get_height() // 2))
#
#         if pin_error and (time.time() - pin_error_t0) < 2.0:
#             err = font_small.render(pin_error, True, (255, 90, 90))
#             screen.blit(err, (W // 2 - err.get_width() // 2, pad_y + pad_h + 18))
#
#         tip = font_small.render("Enter/OK=submit, Backspace=delete, Esc/CANCEL=back.", True, (230, 230, 230))
#         screen.blit(tip, (W // 2 - tip.get_width() // 2, pad_y + pad_h + 50))
#
#         pygame.display.flip()
#         clock.tick(60)
#
#
# def calc_jig_snap_dist(W: int, BOARD_H: int, cols: int, rows: int) -> int:
#     cols = max(1, int(cols))
#     rows = max(1, int(rows))
#     cell_w = W // cols
#     cell_h = BOARD_H // rows
#     base = int(min(cell_w, cell_h) * JIG_SNAP_FRAC)
#     return max(JIG_SNAP_MIN, min(JIG_SNAP_MAX, base))
#
#
# def _make_jigsaw_edges(cols, rows):
#     h_edges = [
#         [{"dir": random.choice([-1, 1]), "off": random.uniform(-JIG_EDGE_OFF_FRAC, JIG_EDGE_OFF_FRAC)}
#          for _ in range(cols)]
#         for _ in range(rows - 1)
#     ]
#     v_edges = [
#         [{"dir": random.choice([-1, 1]), "off": random.uniform(-JIG_EDGE_OFF_FRAC, JIG_EDGE_OFF_FRAC)}
#          for _ in range(cols - 1)]
#         for _ in range(rows)
#     ]
#     return h_edges, v_edges
#
#
# def _apply_edge_circle(mask_surf, kind, center, radius):
#     if kind == 0:
#         return
#     if kind > 0:
#         pygame.draw.circle(mask_surf, (255, 255, 255, 255), center, radius)
#     else:
#         pygame.draw.circle(mask_surf, (255, 255, 255, 0), center, radius)
#
#
# def build_jigsaw_pieces(W, BOARD_H, board_surf, cols, rows):
#     cell_w = W // cols
#     cell_h = BOARD_H // rows
#
#     knob_r = int(min(cell_w, cell_h) * JIG_KNOB_FRAC)
#     margin = knob_r + 3
#
#     h_edges, v_edges = _make_jigsaw_edges(cols, rows)
#
#     pieces = []
#     for y in range(rows):
#         for x in range(cols):
#             if y == 0:
#                 top_kind, top_off = 0, 0.0
#             else:
#                 top_kind = -h_edges[y - 1][x]["dir"]
#                 top_off = h_edges[y - 1][x]["off"]
#
#             if y == rows - 1:
#                 bot_kind, bot_off = 0, 0.0
#             else:
#                 bot_kind = h_edges[y][x]["dir"]
#                 bot_off = h_edges[y][x]["off"]
#
#             if x == 0:
#                 left_kind, left_off = 0, 0.0
#             else:
#                 left_kind = -v_edges[y][x - 1]["dir"]
#                 left_off = v_edges[y][x - 1]["off"]
#
#             if x == cols - 1:
#                 right_kind, right_off = 0, 0.0
#             else:
#                 right_kind = v_edges[y][x]["dir"]
#                 right_off = v_edges[y][x]["off"]
#
#             pw = cell_w + 2 * margin
#             ph = cell_h + 2 * margin
#
#             mask_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
#             mask_surf.fill((255, 255, 255, 0))
#             pygame.draw.rect(mask_surf, (255, 255, 255, 255), pygame.Rect(margin, margin, cell_w, cell_h))
#
#             cx_top = margin + (cell_w // 2) + int(top_off * cell_w)
#             cy_top = margin
#             _apply_edge_circle(mask_surf, top_kind, (cx_top, cy_top), knob_r)
#
#             cx_bot = margin + (cell_w // 2) + int(bot_off * cell_w)
#             cy_bot = margin + cell_h
#             _apply_edge_circle(mask_surf, bot_kind, (cx_bot, cy_bot), knob_r)
#
#             cx_left = margin
#             cy_left = margin + (cell_h // 2) + int(left_off * cell_h)
#             _apply_edge_circle(mask_surf, left_kind, (cx_left, cy_left), knob_r)
#
#             cx_right = margin + cell_w
#             cy_right = margin + (cell_h // 2) + int(right_off * cell_h)
#             _apply_edge_circle(mask_surf, right_kind, (cx_right, cy_right), knob_r)
#
#             piece_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
#             piece_surf.blit(board_surf, (margin - x * cell_w, margin - y * cell_h))
#             piece_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
#
#             piece_mask = pygame.mask.from_surface(mask_surf)
#             correct_pos = (x * cell_w - margin, y * cell_h - margin)
#
#             pieces.append({
#                 "surf": piece_surf,
#                 "mask": piece_mask,
#                 "correct_pos": correct_pos,
#                 "pos": list(correct_pos),
#                 "locked": False,
#                 "fall_from": list(correct_pos),
#                 "fall_to": list(correct_pos),
#             })
#
#     return pieces
#
#
# def tray_random_pos_sized(W, tray_rect, obj_w, obj_h):
#     x0 = TRAY_MARGIN
#     x1 = W - TRAY_MARGIN - obj_w
#     y0 = tray_rect.top + TRAY_MARGIN
#     y1 = tray_rect.bottom - TRAY_MARGIN - obj_h
#     if x1 < x0:
#         x1 = x0
#     if y1 < y0:
#         y1 = y0
#     return (random.randint(x0, x1), random.randint(y0, y1))
#
#
# def jigsaw_all_locked(pieces):
#     return all(p.get("locked") for p in pieces)
#
#
# def _clip_surface_to_roundrect(src: pygame.Surface, size: Tuple[int, int], radius: int) -> pygame.Surface:
#     """Returns src scaled to size and clipped to a rounded rect (prevents 'image over weird rounded panel' look)."""
#     w, h = size
#     scaled = pygame.transform.smoothscale(src, (w, h))
#     out = pygame.Surface((w, h), pygame.SRCALPHA)
#     mask = pygame.Surface((w, h), pygame.SRCALPHA)
#     mask.fill((0, 0, 0, 0))
#     pygame.draw.rect(mask, (255, 255, 255, 255), pygame.Rect(0, 0, w, h), border_radius=radius)
#     out.blit(scaled, (0, 0))
#     out.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
#     return out
#
#
# # ---------------- LockApp ----------------
# class LockApp:
#     STATE_LOCK = "LOCK"
#     STATE_SQUARE = "SQUARE"
#     STATE_JIG_SELECT = "JIG_SELECT"
#     STATE_JIGSAW = "JIGSAW"
#
#     PUZ_INTRO = "INTRO"
#     PUZ_FALL = "FALL"
#     PUZ_PLAY = "PLAY"
#
#     JIG_INTRO = "INTRO"
#     JIG_FALL = "FALL"
#     JIG_PLAY = "PLAY"
#
#     LOCK_TRANS_NONE = None
#     LOCK_TRANS_BREAK = "BREAK"
#     LOCK_TRANS_FADEIN = "FADEIN"
#
#     def __init__(self, screen: Optional[pygame.Surface] = None, clock: Optional[pygame.time.Clock] = None,
#                  cfg: Optional[Dict[str, Any]] = None):
#         self.cfg = cfg or {}
#         ff = (self.cfg.get("feature_flags") or {})
#         sec = (self.cfg.get("security") or {})
#
#         self.admin_pin = str(sec.get("pi_pin", ADMIN_PIN_DEFAULT))
#         self.unlock_levels = max(1, int(ff.get("unlock_levels", 1)))
#         self.unlock_mode = str(ff.get("unlock_mode", "square")).lower().strip()  # square|jigsaw|mixed
#         self.endless_jigsaw = bool(ff.get("enable_endless_jigsaw", True))
#
#         self._shared = (screen is not None)
#
#         if not pygame.get_init():
#             pygame.init()
#         try:
#             if not pygame.font.get_init():
#                 pygame.font.init()
#         except Exception:
#             pass
#
#         try:
#             if not pygame.mixer.get_init():
#                 pygame.mixer.init()
#         except Exception:
#             pass
#
#         if screen is None:
#             self.screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)
#             pygame.display.set_caption("SPARC Lock")
#         else:
#             self.screen = screen
#
#         self.clock = clock or pygame.time.Clock()
#         self.W, self.H = self.screen.get_size()
#         pygame.mouse.set_visible(True)
#
#         self.font = pygame.font.SysFont(None, 52)
#         self.font_small = pygame.font.SysFont(None, 26)
#         self.font_brand = pygame.font.SysFont(None, 64)
#         self.font_brand2 = pygame.font.SysFont(None, 28)
#         self.font_dock = pygame.font.SysFont(None, 28)
#
#         self.snd_pick = load_sound(SND_PICK)
#         self.snd_drop = load_sound(SND_DROP)
#         self.snd_snap = load_sound(SND_SNAP)
#         self.snd_error = load_sound(SND_ERROR)
#
#         self.TRAY_H = int(self.H * TRAY_H_FRAC)
#         self.BOARD_H = self.H - self.TRAY_H
#         self.board_rect = pygame.Rect(0, 0, self.W, self.BOARD_H)
#         self.tray_rect = pygame.Rect(0, self.BOARD_H, self.W, self.TRAY_H)
#
#         self.images = self._load_images()
#         self.playlist = list(self.images)
#         if LOCK_BG_SHUFFLE:
#             random.shuffle(self.playlist)
#         else:
#             self.playlist.sort()
#         self.lock_idx = random.randrange(len(self.playlist)) if (LOCK_BG_RANDOM_START and self.playlist) else 0
#
#         self.lock_bg_big = None
#         self.lock_fg = None
#         self.lock_fg_rect = None
#         self.board_surf = None
#         self.img_name = ""
#
#         self.pan_x = 0.0
#         self.pan_y = 0.0
#         self.pan_vx = 0.0
#         self.pan_vy = 0.0
#
#         self.lock_cycle_t0 = time.time()
#         self.lock_trans = self.LOCK_TRANS_NONE
#         self.lock_trans_t0 = 0.0
#
#         self.break_style = "shatter"
#         self.break_dur = float(LOCK_BREAK_DURATIONS.get("shatter", 0.85))
#
#         self.lock_snapshot = pygame.Surface((self.W, self.H))
#         self.break_pieces: List[Dict[str, Any]] = []
#
#         if self.playlist:
#             self._set_image_by_index(self.lock_idx)
#
#         now = time.time()
#         self.lock_ui_visible_until = (now + LOCK_UI_AUTOHIDE_S) if not LOCK_UI_START_HIDDEN else 0.0
#         self.last_mouse_pos = pygame.mouse.get_pos()
#         self.ui_alpha = 0.0 if LOCK_UI_START_HIDDEN else 255.0
#
#         self._layout_lock_dock()
#         self.lock_pressed = None
#
#         self.state = self.STATE_LOCK
#
#         # Unlock progression
#         self.unlock_level = 0  # completed so far (square unlock path)
#
#         # Square puzzle state
#         self.tiles: List[Dict[str, Any]] = []
#         self.tile_w = 0
#         self.tile_h = 0
#         self.slot_positions: List[Tuple[int, int]] = []
#         self.drag_tile: Optional[Dict[str, Any]] = None
#         self.drag_ox = 0
#         self.drag_oy = 0
#         self.puz_stage = self.PUZ_INTRO
#         self.puz_t0 = 0.0
#
#         # Jigsaw state
#         self.jig_level = 0
#         self.jig_cols, self.jig_rows = JIG_DIFFICULTY_CHOICES[1][1], JIG_DIFFICULTY_CHOICES[1][2]
#         self.jig_snap_dist = calc_jig_snap_dist(self.W, self.BOARD_H, self.jig_cols, self.jig_rows)
#         self.jig_pieces: List[Dict[str, Any]] = []
#         self.jig_drag_piece: Optional[Dict[str, Any]] = None
#         self.jig_drag_ox = 0
#         self.jig_drag_oy = 0
#         self.jig_stage = self.JIG_INTRO
#         self.jig_t0 = 0.0
#
#         self.back_btn = make_button(pygame.Rect(16, 16, 160, 48), "BACK", color=(120, 120, 120))
#
#         self._running = True
#         self._result_unlocked = False
#
#         # Cached overlays (perf)
#         self._dim_full_180 = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
#         self._dim_full_180.fill((0, 0, 0, 180))
#
#     def _layout_lock_dock(self):
#         margin_bottom = 28
#         dock_w = min(780, int(self.W * 0.68))
#         dock_h = 96
#         dock_x = (self.W - dock_w) // 2
#         dock_y = self.H - dock_h - margin_bottom
#         self.dock_rect = pygame.Rect(dock_x, dock_y, dock_w, dock_h)
#
#         pad = 14
#         gap = 12
#         btn_h = 64
#         btn_y = dock_y + (dock_h - btn_h) // 2
#         btn_w = (dock_w - pad * 2 - gap * 2) // 3
#
#         self.btn_unlock = pygame.Rect(dock_x + pad + (btn_w + gap) * 0, btn_y, btn_w, btn_h)
#         self.btn_jigsaw = pygame.Rect(dock_x + pad + (btn_w + gap) * 1, btn_y, btn_w, btn_h)
#         self.btn_admin = pygame.Rect(dock_x + pad + (btn_w + gap) * 2, btn_y, btn_w, btn_h)
#
#     def _load_images(self):
#         if not os.path.isdir(IMAGE_DIR):
#             return []
#         imgs = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
#         return imgs
#
#     def _touch_lock_ui(self):
#         self.lock_ui_visible_until = time.time() + LOCK_UI_AUTOHIDE_S
#
#     def _lock_ui_visible(self) -> bool:
#         return time.time() < self.lock_ui_visible_until
#
#     def _set_image_by_index(self, idx: int):
#         if not self.playlist:
#             return
#         self.lock_idx = idx % len(self.playlist)
#         fname = self.playlist[self.lock_idx]
#         raw = safe_load_image(os.path.join(IMAGE_DIR, fname))
#         self.img_name = fname
#
#         if LOCK_VISIBLE_SCALE_MODE.lower() == "cover":
#             self.lock_fg = scale_cover(raw, self.W, self.H)
#             self.lock_fg_rect = self.lock_fg.get_rect(topleft=(0, 0))
#         else:
#             self.lock_fg, self.lock_fg_rect = scale_contain(raw, self.W, self.H)
#
#         big_w = self.W + LOCK_BG_PAN_RANGE_PX
#         big_h = self.H + LOCK_BG_PAN_RANGE_PX
#         bg = scale_cover(raw, big_w, big_h).convert()
#
#         if LOCK_BG_BLUR_METHOD.lower() == "hq":
#             bg = blur_surface_hq(bg, radius=LOCK_BG_HQ_RADIUS, downscale=LOCK_BG_HQ_DOWNSCALE)
#         else:
#             bg = blur_surface_once(bg, LOCK_BG_BLUR_DOWNSCALE).convert()
#
#         if LOCK_BG_DIM_ALPHA > 0:
#             dim = pygame.Surface((big_w, big_h), pygame.SRCALPHA)
#             dim.fill((0, 0, 0, clamp255(LOCK_BG_DIM_ALPHA)))
#             bg.blit(dim, (0, 0))
#
#         self.lock_bg_big = bg.convert()
#
#         if PUZZLE_BOARD_SCALE_MODE.lower() == "contain":
#             board_fit, rect = scale_contain(raw, self.W, self.BOARD_H)
#             board = pygame.Surface((self.W, self.BOARD_H))
#             board.fill((0, 0, 0))
#             board.blit(board_fit, rect)
#             self.board_surf = board.convert()
#         else:
#             self.board_surf = scale_cover(raw, self.W, self.BOARD_H).convert()
#
#         max_x = max(0, self.lock_bg_big.get_width() - self.W)
#         max_y = max(0, self.lock_bg_big.get_height() - self.H)
#         self.pan_x = float(random.randint(0, max_x)) if max_x else 0.0
#         self.pan_y = float(random.randint(0, max_y)) if max_y else 0.0
#
#         ang = random.uniform(0, math.tau)
#         self.pan_vx = math.cos(ang) * LOCK_BG_PAN_SPEED_PX_S
#         self.pan_vy = math.sin(ang) * LOCK_BG_PAN_SPEED_PX_S
#
#         self.lock_cycle_t0 = time.time()
#
#     def _advance_image(self):
#         if not self.playlist:
#             return
#         nxt = self.lock_idx + 1
#         if nxt >= len(self.playlist):
#             nxt = 0
#             if LOCK_BG_SHUFFLE:
#                 random.shuffle(self.playlist)
#         self._set_image_by_index(nxt)
#
#     def _update_pan(self, dt: float):
#         if not self.lock_bg_big:
#             return
#         max_x = max(0, self.lock_bg_big.get_width() - self.W)
#         max_y = max(0, self.lock_bg_big.get_height() - self.H)
#
#         self.pan_x += self.pan_vx * dt
#         self.pan_y += self.pan_vy * dt
#
#         if max_x > 0:
#             if self.pan_x < 0:
#                 self.pan_x = 0.0
#                 self.pan_vx = abs(self.pan_vx)
#             elif self.pan_x > max_x:
#                 self.pan_x = float(max_x)
#                 self.pan_vx = -abs(self.pan_vx)
#         else:
#             self.pan_x = 0.0
#
#         if max_y > 0:
#             if self.pan_y < 0:
#                 self.pan_y = 0.0
#                 self.pan_vy = abs(self.pan_vy)
#             elif self.pan_y > max_y:
#                 self.pan_y = float(max_y)
#                 self.pan_vy = -abs(self.pan_vy)
#         else:
#             self.pan_y = 0.0
#
#     def _draw_lock_frame_to(self, target_surf: pygame.Surface):
#         if self.lock_bg_big:
#             max_x = max(0, self.lock_bg_big.get_width() - self.W)
#             max_y = max(0, self.lock_bg_big.get_height() - self.H)
#             vx = int(max(0, min(max_x, self.pan_x)))
#             vy = int(max(0, min(max_y, self.pan_y)))
#             view = pygame.Rect(vx, vy, self.W, self.H)
#             target_surf.blit(self.lock_bg_big.subsurface(view), (0, 0))
#         else:
#             target_surf.fill((0, 0, 0))
#
#         if self.lock_fg and self.lock_fg_rect:
#             target_surf.blit(self.lock_fg, self.lock_fg_rect)
#
#     def _build_lock_frame_surface(self) -> pygame.Surface:
#         surf = pygame.Surface((self.W, self.H))
#         self._draw_lock_frame_to(surf)
#         return surf
#
#     def _draw_status_bar(self):
#         if not SHOW_STATUS_BAR:
#             return
#         bar = pygame.Surface((self.W, STATUS_BAR_H), pygame.SRCALPHA)
#         bar.fill((0, 0, 0, 140))
#         self.screen.blit(bar, (0, 0))
#         now = datetime.datetime.now()
#         txt = now.strftime("%a %b %d   %I:%M %p").lstrip("0")
#         t = self.font_small.render(txt, True, (230, 230, 230))
#         self.screen.blit(t, (self.W - t.get_width() - 16, (STATUS_BAR_H - t.get_height()) // 2))
#
#     def _choose_break_style(self) -> str:
#         if LOCK_TRANSITION_STYLE == "random":
#             return random.choice(LOCK_TRANSITION_STYLES)
#         if LOCK_TRANSITION_STYLE in LOCK_TRANSITION_STYLES:
#             return LOCK_TRANSITION_STYLE
#         return "shatter"
#
#     def _make_break_pieces(self, snap: pygame.Surface, style: str) -> List[Dict[str, Any]]:
#         pieces: List[Dict[str, Any]] = []
#         W, H = self.W, self.H
#
#         if style == "blinds":
#             n = 16
#             tile_w = max(16, W // n)
#             for i in range(n):
#                 x = i * tile_w
#                 w = tile_w if i < n - 1 else (W - x)
#                 rect = pygame.Rect(x, 0, w, H)
#                 surf = snap.subsurface(rect).copy()
#                 dir_sign = -1 if (i % 2 == 0) else 1
#                 vx = dir_sign * random.uniform(250, 450)
#                 pieces.append({
#                     "surf": surf,
#                     "pos": [float(rect.x), float(rect.y)],
#                     "vel": [vx, random.uniform(-40, 40)],
#                     "rot": 0.0,
#                     "ang": random.uniform(-30, 30),
#                 })
#             return pieces
#
#         target = LOCK_SHATTER_TILE_TARGET
#         cols = int(math.sqrt(target * (W / max(1.0, H))))
#         cols = max(6, min(30, cols))
#         rows = max(6, min(24, int(target / cols)))
#         tile_w = max(18, W // cols)
#         tile_h = max(18, H // rows)
#
#         for y in range(0, H, tile_h):
#             for x in range(0, W, tile_w):
#                 rect = pygame.Rect(x, y, min(tile_w, W - x), min(tile_h, H - y))
#                 surf = snap.subsurface(rect).copy()
#                 cx = rect.centerx - W / 2.0
#                 cy = rect.centery - H / 2.0
#
#                 if style == "explode":
#                     mag = random.uniform(220, 520)
#                     ang = math.atan2(cy, cx) + random.uniform(-0.25, 0.25)
#                     vx = math.cos(ang) * mag
#                     vy = math.sin(ang) * mag
#                 elif style == "drop":
#                     vx = random.uniform(-80, 80)
#                     vy = random.uniform(50, 160)
#                 else:
#                     vx = random.uniform(-260, 260) + (cx * 0.25)
#                     vy = random.uniform(-180, 120) + (cy * 0.20)
#
#                 rot = random.uniform(-35, 35)
#                 pieces.append({
#                     "surf": surf,
#                     "pos": [float(rect.x), float(rect.y)],
#                     "vel": [vx, vy],
#                     "rot": 0.0,
#                     "ang": rot,
#                 })
#
#         return pieces
#
#     def _begin_lock_transition(self):
#         self.lock_snapshot = self._build_lock_frame_surface()
#         self.break_style = self._choose_break_style()
#         self.break_dur = float(LOCK_BREAK_DURATIONS.get(self.break_style, 0.85))
#         self.lock_trans = self.LOCK_TRANS_BREAK
#         self.lock_trans_t0 = time.time()
#         self.break_pieces = self._make_break_pieces(self.lock_snapshot, self.break_style)
#
#     def _draw_break(self, t: float):
#         self.screen.fill((0, 0, 0))
#         dt = 1.0 / 60.0
#         grav = LOCK_SHATTER_GRAVITY
#
#         for p in self.break_pieces:
#             vx, vy = p["vel"]
#             if self.break_style in ("shatter", "drop"):
#                 vy += grav * dt * (0.70 if self.break_style == "drop" else 0.40)
#                 p["vel"][1] = vy
#
#             p["pos"][0] += vx * dt
#             p["pos"][1] += vy * dt
#
#             damp = 1.0 - (0.12 * t)
#             p["vel"][0] *= damp
#             p["vel"][1] *= damp
#
#             p["rot"] += p["ang"] * dt
#
#             surf = p["surf"]
#             if abs(p["rot"]) > 0.5:
#                 rs = pygame.transform.rotozoom(surf, p["rot"], 1.0)
#                 r = rs.get_rect(center=(p["pos"][0] + surf.get_width() / 2, p["pos"][1] + surf.get_height() / 2))
#                 self.screen.blit(rs, r.topleft)
#             else:
#                 self.screen.blit(surf, (p["pos"][0], p["pos"][1]))
#
#         ov = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
#         ov.fill((0, 0, 0, int(220 * _ease_in_quad(t))))
#         self.screen.blit(ov, (0, 0))
#
#     def _draw_fadein(self, t: float):
#         self._draw_lock_frame_to(self.screen)
#         a = int(255 * (1.0 - _ease_out_cubic(t)))
#         ov = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
#         ov.fill((0, 0, 0, a))
#         self.screen.blit(ov, (0, 0))
#
#     # ---------- Square puzzle ----------
#     def _square_setup(self):
#         if self.board_surf is None:
#             return
#
#         margin = 40
#         usable_w = self.W - margin * 2
#         usable_h = self.BOARD_H - margin * 2
#         cols, rows = GRID_X, GRID_Y
#
#         self.tile_w = usable_w // cols
#         self.tile_h = usable_h // rows
#
#         self.slot_positions = []
#         for j in range(rows):
#             for i in range(cols):
#                 sx = margin + i * self.tile_w
#                 sy = margin + j * self.tile_h
#                 self.slot_positions.append((sx, sy))
#
#         board_scaled = pygame.transform.smoothscale(self.board_surf, (usable_w, usable_h))
#         tiles: List[Dict[str, Any]] = []
#         for j in range(rows):
#             for i in range(cols):
#                 src_rect = pygame.Rect(i * self.tile_w, j * self.tile_h, self.tile_w, self.tile_h)
#                 surf = board_scaled.subsurface(src_rect).copy()
#                 tile = pygame.Surface((self.tile_w, self.tile_h), pygame.SRCALPHA)
#                 tile.blit(surf, (0, 0))
#                 pygame.draw.rect(tile, (255, 255, 255, 70), pygame.Rect(0, 0, self.tile_w, self.tile_h), 2, border_radius=10)
#
#                 correct = self.slot_positions[j * cols + i]
#                 pos = tray_random_pos_sized(self.W, self.tray_rect, self.tile_w, self.tile_h)
#                 tiles.append({
#                     "surf": tile,
#                     "correct": correct,
#                     "pos": [float(pos[0]), float(pos[1])],
#                     "locked": False,
#                     "fall_from": [float(pos[0]), float(-self.tile_h - random.randint(20, 400))],
#                     "fall_to": [float(pos[0]), float(pos[1])],
#                 })
#
#         random.shuffle(tiles)
#         self.tiles = tiles
#         self.drag_tile = None
#         self.puz_stage = self.PUZ_INTRO
#         self.puz_t0 = time.time()
#
#     def _square_all_locked(self) -> bool:
#         return all(t["locked"] for t in self.tiles)
#
#     def _square_slot_occupied(self, slot_xy: Tuple[int, int]) -> bool:
#         for t in self.tiles:
#             if t["locked"] and tuple(map(int, t["pos"])) == slot_xy:
#                 return True
#         return False
#
#     def _square_find_tile_at(self, x: int, y: int) -> Optional[Dict[str, Any]]:
#         for t in reversed(self.tiles):
#             if t["locked"]:
#                 continue
#             r = pygame.Rect(int(t["pos"][0]), int(t["pos"][1]), self.tile_w, self.tile_h)
#             if r.collidepoint((x, y)):
#                 return t
#         return None
#
#     def _square_update_stage(self):
#         now = time.time()
#         if self.puz_stage == self.PUZ_INTRO:
#             if (now - self.puz_t0) >= PUZ_INTRO_HOLD_S:
#                 for t in self.tiles:
#                     pos = tray_random_pos_sized(self.W, self.tray_rect, self.tile_w, self.tile_h)
#                     t["fall_from"] = [float(pos[0]), float(-self.tile_h - random.randint(20, 400))]
#                     t["fall_to"] = [float(pos[0]), float(pos[1])]
#                     t["pos"] = [t["fall_from"][0], t["fall_from"][1]]
#                 self.puz_stage = self.PUZ_FALL
#                 self.puz_t0 = now
#
#         elif self.puz_stage == self.PUZ_FALL:
#             t = (now - self.puz_t0) / max(0.001, PUZ_FALL_S)
#             if t >= 1.0:
#                 for tile in self.tiles:
#                     tile["pos"] = [tile["fall_to"][0], tile["fall_to"][1]]
#                 self.puz_stage = self.PUZ_PLAY
#                 self.puz_t0 = now
#             else:
#                 tt = _ease_out_cubic(t)
#                 for tile in self.tiles:
#                     fx, fy = tile["fall_from"]
#                     tx, ty = tile["fall_to"]
#                     tile["pos"][0] = fx + (tx - fx) * tt
#                     tile["pos"][1] = fy + (ty - fy) * tt
#
#     def _square_draw(self):
#         # Important: keep unlock modes on clean UI (no lock image as background)
#         self.screen.fill(COLOR_BG)
#
#         header = self.font_small.render(
#             f"Unlock Puzzle  •  Level {self.unlock_level + 1} / {self.unlock_levels}",
#             True,
#             (230, 230, 230),
#         )
#         self.screen.blit(header, (18, 18))
#
#         board_panel = pygame.Rect(18, 56, self.W - 36, self.BOARD_H - 72)
#         pygame.draw.rect(self.screen, (10, 10, 10), board_panel, border_radius=22)
#         pygame.draw.rect(self.screen, (110, 110, 110), board_panel, 2, border_radius=22)
#
#         margin = 40
#         cols, rows = GRID_X, GRID_Y
#         usable_w = self.W - margin * 2
#         usable_h = self.BOARD_H - margin * 2
#         tile_w = usable_w // cols
#         tile_h = usable_h // rows
#
#         for j in range(rows):
#             for i in range(cols):
#                 sx = margin + i * tile_w
#                 sy = margin + j * tile_h
#                 slot_rect = pygame.Rect(sx, sy, tile_w, tile_h)
#                 pygame.draw.rect(self.screen, (55, 55, 55), slot_rect, 2, border_radius=10)
#
#         pygame.draw.rect(self.screen, COLOR_TRAY, self.tray_rect)
#         pygame.draw.line(self.screen, COLOR_LINE, (0, self.BOARD_H), (self.W, self.BOARD_H), 2)
#
#         tray_label = self.font_small.render("Drag pieces into place.", True, (220, 220, 220))
#         self.screen.blit(tray_label, (18, self.BOARD_H + 10))
#
#         mx, my = pygame.mouse.get_pos()
#         draw_button(self.screen, self.back_btn, self.font_small, self.font_small,
#                     active=self.back_btn["rect"].collidepoint((mx, my)), small=True)
#
#         for t in self.tiles:
#             self.screen.blit(t["surf"], (t["pos"][0], t["pos"][1]))
#
#         # Intro reference: clipped to the board panel shape (no “image over rounded rectangle” effect)
#         if self.puz_stage == self.PUZ_INTRO and self.board_surf is not None:
#             inner = board_panel.inflate(-14, -14)
#             ref = _clip_surface_to_roundrect(self.board_surf, (inner.w, inner.h), radius=18)
#             self.screen.blit(ref, inner.topleft)
#             ov = pygame.Surface((inner.w, inner.h), pygame.SRCALPHA)
#             ov.fill((0, 0, 0, 140))
#             self.screen.blit(ov, inner.topleft)
#             msg = self.font_small.render("Memorize the picture...", True, (240, 240, 240))
#             self.screen.blit(msg, (self.W // 2 - msg.get_width() // 2, board_panel.bottom - 32))
#
#     def _complete_unlock_level_or_finish(self):
#         self.unlock_level += 1
#         if self.unlock_level >= self.unlock_levels:
#             bg = self.screen.copy()
#             unlock_success_overlay(
#                 self.screen, self.clock, self.W, self.H, self.font_brand, self.font_small,
#                 self.snd_snap, msg="UNLOCKED", sub="Returning to menu...", hold_s=UNLOCK_SUCCESS_S,
#                 bg_frame_surf=bg
#             )
#             fade_to_black(self.screen, self.clock, 0.18)
#             self._result_unlocked = True
#             self._running = False
#             return
#
#         bg = self.screen.copy()
#         unlock_success_overlay(
#             self.screen, self.clock, self.W, self.H, self.font_brand, self.font_small,
#             self.snd_snap,
#             msg=f"LEVEL {self.unlock_level} COMPLETE",
#             sub="Next puzzle...",
#             hold_s=0.70,
#             bg_frame_surf=bg
#         )
#         # Next level uses next image for variety
#         if self.playlist:
#             self._advance_image()
#         self._square_setup()
#         self.state = self.STATE_SQUARE
#
#     def _square_handle_event(self, ev):
#         if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
#             self.state = self.STATE_LOCK
#             self.lock_pressed = None
#             return
#
#         if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
#             pos = event_pos(ev, self.W, self.H)
#             if not pos:
#                 return
#             x, y = pos
#
#             if self.back_btn["rect"].collidepoint((x, y)):
#                 self.state = self.STATE_LOCK
#                 self.lock_pressed = None
#                 return
#
#             if self.puz_stage != self.PUZ_PLAY:
#                 return
#
#             t = self._square_find_tile_at(x, y)
#             if t:
#                 play(self.snd_pick)
#                 self.drag_tile = t
#                 self.drag_ox = x - int(t["pos"][0])
#                 self.drag_oy = y - int(t["pos"][1])
#                 self.tiles.remove(t)
#                 self.tiles.append(t)
#
#         if ev.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
#             if self.drag_tile is None:
#                 return
#             pos = event_pos(ev, self.W, self.H)
#             if not pos:
#                 return
#             x, y = pos
#             self.drag_tile["pos"][0] = float(x - self.drag_ox)
#             self.drag_tile["pos"][1] = float(y - self.drag_oy)
#
#         if ev.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
#             if self.drag_tile is None:
#                 return
#             t = self.drag_tile
#             self.drag_tile = None
#             play(self.snd_drop)
#
#             cx = int(t["pos"][0] + self.tile_w / 2)
#             cy = int(t["pos"][1] + self.tile_h / 2)
#
#             slot_x, slot_y = t["correct"]
#             slot_c = (slot_x + self.tile_w // 2, slot_y + self.tile_h // 2)
#
#             if dist2((cx, cy), slot_c) <= (SNAP_DIST * SNAP_DIST) and not self._square_slot_occupied((slot_x, slot_y)):
#                 t["pos"][0] = float(slot_x)
#                 t["pos"][1] = float(slot_y)
#                 t["locked"] = True
#                 play(self.snd_snap)
#
#                 if self._square_all_locked():
#                     self._complete_unlock_level_or_finish()
#
#     # ---------- Jigsaw ----------
#     def _jigsaw_setup(self, cols: int, rows: int):
#         if self.board_surf is None:
#             return
#         self.jig_cols, self.jig_rows = cols, rows
#         self.jig_snap_dist = calc_jig_snap_dist(self.W, self.BOARD_H, cols, rows)
#
#         pieces = build_jigsaw_pieces(self.W, self.BOARD_H, self.board_surf, cols, rows)
#         for p in pieces:
#             w, h = p["surf"].get_size()
#             pos = tray_random_pos_sized(self.W, self.tray_rect, w, h)
#             p["fall_from"] = [float(pos[0]), float(-h - random.randint(20, 400))]
#             p["fall_to"] = [float(pos[0]), float(pos[1])]
#             p["pos"] = [p["fall_from"][0], p["fall_from"][1]]
#             p["locked"] = False
#         random.shuffle(pieces)
#
#         self.jig_pieces = pieces
#         self.jig_drag_piece = None
#         self.jig_stage = self.JIG_INTRO
#         self.jig_t0 = time.time()
#
#     def _jigsaw_find_piece_at(self, x: int, y: int) -> Optional[Dict[str, Any]]:
#         for p in reversed(self.jig_pieces):
#             if p.get("locked"):
#                 continue
#             px, py = int(p["pos"][0]), int(p["pos"][1])
#             lx, ly = x - px, y - py
#             if lx < 0 or ly < 0:
#                 continue
#             if lx >= p["surf"].get_width() or ly >= p["surf"].get_height():
#                 continue
#             if p["mask"].get_at((lx, ly)):
#                 return p
#         return None
#
#     def _jigsaw_update_stage(self):
#         now = time.time()
#         if self.jig_stage == self.JIG_INTRO:
#             if (now - self.jig_t0) >= JIG_INTRO_HOLD_S:
#                 self.jig_stage = self.JIG_FALL
#                 self.jig_t0 = now
#
#         elif self.jig_stage == self.JIG_FALL:
#             t = (now - self.jig_t0) / max(0.001, JIG_FALL_S)
#             if t >= 1.0:
#                 for p in self.jig_pieces:
#                     p["pos"] = [p["fall_to"][0], p["fall_to"][1]]
#                 self.jig_stage = self.JIG_PLAY
#                 self.jig_t0 = now
#             else:
#                 tt = _ease_out_cubic(t)
#                 for p in self.jig_pieces:
#                     fx, fy = p["fall_from"]
#                     tx, ty = p["fall_to"]
#                     p["pos"][0] = fx + (tx - fx) * tt
#                     p["pos"][1] = fy + (ty - fy) * tt
#
#     def _jigsaw_draw(self):
#         self.screen.fill(COLOR_BG)
#
#         header = self.font_small.render(
#             f"Jigsaw  {self.jig_cols} x {self.jig_rows}  •  Level {self.jig_level + 1}",
#             True,
#             (230, 230, 230),
#         )
#         self.screen.blit(header, (18, 18))
#
#         board_panel = pygame.Rect(18, 56, self.W - 36, self.BOARD_H - 72)
#         pygame.draw.rect(self.screen, (10, 10, 10), board_panel, border_radius=22)
#         pygame.draw.rect(self.screen, (110, 110, 110), board_panel, 2, border_radius=22)
#
#         if self.jig_stage == self.JIG_INTRO and self.board_surf is not None:
#             inner = board_panel.inflate(-14, -14)
#             ref = _clip_surface_to_roundrect(self.board_surf, (inner.w, inner.h), radius=18)
#             self.screen.blit(ref, inner.topleft)
#             ov = pygame.Surface((inner.w, inner.h), pygame.SRCALPHA)
#             ov.fill((0, 0, 0, 155))
#             self.screen.blit(ov, inner.topleft)
#
#         pygame.draw.rect(self.screen, COLOR_TRAY, self.tray_rect)
#         pygame.draw.line(self.screen, COLOR_LINE, (0, self.BOARD_H), (self.W, self.BOARD_H), 2)
#
#         tray_label = self.font_small.render("Drag pieces into place (snaps when close).", True, (220, 220, 220))
#         self.screen.blit(tray_label, (18, self.BOARD_H + 10))
#
#         mx, my = pygame.mouse.get_pos()
#         draw_button(self.screen, self.back_btn, self.font_small, self.font_small,
#                     active=self.back_btn["rect"].collidepoint((mx, my)), small=True)
#
#         for p in self.jig_pieces:
#             self.screen.blit(p["surf"], (p["pos"][0], p["pos"][1]))
#
#     def _jigsaw_on_solved(self):
#         self.jig_level += 1
#         bg = self.screen.copy()
#         unlock_success_overlay(
#             self.screen, self.clock, self.W, self.H, self.font_brand, self.font_small,
#             self.snd_snap,
#             msg=f"LEVEL {self.jig_level} COMPLETE",
#             sub="Next jigsaw...",
#             hold_s=JIG_SOLVED_HOLD_S,
#             bg_frame_surf=bg
#         )
#         fade_to_black(self.screen, self.clock, 0.12)
#
#         if self.playlist:
#             self._advance_image()
#
#         # Endless mode: always continue
#         if self.endless_jigsaw:
#             self._jigsaw_setup(self.jig_cols, self.jig_rows)
#             self.state = self.STATE_JIGSAW
#             return
#
#         # Non-endless: solving jigsaw unlocks (if you ever choose to use it that way)
#         self._result_unlocked = True
#         self._running = False
#
#     def _jigsaw_handle_event(self, ev):
#         if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
#             self.state = self.STATE_LOCK
#             self.lock_pressed = None
#             return
#
#         if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
#             pos = event_pos(ev, self.W, self.H)
#             if not pos:
#                 return
#             x, y = pos
#
#             if self.back_btn["rect"].collidepoint((x, y)):
#                 self.state = self.STATE_LOCK
#                 self.lock_pressed = None
#                 return
#
#             if self.jig_stage != self.JIG_PLAY:
#                 return
#
#             p = self._jigsaw_find_piece_at(x, y)
#             if p:
#                 play(self.snd_pick)
#                 self.jig_drag_piece = p
#                 self.jig_drag_ox = x - int(p["pos"][0])
#                 self.jig_drag_oy = y - int(p["pos"][1])
#                 self.jig_pieces.remove(p)
#                 self.jig_pieces.append(p)
#
#         if ev.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
#             if self.jig_drag_piece is None:
#                 return
#             pos = event_pos(ev, self.W, self.H)
#             if not pos:
#                 return
#             x, y = pos
#             self.jig_drag_piece["pos"][0] = float(x - self.jig_drag_ox)
#             self.jig_drag_piece["pos"][1] = float(y - self.jig_drag_oy)
#
#         if ev.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
#             if self.jig_drag_piece is None:
#                 return
#             p = self.jig_drag_piece
#             self.jig_drag_piece = None
#             play(self.snd_drop)
#
#             correct = p["correct_pos"]
#             px, py = p["pos"]
#             dx = (px - correct[0])
#             dy = (py - correct[1])
#             if (dx * dx + dy * dy) <= (self.jig_snap_dist * self.jig_snap_dist):
#                 p["pos"][0] = float(correct[0])
#                 p["pos"][1] = float(correct[1])
#                 p["locked"] = True
#                 play(self.snd_snap)
#
#                 if jigsaw_all_locked(self.jig_pieces):
#                     self._jigsaw_on_solved()
#
#     # ---------- Lock state ----------
#     def _draw_lock(self):
#         if self.lock_trans == self.LOCK_TRANS_BREAK:
#             t = (time.time() - self.lock_trans_t0) / max(0.001, self.break_dur)
#             if t >= 1.0:
#                 self._advance_image()
#                 self.lock_trans = self.LOCK_TRANS_FADEIN
#                 self.lock_trans_t0 = time.time()
#                 self._draw_fadein(0.0)
#             else:
#                 self._draw_break(t)
#         elif self.lock_trans == self.LOCK_TRANS_FADEIN:
#             t = (time.time() - self.lock_trans_t0) / max(0.001, LOCK_FADEIN_S)
#             if t >= 1.0:
#                 self.lock_trans = self.LOCK_TRANS_NONE
#                 self._draw_lock_frame_to(self.screen)
#             else:
#                 self._draw_fadein(t)
#         else:
#             self._draw_lock_frame_to(self.screen)
#
#         title = self.font_brand.render(BRAND_TEXT, True, (255, 255, 255))
#         subtitle = self.font_brand2.render(BRAND_SUB, True, (230, 230, 230))
#         self.screen.blit(title, (30, 70))
#         self.screen.blit(subtitle, (30, 135))
#
#         self._draw_status_bar()
#
#         target = 255.0 if self._lock_ui_visible() else 0.0
#         dt = 1.0 / 60.0
#         step = (255.0 / max(0.001, LOCK_UI_FADE_S)) * dt
#         if self.ui_alpha < target:
#             self.ui_alpha = min(target, self.ui_alpha + step)
#         elif self.ui_alpha > target:
#             self.ui_alpha = max(target, self.ui_alpha - step)
#
#         a = int(self.ui_alpha)
#         if a > 0:
#             draw_modern_dock(self.screen, self.dock_rect, a)
#
#             mx, my = pygame.mouse.get_pos()
#             over_unlock = self.btn_unlock.collidepoint((mx, my))
#             over_jigsaw = self.btn_jigsaw.collidepoint((mx, my))
#             over_admin = self.btn_admin.collidepoint((mx, my))
#
#             pressed_unlock = (self.lock_pressed == "unlock")
#             pressed_jigsaw = (self.lock_pressed == "jigsaw")
#             pressed_admin = (self.lock_pressed == "admin")
#
#             draw_modern_button(self.screen, self.btn_unlock, "Unlock", self.font_dock,
#                                _draw_icon_lock, ACCENT_UNLOCK, over_unlock, pressed_unlock, a)
#             draw_modern_button(self.screen, self.btn_jigsaw, "Jigsaw", self.font_dock,
#                                _draw_icon_jigsaw, ACCENT_JIGSAW, over_jigsaw, pressed_jigsaw, a)
#             draw_modern_button(self.screen, self.btn_admin, "PIN", self.font_dock,
#                                _draw_icon_key, ACCENT_ADMIN, over_admin, pressed_admin, a)
#
#     def _lock_handle_event(self, ev):
#         if ev.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
#             pos = event_pos(ev, self.W, self.H)
#             if pos:
#                 x, y = pos
#                 lx, ly = self.last_mouse_pos
#                 if abs(x - lx) + abs(y - ly) >= LOCK_UI_MOUSE_MOVE_THRESH:
#                     self._touch_lock_ui()
#                 self.last_mouse_pos = (x, y)
#
#         if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
#             self._touch_lock_ui()
#             pos = event_pos(ev, self.W, self.H)
#             if not pos:
#                 return
#             x, y = pos
#
#             if self.ui_alpha >= 40:
#                 if self.btn_unlock.collidepoint((x, y)):
#                     self.lock_pressed = "unlock"
#                     play(self.snd_pick)
#                 elif self.btn_jigsaw.collidepoint((x, y)):
#                     self.lock_pressed = "jigsaw"
#                     play(self.snd_pick)
#                 elif self.btn_admin.collidepoint((x, y)):
#                     self.lock_pressed = "admin"
#                     play(self.snd_pick)
#                 else:
#                     self.lock_pressed = None
#
#         if ev.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
#             pos = event_pos(ev, self.W, self.H)
#             if not pos:
#                 self.lock_pressed = None
#                 return
#             x, y = pos
#
#             pressed = self.lock_pressed
#             self.lock_pressed = None
#             if pressed is None:
#                 return
#
#             if pressed == "unlock" and self.btn_unlock.collidepoint((x, y)):
#                 # Unlock always uses square puzzle progression (N levels)
#                 self.unlock_level = 0
#                 self._square_setup()
#                 self.state = self.STATE_SQUARE
#                 return
#
#             if pressed == "jigsaw" and self.btn_jigsaw.collidepoint((x, y)):
#                 # Jigsaw button goes to difficulty select for endless mode
#                 self.state = self.STATE_JIG_SELECT
#                 return
#
#             if pressed == "admin" and self.btn_admin.collidepoint((x, y)):
#                 bg = self.screen.copy()
#                 ok = pin_overlay_loop(
#                     self.screen, self.clock, self.W, self.H, bg,
#                     self.font, self.font_small, self.snd_error,
#                     admin_pin=self.admin_pin
#                 )
#                 if ok:
#                     bg2 = self.screen.copy()
#                     unlock_success_overlay(self.screen, self.clock, self.W, self.H,
#                                           self.font_brand, self.font_small, self.snd_snap,
#                                           bg_frame_surf=bg2)
#                     fade_to_black(self.screen, self.clock, 0.18)
#                     self._result_unlocked = True
#                     self._running = False
#                 return
#
#         if ev.type == pygame.KEYDOWN:
#             self._touch_lock_ui()
#             if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
#                 self.unlock_level = 0
#                 self._square_setup()
#                 self.state = self.STATE_SQUARE
#                 return
#             if ev.key == pygame.K_j:
#                 self.state = self.STATE_JIG_SELECT
#                 return
#
#     def run(self) -> bool:
#         if not self.playlist:
#             self.lock_trans = self.LOCK_TRANS_NONE
#
#         selected_jig = 1
#         prev_time = time.time()
#
#         while self._running:
#             now = time.time()
#             dt = now - prev_time
#             prev_time = now
#
#             if self.state == self.STATE_LOCK:
#                 self._update_pan(dt)
#                 if self.lock_trans == self.LOCK_TRANS_NONE and LOCK_TRANSITION_ENABLE and self.playlist:
#                     if (now - self.lock_cycle_t0) >= LOCK_BG_CYCLE_S:
#                         self._begin_lock_transition()
#
#             for ev in pygame.event.get():
#                 if ev.type == pygame.QUIT:
#                     self._running = False
#                     break
#
#                 if self.state == self.STATE_LOCK:
#                     self._lock_handle_event(ev)
#
#                 elif self.state == self.STATE_SQUARE:
#                     self._square_handle_event(ev)
#
#                 elif self.state == self.STATE_JIG_SELECT:
#                     if ev.type == pygame.KEYDOWN:
#                         if ev.key == pygame.K_ESCAPE:
#                             self.state = self.STATE_LOCK
#                             continue
#                         if ev.key == pygame.K_UP:
#                             selected_jig = max(0, selected_jig - 1)
#                         if ev.key == pygame.K_DOWN:
#                             selected_jig = min(len(JIG_DIFFICULTY_CHOICES) - 1, selected_jig + 1)
#                         if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
#                             _, c, r = JIG_DIFFICULTY_CHOICES[selected_jig]
#                             self.jig_level = 0
#                             self._jigsaw_setup(c, r)
#                             self.state = self.STATE_JIGSAW
#                             continue
#
#                     if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
#                         pos = event_pos(ev, self.W, self.H)
#                         if pos:
#                             x, y = pos
#                             if self.back_btn["rect"].collidepoint((x, y)):
#                                 self.state = self.STATE_LOCK
#                                 continue
#
#                             row_h = 70
#                             gap = 12
#                             start_y = 170
#                             for i in range(len(JIG_DIFFICULTY_CHOICES)):
#                                 rect = pygame.Rect(int(self.W * 0.18), start_y + i * (row_h + gap),
#                                                    int(self.W * 0.64), row_h)
#                                 if rect.collidepoint((x, y)):
#                                     selected_jig = i
#                                     _, c, r = JIG_DIFFICULTY_CHOICES[selected_jig]
#                                     self.jig_level = 0
#                                     self._jigsaw_setup(c, r)
#                                     self.state = self.STATE_JIGSAW
#                                     break
#
#                 elif self.state == self.STATE_JIGSAW:
#                     self._jigsaw_handle_event(ev)
#
#             if self.state == self.STATE_SQUARE:
#                 self._square_update_stage()
#             if self.state == self.STATE_JIGSAW:
#                 self._jigsaw_update_stage()
#
#             if self.state == self.STATE_LOCK:
#                 self._draw_lock()
#             elif self.state == self.STATE_SQUARE:
#                 self._square_draw()
#             elif self.state == self.STATE_JIG_SELECT:
#                 self.screen.fill(COLOR_BG)
#                 title = self.font_brand.render("Jigsaw Mode", True, (255, 255, 255))
#                 self.screen.blit(title, (self.W // 2 - title.get_width() // 2, 60))
#                 sub = self.font_small.render("Select difficulty (endless levels)", True, (220, 220, 220))
#                 self.screen.blit(sub, (self.W // 2 - sub.get_width() // 2, 120))
#
#                 mx, my = pygame.mouse.get_pos()
#                 draw_button(self.screen, self.back_btn, self.font_small, self.font_small,
#                             active=self.back_btn["rect"].collidepoint((mx, my)), small=True)
#
#                 row_h = 70
#                 gap = 12
#                 start_y = 170
#                 for i, (name, c, r) in enumerate(JIG_DIFFICULTY_CHOICES):
#                     rect = pygame.Rect(int(self.W * 0.18), start_y + i * (row_h + gap),
#                                        int(self.W * 0.64), row_h)
#                     active = rect.collidepoint((mx, my))
#                     bg = (40, 40, 40) if (i == selected_jig) else (22, 22, 22)
#                     if active:
#                         bg = lighten(bg, 10)
#                     pygame.draw.rect(self.screen, bg, rect, border_radius=16)
#                     pygame.draw.rect(self.screen, (140, 140, 140), rect, 2, border_radius=16)
#
#                     label = self.font.render(f"{name}", True, (240, 240, 240))
#                     dims = self.font_small.render(f"{c} x {r}", True, (210, 210, 210))
#                     self.screen.blit(label, (rect.x + 22, rect.centery - label.get_height() // 2))
#                     self.screen.blit(dims, (rect.right - dims.get_width() - 22, rect.centery - dims.get_height() // 2))
#
#             elif self.state == self.STATE_JIGSAW:
#                 self._jigsaw_draw()
#
#             pygame.display.flip()
#             self.clock.tick(60)
#
#         return bool(self._result_unlocked)
#
#
# # ============================================================
# # Public entrypoint for kiosk_shell shared-window use
# # ============================================================
# def run_lock_shared(screen: pygame.Surface, clock: Optional[pygame.time.Clock] = None,
#                     cfg: Optional[Dict[str, Any]] = None) -> bool:
#     """
#     Runs the lock UI on an existing fullscreen pygame display (no new window).
#     Returns True if unlocked (square puzzle levels or PIN).
#     """
#     app = LockApp(screen=screen, clock=clock, cfg=cfg)
#     return app.run()
#
#
# if __name__ == "__main__":
#     app = LockApp(screen=None, clock=None, cfg=None)
#     ok = app.run()
#     sys.exit(0 if ok else 1)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import math
import random
import datetime
from typing import Optional, Tuple, List, Dict, Any

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "x11")
os.environ.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")
os.environ.setdefault("SDL_VIDEO_WINDOW_POS", "0,0")
os.environ.setdefault("SDL_VIDEO_CENTERED", "0")

import pygame  # noqa: E402


# ---------------- CONFIG (defaults; can be overridden via cfg passed from kiosk_shell) ----------------
GRID_X = 3
GRID_Y = 4

SNAP_DIST = 190

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "images")
SOUNDS_DIR = os.path.join(BASE_DIR, "sounds")

BRAND_TEXT = "Glover SPARCstation"
BRAND_SUB = "Puzzle Lock"

ADMIN_PIN_DEFAULT = "1193"
PIN_MAX_LEN = 12

SHOW_STATUS_BAR = True
STATUS_BAR_H = 40

LOCK_UI_START_HIDDEN = True
LOCK_UI_AUTOHIDE_S = 6.0
LOCK_UI_MOUSE_MOVE_THRESH = 10
LOCK_UI_FADE_S = 0.18

LOCK_BG_CYCLE_S = 18.0
LOCK_VISIBLE_SCALE_MODE = "contain"

LOCK_BG_PAN_RANGE_PX = 900
LOCK_BG_PAN_SPEED_PX_S = 90.0

LOCK_BG_BLUR_METHOD = "hq"
LOCK_BG_HQ_DOWNSCALE = 2
LOCK_BG_HQ_RADIUS = 10

LOCK_BG_BLUR_DOWNSCALE = 12
LOCK_BG_DIM_ALPHA = 60

LOCK_TRANSITION_ENABLE = True
LOCK_FADEIN_S = 0.55

LOCK_TRANSITION_STYLES = ["shatter", "blinds", "explode", "drop"]
LOCK_TRANSITION_STYLE = "random"
LOCK_BREAK_DURATIONS = {
    "shatter": 0.85,
    "blinds":  0.95,
    "explode": 0.80,
    "drop":    0.90,
}

LOCK_SHATTER_TILE_TARGET = 180
LOCK_SHATTER_GRAVITY = 1200.0

LOCK_BG_RANDOM_START = True
LOCK_BG_SHUFFLE = False

COLOR_BG = (0, 0, 0)
COLOR_TRAY = (18, 18, 18)
COLOR_LINE = (70, 70, 70)

ACCENT_UNLOCK = (70, 185, 120)
ACCENT_JIGSAW = (170, 170, 170)
ACCENT_ADMIN = (120, 200, 255)

SND_PICK = "pick.wav"
SND_DROP = "drop.wav"
SND_SNAP = "snap.wav"
SND_ERROR = "error.wav"

TRAY_H_FRAC = 0.28
TRAY_MARGIN = 14

PUZ_INTRO_HOLD_S = 0.55
PUZ_FALL_S = 0.85
UNLOCK_SUCCESS_S = 0.85

JIG_KNOB_FRAC = 0.22
JIG_EDGE_OFF_FRAC = 0.18

JIG_SNAP_FRAC = 0.55
JIG_SNAP_MIN = 40
JIG_SNAP_MAX = 140

JIG_INTRO_HOLD_S = 0.55
JIG_FALL_S = 0.85
JIG_SOLVED_HOLD_S = 0.85

JIG_BG_DIM_ALPHA = 130

JIG_DIFFICULTY_CHOICES = [
    ("Easy",    3, 2),
    ("Normal",  4, 3),
    ("Hard",    5, 4),
    ("Expert",  6, 4),
    ("Insane", 10, 5),
    ("Extreme", 12, 5),
]

PUZZLE_BOARD_SCALE_MODE = "cover"


# ---------------- helpers ----------------
def clamp255(v: float) -> int:
    return max(0, min(255, int(v)))


def lighten(color, amt=22):
    return (clamp255(color[0] + amt), clamp255(color[1] + amt), clamp255(color[2] + amt))


def _ease_in_quad(t: float) -> float:
    return t * t


def _ease_out_cubic(t: float) -> float:
    u = 1.0 - t
    return 1.0 - (u * u * u)


def dist2(a, b) -> float:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return dx * dx + dy * dy


def load_sound(name: str):
    path = os.path.join(SOUNDS_DIR, name)
    if os.path.exists(path):
        try:
            return pygame.mixer.Sound(path)
        except Exception:
            return None
    return None


def play(snd):
    if snd:
        try:
            snd.play()
        except Exception:
            pass


def event_pos(ev, W: int, H: int):
    if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
        return ev.pos
    if ev.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
        return (int(ev.x * W), int(ev.y * H))
    return None


def safe_load_image(path: str) -> pygame.Surface:
    try:
        from PIL import Image, ImageOps  # type: ignore
        img = Image.open(path)
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "LA") or ("transparency" in img.info):
            img = img.convert("RGBA")
            surf = pygame.image.frombuffer(img.tobytes(), img.size, "RGBA").convert_alpha()
        else:
            img = img.convert("RGB")
            surf = pygame.image.frombuffer(img.tobytes(), img.size, "RGB").convert()
        return surf
    except Exception:
        surf = pygame.image.load(path)
        try:
            return surf.convert_alpha() if surf.get_alpha() is not None else surf.convert()
        except Exception:
            return surf


def scale_cover(src_surf: pygame.Surface, target_w: int, target_h: int) -> pygame.Surface:
    sw, sh = src_surf.get_size()
    scale = max(target_w / sw, target_h / sh)
    nw = max(1, int(sw * scale))
    nh = max(1, int(sh * scale))
    scaled = pygame.transform.smoothscale(src_surf, (nw, nh))
    x = (nw - target_w) // 2
    y = (nh - target_h) // 2
    return scaled.subsurface(pygame.Rect(x, y, target_w, target_h)).copy()


def scale_contain(src_surf: pygame.Surface, target_w: int, target_h: int):
    sw, sh = src_surf.get_size()
    scale = min(target_w / sw, target_h / sh)
    nw = max(1, int(sw * scale))
    nh = max(1, int(sh * scale))
    scaled = pygame.transform.smoothscale(src_surf, (nw, nh))
    rect = scaled.get_rect(center=(target_w // 2, target_h // 2))
    return scaled, rect


def blur_surface_once(src: pygame.Surface, downscale: int = 12) -> pygame.Surface:
    downscale = max(2, int(downscale))
    w, h = src.get_size()
    dw = max(2, w // downscale)
    dh = max(2, h // downscale)
    small = pygame.transform.smoothscale(src, (dw, dh))
    return pygame.transform.smoothscale(small, (w, h))


def blur_surface_hq(src: pygame.Surface, radius: int = 10, downscale: int = 2) -> pygame.Surface:
    try:
        from PIL import Image, ImageFilter  # type: ignore
        w, h = src.get_size()
        ds = max(1, int(downscale))
        if ds > 1:
            sw = max(2, w // ds)
            sh = max(2, h // ds)
            src_small = pygame.transform.smoothscale(src, (sw, sh))
            raw = pygame.image.tostring(src_small, "RGB")
            im = Image.frombytes("RGB", (sw, sh), raw)
        else:
            raw = pygame.image.tostring(src, "RGB")
            im = Image.frombytes("RGB", (w, h), raw)

        im = im.filter(ImageFilter.GaussianBlur(radius=max(0, int(radius))))
        if ds > 1:
            im = im.resize((w, h), resample=Image.LANCZOS)

        out = pygame.image.frombuffer(im.tobytes(), (w, h), "RGB").convert()
        return out
    except Exception:
        return blur_surface_once(src, LOCK_BG_BLUR_DOWNSCALE)


def _draw_round_rect_alpha(dst, rect: pygame.Rect, rgb, alpha: int, radius: int):
    a = clamp255(alpha)
    s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(s, (rgb[0], rgb[1], rgb[2], a), pygame.Rect(0, 0, rect.w, rect.h), border_radius=radius)
    dst.blit(s, rect.topleft)


def _draw_round_rect_outline_alpha(dst, rect: pygame.Rect, rgb, alpha: int, radius: int, width: int = 2):
    a = clamp255(alpha)
    s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(s, (rgb[0], rgb[1], rgb[2], a), pygame.Rect(0, 0, rect.w, rect.h), width, border_radius=radius)
    dst.blit(s, rect.topleft)


def _draw_icon_lock(dst, center, color, alpha=255):
    cx, cy = center
    a = clamp255(alpha)
    col = (color[0], color[1], color[2], a)
    s = pygame.Surface((40, 40), pygame.SRCALPHA)
    pygame.draw.arc(s, col, pygame.Rect(10, 6, 20, 18), math.pi, 0, 3)
    pygame.draw.rect(s, col, pygame.Rect(10, 18, 20, 16), border_radius=5)
    dst.blit(s, (cx - 20, cy - 20))


def _draw_icon_jigsaw(dst, center, color, alpha=255):
    cx, cy = center
    a = clamp255(alpha)
    col = (color[0], color[1], color[2], a)
    s = pygame.Surface((40, 40), pygame.SRCALPHA)
    pygame.draw.rect(s, col, pygame.Rect(10, 10, 18, 14), 2, border_radius=3)
    pygame.draw.rect(s, col, pygame.Rect(14, 14, 18, 14), 2, border_radius=3)
    pygame.draw.line(s, col, (16, 24), (22, 18), 2)
    pygame.draw.line(s, col, (22, 18), (30, 26), 2)
    dst.blit(s, (cx - 20, cy - 20))


def _draw_icon_key(dst, center, color, alpha=255):
    cx, cy = center
    a = clamp255(alpha)
    col = (color[0], color[1], color[2], a)
    s = pygame.Surface((40, 40), pygame.SRCALPHA)
    pygame.draw.circle(s, col, (14, 20), 6, 2)
    pygame.draw.line(s, col, (20, 20), (34, 20), 2)
    pygame.draw.line(s, col, (28, 20), (28, 26), 2)
    pygame.draw.line(s, col, (32, 20), (32, 24), 2)
    dst.blit(s, (cx - 20, cy - 20))


def draw_modern_dock(dst, dock_rect: pygame.Rect, alpha: int):
    _draw_round_rect_alpha(dst, dock_rect, (0, 0, 0), int(150 * (alpha / 255.0)), radius=22)
    _draw_round_rect_outline_alpha(dst, dock_rect, (255, 255, 255), int(90 * (alpha / 255.0)), radius=22, width=2)


def draw_modern_button(dst, rect: pygame.Rect, label: str, font, icon_fn, accent_rgb,
                       active: bool, pressed: bool, alpha: int):
    a = clamp255(alpha)
    shadow_off = 3 if not pressed else 1
    _draw_round_rect_alpha(dst, rect.move(0, shadow_off), (0, 0, 0), int(90 * (a / 255.0)), radius=16)

    base = (18, 18, 18)
    if active:
        base = (26, 26, 26)
    if pressed:
        base = (12, 12, 12)

    _draw_round_rect_alpha(dst, rect, base, int(210 * (a / 255.0)), radius=16)

    strip = pygame.Rect(rect.x + 12, rect.y + rect.h - 10, rect.w - 24, 4)
    _draw_round_rect_alpha(dst, strip, accent_rgb, int(200 * (a / 255.0)), radius=4)

    _draw_round_rect_outline_alpha(dst, rect, (255, 255, 255), int(95 * (a / 255.0)), radius=16, width=2)

    icon_center = (rect.x + 26, rect.centery)
    icon_fn(dst, icon_center, accent_rgb, alpha=a)

    txt = font.render(label, True, (240, 240, 240))
    txt.set_alpha(a)
    dst.blit(txt, (rect.x + 52, rect.centery - txt.get_height() // 2))


def make_button(rect: pygame.Rect, label: str, color=(90, 90, 90)):
    return {"rect": rect, "label": label, "color": color}


def draw_button(screen, btn, font_main, font_small, active=False, small=False):
    r = btn["rect"]
    base = btn.get("color", (90, 90, 90))
    bg = base if not active else lighten(base, 28)

    pygame.draw.rect(screen, bg, r, border_radius=16)
    pygame.draw.rect(screen, (230, 230, 230), r, 2, border_radius=16)

    f = font_small if small else font_main
    t = f.render(btn["label"], True, (255, 255, 255))
    screen.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))


def fade_to_black(screen, clock, dur_s: float = 0.18):
    t0 = time.time()
    w, h = screen.get_size()
    ov = pygame.Surface((w, h), pygame.SRCALPHA)
    while True:
        now = time.time()
        t = (now - t0) / max(0.001, dur_s)
        if t >= 1.0:
            break
        a = int(255 * t)
        ov.fill((0, 0, 0, a))
        screen.blit(ov, (0, 0))
        pygame.display.flip()
        clock.tick(60)
    screen.fill((0, 0, 0))
    pygame.display.flip()


def unlock_success_overlay(screen, clock, W, H, font_brand, font_small, snd_snap,
                          msg="UNLOCKED", sub="Returning to menu...", hold_s=UNLOCK_SUCCESS_S,
                          bg_frame_surf: Optional[pygame.Surface] = None):
    play(snd_snap)
    t0 = time.time()
    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    while time.time() - t0 < hold_s:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                raise SystemExit

        if bg_frame_surf is not None:
            screen.blit(bg_frame_surf, (0, 0))
        else:
            screen.fill(COLOR_BG)

        screen.blit(overlay, (0, 0))

        m = font_brand.render(msg, True, (255, 255, 255))
        s = font_small.render(sub, True, (230, 230, 230))
        screen.blit(m, (W // 2 - m.get_width() // 2, H // 2 - 40))
        screen.blit(s, (W // 2 - s.get_width() // 2, H // 2 + 20))
        pygame.display.flip()
        clock.tick(60)


def pin_overlay_loop(screen, clock, W, H, bg_frame_surf, font, font_small, snd_error, admin_pin: str) -> bool:
    pin_input = ""
    pin_error = ""
    pin_error_t0 = 0.0

    cancel_btn = make_button(pygame.Rect(16, 16, 170, 48), "CANCEL", color=(120, 120, 120))

    KEYPAD_COLS = 3
    KEYPAD_ROWS = 4
    KEYS = ["1", "2", "3",
            "4", "5", "6",
            "7", "8", "9",
            "C", "0", "OK"]

    def submit() -> bool:
        nonlocal pin_input, pin_error, pin_error_t0
        if pin_input == admin_pin:
            return True
        pin_error = "Incorrect PIN"
        pin_error_t0 = time.time()
        pin_input = ""
        play(snd_error)
        return False

    dim = pygame.Surface((W, H), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 205))

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                raise SystemExit

            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return False
                if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if submit():
                        return True
                elif ev.key == pygame.K_BACKSPACE:
                    pin_input = pin_input[:-1]
                else:
                    if ev.unicode.isdigit() and len(pin_input) < PIN_MAX_LEN:
                        pin_input += ev.unicode

            if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
                pos = event_pos(ev, W, H)
                if not pos:
                    continue

                if cancel_btn["rect"].collidepoint(pos):
                    return False

                pad_w = min(520, int(W * 0.42))
                pad_h = min(520, int(H * 0.62))
                pad_x = (W - pad_w) // 2
                pad_y = (H - pad_h) // 2 + 40
                cell_w = pad_w // KEYPAD_COLS
                cell_h = pad_h // KEYPAD_ROWS

                idx = 0
                for r in range(KEYPAD_ROWS):
                    for c in range(KEYPAD_COLS):
                        x = pad_x + c * cell_w + 8
                        y = pad_y + r * cell_h + 8
                        rect = pygame.Rect(x, y, cell_w - 16, cell_h - 16)
                        if rect.collidepoint(pos):
                            key = KEYS[idx]
                            if key == "C":
                                pin_input = ""
                            elif key == "OK":
                                if submit():
                                    return True
                            else:
                                if len(pin_input) < PIN_MAX_LEN:
                                    pin_input += key
                            break
                        idx += 1

        screen.blit(bg_frame_surf, (0, 0))
        screen.blit(dim, (0, 0))

        mx, my = pygame.mouse.get_pos()
        draw_button(screen, cancel_btn, font, font_small, active=cancel_btn["rect"].collidepoint((mx, my)), small=True)

        title = font.render("PIN UNLOCK", True, (255, 255, 255))
        prompt = font_small.render("Enter PIN (keyboard or touchscreen keypad):", True, (230, 230, 230))
        masked = "*" * len(pin_input)
        entry = font.render(masked, True, (255, 255, 0))

        screen.blit(title, (W // 2 - title.get_width() // 2, 80))
        screen.blit(prompt, (W // 2 - prompt.get_width() // 2, 130))
        screen.blit(entry, (W // 2 - entry.get_width() // 2, 165))

        pad_w = min(520, int(W * 0.42))
        pad_h = min(520, int(H * 0.62))
        pad_x = (W - pad_w) // 2
        pad_y = (H - pad_h) // 2 + 40
        cell_w = pad_w // KEYPAD_COLS
        cell_h = pad_h // KEYPAD_ROWS

        pygame.draw.rect(screen, (35, 35, 35), pygame.Rect(pad_x, pad_y, pad_w, pad_h), border_radius=12)

        rects = []
        for r in range(KEYPAD_ROWS):
            for c in range(KEYPAD_COLS):
                x = pad_x + c * cell_w + 8
                y = pad_y + r * cell_h + 8
                rects.append(pygame.Rect(x, y, cell_w - 16, cell_h - 16))

        for i, r in enumerate(rects):
            pygame.draw.rect(screen, (70, 70, 70), r, border_radius=10)
            label = font.render(KEYS[i], True, (255, 255, 255))
            screen.blit(label, (r.centerx - label.get_width() // 2, r.centery - label.get_height() // 2))

        if pin_error and (time.time() - pin_error_t0) < 2.0:
            err = font_small.render(pin_error, True, (255, 90, 90))
            screen.blit(err, (W // 2 - err.get_width() // 2, pad_y + pad_h + 18))

        tip = font_small.render("Enter/OK=submit, Backspace=delete, Esc/CANCEL=back.", True, (230, 230, 230))
        screen.blit(tip, (W // 2 - tip.get_width() // 2, pad_y + pad_h + 50))

        pygame.display.flip()
        clock.tick(60)


def calc_jig_snap_dist(W: int, BOARD_H: int, cols: int, rows: int) -> int:
    cols = max(1, int(cols))
    rows = max(1, int(rows))
    cell_w = W // cols
    cell_h = BOARD_H // rows
    base = int(min(cell_w, cell_h) * JIG_SNAP_FRAC)
    return max(JIG_SNAP_MIN, min(JIG_SNAP_MAX, base))


def _make_jigsaw_edges(cols, rows):
    h_edges = [
        [{"dir": random.choice([-1, 1]), "off": random.uniform(-JIG_EDGE_OFF_FRAC, JIG_EDGE_OFF_FRAC)}
         for _ in range(cols)]
        for _ in range(rows - 1)
    ]
    v_edges = [
        [{"dir": random.choice([-1, 1]), "off": random.uniform(-JIG_EDGE_OFF_FRAC, JIG_EDGE_OFF_FRAC)}
         for _ in range(cols - 1)]
        for _ in range(rows)
    ]
    return h_edges, v_edges


def _apply_edge_circle(mask_surf, kind, center, radius):
    if kind == 0:
        return
    if kind > 0:
        pygame.draw.circle(mask_surf, (255, 255, 255, 255), center, radius)
    else:
        pygame.draw.circle(mask_surf, (255, 255, 255, 0), center, radius)


def build_jigsaw_pieces(W, BOARD_H, board_surf, cols, rows):
    cell_w = W // cols
    cell_h = BOARD_H // rows

    knob_r = int(min(cell_w, cell_h) * JIG_KNOB_FRAC)
    margin = knob_r + 3

    h_edges, v_edges = _make_jigsaw_edges(cols, rows)

    pieces = []
    for y in range(rows):
        for x in range(cols):
            if y == 0:
                top_kind, top_off = 0, 0.0
            else:
                top_kind = -h_edges[y - 1][x]["dir"]
                top_off = h_edges[y - 1][x]["off"]

            if y == rows - 1:
                bot_kind, bot_off = 0, 0.0
            else:
                bot_kind = h_edges[y][x]["dir"]
                bot_off = h_edges[y][x]["off"]

            if x == 0:
                left_kind, left_off = 0, 0.0
            else:
                left_kind = -v_edges[y][x - 1]["dir"]
                left_off = v_edges[y][x - 1]["off"]

            if x == cols - 1:
                right_kind, right_off = 0, 0.0
            else:
                right_kind = v_edges[y][x]["dir"]
                right_off = v_edges[y][x]["off"]

            pw = cell_w + 2 * margin
            ph = cell_h + 2 * margin

            mask_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
            mask_surf.fill((255, 255, 255, 0))
            pygame.draw.rect(mask_surf, (255, 255, 255, 255), pygame.Rect(margin, margin, cell_w, cell_h))

            cx_top = margin + (cell_w // 2) + int(top_off * cell_w)
            cy_top = margin
            _apply_edge_circle(mask_surf, top_kind, (cx_top, cy_top), knob_r)

            cx_bot = margin + (cell_w // 2) + int(bot_off * cell_w)
            cy_bot = margin + cell_h
            _apply_edge_circle(mask_surf, bot_kind, (cx_bot, cy_bot), knob_r)

            cx_left = margin
            cy_left = margin + (cell_h // 2) + int(left_off * cell_h)
            _apply_edge_circle(mask_surf, left_kind, (cx_left, cy_left), knob_r)

            cx_right = margin + cell_w
            cy_right = margin + (cell_h // 2) + int(right_off * cell_h)
            _apply_edge_circle(mask_surf, right_kind, (cx_right, cy_right), knob_r)

            piece_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
            piece_surf.blit(board_surf, (margin - x * cell_w, margin - y * cell_h))
            piece_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

            piece_mask = pygame.mask.from_surface(mask_surf)
            correct_pos = (x * cell_w - margin, y * cell_h - margin)

            pieces.append({
                "surf": piece_surf,
                "mask": piece_mask,
                "correct_pos": correct_pos,
                "pos": list(correct_pos),
                "locked": False,
                "fall_from": list(correct_pos),
                "fall_to": list(correct_pos),
            })

    return pieces


def tray_random_pos_sized(W, tray_rect, obj_w, obj_h):
    x0 = TRAY_MARGIN
    x1 = W - TRAY_MARGIN - obj_w
    y0 = tray_rect.top + TRAY_MARGIN
    y1 = tray_rect.bottom - TRAY_MARGIN - obj_h
    if x1 < x0:
        x1 = x0
    if y1 < y0:
        y1 = y0
    return (random.randint(x0, x1), random.randint(y0, y1))


def jigsaw_all_locked(pieces):
    return all(p.get("locked") for p in pieces)


def _clip_surface_to_roundrect(src: pygame.Surface, size: Tuple[int, int], radius: int) -> pygame.Surface:
    """Returns src scaled to size and clipped to a rounded rect."""
    w, h = size
    scaled = pygame.transform.smoothscale(src, (w, h))
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    mask.fill((0, 0, 0, 0))
    pygame.draw.rect(mask, (255, 255, 255, 255), pygame.Rect(0, 0, w, h), border_radius=radius)
    out.blit(scaled, (0, 0))
    out.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return out


# ---------------- LockApp ----------------
class LockApp:
    STATE_LOCK = "LOCK"
    STATE_SQUARE = "SQUARE"
    STATE_JIG_SELECT = "JIG_SELECT"
    STATE_JIGSAW = "JIGSAW"

    PUZ_INTRO = "INTRO"
    PUZ_FALL = "FALL"
    PUZ_PLAY = "PLAY"

    JIG_INTRO = "INTRO"
    JIG_FALL = "FALL"
    JIG_PLAY = "PLAY"

    LOCK_TRANS_NONE = None
    LOCK_TRANS_BREAK = "BREAK"
    LOCK_TRANS_FADEIN = "FADEIN"

    def __init__(self, screen: Optional[pygame.Surface] = None, clock: Optional[pygame.time.Clock] = None,
                 cfg: Optional[Dict[str, Any]] = None):
        self.cfg = cfg or {}
        ff = (self.cfg.get("feature_flags") or {})
        sec = (self.cfg.get("security") or {})

        self.admin_pin = str(sec.get("pi_pin", ADMIN_PIN_DEFAULT))
        self.unlock_levels = max(1, int(ff.get("unlock_levels", 1)))
        self.unlock_mode = str(ff.get("unlock_mode", "square")).lower().strip()
        self.endless_jigsaw = bool(ff.get("enable_endless_jigsaw", True))

        self._shared = (screen is not None)

        if not pygame.get_init():
            pygame.init()
        try:
            if not pygame.font.get_init():
                pygame.font.init()
        except Exception:
            pass

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except Exception:
            pass

        if screen is None:
            self.screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)
            pygame.display.set_caption("SPARC Lock")
        else:
            self.screen = screen

        self.clock = clock or pygame.time.Clock()
        self.W, self.H = self.screen.get_size()
        pygame.mouse.set_visible(True)

        self.font = pygame.font.SysFont(None, 52)
        self.font_small = pygame.font.SysFont(None, 26)
        self.font_brand = pygame.font.SysFont(None, 64)
        self.font_brand2 = pygame.font.SysFont(None, 28)
        self.font_dock = pygame.font.SysFont(None, 28)

        self.snd_pick = load_sound(SND_PICK)
        self.snd_drop = load_sound(SND_DROP)
        self.snd_snap = load_sound(SND_SNAP)
        self.snd_error = load_sound(SND_ERROR)

        self.TRAY_H = int(self.H * TRAY_H_FRAC)
        self.BOARD_H = self.H - self.TRAY_H
        self.board_rect = pygame.Rect(0, 0, self.W, self.BOARD_H)
        self.tray_rect = pygame.Rect(0, self.BOARD_H, self.W, self.TRAY_H)

        self.images = self._load_images()
        self.playlist = list(self.images)
        if LOCK_BG_SHUFFLE:
            random.shuffle(self.playlist)
        else:
            self.playlist.sort()
        self.lock_idx = random.randrange(len(self.playlist)) if (LOCK_BG_RANDOM_START and self.playlist) else 0

        self.lock_bg_big = None
        self.lock_fg = None
        self.lock_fg_rect = None
        self.board_surf = None
        self.img_name = ""

        self.pan_x = 0.0
        self.pan_y = 0.0
        self.pan_vx = 0.0
        self.pan_vy = 0.0

        self.lock_cycle_t0 = time.time()
        self.lock_trans = self.LOCK_TRANS_NONE
        self.lock_trans_t0 = 0.0

        self.break_style = "shatter"
        self.break_dur = float(LOCK_BREAK_DURATIONS.get("shatter", 0.85))

        self.lock_snapshot = pygame.Surface((self.W, self.H))
        self.break_pieces: List[Dict[str, Any]] = []

        if self.playlist:
            self._set_image_by_index(self.lock_idx)

        now = time.time()
        self.lock_ui_visible_until = (now + LOCK_UI_AUTOHIDE_S) if not LOCK_UI_START_HIDDEN else 0.0
        self.last_mouse_pos = pygame.mouse.get_pos()
        self.ui_alpha = 0.0 if LOCK_UI_START_HIDDEN else 255.0

        self._layout_lock_dock()
        self.lock_pressed = None

        self.state = self.STATE_LOCK

        # Unlock progression
        self.unlock_level = 0

        # Square puzzle state
        self.tiles: List[Dict[str, Any]] = []
        self.tile_w = 0
        self.tile_h = 0
        self.slot_positions: List[Tuple[int, int]] = []
        self.drag_tile: Optional[Dict[str, Any]] = None
        self.drag_ox = 0
        self.drag_oy = 0
        self.puz_stage = self.PUZ_INTRO
        self.puz_t0 = 0.0

        # Jigsaw state
        self.jig_level = 0
        self.jig_cols, self.jig_rows = JIG_DIFFICULTY_CHOICES[1][1], JIG_DIFFICULTY_CHOICES[1][2]
        self.jig_snap_dist = calc_jig_snap_dist(self.W, self.BOARD_H, self.jig_cols, self.jig_rows)
        self.jig_pieces: List[Dict[str, Any]] = []
        self.jig_drag_piece: Optional[Dict[str, Any]] = None
        self.jig_drag_ox = 0
        self.jig_drag_oy = 0
        self.jig_stage = self.JIG_INTRO
        self.jig_t0 = 0.0

        self.back_btn = make_button(pygame.Rect(16, 16, 160, 48), "BACK", color=(120, 120, 120))

        self._running = True
        self._result_unlocked = False

        # Cached overlays (perf)
        self._dim_full_180 = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        self._dim_full_180.fill((0, 0, 0, 180))

        # Frame dt (fixes abrupt transition physics + UI fade timing)
        self._dt = 1.0 / 60.0

        # Cached overlays for transition
        self._ov_break = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        self._ov_fade = pygame.Surface((self.W, self.H), pygame.SRCALPHA)

    def _layout_lock_dock(self):
        margin_bottom = 28
        dock_w = min(780, int(self.W * 0.68))
        dock_h = 96
        dock_x = (self.W - dock_w) // 2
        dock_y = self.H - dock_h - margin_bottom
        self.dock_rect = pygame.Rect(dock_x, dock_y, dock_w, dock_h)

        pad = 14
        gap = 12
        btn_h = 64
        btn_y = dock_y + (dock_h - btn_h) // 2
        btn_w = (dock_w - pad * 2 - gap * 2) // 3

        self.btn_unlock = pygame.Rect(dock_x + pad + (btn_w + gap) * 0, btn_y, btn_w, btn_h)
        self.btn_jigsaw = pygame.Rect(dock_x + pad + (btn_w + gap) * 1, btn_y, btn_w, btn_h)
        self.btn_admin = pygame.Rect(dock_x + pad + (btn_w + gap) * 2, btn_y, btn_w, btn_h)

    def _load_images(self):
        if not os.path.isdir(IMAGE_DIR):
            return []
        imgs = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        return imgs

    def _touch_lock_ui(self):
        self.lock_ui_visible_until = time.time() + LOCK_UI_AUTOHIDE_S

    def _lock_ui_visible(self) -> bool:
        return time.time() < self.lock_ui_visible_until

    def _set_image_by_index(self, idx: int):
        if not self.playlist:
            return
        self.lock_idx = idx % len(self.playlist)
        fname = self.playlist[self.lock_idx]
        raw = safe_load_image(os.path.join(IMAGE_DIR, fname))
        self.img_name = fname

        if LOCK_VISIBLE_SCALE_MODE.lower() == "cover":
            self.lock_fg = scale_cover(raw, self.W, self.H)
            self.lock_fg_rect = self.lock_fg.get_rect(topleft=(0, 0))
        else:
            self.lock_fg, self.lock_fg_rect = scale_contain(raw, self.W, self.H)

        big_w = self.W + LOCK_BG_PAN_RANGE_PX
        big_h = self.H + LOCK_BG_PAN_RANGE_PX
        bg = scale_cover(raw, big_w, big_h).convert()

        if LOCK_BG_BLUR_METHOD.lower() == "hq":
            bg = blur_surface_hq(bg, radius=LOCK_BG_HQ_RADIUS, downscale=LOCK_BG_HQ_DOWNSCALE)
        else:
            bg = blur_surface_once(bg, LOCK_BG_BLUR_DOWNSCALE).convert()

        if LOCK_BG_DIM_ALPHA > 0:
            dim = pygame.Surface((big_w, big_h), pygame.SRCALPHA)
            dim.fill((0, 0, 0, clamp255(LOCK_BG_DIM_ALPHA)))
            bg.blit(dim, (0, 0))

        self.lock_bg_big = bg.convert()

        if PUZZLE_BOARD_SCALE_MODE.lower() == "contain":
            board_fit, rect = scale_contain(raw, self.W, self.BOARD_H)
            board = pygame.Surface((self.W, self.BOARD_H))
            board.fill((0, 0, 0))
            board.blit(board_fit, rect)
            self.board_surf = board.convert()
        else:
            self.board_surf = scale_cover(raw, self.W, self.BOARD_H).convert()

        max_x = max(0, self.lock_bg_big.get_width() - self.W)
        max_y = max(0, self.lock_bg_big.get_height() - self.H)
        self.pan_x = float(random.randint(0, max_x)) if max_x else 0.0
        self.pan_y = float(random.randint(0, max_y)) if max_y else 0.0

        ang = random.uniform(0, math.tau)
        self.pan_vx = math.cos(ang) * LOCK_BG_PAN_SPEED_PX_S
        self.pan_vy = math.sin(ang) * LOCK_BG_PAN_SPEED_PX_S

        self.lock_cycle_t0 = time.time()

    def _advance_image(self):
        if not self.playlist:
            return
        nxt = self.lock_idx + 1
        if nxt >= len(self.playlist):
            nxt = 0
            if LOCK_BG_SHUFFLE:
                random.shuffle(self.playlist)
        self._set_image_by_index(nxt)

    def _update_pan(self, dt: float):
        if not self.lock_bg_big:
            return
        max_x = max(0, self.lock_bg_big.get_width() - self.W)
        max_y = max(0, self.lock_bg_big.get_height() - self.H)

        self.pan_x += self.pan_vx * dt
        self.pan_y += self.pan_vy * dt

        if max_x > 0:
            if self.pan_x < 0:
                self.pan_x = 0.0
                self.pan_vx = abs(self.pan_vx)
            elif self.pan_x > max_x:
                self.pan_x = float(max_x)
                self.pan_vx = -abs(self.pan_vx)
        else:
            self.pan_x = 0.0

        if max_y > 0:
            if self.pan_y < 0:
                self.pan_y = 0.0
                self.pan_vy = abs(self.pan_vy)
            elif self.pan_y > max_y:
                self.pan_y = float(max_y)
                self.pan_vy = -abs(self.pan_vy)
        else:
            self.pan_y = 0.0

    def _draw_lock_frame_to(self, target_surf: pygame.Surface):
        if self.lock_bg_big:
            max_x = max(0, self.lock_bg_big.get_width() - self.W)
            max_y = max(0, self.lock_bg_big.get_height() - self.H)
            vx = int(max(0, min(max_x, self.pan_x)))
            vy = int(max(0, min(max_y, self.pan_y)))
            view = pygame.Rect(vx, vy, self.W, self.H)
            target_surf.blit(self.lock_bg_big.subsurface(view), (0, 0))
        else:
            target_surf.fill((0, 0, 0))

        if self.lock_fg and self.lock_fg_rect:
            target_surf.blit(self.lock_fg, self.lock_fg_rect)

    def _build_lock_frame_surface(self) -> pygame.Surface:
        surf = pygame.Surface((self.W, self.H))
        self._draw_lock_frame_to(surf)
        return surf

    def _draw_status_bar(self):
        if not SHOW_STATUS_BAR:
            return
        bar = pygame.Surface((self.W, STATUS_BAR_H), pygame.SRCALPHA)
        bar.fill((0, 0, 0, 140))
        self.screen.blit(bar, (0, 0))
        now = datetime.datetime.now()
        txt = now.strftime("%a %b %d   %I:%M %p").lstrip("0")
        t = self.font_small.render(txt, True, (230, 230, 230))
        self.screen.blit(t, (self.W - t.get_width() - 16, (STATUS_BAR_H - t.get_height()) // 2))

    def _choose_break_style(self) -> str:
        if LOCK_TRANSITION_STYLE == "random":
            return random.choice(LOCK_TRANSITION_STYLES)
        if LOCK_TRANSITION_STYLE in LOCK_TRANSITION_STYLES:
            return LOCK_TRANSITION_STYLE
        return "shatter"

    def _make_break_pieces(self, snap: pygame.Surface, style: str) -> List[Dict[str, Any]]:
        pieces: List[Dict[str, Any]] = []
        W, H = self.W, self.H

        if style == "blinds":
            n = 16
            tile_w = max(16, W // n)
            for i in range(n):
                x = i * tile_w
                w = tile_w if i < n - 1 else (W - x)
                rect = pygame.Rect(x, 0, w, H)
                surf = snap.subsurface(rect).copy()
                dir_sign = -1 if (i % 2 == 0) else 1
                vx = dir_sign * random.uniform(250, 450)
                pieces.append({
                    "surf": surf,
                    "pos": [float(rect.x), float(rect.y)],
                    "vel": [vx, random.uniform(-40, 40)],
                    "rot": 0.0,
                    "ang": random.uniform(-30, 30),
                })
            return pieces

        target = LOCK_SHATTER_TILE_TARGET
        cols = int(math.sqrt(target * (W / max(1.0, H))))
        cols = max(6, min(30, cols))
        rows = max(6, min(24, int(target / cols)))
        tile_w = max(18, W // cols)
        tile_h = max(18, H // rows)

        for y in range(0, H, tile_h):
            for x in range(0, W, tile_w):
                rect = pygame.Rect(x, y, min(tile_w, W - x), min(tile_h, H - y))
                surf = snap.subsurface(rect).copy()
                cx = rect.centerx - W / 2.0
                cy = rect.centery - H / 2.0

                if style == "explode":
                    mag = random.uniform(220, 520)
                    ang = math.atan2(cy, cx) + random.uniform(-0.25, 0.25)
                    vx = math.cos(ang) * mag
                    vy = math.sin(ang) * mag
                elif style == "drop":
                    vx = random.uniform(-80, 80)
                    vy = random.uniform(50, 160)
                else:
                    vx = random.uniform(-260, 260) + (cx * 0.25)
                    vy = random.uniform(-180, 120) + (cy * 0.20)

                rot = random.uniform(-35, 35)
                pieces.append({
                    "surf": surf,
                    "pos": [float(rect.x), float(rect.y)],
                    "vel": [vx, vy],
                    "rot": 0.0,
                    "ang": rot,
                })

        return pieces

    def _begin_lock_transition(self):
        self.lock_snapshot = self._build_lock_frame_surface()
        self.break_style = self._choose_break_style()
        self.break_dur = float(LOCK_BREAK_DURATIONS.get(self.break_style, 0.85))
        self.lock_trans = self.LOCK_TRANS_BREAK
        self.lock_trans_t0 = time.time()
        self.break_pieces = self._make_break_pieces(self.lock_snapshot, self.break_style)

    def _draw_break(self, t: float):
        self.screen.fill((0, 0, 0))

        # FIX: use real dt (clamped) so physics doesn't look like it "stops early"
        dt = self._dt
        grav = LOCK_SHATTER_GRAVITY

        for p in self.break_pieces:
            vx, vy = p["vel"]
            if self.break_style in ("shatter", "drop"):
                vy += grav * dt * (0.70 if self.break_style == "drop" else 0.40)
                p["vel"][1] = vy

            p["pos"][0] += vx * dt
            p["pos"][1] += vy * dt

            damp = 1.0 - (0.12 * t)
            p["vel"][0] *= damp
            p["vel"][1] *= damp

            p["rot"] += p["ang"] * dt

            surf = p["surf"]
            if abs(p["rot"]) > 0.5:
                rs = pygame.transform.rotozoom(surf, p["rot"], 1.0)
                r = rs.get_rect(center=(p["pos"][0] + surf.get_width() / 2, p["pos"][1] + surf.get_height() / 2))
                self.screen.blit(rs, r.topleft)
            else:
                self.screen.blit(surf, (p["pos"][0], p["pos"][1]))

        # FIX: reduce blackout intensity (less abrupt)
        self._ov_break.fill((0, 0, 0, int(150 * _ease_in_quad(t))))
        self.screen.blit(self._ov_break, (0, 0))

    def _draw_fadein(self, t: float):
        self._draw_lock_frame_to(self.screen)
        a = int(255 * (1.0 - _ease_out_cubic(t)))
        self._ov_fade.fill((0, 0, 0, a))
        self.screen.blit(self._ov_fade, (0, 0))

    # ---------- Square puzzle ----------
    def _square_setup(self):
        if self.board_surf is None:
            return

        margin = 40
        usable_w = self.W - margin * 2
        usable_h = self.BOARD_H - margin * 2
        cols, rows = GRID_X, GRID_Y

        self.tile_w = usable_w // cols
        self.tile_h = usable_h // rows

        self.slot_positions = []
        for j in range(rows):
            for i in range(cols):
                sx = margin + i * self.tile_w
                sy = margin + j * self.tile_h
                self.slot_positions.append((sx, sy))

        board_scaled = pygame.transform.smoothscale(self.board_surf, (usable_w, usable_h))
        tiles: List[Dict[str, Any]] = []
        for j in range(rows):
            for i in range(cols):
                src_rect = pygame.Rect(i * self.tile_w, j * self.tile_h, self.tile_w, self.tile_h)
                surf = board_scaled.subsurface(src_rect).copy()
                tile = pygame.Surface((self.tile_w, self.tile_h), pygame.SRCALPHA)
                tile.blit(surf, (0, 0))
                pygame.draw.rect(tile, (255, 255, 255, 70), pygame.Rect(0, 0, self.tile_w, self.tile_h), 2, border_radius=10)

                correct = self.slot_positions[j * cols + i]
                pos = tray_random_pos_sized(self.W, self.tray_rect, self.tile_w, self.tile_h)
                tiles.append({
                    "surf": tile,
                    "correct": correct,
                    "pos": [float(pos[0]), float(pos[1])],
                    "locked": False,
                    "fall_from": [float(pos[0]), float(-self.tile_h - random.randint(20, 400))],
                    "fall_to": [float(pos[0]), float(pos[1])],
                })

        random.shuffle(tiles)
        self.tiles = tiles
        self.drag_tile = None
        self.puz_stage = self.PUZ_INTRO
        self.puz_t0 = time.time()

    def _square_all_locked(self) -> bool:
        return all(t["locked"] for t in self.tiles)

    def _square_slot_occupied(self, slot_xy: Tuple[int, int]) -> bool:
        for t in self.tiles:
            if t["locked"] and tuple(map(int, t["pos"])) == slot_xy:
                return True
        return False

    def _square_find_tile_at(self, x: int, y: int) -> Optional[Dict[str, Any]]:
        for t in reversed(self.tiles):
            if t["locked"]:
                continue
            r = pygame.Rect(int(t["pos"][0]), int(t["pos"][1]), self.tile_w, self.tile_h)
            if r.collidepoint((x, y)):
                return t
        return None

    def _square_update_stage(self):
        now = time.time()
        if self.puz_stage == self.PUZ_INTRO:
            if (now - self.puz_t0) >= PUZ_INTRO_HOLD_S:
                for t in self.tiles:
                    pos = tray_random_pos_sized(self.W, self.tray_rect, self.tile_w, self.tile_h)
                    t["fall_from"] = [float(pos[0]), float(-self.tile_h - random.randint(20, 400))]
                    t["fall_to"] = [float(pos[0]), float(pos[1])]
                    t["pos"] = [t["fall_from"][0], t["fall_from"][1]]
                self.puz_stage = self.PUZ_FALL
                self.puz_t0 = now

        elif self.puz_stage == self.PUZ_FALL:
            t = (now - self.puz_t0) / max(0.001, PUZ_FALL_S)
            if t >= 1.0:
                for tile in self.tiles:
                    tile["pos"] = [tile["fall_to"][0], tile["fall_to"][1]]
                self.puz_stage = self.PUZ_PLAY
                self.puz_t0 = now
            else:
                tt = _ease_out_cubic(t)
                for tile in self.tiles:
                    fx, fy = tile["fall_from"]
                    tx, ty = tile["fall_to"]
                    tile["pos"][0] = fx + (tx - fx) * tt
                    tile["pos"][1] = fy + (ty - fy) * tt

    def _square_draw(self):
        # Clean UI: no lock image bleed-through
        self.screen.fill(COLOR_BG)

        header = self.font_small.render(
            f"Unlock Puzzle  •  Level {self.unlock_level + 1} / {self.unlock_levels}",
            True,
            (230, 230, 230),
        )
        self.screen.blit(header, (18, 18))

        # NOTE: Removed the big rectangular "board panel" background/border
        ref_rect = pygame.Rect(18, 56, self.W - 36, self.BOARD_H - 72)

        margin = 40
        cols, rows = GRID_X, GRID_Y
        usable_w = self.W - margin * 2
        usable_h = self.BOARD_H - margin * 2
        tile_w = usable_w // cols
        tile_h = usable_h // rows

        for j in range(rows):
            for i in range(cols):
                sx = margin + i * tile_w
                sy = margin + j * tile_h
                slot_rect = pygame.Rect(sx, sy, tile_w, tile_h)
                pygame.draw.rect(self.screen, (55, 55, 55), slot_rect, 2, border_radius=10)

        pygame.draw.rect(self.screen, COLOR_TRAY, self.tray_rect)
        pygame.draw.line(self.screen, COLOR_LINE, (0, self.BOARD_H), (self.W, self.BOARD_H), 2)

        tray_label = self.font_small.render("Drag pieces into place.", True, (220, 220, 220))
        self.screen.blit(tray_label, (18, self.BOARD_H + 10))

        mx, my = pygame.mouse.get_pos()
        draw_button(self.screen, self.back_btn, self.font_small, self.font_small,
                    active=self.back_btn["rect"].collidepoint((mx, my)), small=True)

        for t in self.tiles:
            self.screen.blit(t["surf"], (t["pos"][0], t["pos"][1]))

        if self.puz_stage == self.PUZ_INTRO and self.board_surf is not None:
            inner = ref_rect.inflate(-14, -14)
            ref = _clip_surface_to_roundrect(self.board_surf, (inner.w, inner.h), radius=22)
            self.screen.blit(ref, inner.topleft)
            ov = pygame.Surface((inner.w, inner.h), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 140))
            self.screen.blit(ov, inner.topleft)
            msg = self.font_small.render("Memorize the picture...", True, (240, 240, 240))
            self.screen.blit(msg, (self.W // 2 - msg.get_width() // 2, ref_rect.bottom - 32))

    def _complete_unlock_level_or_finish(self):
        self.unlock_level += 1
        if self.unlock_level >= self.unlock_levels:
            bg = self.screen.copy()
            unlock_success_overlay(
                self.screen, self.clock, self.W, self.H, self.font_brand, self.font_small,
                self.snd_snap, msg="UNLOCKED", sub="Returning to menu...", hold_s=UNLOCK_SUCCESS_S,
                bg_frame_surf=bg
            )
            fade_to_black(self.screen, self.clock, 0.18)
            self._result_unlocked = True
            self._running = False
            return

        bg = self.screen.copy()
        unlock_success_overlay(
            self.screen, self.clock, self.W, self.H, self.font_brand, self.font_small,
            self.snd_snap,
            msg=f"LEVEL {self.unlock_level} COMPLETE",
            sub="Next puzzle...",
            hold_s=0.70,
            bg_frame_surf=bg
        )
        if self.playlist:
            self._advance_image()
        self._square_setup()
        self.state = self.STATE_SQUARE

    def _square_handle_event(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self.state = self.STATE_LOCK
            self.lock_pressed = None
            return

        if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
            pos = event_pos(ev, self.W, self.H)
            if not pos:
                return
            x, y = pos

            if self.back_btn["rect"].collidepoint((x, y)):
                self.state = self.STATE_LOCK
                self.lock_pressed = None
                return

            if self.puz_stage != self.PUZ_PLAY:
                return

            t = self._square_find_tile_at(x, y)
            if t:
                play(self.snd_pick)
                self.drag_tile = t
                self.drag_ox = x - int(t["pos"][0])
                self.drag_oy = y - int(t["pos"][1])
                self.tiles.remove(t)
                self.tiles.append(t)

        if ev.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
            if self.drag_tile is None:
                return
            pos = event_pos(ev, self.W, self.H)
            if not pos:
                return
            x, y = pos
            self.drag_tile["pos"][0] = float(x - self.drag_ox)
            self.drag_tile["pos"][1] = float(y - self.drag_oy)

        if ev.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
            if self.drag_tile is None:
                return
            t = self.drag_tile
            self.drag_tile = None
            play(self.snd_drop)

            cx = int(t["pos"][0] + self.tile_w / 2)
            cy = int(t["pos"][1] + self.tile_h / 2)

            slot_x, slot_y = t["correct"]
            slot_c = (slot_x + self.tile_w // 2, slot_y + self.tile_h // 2)

            if dist2((cx, cy), slot_c) <= (SNAP_DIST * SNAP_DIST) and not self._square_slot_occupied((slot_x, slot_y)):
                t["pos"][0] = float(slot_x)
                t["pos"][1] = float(slot_y)
                t["locked"] = True
                play(self.snd_snap)

                if self._square_all_locked():
                    self._complete_unlock_level_or_finish()

    # ---------- Jigsaw ----------
    def _jigsaw_setup(self, cols: int, rows: int):
        if self.board_surf is None:
            return
        self.jig_cols, self.jig_rows = cols, rows
        self.jig_snap_dist = calc_jig_snap_dist(self.W, self.BOARD_H, cols, rows)

        pieces = build_jigsaw_pieces(self.W, self.BOARD_H, self.board_surf, cols, rows)
        for p in pieces:
            w, h = p["surf"].get_size()
            pos = tray_random_pos_sized(self.W, self.tray_rect, w, h)
            p["fall_from"] = [float(pos[0]), float(-h - random.randint(20, 400))]
            p["fall_to"] = [float(pos[0]), float(pos[1])]
            p["pos"] = [p["fall_from"][0], p["fall_from"][1]]
            p["locked"] = False
        random.shuffle(pieces)

        self.jig_pieces = pieces
        self.jig_drag_piece = None
        self.jig_stage = self.JIG_INTRO
        self.jig_t0 = time.time()

    def _jigsaw_find_piece_at(self, x: int, y: int) -> Optional[Dict[str, Any]]:
        for p in reversed(self.jig_pieces):
            if p.get("locked"):
                continue
            px, py = int(p["pos"][0]), int(p["pos"][1])
            lx, ly = x - px, y - py
            if lx < 0 or ly < 0:
                continue
            if lx >= p["surf"].get_width() or ly >= p["surf"].get_height():
                continue
            if p["mask"].get_at((lx, ly)):
                return p
        return None

    def _jigsaw_update_stage(self):
        now = time.time()
        if self.jig_stage == self.JIG_INTRO:
            if (now - self.jig_t0) >= JIG_INTRO_HOLD_S:
                self.jig_stage = self.JIG_FALL
                self.jig_t0 = now

        elif self.jig_stage == self.JIG_FALL:
            t = (now - self.jig_t0) / max(0.001, JIG_FALL_S)
            if t >= 1.0:
                for p in self.jig_pieces:
                    p["pos"] = [p["fall_to"][0], p["fall_to"][1]]
                self.jig_stage = self.JIG_PLAY
                self.jig_t0 = now
            else:
                tt = _ease_out_cubic(t)
                for p in self.jig_pieces:
                    fx, fy = p["fall_from"]
                    tx, ty = p["fall_to"]
                    p["pos"][0] = fx + (tx - fx) * tt
                    p["pos"][1] = fy + (ty - fy) * tt

    def _jigsaw_draw(self):
        self.screen.fill(COLOR_BG)

        header = self.font_small.render(
            f"Jigsaw  {self.jig_cols} x {self.jig_rows}  •  Level {self.jig_level + 1}",
            True,
            (230, 230, 230),
        )
        self.screen.blit(header, (18, 18))

        # NOTE: Removed the big rectangular "board panel" background/border
        ref_rect = pygame.Rect(18, 56, self.W - 36, self.BOARD_H - 72)

        if self.jig_stage == self.JIG_INTRO and self.board_surf is not None:
            inner = ref_rect.inflate(-14, -14)
            ref = _clip_surface_to_roundrect(self.board_surf, (inner.w, inner.h), radius=22)
            self.screen.blit(ref, inner.topleft)
            ov = pygame.Surface((inner.w, inner.h), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 155))
            self.screen.blit(ov, inner.topleft)

        pygame.draw.rect(self.screen, COLOR_TRAY, self.tray_rect)
        pygame.draw.line(self.screen, COLOR_LINE, (0, self.BOARD_H), (self.W, self.BOARD_H), 2)

        tray_label = self.font_small.render("Drag pieces into place (snaps when close).", True, (220, 220, 220))
        self.screen.blit(tray_label, (18, self.BOARD_H + 10))

        mx, my = pygame.mouse.get_pos()
        draw_button(self.screen, self.back_btn, self.font_small, self.font_small,
                    active=self.back_btn["rect"].collidepoint((mx, my)), small=True)

        for p in self.jig_pieces:
            self.screen.blit(p["surf"], (p["pos"][0], p["pos"][1]))

    def _jigsaw_on_solved(self):
        self.jig_level += 1
        bg = self.screen.copy()
        unlock_success_overlay(
            self.screen, self.clock, self.W, self.H, self.font_brand, self.font_small,
            self.snd_snap,
            msg=f"LEVEL {self.jig_level} COMPLETE",
            sub="Next jigsaw...",
            hold_s=JIG_SOLVED_HOLD_S,
            bg_frame_surf=bg
        )
        fade_to_black(self.screen, self.clock, 0.12)

        if self.playlist:
            self._advance_image()

        if self.endless_jigsaw:
            self._jigsaw_setup(self.jig_cols, self.jig_rows)
            self.state = self.STATE_JIGSAW
            return

        self._result_unlocked = True
        self._running = False

    def _jigsaw_handle_event(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self.state = self.STATE_LOCK
            self.lock_pressed = None
            return

        if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
            pos = event_pos(ev, self.W, self.H)
            if not pos:
                return
            x, y = pos

            if self.back_btn["rect"].collidepoint((x, y)):
                self.state = self.STATE_LOCK
                self.lock_pressed = None
                return

            if self.jig_stage != self.JIG_PLAY:
                return

            p = self._jigsaw_find_piece_at(x, y)
            if p:
                play(self.snd_pick)
                self.jig_drag_piece = p
                self.jig_drag_ox = x - int(p["pos"][0])
                self.jig_drag_oy = y - int(p["pos"][1])
                self.jig_pieces.remove(p)
                self.jig_pieces.append(p)

        if ev.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
            if self.jig_drag_piece is None:
                return
            pos = event_pos(ev, self.W, self.H)
            if not pos:
                return
            x, y = pos
            self.jig_drag_piece["pos"][0] = float(x - self.jig_drag_ox)
            self.jig_drag_piece["pos"][1] = float(y - self.jig_drag_oy)

        if ev.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
            if self.jig_drag_piece is None:
                return
            p = self.jig_drag_piece
            self.jig_drag_piece = None
            play(self.snd_drop)

            correct = p["correct_pos"]
            px, py = p["pos"]
            dx = (px - correct[0])
            dy = (py - correct[1])
            if (dx * dx + dy * dy) <= (self.jig_snap_dist * self.jig_snap_dist):
                p["pos"][0] = float(correct[0])
                p["pos"][1] = float(correct[1])
                p["locked"] = True
                play(self.snd_snap)

                if jigsaw_all_locked(self.jig_pieces):
                    self._jigsaw_on_solved()

    # ---------- Lock state ----------
    def _draw_lock(self):
        if self.lock_trans == self.LOCK_TRANS_BREAK:
            t = (time.time() - self.lock_trans_t0) / max(0.001, self.break_dur)
            if t >= 1.0:
                self._advance_image()
                self.lock_trans = self.LOCK_TRANS_FADEIN
                self.lock_trans_t0 = time.time()
                self._draw_fadein(0.0)
            else:
                self._draw_break(t)
        elif self.lock_trans == self.LOCK_TRANS_FADEIN:
            t = (time.time() - self.lock_trans_t0) / max(0.001, LOCK_FADEIN_S)
            if t >= 1.0:
                self.lock_trans = self.LOCK_TRANS_NONE
                self._draw_lock_frame_to(self.screen)
            else:
                self._draw_fadein(t)
        else:
            self._draw_lock_frame_to(self.screen)

        title = self.font_brand.render(BRAND_TEXT, True, (255, 255, 255))
        subtitle = self.font_brand2.render(BRAND_SUB, True, (230, 230, 230))
        self.screen.blit(title, (30, 70))
        self.screen.blit(subtitle, (30, 135))

        self._draw_status_bar()

        target = 255.0 if self._lock_ui_visible() else 0.0
        dt = max(1.0 / 240.0, min(1.0 / 20.0, self._dt))
        step = (255.0 / max(0.001, LOCK_UI_FADE_S)) * dt
        if self.ui_alpha < target:
            self.ui_alpha = min(target, self.ui_alpha + step)
        elif self.ui_alpha > target:
            self.ui_alpha = max(target, self.ui_alpha - step)

        a = int(self.ui_alpha)
        if a > 0:
            draw_modern_dock(self.screen, self.dock_rect, a)

            mx, my = pygame.mouse.get_pos()
            over_unlock = self.btn_unlock.collidepoint((mx, my))
            over_jigsaw = self.btn_jigsaw.collidepoint((mx, my))
            over_admin = self.btn_admin.collidepoint((mx, my))

            pressed_unlock = (self.lock_pressed == "unlock")
            pressed_jigsaw = (self.lock_pressed == "jigsaw")
            pressed_admin = (self.lock_pressed == "admin")

            draw_modern_button(self.screen, self.btn_unlock, "Unlock", self.font_dock,
                               _draw_icon_lock, ACCENT_UNLOCK, over_unlock, pressed_unlock, a)
            draw_modern_button(self.screen, self.btn_jigsaw, "Jigsaw", self.font_dock,
                               _draw_icon_jigsaw, ACCENT_JIGSAW, over_jigsaw, pressed_jigsaw, a)
            draw_modern_button(self.screen, self.btn_admin, "PIN", self.font_dock,
                               _draw_icon_key, ACCENT_ADMIN, over_admin, pressed_admin, a)

    def _lock_handle_event(self, ev):
        if ev.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
            pos = event_pos(ev, self.W, self.H)
            if pos:
                x, y = pos
                lx, ly = self.last_mouse_pos
                if abs(x - lx) + abs(y - ly) >= LOCK_UI_MOUSE_MOVE_THRESH:
                    self._touch_lock_ui()
                self.last_mouse_pos = (x, y)

        if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
            self._touch_lock_ui()
            pos = event_pos(ev, self.W, self.H)
            if not pos:
                return
            x, y = pos

            if self.ui_alpha >= 40:
                if self.btn_unlock.collidepoint((x, y)):
                    self.lock_pressed = "unlock"
                    play(self.snd_pick)
                elif self.btn_jigsaw.collidepoint((x, y)):
                    self.lock_pressed = "jigsaw"
                    play(self.snd_pick)
                elif self.btn_admin.collidepoint((x, y)):
                    self.lock_pressed = "admin"
                    play(self.snd_pick)
                else:
                    self.lock_pressed = None

        if ev.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
            pos = event_pos(ev, self.W, self.H)
            if not pos:
                self.lock_pressed = None
                return
            x, y = pos

            pressed = self.lock_pressed
            self.lock_pressed = None
            if pressed is None:
                return

            if pressed == "unlock" and self.btn_unlock.collidepoint((x, y)):
                self.unlock_level = 0
                self._square_setup()
                self.state = self.STATE_SQUARE
                return

            if pressed == "jigsaw" and self.btn_jigsaw.collidepoint((x, y)):
                self.state = self.STATE_JIG_SELECT
                return

            if pressed == "admin" and self.btn_admin.collidepoint((x, y)):
                # FIX: make PIN screens black-backed (prevents lock photo flash)
                bg = pygame.Surface((self.W, self.H))
                bg.fill((0, 0, 0))
                ok = pin_overlay_loop(
                    self.screen, self.clock, self.W, self.H, bg,
                    self.font, self.font_small, self.snd_error,
                    admin_pin=self.admin_pin
                )
                if ok:
                    # FIX: unlock success should not reuse captured frame that contains the photo
                    unlock_success_overlay(
                        self.screen, self.clock, self.W, self.H,
                        self.font_brand, self.font_small, self.snd_snap,
                        msg="UNLOCKED", sub="Returning to menu...",
                        hold_s=UNLOCK_SUCCESS_S,
                        bg_frame_surf=None
                    )
                    fade_to_black(self.screen, self.clock, 0.18)
                    self._result_unlocked = True
                    self._running = False
                return

        if ev.type == pygame.KEYDOWN:
            self._touch_lock_ui()
            if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.unlock_level = 0
                self._square_setup()
                self.state = self.STATE_SQUARE
                return
            if ev.key == pygame.K_j:
                self.state = self.STATE_JIG_SELECT
                return

    def run(self) -> bool:
        if not self.playlist:
            self.lock_trans = self.LOCK_TRANS_NONE

        selected_jig = 1
        prev_time = time.time()

        while self._running:
            now = time.time()
            dt = now - prev_time
            prev_time = now

            # Clamp dt to keep animations stable on occasional stalls
            dt = max(1.0 / 240.0, min(1.0 / 20.0, dt))
            self._dt = dt

            if self.state == self.STATE_LOCK:
                self._update_pan(dt)
                if self.lock_trans == self.LOCK_TRANS_NONE and LOCK_TRANSITION_ENABLE and self.playlist:
                    if (now - self.lock_cycle_t0) >= LOCK_BG_CYCLE_S:
                        self._begin_lock_transition()

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self._running = False
                    break

                if self.state == self.STATE_LOCK:
                    self._lock_handle_event(ev)

                elif self.state == self.STATE_SQUARE:
                    self._square_handle_event(ev)

                elif self.state == self.STATE_JIG_SELECT:
                    if ev.type == pygame.KEYDOWN:
                        if ev.key == pygame.K_ESCAPE:
                            self.state = self.STATE_LOCK
                            continue
                        if ev.key == pygame.K_UP:
                            selected_jig = max(0, selected_jig - 1)
                        if ev.key == pygame.K_DOWN:
                            selected_jig = min(len(JIG_DIFFICULTY_CHOICES) - 1, selected_jig + 1)
                        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            _, c, r = JIG_DIFFICULTY_CHOICES[selected_jig]
                            self.jig_level = 0
                            self._jigsaw_setup(c, r)
                            self.state = self.STATE_JIGSAW
                            continue

                    if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
                        pos = event_pos(ev, self.W, self.H)
                        if pos:
                            x, y = pos
                            if self.back_btn["rect"].collidepoint((x, y)):
                                self.state = self.STATE_LOCK
                                continue

                            row_h = 70
                            gap = 12
                            start_y = 170
                            for i in range(len(JIG_DIFFICULTY_CHOICES)):
                                rect = pygame.Rect(int(self.W * 0.18), start_y + i * (row_h + gap),
                                                   int(self.W * 0.64), row_h)
                                if rect.collidepoint((x, y)):
                                    selected_jig = i
                                    _, c, r = JIG_DIFFICULTY_CHOICES[selected_jig]
                                    self.jig_level = 0
                                    self._jigsaw_setup(c, r)
                                    self.state = self.STATE_JIGSAW
                                    break

                elif self.state == self.STATE_JIGSAW:
                    self._jigsaw_handle_event(ev)

            if self.state == self.STATE_SQUARE:
                self._square_update_stage()
            if self.state == self.STATE_JIGSAW:
                self._jigsaw_update_stage()

            if self.state == self.STATE_LOCK:
                self._draw_lock()
            elif self.state == self.STATE_SQUARE:
                self._square_draw()
            elif self.state == self.STATE_JIG_SELECT:
                self.screen.fill(COLOR_BG)
                title = self.font_brand.render("Jigsaw Mode", True, (255, 255, 255))
                self.screen.blit(title, (self.W // 2 - title.get_width() // 2, 60))
                sub = self.font_small.render("Select difficulty (endless levels)", True, (220, 220, 220))
                self.screen.blit(sub, (self.W // 2 - sub.get_width() // 2, 120))

                mx, my = pygame.mouse.get_pos()
                draw_button(self.screen, self.back_btn, self.font_small, self.font_small,
                            active=self.back_btn["rect"].collidepoint((mx, my)), small=True)

                row_h = 70
                gap = 12
                start_y = 170
                for i, (name, c, r) in enumerate(JIG_DIFFICULTY_CHOICES):
                    rect = pygame.Rect(int(self.W * 0.18), start_y + i * (row_h + gap),
                                       int(self.W * 0.64), row_h)
                    active = rect.collidepoint((mx, my))
                    bg = (40, 40, 40) if (i == selected_jig) else (22, 22, 22)
                    if active:
                        bg = lighten(bg, 10)
                    pygame.draw.rect(self.screen, bg, rect, border_radius=16)
                    pygame.draw.rect(self.screen, (140, 140, 140), rect, 2, border_radius=16)

                    label = self.font.render(f"{name}", True, (240, 240, 240))
                    dims = self.font_small.render(f"{c} x {r}", True, (210, 210, 210))
                    self.screen.blit(label, (rect.x + 22, rect.centery - label.get_height() // 2))
                    self.screen.blit(dims, (rect.right - dims.get_width() - 22, rect.centery - dims.get_height() // 2))

            elif self.state == self.STATE_JIGSAW:
                self._jigsaw_draw()

            pygame.display.flip()
            self.clock.tick(60)

        return bool(self._result_unlocked)


# ============================================================
# Public entrypoint for kiosk_shell shared-window use
# ============================================================
def run_lock_shared(screen: pygame.Surface, clock: Optional[pygame.time.Clock] = None,
                    cfg: Optional[Dict[str, Any]] = None) -> bool:
    """
    Runs the lock UI on an existing fullscreen pygame display (no new window).
    Returns True if unlocked (square puzzle levels or PIN).
    """
    app = LockApp(screen=screen, clock=clock, cfg=cfg)
    return app.run()


if __name__ == "__main__":
    app = LockApp(screen=None, clock=None, cfg=None)
    ok = app.run()
    sys.exit(0 if ok else 1)
