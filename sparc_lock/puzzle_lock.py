#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import sys
import time
import math
import random
import datetime
import pygame

# ============================================================
# Configuration
# ============================================================
os.environ.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "images")
SOUNDS_DIR = os.path.join(BASE_DIR, "sounds")

# Branding
BRAND_TEXT = "Glover SPARCstation"
BRAND_SUB = "Puzzle Lock"

# PIN (lock-screen PIN unlock only)
ADMIN_PIN = "1193"
PIN_MAX_LEN = 12

# Status bar
SHOW_STATUS_BAR = True
STATUS_BAR_H = 40

# ---------------- LOCK UI VISIBILITY ----------------
LOCK_UI_START_HIDDEN = True
LOCK_UI_AUTOHIDE_S = 6.0
LOCK_UI_MOUSE_MOVE_THRESH = 10
LOCK_UI_FADE_S = 0.18   # visual fade of dock (seconds)

# ---------------- LOCK SLIDESHOW / EFFECTS ----------------
LOCK_BG_CYCLE_S = 18.0

# Visible photo scale on lock:
#   "contain" = show entire image, no cropping
#   "cover"   = fill screen, may crop
LOCK_VISIBLE_SCALE_MODE = "contain"

# Background layer (behind visible photo) uses cover + blur + pan.
LOCK_BG_PAN_RANGE_PX = 900
LOCK_BG_PAN_SPEED_PX_S = 90.0

# Background blur quality
#   "hq" = PIL Gaussian blur (best quality) with mild downscale for speed
#   "downscale" = cheap downscale/upscale blur
LOCK_BG_BLUR_METHOD = "hq"
LOCK_BG_HQ_DOWNSCALE = 2
LOCK_BG_HQ_RADIUS = 10

LOCK_BG_BLUR_DOWNSCALE = 12
LOCK_BG_DIM_ALPHA = 60

# Breaking transitions on slideshow change
LOCK_TRANSITION_ENABLE = True
LOCK_FADEIN_S = 0.55

LOCK_TRANSITION_STYLES = ["shatter", "blinds", "explode", "drop"]
LOCK_TRANSITION_STYLE = "random"  # "random" or one of the styles above
LOCK_BREAK_DURATIONS = {
    "shatter": 0.85,
    "blinds":  0.95,
    "explode": 0.80,
    "drop":    0.90,
}

LOCK_SHATTER_TILE_TARGET = 180
LOCK_SHATTER_GRAVITY = 1200.0

# Playlist behavior
LOCK_BG_RANDOM_START = True
LOCK_BG_SHUFFLE = False

# Colors
COLOR_BG = (0, 0, 0)
COLOR_TRAY = (18, 18, 18)
COLOR_LINE = (70, 70, 70)

# Modern dock + button theme
UI_TEXT = (240, 240, 240)
UI_MUTED = (210, 210, 210)

# Button �accents� (subtle, not loud)
ACCENT_UNLOCK = (70, 185, 120)
ACCENT_JigSaw = (170, 170, 170)
ACCENT_ADMIN = (120, 200, 255)

# Sounds (optional wav files in ./sounds/)
SND_PICK = "pick.wav"
SND_DROP = "drop.wav"
SND_SNAP = "snap.wav"
SND_ERROR = "error.wav"

# ---------------- Square puzzle defaults ----------------
GRID_X = 3
GRID_Y = 4

TRAY_H_FRAC = 0.28
TRAY_MARGIN = 14

SNAP_DIST = 190

PUZ_INTRO_HOLD_S = 0.55
PUZ_FALL_S = 0.85
UNLOCK_SUCCESS_S = 0.85

# ---------------- Jigsaw puzzle defaults ----------------
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

# Puzzle board scaling:
#   "cover" keeps play area filled
#   "contain" shows full photo but may introduce bars in puzzle
PUZZLE_BOARD_SCALE_MODE = "cover"

# ============================================================
# Helpers / utilities
# ============================================================
def clamp255(v: float) -> int:
    return max(0, min(255, int(v)))

def lighten(color, amt=22):
    return (clamp255(color[0] + amt), clamp255(color[1] + amt), clamp255(color[2] + amt))

def mix(a, b, t: float):
    t = max(0.0, min(1.0, t))
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))

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
    """
    Fix EXIF orientation if Pillow is available; fallback to pygame loader otherwise.
    """
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
    if sw <= 0 or sh <= 0:
        return pygame.Surface((target_w, target_h))
    scale = max(target_w / sw, target_h / sh)
    nw = int(sw * scale)
    nh = int(sh * scale)
    scaled = pygame.transform.smoothscale(src_surf, (nw, nh))
    x = (nw - target_w) // 2
    y = (nh - target_h) // 2
    return scaled.subsurface(pygame.Rect(x, y, target_w, target_h)).copy()

def scale_contain(src_surf: pygame.Surface, target_w: int, target_h: int):
    """
    Fit entire image within target (no cropping). Returns (scaled_surf, rect_to_blit_centered).
    """
    sw, sh = src_surf.get_size()
    if sw <= 0 or sh <= 0:
        blank = pygame.Surface((target_w, target_h))
        return blank, blank.get_rect()
    scale = min(target_w / sw, target_h / sh)
    nw = max(1, int(sw * scale))
    nh = max(1, int(sh * scale))
    scaled = pygame.transform.smoothscale(src_surf, (nw, nh))
    rect = scaled.get_rect(center=(target_w // 2, target_h // 2))
    return scaled, rect

def blur_surface_once(src: pygame.Surface, downscale: int = 12) -> pygame.Surface:
    """
    Cheap blur: downscale then upscale (computed once per image).
    """
    downscale = max(2, int(downscale))
    w, h = src.get_size()
    dw = max(2, w // downscale)
    dh = max(2, h // downscale)
    small = pygame.transform.smoothscale(src, (dw, dh))
    return pygame.transform.smoothscale(small, (w, h))

def blur_surface_hq(src: pygame.Surface, radius: int = 10, downscale: int = 2) -> pygame.Surface:
    """
    Higher-quality blur computed once per image swap.
    Uses PIL GaussianBlur if available; falls back to blur_surface_once.
    """
    try:
        from PIL import Image, ImageFilter  # type: ignore
        w, h = src.get_size()
        if w <= 2 or h <= 2:
            return src

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

# ============================================================
# Modern UI drawing
# ============================================================
def _draw_round_rect_alpha(dst, rect: pygame.Rect, rgb, alpha: int, radius: int):
    alpha = clamp255(alpha)
    s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(s, (rgb[0], rgb[1], rgb[2], alpha), pygame.Rect(0, 0, rect.w, rect.h), border_radius=radius)
    dst.blit(s, rect.topleft)

def _draw_round_rect_outline_alpha(dst, rect: pygame.Rect, rgb, alpha: int, radius: int, width: int = 2):
    alpha = clamp255(alpha)
    s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(s, (rgb[0], rgb[1], rgb[2], alpha), pygame.Rect(0, 0, rect.w, rect.h), width, border_radius=radius)
    dst.blit(s, rect.topleft)

def _draw_icon_lock(dst, center, color, alpha=255):
    cx, cy = center
    a = clamp255(alpha)
    col = (color[0], color[1], color[2], a)
    s = pygame.Surface((40, 40), pygame.SRCALPHA)
    # shackle
    pygame.draw.arc(s, col, pygame.Rect(10, 6, 20, 18), math.pi, 0, 3)
    # body
    pygame.draw.rect(s, col, pygame.Rect(10, 18, 20, 16), border_radius=5)
    dst.blit(s, (cx - 20, cy - 20))

def _draw_icon_JigSaw(dst, center, color, alpha=255):
    cx, cy = center
    a = clamp255(alpha)
    col = (color[0], color[1], color[2], a)
    s = pygame.Surface((40, 40), pygame.SRCALPHA)
    # stacked frames
    pygame.draw.rect(s, col, pygame.Rect(10, 10, 18, 14), 2, border_radius=3)
    pygame.draw.rect(s, col, pygame.Rect(14, 14, 18, 14), 2, border_radius=3)
    # small �mountain� line
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
    # glassy panel
    _draw_round_rect_alpha(dst, dock_rect, (0, 0, 0), int(150 * (alpha / 255.0)), radius=22)
    _draw_round_rect_outline_alpha(dst, dock_rect, (255, 255, 255), int(90 * (alpha / 255.0)), radius=22, width=2)

# def draw_modern_button(dst, rect: pygame.Rect, label: str, font, icon_fn, accent_rgb, active: bool, pressed: bool, alpha: int):
#     a = clamp255(alpha)
#     # shadow
#     shadow_off = 3 if not pressed else 1
#     _draw_round_rect_alpha(dst, rect.move(0, shadow_off), (0, 0, 0), int(90 * (a / 255.0)), radius=16)

#     # base fill
#     base = (18, 18, 18)
#     if active:
#         base = (26, 26, 26)
#     if pressed:
#         base = (12, 12, 12)

#     _draw_round_rect_alpha(dst, rect, base, int(210 * (a / 255.0)), radius=16)

#     # accent strip
#     strip = pygame.Rect(rect.x + 12, rect.y + rect.h - 10, rect.w - 24, 4)
#     _draw_round_rect_alpha(dst, strip, accent_rgb, int(200 * (a / 255.0)), radius=4)

#     # outline
#     _draw_round_rect_outline_alpha(dst, rect, (255, 255, 255), int(95 * (a / 255.0)), radius=16, width=2)

#     # icon + label
#     icon_center = (rect.x + 26, rect.centery)
#     icon_fn(dst, icon_center, accent_rgb, alpha=a)

#     txt = font.render(label, True, (240, 240, 240))
#     dst.blit(txt, (rect.x + 52, rect.centery - txt.get_height() // 2))
def draw_modern_button(dst, rect: pygame.Rect, label: str, font, icon_fn, accent_rgb,
                       active: bool, pressed: bool, alpha: int):
    a = clamp255(alpha)

    # shadow
    shadow_off = 3 if not pressed else 1
    _draw_round_rect_alpha(dst, rect.move(0, shadow_off), (0, 0, 0), int(90 * (a / 255.0)), radius=16)

    # base fill
    base = (18, 18, 18)
    if active:
        base = (26, 26, 26)
    if pressed:
        base = (12, 12, 12)

    _draw_round_rect_alpha(dst, rect, base, int(210 * (a / 255.0)), radius=16)

    # accent strip
    strip = pygame.Rect(rect.x + 12, rect.y + rect.h - 10, rect.w - 24, 4)
    _draw_round_rect_alpha(dst, strip, accent_rgb, int(200 * (a / 255.0)), radius=4)

    # outline
    _draw_round_rect_outline_alpha(dst, rect, (255, 255, 255), int(95 * (a / 255.0)), radius=16, width=2)

    # icon + label
    icon_center = (rect.x + 26, rect.centery)
    icon_fn(dst, icon_center, accent_rgb, alpha=a)

    # --- FIX: fade the label with the same alpha as the dock ---
    txt = font.render(label, True, (240, 240, 240))
    txt.set_alpha(a)  # key line: makes text fade with dock
    dst.blit(txt, (rect.x + 52, rect.centery - txt.get_height() // 2))

# ============================================================
# PIN overlay
# ============================================================
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

def pin_overlay_loop(screen, clock, W, H, bg_frame_surf, font, font_small, snd_error) -> bool:
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
        if pin_input == ADMIN_PIN:
            return True
        pin_error = "Incorrect PIN"
        pin_error_t0 = time.time()
        pin_input = ""
        play(snd_error)
        return False

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                raise SystemExit

            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return False
                if ev.key == pygame.K_RETURN:
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

        # draw
        screen.blit(bg_frame_surf, (0, 0))
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 205))
        screen.blit(overlay, (0, 0))

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

# ============================================================
# Unlock success overlay
# ============================================================
def unlock_success_overlay(screen, clock, W, H, font_brand, font_small, snd_snap,
                          msg="UNLOCKED", sub="Returning to menu...", hold_s=UNLOCK_SUCCESS_S):
    t0 = time.time()
    play(snd_snap)
    while time.time() - t0 < hold_s:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                raise SystemExit
        screen.fill(COLOR_BG)
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        m = font_brand.render(msg, True, (255, 255, 255))
        s = font_small.render(sub, True, (230, 230, 230))
        screen.blit(m, (W // 2 - m.get_width() // 2, H // 2 - 40))
        screen.blit(s, (W // 2 - s.get_width() // 2, H // 2 + 20))
        pygame.display.flip()
        clock.tick(60)

# ============================================================
# Jigsaw internals
# ============================================================
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
                "pos": correct_pos,
                "locked": False,
                "fall_from": correct_pos,
                "fall_to": correct_pos,
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

# ============================================================
# App
# ============================================================
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
    JIG_SOLVED = "SOLVED"

    LOCK_TRANS_NONE = None
    LOCK_TRANS_BREAK = "BREAK"
    LOCK_TRANS_FADEIN = "FADEIN"

    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init()
        except Exception:
            pass

        # Request vsync for smoother motion when supported.
        try:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN, vsync=1)
        except Exception:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

        pygame.display.set_caption("SPARC Lock")
        self.clock = pygame.time.Clock()
        self.W, self.H = self.screen.get_size()
        pygame.mouse.set_visible(True)

        self.font = pygame.font.SysFont(None, 52)
        self.font_small = pygame.font.SysFont(None, 26)
        self.font_brand = pygame.font.SysFont(None, 64)
        self.font_brand2 = pygame.font.SysFont(None, 28)

        # Dock text slightly smaller than prior big buttons
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
        self.lock_idx = random.randrange(len(self.playlist)) if LOCK_BG_RANDOM_START else 0

        # Lock surfaces
        self.lock_bg_big = None
        self.lock_fg = None
        self.lock_fg_rect = None
        self.board_surf = None
        self.img_name = ""

        # Pan state (float)
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.pan_vx = 0.0
        self.pan_vy = 0.0

        # slideshow cycle + transitions
        self.lock_cycle_t0 = time.time()
        self.lock_trans = self.LOCK_TRANS_NONE
        self.lock_trans_t0 = 0.0

        self.break_style = "shatter"
        self.break_dur = float(LOCK_BREAK_DURATIONS.get("shatter", 0.85))

        self.lock_snapshot = pygame.Surface((self.W, self.H))
        self.break_pieces = []

        self._set_image_by_index(self.lock_idx)

        # Lock UI visibility
        now = time.time()
        self.lock_ui_visible_until = (now + LOCK_UI_AUTOHIDE_S) if not LOCK_UI_START_HIDDEN else 0.0
        self.last_mouse_pos = pygame.mouse.get_pos()

        # Dock fade alpha
        self.ui_alpha = 0.0 if LOCK_UI_START_HIDDEN else 255.0

        # Modern dock layout
        self._layout_lock_dock()

        # Lock press tracking (activate on release)
        self.lock_pressed = None  # "unlock" | "JigSaw" | "admin"

        # State machine
        self.state = self.STATE_LOCK

        # Square puzzle runtime
        self.tiles = []
        self.tile_w = 0
        self.tile_h = 0
        self.slot_positions = []
        self.drag_tile = None
        self.drag_ox = 0
        self.drag_oy = 0
        self.puz_stage = self.PUZ_INTRO
        self.puz_t0 = 0.0

        # Jigsaw runtime
        self.jigsaw_session = False
        self.jig_cols, self.jig_rows = JIG_DIFFICULTY_CHOICES[1][1], JIG_DIFFICULTY_CHOICES[1][2]
        self.jig_snap_dist = calc_jig_snap_dist(self.W, self.BOARD_H, self.jig_cols, self.jig_rows)
        self.jig_pieces = []
        self.jig_drag_piece = None
        self.jig_drag_ox = 0
        self.jig_drag_oy = 0
        self.jig_stage = self.JIG_INTRO
        self.jig_t0 = 0.0

        # Back button (keep old style for now; it�s already compact)
        self.back_btn = make_button(pygame.Rect(16, 16, 160, 48), "BACK", color=(120, 120, 120))

    def _layout_lock_dock(self):
        # A compact �family kiosk� dock: centered, not oversized.
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
        self.btn_JigSaw = pygame.Rect(dock_x + pad + (btn_w + gap) * 1, btn_y, btn_w, btn_h)
        self.btn_admin = pygame.Rect(dock_x + pad + (btn_w + gap) * 2, btn_y, btn_w, btn_h)

    def _load_images(self):
        if not os.path.isdir(IMAGE_DIR):
            print(f"Missing images dir: {IMAGE_DIR}", file=sys.stderr)
            sys.exit(1)
        imgs = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        if not imgs:
            print(f"No images found in {IMAGE_DIR}", file=sys.stderr)
            sys.exit(1)
        return imgs

    def exit_unlocked(self):
        try:
            pygame.quit()
        except Exception:
            pass
        sys.exit(0)

    # ---------------- lock UI visibility ----------------
    def _touch_lock_ui(self):
        self.lock_ui_visible_until = time.time() + LOCK_UI_AUTOHIDE_S

    def _lock_ui_visible(self) -> bool:
        return time.time() < self.lock_ui_visible_until

    # ---------------- lock surfaces ----------------
    def _set_image_by_index(self, idx: int):
        self.lock_idx = idx % len(self.playlist)
        fname = self.playlist[self.lock_idx]
        raw = safe_load_image(os.path.join(IMAGE_DIR, fname))
        self.img_name = fname

        # 1) Visible photo (full view if contain)
        if LOCK_VISIBLE_SCALE_MODE.lower() == "cover":
            self.lock_fg = scale_cover(raw, self.W, self.H)
            self.lock_fg_rect = self.lock_fg.get_rect(topleft=(0, 0))
        else:
            self.lock_fg, self.lock_fg_rect = scale_contain(raw, self.W, self.H)

        # 2) Background: oversized cover + blur + dim, used for smooth pan
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

        # 3) Puzzle board: cover by default (so play area is filled)
        if PUZZLE_BOARD_SCALE_MODE.lower() == "contain":
            board_fit, rect = scale_contain(raw, self.W, self.BOARD_H)
            board = pygame.Surface((self.W, self.BOARD_H))
            board.fill((0, 0, 0))
            board.blit(board_fit, rect)
            self.board_surf = board.convert()
        else:
            self.board_surf = scale_cover(raw, self.W, self.BOARD_H).convert()

        # Pan state init
        max_x = max(0, self.lock_bg_big.get_width() - self.W)
        max_y = max(0, self.lock_bg_big.get_height() - self.H)
        self.pan_x = float(random.randint(0, max_x)) if max_x else 0.0
        self.pan_y = float(random.randint(0, max_y)) if max_y else 0.0

        ang = random.uniform(0, math.tau)
        self.pan_vx = math.cos(ang) * LOCK_BG_PAN_SPEED_PX_S
        self.pan_vy = math.sin(ang) * LOCK_BG_PAN_SPEED_PX_S

        self.lock_cycle_t0 = time.time()

    def _advance_image(self):
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

        # Bounce
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
        # Draw panning background crop
        if self.lock_bg_big:
            max_x = max(0, self.lock_bg_big.get_width() - self.W)
            max_y = max(0, self.lock_bg_big.get_height() - self.H)
            vx = int(max(0, min(max_x, self.pan_x)))
            vy = int(max(0, min(max_y, self.pan_y)))
            view = pygame.Rect(vx, vy, self.W, self.H)
            target_surf.blit(self.lock_bg_big.subsurface(view), (0, 0))
        else:
            target_surf.fill((0, 0, 0))

        # Draw visible photo (fit/contain) on top
        if self.lock_fg and self.lock_fg_rect:
            target_surf.blit(self.lock_fg, self.lock_fg_rect)

    def _build_lock_frame_surface(self) -> pygame.Surface:
        surf = pygame.Surface((self.W, self.H))
        self._draw_lock_frame_to(surf)
        return surf

    # ---------------- status bar ----------------
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

    # ---------------- lock transitions ----------------
    def _snapshot_current_lock_view(self):
        self._draw_lock_frame_to(self.lock_snapshot)

    def _choose_break_style(self) -> str:
        mode = (LOCK_TRANSITION_STYLE or "random").lower().strip()
        styles = LOCK_TRANSITION_STYLES or ["shatter"]
        if mode == "random":
            return random.choice(styles)
        if mode in styles:
            return mode
        return "shatter"

    def _build_break_pieces(self, style: str):
        self.break_pieces = []
        style = (style or "shatter").lower()
        W, H = self.W, self.H
        snap = self.lock_snapshot

        if style == "blinds":
            strip_w = max(60, W // 14)
            i = 0
            for x in range(0, W, strip_w):
                w = min(strip_w, W - x)
                rect = pygame.Rect(x, 0, w, H)
                surf = snap.subsurface(rect).copy()

                delay = i * 0.03
                vy = random.uniform(650, 1050)
                vx = random.uniform(-40, 40)

                self.break_pieces.append({
                    "surf": surf,
                    "x": float(x),
                    "y": 0.0,
                    "vx": vx,
                    "vy": vy,
                    "ax": 0.0,
                    "ay": 900.0,
                    "delay": delay,
                })
                i += 1
            return

        # Tile-based effects
        if style == "explode":
            tile = max(120, min(220, int(min(W, H) * 0.12)))
        elif style == "drop":
            tile = max(110, min(200, int(min(W, H) * 0.11)))
        else:
            tile = max(90, min(190, LOCK_SHATTER_TILE_TARGET))

        cx0, cy0 = W * 0.5, H * 0.5

        for y in range(0, H, tile):
            for x in range(0, W, tile):
                w = min(tile, W - x)
                h = min(tile, H - y)
                rect = pygame.Rect(x, y, w, h)
                surf = snap.subsurface(rect).copy()

                pcx = x + w * 0.5
                pcy = y + h * 0.5
                dx = pcx - cx0
                dy = pcy - cy0
                mag = math.hypot(dx, dy) or 1.0
                nx, ny = dx / mag, dy / mag

                if style == "explode":
                    speed = random.uniform(520, 980)
                    vx = nx * speed + random.uniform(-120, 120)
                    vy = ny * speed + random.uniform(-120, 120)
                    ax, ay = 0.0, 0.0
                    delay = random.uniform(0.0, 0.05)
                elif style == "drop":
                    vx = random.uniform(-120, 120)
                    vy = random.uniform(-40, 180)
                    ax, ay = 0.0, 1400.0
                    delay = random.uniform(0.0, 0.12)
                else:  # shatter
                    vx = random.uniform(-240, 240)
                    vy = random.uniform(-520, -200)
                    ax, ay = 0.0, LOCK_SHATTER_GRAVITY
                    delay = random.uniform(0.0, 0.06)

                self.break_pieces.append({
                    "surf": surf,
                    "x": float(x),
                    "y": float(y),
                    "vx": vx,
                    "vy": vy,
                    "ax": ax,
                    "ay": ay,
                    "delay": delay,
                })

    def _start_lock_transition(self):
        self._snapshot_current_lock_view()

        style = self._choose_break_style()
        self.break_style = style
        self.break_dur = float(LOCK_BREAK_DURATIONS.get(style, 0.85))

        self._build_break_pieces(style)

        self.lock_trans = self.LOCK_TRANS_BREAK
        self.lock_trans_t0 = time.time()

    def _update_lock_effects(self, dt: float):
        # Always update pan while on lock (even during fade-in / break)
        self._update_pan(dt)

        if not LOCK_TRANSITION_ENABLE:
            if (time.time() - self.lock_cycle_t0) >= LOCK_BG_CYCLE_S:
                self._advance_image()
            return

        if self.lock_trans == self.LOCK_TRANS_BREAK:
            t = time.time() - self.lock_trans_t0
            for p in self.break_pieces:
                if t < p.get("delay", 0.0):
                    continue
                p["vx"] += p.get("ax", 0.0) * dt
                p["vy"] += p.get("ay", 0.0) * dt
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt

            if t >= self.break_dur:
                self._advance_image()
                self.lock_trans = self.LOCK_TRANS_FADEIN
                self.lock_trans_t0 = time.time()
            return

        if self.lock_trans == self.LOCK_TRANS_FADEIN:
            if (time.time() - self.lock_trans_t0) >= LOCK_FADEIN_S:
                self.lock_trans = self.LOCK_TRANS_NONE
                self.lock_cycle_t0 = time.time()
            return

        if (time.time() - self.lock_cycle_t0) >= LOCK_BG_CYCLE_S:
            self._start_lock_transition()

    def _draw_lock_background(self):
        if self.lock_trans == self.LOCK_TRANS_BREAK:
            self.screen.fill(COLOR_BG)
            t = time.time() - self.lock_trans_t0
            dur = max(0.001, float(self.break_dur))

            u = max(0.0, min(1.0, t / dur))
            alpha = int(255 * (1.0 - (u ** 1.4)))

            for p in self.break_pieces:
                surf = p["surf"]
                surf.set_alpha(alpha)
                self.screen.blit(surf, (int(p["x"]), int(p["y"])))
            return

        self._draw_lock_frame_to(self.screen)

        if self.lock_trans == self.LOCK_TRANS_FADEIN:
            t = time.time() - self.lock_trans_t0
            u = max(0.0, min(1.0, t / max(0.001, LOCK_FADEIN_S)))
            alpha = int(255 * (1.0 - u))
            overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, alpha))
            self.screen.blit(overlay, (0, 0))

    # ---------------- square puzzle ----------------
    def _make_tiles(self):
        tile_w = self.W // GRID_X
        tile_h = self.BOARD_H // GRID_Y

        tiles = []
        slot_positions = []
        for y in range(GRID_Y):
            for x in range(GRID_X):
                slot_positions.append((x * tile_w, y * tile_h))

        for slot_idx, (sx, sy) in enumerate(slot_positions):
            rect = pygame.Rect(sx, sy, tile_w, tile_h)
            tile_img = self.board_surf.subsurface(rect).copy()
            tiles.append({
                "image": tile_img,
                "slot": slot_idx,
                "correct": (sx, sy),
                "pos": (sx, sy),
                "locked": False,
                "fall_from": (sx, sy),
                "fall_to": (sx, sy),
            })
        return tiles, tile_w, tile_h, slot_positions

    def _tray_random_pos(self, tile_w, tile_h):
        x0 = TRAY_MARGIN
        x1 = self.W - TRAY_MARGIN - tile_w
        y0 = self.tray_rect.top + TRAY_MARGIN
        y1 = self.tray_rect.bottom - TRAY_MARGIN - tile_h
        if x1 < x0:
            x1 = x0
        if y1 < y0:
            y1 = y0
        return (random.randint(x0, x1), random.randint(y0, y1))

    def _tile_rect(self, tile):
        return pygame.Rect(tile["pos"], (self.tile_w, self.tile_h))

    def _nearest_slot(self, tile):
        px, py = tile["pos"]
        best_i, best_d2 = None, None
        for i, (sx, sy) in enumerate(self.slot_positions):
            d2 = dist2((px, py), (sx, sy))
            if best_d2 is None or d2 < best_d2:
                best_i, best_d2 = i, d2
        return best_i, math.sqrt(best_d2) if best_d2 is not None else 1e9

    def _rebuild_slot_occupancy(self):
        occ = {}
        for t in self.tiles:
            if t.get("locked"):
                occ[t["slot"]] = t
        return occ

    def _solved_all_locked(self):
        return all(t.get("locked") for t in self.tiles)

    def _auto_snap_lock(self, drag_tile):
        if drag_tile.get("locked"):
            return False
        nearest, d = self._nearest_slot(drag_tile)
        if d > SNAP_DIST:
            return False

        target_slot = nearest
        if target_slot != drag_tile["slot"]:
            return False

        target_pos = self.slot_positions[target_slot]
        occ = self._rebuild_slot_occupancy()
        occupant = occ.get(target_slot, None)
        if occupant and occupant is not drag_tile:
            occupant["locked"] = False
            occupant["pos"] = self._tray_random_pos(self.tile_w, self.tile_h)

        drag_tile["pos"] = target_pos
        drag_tile["locked"] = True
        return True

    def enter_square_puzzle(self):
        self.lock_trans = self.LOCK_TRANS_NONE
        self.tiles, self.tile_w, self.tile_h, self.slot_positions = self._make_tiles()
        self.drag_tile = None
        for t in self.tiles:
            t["locked"] = False
            t["pos"] = t["correct"]
            t["fall_from"] = t["correct"]
            t["fall_to"] = self._tray_random_pos(self.tile_w, self.tile_h)
        self.puz_stage = self.PUZ_INTRO
        self.puz_t0 = time.time()
        self.state = self.STATE_SQUARE

    def _rescramble_square_unlocked(self):
        for t in self.tiles:
            if not t.get("locked"):
                t["pos"] = self._tray_random_pos(self.tile_w, self.tile_h)

    # ---------------- jigsaw ----------------
    def enter_jig_select(self):
        self.lock_trans = self.LOCK_TRANS_NONE
        self.jigsaw_session = True
        self.state = self.STATE_JIG_SELECT

    def enter_jigsaw(self, cols, rows):
        self.jig_cols, self.jig_rows = int(cols), int(rows)
        self.jig_snap_dist = calc_jig_snap_dist(self.W, self.BOARD_H, self.jig_cols, self.jig_rows)

        self.jig_pieces = build_jigsaw_pieces(self.W, self.BOARD_H, self.board_surf, self.jig_cols, self.jig_rows)
        random.shuffle(self.jig_pieces)
        for p in self.jig_pieces:
            p["locked"] = False
            p["pos"] = p["correct_pos"]
            p["fall_from"] = p["correct_pos"]
            p["fall_to"] = tray_random_pos_sized(self.W, self.tray_rect, p["surf"].get_width(), p["surf"].get_height())

        self.jig_drag_piece = None
        self.jig_stage = self.JIG_INTRO
        self.jig_t0 = time.time()
        self.state = self.STATE_JIGSAW

    def back_to_lock(self):
        self.jigsaw_session = False
        self.state = self.STATE_LOCK
        self.lock_cycle_t0 = time.time()
        self.lock_trans = self.LOCK_TRANS_NONE
        if LOCK_UI_START_HIDDEN:
            self.lock_ui_visible_until = 0.0
            self.lock_pressed = None

    # ---------------- drawing helpers ----------------
    def _draw_tray(self):
        pygame.draw.rect(self.screen, COLOR_TRAY, self.tray_rect)
        pygame.draw.line(self.screen, COLOR_LINE, (0, self.tray_rect.top), (self.W, self.tray_rect.top), 2)

    def _draw_board_frame(self):
        pygame.draw.rect(self.screen, COLOR_LINE, self.board_rect, 2)

    # ---------------- lock dock interactions ----------------
    def _dock_hit(self, pos):
        if self.btn_unlock.collidepoint(pos):
            return "unlock"
        if self.btn_JigSaw.collidepoint(pos):
            return "JigSaw"
        if self.btn_admin.collidepoint(pos):
            return "admin"
        return None

    def _draw_lock_dock(self):
        a = clamp255(self.ui_alpha)
        if a <= 0:
            return

        draw_modern_dock(self.screen, self.dock_rect, a)

        mx, my = pygame.mouse.get_pos()
        hover_unlock = self.btn_unlock.collidepoint((mx, my))
        hover_JigSaw = self.btn_JigSaw.collidepoint((mx, my))
        hover_admin = self.btn_admin.collidepoint((mx, my))

        draw_modern_button(
            self.screen, self.btn_unlock, "Unlock", self.font_dock,
            _draw_icon_lock, ACCENT_UNLOCK,
            active=hover_unlock, pressed=(self.lock_pressed == "unlock"), alpha=a
        )
        draw_modern_button(
            self.screen, self.btn_JigSaw, "JigSaw", self.font_dock,
            _draw_icon_JigSaw, ACCENT_JigSaw,
            active=hover_JigSaw, pressed=(self.lock_pressed == "JigSaw"), alpha=a
        )
        draw_modern_button(
            self.screen, self.btn_admin, "Admin", self.font_dock,
            _draw_icon_key, ACCENT_ADMIN,
            active=hover_admin, pressed=(self.lock_pressed == "admin"), alpha=a
        )

    # ---------------- main loop ----------------
    def run(self):
        try:
            while True:
                dt = min(0.05, self.clock.tick(60) / 1000.0)

                for ev in pygame.event.get():
                    if ev.type == pygame.QUIT:
                        continue

                    # Interaction tracking for lock UI visibility
                    if self.state == self.STATE_LOCK:
                        if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN, pygame.FINGERMOTION):
                            self._touch_lock_ui()
                        elif ev.type == pygame.MOUSEMOTION:
                            mx, my = ev.pos
                            lx, ly = self.last_mouse_pos
                            if (abs(mx - lx) + abs(my - ly)) >= LOCK_UI_MOUSE_MOVE_THRESH:
                                self._touch_lock_ui()
                                self.last_mouse_pos = (mx, my)

                    # ESC returns to lock
                    if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                        if self.state != self.STATE_LOCK:
                            self.back_to_lock()
                        continue

                    # LOCK
                    if self.state == self.STATE_LOCK:
                        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN:
                            self.enter_square_puzzle()
                            continue

                        if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
                            pos = event_pos(ev, self.W, self.H)
                            if not pos:
                                continue

                            # First tap/click reveals UI only (no activation)
                            if not self._lock_ui_visible():
                                self._touch_lock_ui()
                                self.lock_pressed = None
                                continue

                            # Press tracking (activate on release)
                            self.lock_pressed = self._dock_hit(pos)

                        if ev.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
                            if not self._lock_ui_visible():
                                self.lock_pressed = None
                                continue
                            pos = event_pos(ev, self.W, self.H)
                            if not pos:
                                self.lock_pressed = None
                                continue
                            hit = self._dock_hit(pos)

                            if self.lock_pressed and hit == self.lock_pressed:
                                action = self.lock_pressed
                                self.lock_pressed = None

                                if action == "unlock":
                                    self.enter_square_puzzle()
                                    continue
                                if action == "JigSaw":
                                    self.enter_jig_select()
                                    continue
                                if action == "admin":
                                    bg_frame = self._build_lock_frame_surface()
                                    ok = pin_overlay_loop(self.screen, self.clock, self.W, self.H, bg_frame,
                                                         self.font, self.font_small, self.snd_error)
                                    if ok:
                                        unlock_success_overlay(self.screen, self.clock, self.W, self.H,
                                                             self.font_brand, self.font_small, self.snd_snap)
                                        self.exit_unlocked()
                                    continue
                            else:
                                self.lock_pressed = None

                    # SQUARE
                    elif self.state == self.STATE_SQUARE:
                        if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
                            pos = event_pos(ev, self.W, self.H)
                            if not pos:
                                continue
                            if self.back_btn["rect"].collidepoint(pos):
                                self.back_to_lock()
                                continue
                            if self.puz_stage != self.PUZ_PLAY:
                                continue

                            picked = None
                            for t in reversed(self.tiles):
                                if t.get("locked"):
                                    continue
                                if self._tile_rect(t).collidepoint(pos):
                                    picked = t
                                    break

                            if picked:
                                self.tiles.remove(picked)
                                self.tiles.append(picked)
                                self.drag_tile = picked
                                self.drag_ox = pos[0] - picked["pos"][0]
                                self.drag_oy = pos[1] - picked["pos"][1]
                                play(self.snd_pick)
                            else:
                                self._rescramble_square_unlocked()

                        elif ev.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
                            if self.puz_stage != self.PUZ_PLAY:
                                continue
                            if self.drag_tile:
                                locked_now = self._auto_snap_lock(self.drag_tile)
                                play(self.snd_snap if locked_now else self.snd_drop)
                                self.drag_tile = None
                                if self._solved_all_locked():
                                    unlock_success_overlay(self.screen, self.clock, self.W, self.H,
                                                         self.font_brand, self.font_small, self.snd_snap)
                                    self.exit_unlocked()

                        elif ev.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
                            if self.puz_stage != self.PUZ_PLAY or not self.drag_tile:
                                continue
                            pos = event_pos(ev, self.W, self.H)
                            if not pos:
                                continue
                            self.drag_tile["pos"] = (pos[0] - self.drag_ox, pos[1] - self.drag_oy)
                            if self._auto_snap_lock(self.drag_tile):
                                play(self.snd_snap)
                                self.drag_tile = None
                                if self._solved_all_locked():
                                    unlock_success_overlay(self.screen, self.clock, self.W, self.H,
                                                         self.font_brand, self.font_small, self.snd_snap)
                                    self.exit_unlocked()

                    # JIG SELECT
                    elif self.state == self.STATE_JIG_SELECT:
                        if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
                            pos = event_pos(ev, self.W, self.H)
                            if not pos:
                                continue
                            if self.back_btn["rect"].collidepoint(pos):
                                self.back_to_lock()
                                continue

                            box_w = min(720, int(self.W * 0.68))
                            box_h = min(520, int(self.H * 0.62))
                            box_x = (self.W - box_w) // 2
                            box_y = (self.H - box_h) // 2
                            option_h = 64
                            gap = 12
                            y = box_y + 90

                            for label, c, r in JIG_DIFFICULTY_CHOICES:
                                rect = pygame.Rect(box_x + 24, y, box_w - 48, option_h)
                                if rect.collidepoint(pos):
                                    self.enter_jigsaw(c, r)
                                    break
                                y += option_h + gap

                    # JIGSAW
                    elif self.state == self.STATE_JIGSAW:
                        if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
                            pos = event_pos(ev, self.W, self.H)
                            if not pos:
                                continue
                            if self.back_btn["rect"].collidepoint(pos):
                                self.back_to_lock()
                                continue
                            if self.jig_stage != self.JIG_PLAY:
                                continue

                            picked = None
                            for p in reversed(self.jig_pieces):
                                if p.get("locked"):
                                    continue
                                px, py = p["pos"]
                                lx = pos[0] - px
                                ly = pos[1] - py
                                if 0 <= lx < p["surf"].get_width() and 0 <= ly < p["surf"].get_height():
                                    if p["mask"].get_at((int(lx), int(ly))):
                                        picked = p
                                        break

                            if picked:
                                self.jig_pieces.remove(picked)
                                self.jig_pieces.append(picked)
                                self.jig_drag_piece = picked
                                self.jig_drag_ox = pos[0] - picked["pos"][0]
                                self.jig_drag_oy = pos[1] - picked["pos"][1]
                                play(self.snd_pick)
                            else:
                                for p in self.jig_pieces:
                                    if not p.get("locked"):
                                        p["pos"] = tray_random_pos_sized(self.W, self.tray_rect,
                                                                        p["surf"].get_width(), p["surf"].get_height())

                        elif ev.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
                            if self.jig_stage != self.JIG_PLAY:
                                continue
                            if self.jig_drag_piece:
                                p = self.jig_drag_piece
                                cx, cy = p["correct_pos"]
                                x, y = p["pos"]
                                d = math.hypot(x - cx, y - cy)

                                if d <= self.jig_snap_dist:
                                    p["pos"] = p["correct_pos"]
                                    p["locked"] = True
                                    play(self.snd_snap)
                                else:
                                    play(self.snd_drop)

                                self.jig_drag_piece = None

                                if jigsaw_all_locked(self.jig_pieces):
                                    self.jig_stage = self.JIG_SOLVED
                                    self.jig_t0 = time.time()

                        elif ev.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
                            if self.jig_stage != self.JIG_PLAY or not self.jig_drag_piece:
                                continue
                            pos = event_pos(ev, self.W, self.H)
                            if not pos:
                                continue
                            self.jig_drag_piece["pos"] = (pos[0] - self.jig_drag_ox, pos[1] - self.jig_drag_oy)

                # Updates / transitions
                if self.state == self.STATE_LOCK:
                    self._update_lock_effects(dt)

                    # Dock fade alpha toward visible state
                    target = 255.0 if self._lock_ui_visible() else 0.0
                    if abs(target - self.ui_alpha) > 0.5:
                        k = min(1.0, dt / max(0.001, LOCK_UI_FADE_S))
                        self.ui_alpha = self.ui_alpha + (target - self.ui_alpha) * k
                    else:
                        self.ui_alpha = target

                if self.state == self.STATE_SQUARE:
                    elapsed = time.time() - self.puz_t0
                    if self.puz_stage == self.PUZ_INTRO:
                        if elapsed >= PUZ_INTRO_HOLD_S:
                            self.puz_stage = self.PUZ_FALL
                            self.puz_t0 = time.time()
                    elif self.puz_stage == self.PUZ_FALL:
                        t = min(1.0, elapsed / max(0.001, PUZ_FALL_S))
                        tx = _ease_out_cubic(t)
                        ty = _ease_in_quad(t)
                        for tile in self.tiles:
                            x0, y0 = tile["fall_from"]
                            x1, y1 = tile["fall_to"]
                            tile["pos"] = (int(x0 + (x1 - x0) * tx), int(y0 + (y1 - y0) * ty))
                        if t >= 1.0:
                            self.puz_stage = self.PUZ_PLAY
                            self.puz_t0 = time.time()

                if self.state == self.STATE_JIGSAW:
                    elapsed = time.time() - self.jig_t0
                    if self.jig_stage == self.JIG_INTRO:
                        if elapsed >= JIG_INTRO_HOLD_S:
                            self.jig_stage = self.JIG_FALL
                            self.jig_t0 = time.time()
                    elif self.jig_stage == self.JIG_FALL:
                        t = min(1.0, elapsed / max(0.001, JIG_FALL_S))
                        tx = _ease_out_cubic(t)
                        ty = _ease_in_quad(t)
                        for p in self.jig_pieces:
                            x0, y0 = p["fall_from"]
                            x1, y1 = p["fall_to"]
                            p["pos"] = (int(x0 + (x1 - x0) * tx), int(y0 + (y1 - y0) * ty))
                        if t >= 1.0:
                            self.jig_stage = self.JIG_PLAY
                            self.jig_t0 = time.time()
                    elif self.jig_stage == self.JIG_SOLVED:
                        if elapsed >= JIG_SOLVED_HOLD_S:
                            if self.jigsaw_session:
                                unlock_success_overlay(self.screen, self.clock, self.W, self.H,
                                                     self.font_brand, self.font_small, self.snd_snap,
                                                     msg="PUZZLE SOLVED", sub="Loading next image...", hold_s=0.65)
                                self._advance_image()
                                self.enter_jigsaw(self.jig_cols, self.jig_rows)
                            else:
                                unlock_success_overlay(self.screen, self.clock, self.W, self.H,
                                                     self.font_brand, self.font_small, self.snd_snap)
                                self.exit_unlocked()

                # Draw
                self.screen.fill(COLOR_BG)

                # LOCK
                if self.state == self.STATE_LOCK:
                    self._draw_lock_background()
                    self._draw_status_bar()

                    pulse = 0.5 + 0.5 * math.sin(time.time() * 1.5)
                    brand_color = (255, 255, int(180 + 60 * pulse))
                    bt = self.font_brand.render(BRAND_TEXT, True, brand_color)
                    bs = self.font_brand2.render(BRAND_SUB, True, (230, 230, 230))
                    y0 = STATUS_BAR_H + 10 if SHOW_STATUS_BAR else 18
                    self.screen.blit(bt, (self.W // 2 - bt.get_width() // 2, y0))
                    self.screen.blit(bs, (self.W // 2 - bs.get_width() // 2, y0 + bt.get_height() + 6))

                    # Dock (modern buttons)
                    self._draw_lock_dock()

                    # Hint line (always)
                    if self._lock_ui_visible() or self.ui_alpha > 40:
                        hint = self.font_small.render("", True, (230, 230, 230))
                    else:
                        hint = self.font_small.render("Tap to show options", True, (230, 230, 230))
                    self.screen.blit(hint, (self.W // 2 - hint.get_width() // 2, self.H - 42))

                # SQUARE
                elif self.state == self.STATE_SQUARE:
                    if self.puz_stage == self.PUZ_INTRO:
                        bg = self._build_lock_frame_surface()
                        self.screen.blit(bg, (0, 0))
                        mx, my = pygame.mouse.get_pos()
                        draw_button(self.screen, self.back_btn, self.font, self.font_small,
                                    active=self.back_btn["rect"].collidepoint((mx, my)), small=True)
                        msg = self.font_small.render("Preparing puzzle...", True, (235, 235, 235))
                        self.screen.blit(msg, (self.W // 2 - msg.get_width() // 2, self.H - 42))
                    else:
                        pygame.draw.rect(self.screen, COLOR_BG, self.board_rect)
                        self._draw_tray()
                        self._draw_board_frame()

                        for x in range(1, GRID_X):
                            pygame.draw.line(self.screen, (35, 35, 35), (x * self.tile_w, 0), (x * self.tile_w, self.BOARD_H), 1)
                        for y in range(1, GRID_Y):
                            pygame.draw.line(self.screen, (35, 35, 35), (0, y * self.tile_h), (self.W, y * self.tile_h), 1)

                        for t in self.tiles:
                            self.screen.blit(t["image"], t["pos"])
                            if t.get("locked"):
                                pygame.draw.rect(self.screen, (0, 255, 0), pygame.Rect(t["pos"], (self.tile_w, self.tile_h)), 3)

                        mx, my = pygame.mouse.get_pos()
                        draw_button(self.screen, self.back_btn, self.font, self.font_small,
                                    active=self.back_btn["rect"].collidepoint((mx, my)), small=True)

                        hint = self.font_small.render(
                            "Drag tiles into place. Tap empty to re-scramble." if self.puz_stage == self.PUZ_PLAY else "Breaking...",
                            True, (230, 230, 230)
                        )
                        self.screen.blit(hint, (16, self.BOARD_H - 32))

                # JIG SELECT
                elif self.state == self.STATE_JIG_SELECT:
                    bg = self._build_lock_frame_surface()
                    self.screen.blit(bg, (0, 0))
                    overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
                    overlay.fill((0, 0, 0, 175))
                    self.screen.blit(overlay, (0, 0))

                    mx, my = pygame.mouse.get_pos()
                    draw_button(self.screen, self.back_btn, self.font, self.font_small,
                                active=self.back_btn["rect"].collidepoint((mx, my)), small=True)

                    box_w = min(720, int(self.W * 0.68))
                    box_h = min(520, int(self.H * 0.62))
                    box_x = (self.W - box_w) // 2
                    box_y = (self.H - box_h) // 2
                    pygame.draw.rect(self.screen, (35, 35, 35), pygame.Rect(box_x, box_y, box_w, box_h), border_radius=18)
                    pygame.draw.rect(self.screen, (230, 230, 230), pygame.Rect(box_x, box_y, box_w, box_h), 2, border_radius=18)

                    title = self.font.render("JIGSAW DIFFICULTY", True, (255, 255, 255))
                    sub = self.font_small.render("Select a grid size (more pieces = harder)", True, (230, 230, 230))
                    self.screen.blit(title, (self.W // 2 - title.get_width() // 2, box_y + 20))
                    self.screen.blit(sub, (self.W // 2 - sub.get_width() // 2, box_y + 60))

                    option_h = 64
                    gap = 12
                    y = box_y + 90
                    for label, c, r in JIG_DIFFICULTY_CHOICES:
                        rect = pygame.Rect(box_x + 24, y, box_w - 48, option_h)
                        btn = make_button(rect, f"{label} | {c} x {r}", color=(120, 120, 120))
                        draw_button(self.screen, btn, self.font, self.font_small, active=rect.collidepoint((mx, my)), small=True)
                        y += option_h + gap

                # JIGSAW
                elif self.state == self.STATE_JIGSAW:
                    if self.jig_stage == self.JIG_INTRO:
                        bg = self._build_lock_frame_surface()
                        self.screen.blit(bg, (0, 0))
                        mx, my = pygame.mouse.get_pos()
                        draw_button(self.screen, self.back_btn, self.font, self.font_small,
                                    active=self.back_btn["rect"].collidepoint((mx, my)), small=True)
                    else:
                        self.screen.blit(self.board_surf, (0, 0))
                        if self.jig_stage in (self.JIG_PLAY, self.JIG_SOLVED) and JIG_BG_DIM_ALPHA > 0:
                            dim = pygame.Surface((self.W, self.BOARD_H), pygame.SRCALPHA)
                            dim.fill((0, 0, 0, JIG_BG_DIM_ALPHA))
                            self.screen.blit(dim, (0, 0))

                        self._draw_tray()

                        for p in self.jig_pieces:
                            self.screen.blit(p["surf"], p["pos"])
                            if p.get("locked"):
                                pygame.draw.rect(self.screen, (0, 180, 0), pygame.Rect(p["pos"], p["surf"].get_size()), 2)

                        mx, my = pygame.mouse.get_pos()
                        draw_button(self.screen, self.back_btn, self.font, self.font_small,
                                    active=self.back_btn["rect"].collidepoint((mx, my)), small=True)

                        hint = self.font_small.render(
                            "Drag pieces into place. Tap empty to re-scramble." if self.jig_stage == self.JIG_PLAY else
                            ("Breaking..." if self.jig_stage == self.JIG_FALL else "Solved. Loading next image..."),
                            True, (230, 230, 230)
                        )
                        self.screen.blit(hint, (16, self.BOARD_H - 32))

                pygame.display.flip()

        except SystemExit:
            raise
        except Exception as e:
            try:
                print(f"FATAL: {e}", file=sys.stderr)
            except Exception:
                pass
            sys.exit(1)
        finally:
            try:
                pygame.quit()
            except Exception:
                pass

# ============================================================
# Entrypoint
# ============================================================
if __name__ == "__main__":
    LockApp().run()
