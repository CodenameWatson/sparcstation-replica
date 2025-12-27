# -*- coding: utf-8 -*-
import pygame
import random
import os
import subprocess
import sys
import time
import math
import shutil
import socket
import datetime

# ---------------- CONFIG ----------------
GRID_X = 3
GRID_Y = 4

# snap/lock (touch-friendly) — square puzzle
SNAP_DIST = 190  # px from slot to auto-snap+lock

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "images")
SOUNDS_DIR = os.path.join(BASE_DIR, "sounds")

# QEMU control
QEMU_PIDFILE = "/home/pi/sparc_vm/qemu-sparc.pid"
RUN_QEMU_CMD = ["/home/pi/sparc_vm/run_sol8.sh"]  # headless QEMU with VNC :1
VM_VNC_TARGET = "127.0.0.1:1"
VM_VNC_HOST = "127.0.0.1"
VM_VNC_PORT = 5901  # :1

# VNC viewer args (kiosk-safe)
VNCVIEWER_ARGS = [
    "-FullScreen=1",
    "-Shared=1",
    "-RemoteResize=0",
    "-AcceptClipboard=0",
    "-SendClipboard=0",
    "-FullscreenSystemKeys=1",
]
VNCVIEWER_LOG = "/home/pi/sparc_lock/vncviewer.log"
LAUNCH_SOLARIS_SH = "/home/pi/sparc_lock/launch_solaris.sh"

# Exit code used to signal "switch to Pi desktop" to the session wrapper
ADMIN_DESKTOP_EXIT_CODE = 42

# Auto re-lock after inactivity while VM is shown (milliseconds)
VM_IDLE_LOCK_MS = 1 * 30 * 1000  # 30 seconds

# VM idle/relock tracking (xprintidle-based)
VM_IDLE_POLL_MS = 500
VM_IDLE_ACTIVITY_DROP_MS = 1500  # idle drops by ~this much => user activity occurred

# Layout: tray appears only in puzzle modes
TRAY_H_FRAC = 0.28
TRAY_MARGIN = 14

# Sounds (optional; place wav files in ./sounds/)
SND_PICK = "pick.wav"
SND_DROP = "drop.wav"
SND_SNAP = "snap.wav"
SND_ERROR = "error.wav"

# Branding
BRAND_TEXT = "Glover SPARCstation"
BRAND_SUB = "Puzzle Unlock"

ADMIN_PIN = "1193"

# ---- Lock/Attract UI behavior ----
LOCK_UI_TIMEOUT_S = 12.0      # controls hide after inactivity on lock screen
LOCK_SHOW_STATUS_BAR = True
STATUS_BAR_H = 40

# ---- ATTRACT (lock screen) animation cycle ----
# Shows full image, breaks into tiles, scrambles, assembles, then switches to a new image.
ATTR_WHOLE_HOLD_S = 1.20
ATTR_BREAK_S = 0.55
ATTR_SCRAMBLE_S = 10.0
ATTR_ASSEMBLE_S = 1.00
ATTR_POST_ASSEMBLE_S = 0.60
ATTR_DRIFT_SPEED_MIN = 90
ATTR_DRIFT_SPEED_MAX = 210

# FULL-SCREEN attract grid (includes old tray area)
ATTR_GRID_X = GRID_X
ATTR_GRID_Y = GRID_Y + 1

# ---- Square puzzle start animation ----
PUZ_INTRO_HOLD_S = 0.70       # show full image before breaking
PUZ_FALL_S = 0.90             # tiles fall into tray

# ---- Random break FX (square + jigsaw + attract) ----
BREAK_PROB_CRACK = 0.70
BREAK_PROB_SHAKE = 0.70
BREAK_PROB_SOUND = 0.65

BREAK_SHAKE_DUR_S_MIN = 0.18
BREAK_SHAKE_DUR_S_MAX = 0.40
BREAK_SHAKE_AMP_MIN = 5
BREAK_SHAKE_AMP_MAX = 12

CRACK_LINES_MIN = 12
CRACK_LINES_MAX = 24
CRACK_ALPHA = 135            # baseline alpha; fade handled separately
CRACK_FADE_S = 0.70

# ---- Unlock success (square puzzle) ----
UNLOCK_SUCCESS_S = 0.85

# ---------------- JIGSAW MODE CONFIG ----------------
JIG_KNOB_FRAC = 0.22
JIG_EDGE_OFF_FRAC = 0.18

# Jigsaw snapping: compute per-grid from cell size, with clamps (prevents tiny-piece modes from feeling “magnetic”)
JIG_SNAP_FRAC = 0.55   # snap distance = JIG_SNAP_FRAC * min(cell_w, cell_h)
JIG_SNAP_MIN = 40
JIG_SNAP_MAX = 140

JIG_INTRO_HOLD_S = 0.65       # show full image before fall
JIG_FALL_S = 0.90
JIG_SOLVED_HOLD_S = 0.85
JIG_BG_DIM_ALPHA = 140        # 0 = blank background in play, else dim image by overlay alpha
# ----------------------------------------------------

JIG_DIFFICULTY_CHOICES = [
    ("Easy",    3, 2),
    ("Normal",  4, 3),
    ("Hard",    5, 4),
    ("Expert",  6, 4),
    ("Insane", 10, 5),   # 50 pieces: 128×115 cells on a 1280×576 board
    ("Extreme",12, 5),   # 60 pieces: 106×115 cells (hard, still workable)
]

# ---------------- UI COLORS ----------------
COLOR_BG = (0, 0, 0)
COLOR_TRAY = (18, 18, 18)
COLOR_LINE = (70, 70, 70)
COLOR_TEXT = (255, 255, 255)

COLOR_START = (0, 160, 90)
COLOR_PI = (197, 29, 52)
COLOR_SOLARIS = (102, 190, 255)
COLOR_JIGSAW = (120, 120, 120)
COLOR_HOME = (120, 120, 120)
COLOR_CANCEL = (120, 120, 120)
# -------------------------------------------


def now_ms() -> int:
    return int(time.time() * 1000)


def qemu_is_running() -> bool:
    try:
        with open(QEMU_PIDFILE, "r") as f:
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
            os.remove(QEMU_PIDFILE)
        except OSError:
            pass
        return False
    except Exception:
        return False


def ensure_qemu_running():
    if qemu_is_running():
        return
    try:
        subprocess.Popen(
            RUN_QEMU_CMD,
            cwd="/home/pi/sparc_vm",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        time.sleep(1.0)
    except Exception:
        pass


# ---------- Pygame init ----------
pygame.init()
try:
    pygame.mixer.init()
except Exception:
    pass

screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.display.set_caption("SPARC Lock")
clock = pygame.time.Clock()
W, H = screen.get_size()

pygame.mouse.set_visible(True)

font = pygame.font.SysFont(None, 52)
font_small = pygame.font.SysFont(None, 26)
font_brand = pygame.font.SysFont(None, 64)
font_brand2 = pygame.font.SysFont(None, 28)


# ---------- Sounds ----------
def load_sound(name):
    path = os.path.join(SOUNDS_DIR, name)
    if os.path.exists(path):
        try:
            return pygame.mixer.Sound(path)
        except Exception:
            return None
    return None


snd_pick = load_sound(SND_PICK)
snd_drop = load_sound(SND_DROP)
snd_snap = load_sound(SND_SNAP)
snd_error = load_sound(SND_ERROR)


def play(snd):
    if snd:
        try:
            snd.play()
        except Exception:
            pass


# ---------- Regions ----------
TRAY_H = int(H * TRAY_H_FRAC)
BOARD_H = H - TRAY_H

board_rect = pygame.Rect(0, 0, W, BOARD_H)
tray_rect = pygame.Rect(0, BOARD_H, W, TRAY_H)


def calc_jig_snap_dist(cols: int, rows: int) -> int:
    cols = max(1, int(cols))
    rows = max(1, int(rows))
    cell_w = W // cols
    cell_h = BOARD_H // rows
    base = int(min(cell_w, cell_h) * JIG_SNAP_FRAC)
    return max(JIG_SNAP_MIN, min(JIG_SNAP_MAX, base))


# ---------- High-quality image scaling (cover-crop) ----------
def scale_cover(src_surf, target_w, target_h):
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


# ---------- Images ----------
def load_images():
    imgs = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith((".jpg", ".png"))]
    if not imgs:
        print(f"No images found in {IMAGE_DIR}")
        sys.exit(1)
    return imgs


images = load_images()


def pick_image_surfaces():
    """
    Returns:
      lock_surf:  W x H   (full-screen cover-crop)
      board_surf: W x BOARD_H (top slice of lock_surf so cropping matches exactly)
      fname
    """
    fname = random.choice(images)
    raw = pygame.image.load(os.path.join(IMAGE_DIR, fname)).convert()
    lock_surf = scale_cover(raw, W, H)
    board_surf = lock_surf.subsurface(pygame.Rect(0, 0, W, BOARD_H)).copy()
    return lock_surf, board_surf, fname


# ---------- Tray / Board ----------
def draw_tray():
    pygame.draw.rect(screen, COLOR_TRAY, tray_rect)
    pygame.draw.line(screen, COLOR_LINE, (0, tray_rect.top), (W, tray_rect.top), 2)
    txt = font_small.render("TRAY", True, (210, 210, 210))
    screen.blit(txt, (16, tray_rect.top + 10))


def draw_board_frame():
    pygame.draw.rect(screen, COLOR_LINE, board_rect, 2)


# ---------- UI buttons ----------
def clamp255(v):
    return max(0, min(255, int(v)))


def lighten(color, amt=22):
    return (clamp255(color[0] + amt), clamp255(color[1] + amt), clamp255(color[2] + amt))


def make_button(rect, label, color=(90, 90, 90)):
    return {"rect": rect, "label": label, "color": color}


def draw_button(btn, active=False, small=False):
    r = btn["rect"]
    base = btn.get("color", (90, 90, 90))
    bg = base if not active else lighten(base, 28)

    pygame.draw.rect(screen, bg, r, border_radius=16)
    pygame.draw.rect(screen, (230, 230, 230), r, 2, border_radius=16)

    f = font_small if small else font
    t = f.render(btn["label"], True, (255, 255, 255))
    screen.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))


def draw_status_bar():
    if not LOCK_SHOW_STATUS_BAR:
        return
    bar = pygame.Surface((W, STATUS_BAR_H), pygame.SRCALPHA)
    bar.fill((0, 0, 0, 140))
    screen.blit(bar, (0, 0))

    now = datetime.datetime.now()
    txt = now.strftime("%a %b %d   %I:%M %p").lstrip("0")
    t = font_small.render(txt, True, (230, 230, 230))
    screen.blit(t, (W - t.get_width() - 16, (STATUS_BAR_H - t.get_height()) // 2))


# ---------- Square tiles ----------
def make_tiles(board_surf):
    tile_w = W // GRID_X
    tile_h = BOARD_H // GRID_Y

    tiles = []
    slot_positions = []

    for y in range(GRID_Y):
        for x in range(GRID_X):
            slot_positions.append((x * tile_w, y * tile_h))

    for slot_idx, (sx, sy) in enumerate(slot_positions):
        rect = pygame.Rect(sx, sy, tile_w, tile_h)
        tile_img = board_surf.subsurface(rect).copy()
        tiles.append({
            "image": tile_img,
            "correct": (sx, sy),
            "slot": slot_idx,
            "pos": (sx, sy),
            "locked": False,
            "fall_from": (sx, sy),
            "fall_to": (sx, sy),
        })

    return tiles, tile_w, tile_h, slot_positions


def tray_random_pos(tile_w, tile_h):
    x0 = TRAY_MARGIN
    x1 = W - TRAY_MARGIN - tile_w
    y0 = tray_rect.top + TRAY_MARGIN
    y1 = tray_rect.bottom - TRAY_MARGIN - tile_h
    if x1 < x0:
        x1 = x0
    if y1 < y0:
        y1 = y0
    return (random.randint(x0, x1), random.randint(y0, y1))


def tray_random_pos_sized(obj_w, obj_h):
    x0 = TRAY_MARGIN
    x1 = W - TRAY_MARGIN - obj_w
    y0 = tray_rect.top + TRAY_MARGIN
    y1 = tray_rect.bottom - TRAY_MARGIN - obj_h
    if x1 < x0:
        x1 = x0
    if y1 < y0:
        y1 = y0
    return (random.randint(x0, x1), random.randint(y0, y1))


def tile_rect(tile, tile_w, tile_h):
    return pygame.Rect(tile["pos"], (tile_w, tile_h))


# ---------- Slot snapping (square puzzle) ----------
def dist2(a, b):
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return dx * dx + dy * dy


def nearest_slot(tile, slot_positions):
    px, py = tile["pos"]
    best = None
    best_d2 = None
    for i, (sx, sy) in enumerate(slot_positions):
        d2 = dist2((px, py), (sx, sy))
        if best_d2 is None or d2 < best_d2:
            best = i
            best_d2 = d2
    return best, math.sqrt(best_d2) if best_d2 is not None else 1e9


def rebuild_slot_occupancy(tiles):
    occ = {}
    for t in tiles:
        if t.get("locked"):
            occ[t["slot"]] = t
    return occ


def solved_all_locked(tiles):
    return all(t.get("locked") for t in tiles)


def auto_snap_lock_with_swap(drag_tile, slot_positions, occ, tile_w, tile_h):
    if drag_tile.get("locked"):
        return False

    nearest, d = nearest_slot(drag_tile, slot_positions)
    if d > SNAP_DIST:
        return False

    target_slot = nearest
    target_pos = slot_positions[target_slot]

    if target_slot != drag_tile["slot"]:
        return False

    occupant = occ.get(target_slot, None)
    if occupant and occupant is not drag_tile:
        occupant["locked"] = False
        occupant["pos"] = tray_random_pos(tile_w, tile_h)

    drag_tile["pos"] = target_pos
    drag_tile["locked"] = True
    occ[target_slot] = drag_tile
    return True


# ---------- Break FX: crack overlay + shake + sound (randomized) ----------
def make_crack_overlay(w, h, lines=18, seed=None):
    rnd = random.Random(seed if seed is not None else random.randint(0, 10_000_000))
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    cx = rnd.randint(int(w * 0.35), int(w * 0.65))
    cy = rnd.randint(int(h * 0.25), int(h * 0.75))

    for _ in range(lines):
        ang = rnd.uniform(0, math.tau)
        length = rnd.uniform(w * 0.25, w * 0.80)
        x = cx
        y = cy
        pts = [(x, y)]
        steps = rnd.randint(6, 13)
        for i in range(steps):
            frac = (i + 1) / steps
            jx = rnd.uniform(-11, 11)
            jy = rnd.uniform(-11, 11)
            x = cx + math.cos(ang) * length * frac + jx
            y = cy + math.sin(ang) * length * frac + jy
            pts.append((x, y))

        pygame.draw.lines(surf, (255, 255, 255, CRACK_ALPHA), False, pts, 2)
        pygame.draw.lines(surf, (255, 255, 255, max(0, CRACK_ALPHA - 70)), False, pts, 4)

    return surf


def start_break_fx(w, h):
    """
    Dimension-aware break FX:
      - square/jigsaw use (W, BOARD_H)
      - attract uses (W, H)
    """
    fx = {
        "t0": time.time(),
        "use_crack": (random.random() < BREAK_PROB_CRACK),
        "use_shake": (random.random() < BREAK_PROB_SHAKE),
        "use_sound": (random.random() < BREAK_PROB_SOUND),
        "crack_surf": None,
        "shake_until": 0.0,
        "shake_amp": 0,
    }

    if fx["use_crack"]:
        fx["crack_surf"] = make_crack_overlay(w, h, lines=random.randint(CRACK_LINES_MIN, CRACK_LINES_MAX))

    if fx["use_shake"]:
        dur = random.uniform(BREAK_SHAKE_DUR_S_MIN, BREAK_SHAKE_DUR_S_MAX)
        fx["shake_until"] = fx["t0"] + dur
        fx["shake_amp"] = random.randint(BREAK_SHAKE_AMP_MIN, BREAK_SHAKE_AMP_MAX)

    if fx["use_sound"]:
        choices = []
        if snd_snap:
            choices.append(snd_snap)
        if snd_drop:
            choices.append(snd_drop)
        if snd_pick:
            choices.append(snd_pick)
        if choices:
            play(random.choice(choices))

    return fx


def break_shake_offset(fx):
    if not fx or not fx.get("use_shake"):
        return 0, 0
    if time.time() > fx.get("shake_until", 0.0):
        return 0, 0
    amp = fx.get("shake_amp", 0)
    return random.randint(-amp, amp), random.randint(-amp, amp)


def draw_crack_overlay_fade(fx):
    """
    Draw crack overlay (whatever size the crack surface is) at (0,0) with fade-out.
    """
    if not fx or not fx.get("use_crack") or not fx.get("crack_surf"):
        return
    elapsed = time.time() - fx.get("t0", time.time())
    fade = 1.0 - min(1.0, elapsed / max(0.001, CRACK_FADE_S))
    if fade <= 0:
        return
    crack = fx["crack_surf"].copy()
    crack.set_alpha(int(255 * fade))
    screen.blit(crack, (0, 0))


# ---------- ATTRACT animation helpers ----------
def lerp(a, b, t):
    return a + (b - a) * t


def lerp_pos(p0, p1, t):
    return (int(lerp(p0[0], p1[0], t)), int(lerp(p0[1], p1[1], t)))


def set_random_vel(tile):
    vx = random.uniform(ATTR_DRIFT_SPEED_MIN, ATTR_DRIFT_SPEED_MAX) * random.choice([-1, 1])
    vy = random.uniform(ATTR_DRIFT_SPEED_MIN, ATTR_DRIFT_SPEED_MAX) * random.choice([-1, 1])
    tile["vel"] = (vx, vy)


def make_tiles_fullscreen(full_surf, cols, rows):
    """
    Tiles that cover the entire screen W x H (includes the old tray area).
    Last row/col expand to absorb remainder pixels so there are no un-tiled strips.
    """
    tile_w_base = W // cols
    tile_h_base = H // rows

    tiles = []
    for y in range(rows):
        for x in range(cols):
            sx = x * tile_w_base
            sy = y * tile_h_base
            tw = tile_w_base if x < cols - 1 else (W - sx)
            th = tile_h_base if y < rows - 1 else (H - sy)

            rect = pygame.Rect(sx, sy, tw, th)
            img = full_surf.subsurface(rect).copy()
            tiles.append({
                "image": img,
                "correct": (sx, sy),
                "pos": (sx, sy),
                "w": tw,
                "h": th,
                "vel": (0.0, 0.0),
            })
    return tiles


def scatter_pos_full(tw, th):
    x0 = TRAY_MARGIN
    x1 = W - TRAY_MARGIN - tw
    y0 = TRAY_MARGIN
    y1 = H - TRAY_MARGIN - th
    if x1 < x0:
        x1 = x0
    if y1 < y0:
        y1 = y0
    return (random.randint(x0, x1), random.randint(y0, y1))


# ---------- JIGSAW helpers ----------
def _ease_in_quad(t):
    return t * t


def _ease_out_cubic(t):
    u = 1.0 - t
    return 1.0 - (u * u * u)


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


def build_jigsaw_pieces(board_surf, cols, rows):
    # NOTE: Keep uniform cell sizes for consistent edge matching across pieces.
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


def jigsaw_all_locked(pieces):
    return all(p.get("locked") for p in pieces)


# ---------- VM ----------
def enter_vm_mode():
    ensure_qemu_running()
    if not qemu_is_running():
        return
    try:
        os.execv(LAUNCH_SOLARIS_SH, [LAUNCH_SOLARIS_SH])
    except Exception:
        return


def open_pi_desktop():
    try:
        pygame.quit()
    except Exception:
        pass
    sys.exit(ADMIN_DESKTOP_EXIT_CODE)


# ---------- Lock UI visibility ----------
lock_ui_visible = False
lock_ui_until = 0.0


def wake_lock_ui():
    global lock_ui_visible, lock_ui_until
    lock_ui_visible = True
    lock_ui_until = time.time() + LOCK_UI_TIMEOUT_S


def update_lock_ui_timeout():
    global lock_ui_visible
    if lock_ui_visible and time.time() > lock_ui_until:
        lock_ui_visible = False


# ---------- PIN overlay ----------
STATE_ATTRACT = "ATTRACT"
STATE_PUZZLE = "PUZZLE"
STATE_PIN = "PIN"
STATE_JIG_SELECT = "JIG_SELECT"
STATE_JIGSAW = "JIGSAW"

PIN_ACTION_SOLARIS = "SOLARIS"
PIN_ACTION_PI = "PI"

pin_action = PIN_ACTION_SOLARIS
pin_return_state = STATE_ATTRACT
pin_input = ""
pin_error = ""
pin_error_t0 = 0.0


def open_pin_prompt(action, return_state=STATE_ATTRACT):
    global pin_action, pin_return_state, pin_input, pin_error
    global state
    state = STATE_PIN
    pin_action = action
    pin_return_state = return_state
    pin_input = ""
    pin_error = ""


def close_pin_prompt():
    global state, pin_input, pin_error
    pin_input = ""
    pin_error = ""
    state = pin_return_state


def pin_submit():
    global pin_input, pin_error, pin_error_t0
    if pin_input == ADMIN_PIN:
        if pin_action == PIN_ACTION_SOLARIS:
            enter_vm_mode()
        elif pin_action == PIN_ACTION_PI:
            open_pi_desktop()
    else:
        pin_error = "Incorrect PIN"
        pin_error_t0 = time.time()
        pin_input = ""
        play(snd_error)


# ---------- Unlock success (square puzzle) ----------
def unlock_success_and_enter_vm():
    """
    Brief 'UNLOCKED' overlay, then hand off to Solaris viewer via enter_vm_mode().

    Per your request:
      - Do NOT show the full image again here (no lock_surf/board_surf background).
    """
    t0 = time.time()
    play(snd_snap)

    while True:
        elapsed = time.time() - t0
        if elapsed >= UNLOCK_SUCCESS_S:
            break

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                raise SystemExit

        screen.fill(COLOR_BG)

        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        pulse = 0.55 + 0.45 * math.sin(elapsed * 10.0)
        col = (255, 255, int(180 + 60 * pulse))
        msg = font_brand.render("UNLOCKED", True, col)
        sub = font_small.render("Launching Solaris...", True, (230, 230, 230))

        screen.blit(msg, (W // 2 - msg.get_width() // 2, H // 2 - msg.get_height() // 2 - 18))
        screen.blit(sub, (W // 2 - sub.get_width() // 2, H // 2 + 28))

        pygame.display.flip()
        clock.tick(60)

    enter_vm_mode()


# ---------- Lock image surfaces ----------
lock_surf, board_surf, img_name = pick_image_surfaces()


def _load_lock_image_by_name(fname):
    global lock_surf, board_surf, img_name
    raw = pygame.image.load(os.path.join(IMAGE_DIR, fname)).convert()
    lock_surf = scale_cover(raw, W, H)
    board_surf = lock_surf.subsurface(pygame.Rect(0, 0, W, BOARD_H)).copy()
    img_name = fname


def pick_new_lock_image():
    global lock_surf, board_surf, img_name
    lock_surf, board_surf, img_name = pick_image_surfaces()


# ---------- Square puzzle runtime ----------
PUZ_STAGE_INTRO = "INTRO"
PUZ_STAGE_FALL = "FALL"
PUZ_STAGE_PLAY = "PLAY"

tiles, tile_w, tile_h, slot_positions = make_tiles(board_surf)
drag_tile = None
drag_ox = drag_oy = 0
puz_stage = PUZ_STAGE_INTRO
puz_t0 = 0.0
puz_break_fx = None

# ---------- Jigsaw runtime ----------
JIG_STAGE_INTRO = "INTRO"
JIG_STAGE_FALL = "FALL"
JIG_STAGE_PLAY = "PLAY"
JIG_STAGE_SOLVED = "SOLVED"

jig_stage = JIG_STAGE_INTRO
jig_t0 = 0.0
jig_order = []
jig_index = 0
jig_cols = JIG_DIFFICULTY_CHOICES[1][1]
jig_rows = JIG_DIFFICULTY_CHOICES[1][2]
jig_snap_dist = calc_jig_snap_dist(jig_cols, jig_rows)  # NEW: per-grid snap dist
jig_pieces = []
jig_drag_piece = None
jig_drag_ox = jig_drag_oy = 0
jig_break_fx = None


def _ensure_jig_order():
    global jig_order, jig_index
    if not jig_order:
        jig_order = images[:]
        random.shuffle(jig_order)
        jig_index = 0


def _load_jigsaw_current_image():
    global jig_pieces, jig_stage, jig_t0, jig_drag_piece, jig_break_fx
    global jig_snap_dist
    jig_snap_dist = calc_jig_snap_dist(jig_cols, jig_rows)

    jig_pieces = build_jigsaw_pieces(board_surf, jig_cols, jig_rows)

    random.shuffle(jig_pieces)
    for p in jig_pieces:
        p["locked"] = False
        p["pos"] = p["correct_pos"]
        p["fall_from"] = p["correct_pos"]
        p["fall_to"] = tray_random_pos_sized(p["surf"].get_width(), p["surf"].get_height())

    jig_drag_piece = None
    jig_stage = JIG_STAGE_INTRO
    jig_break_fx = None
    jig_t0 = time.time()


def advance_jigsaw_image():
    global jig_index
    _ensure_jig_order()
    jig_index = (jig_index + 1) % len(jig_order)
    _load_lock_image_by_name(jig_order[jig_index])
    _load_jigsaw_current_image()


# ---------- Buttons ----------
start_btn = make_button(
    pygame.Rect(W // 2 - 160, int(H * 0.66), 320, 96),
    "START",
    color=COLOR_START
)

pi_btn = make_button(
    pygame.Rect(16, H - 76, 180, 56),
    "PI MODE",
    color=COLOR_PI
)

jigsaw_btn = make_button(
    pygame.Rect(W // 2 - 140, H - 76, 280, 56),
    "JIGSAW MODE",
    color=COLOR_JIGSAW
)

solaris_btn = make_button(
    pygame.Rect(W - 16 - 220, H - 76, 220, 56),
    "SOLARIS MODE",
    color=COLOR_SOLARIS
)

home_btn = make_button(
    pygame.Rect(16, 16, 160, 48),
    "HOME",
    color=COLOR_HOME
)

pin_cancel_btn = make_button(
    pygame.Rect(16, 16, 170, 48),
    "CANCEL",
    color=COLOR_CANCEL
)

jig_select_back_btn = make_button(
    pygame.Rect(16, 16, 160, 48),
    "BACK",
    color=COLOR_HOME
)


# ---------- ATTRACT animation runtime ----------
ATTR_STAGE_WHOLE = "WHOLE"
ATTR_STAGE_BREAK = "BREAK"
ATTR_STAGE_SCRAMBLE = "SCRAMBLE"
ATTR_STAGE_ASSEMBLE = "ASSEMBLE"
ATTR_STAGE_HOLD = "HOLD"

attr_stage = ATTR_STAGE_WHOLE
attr_t0 = time.time()
attr_tiles = []
attr_scatter_targets = []
attr_assemble_from = []
attr_break_fx = None


def start_new_attract_cycle():
    """
    FULL-SCREEN break/scramble/assemble (includes old tray area).
    """
    global attr_stage, attr_t0, attr_tiles
    global attr_scatter_targets, attr_assemble_from, attr_break_fx

    pick_new_lock_image()

    attr_tiles = make_tiles_fullscreen(lock_surf, ATTR_GRID_X, ATTR_GRID_Y)
    for t in attr_tiles:
        t["pos"] = t["correct"]
        set_random_vel(t)

    attr_scatter_targets = [scatter_pos_full(t["w"], t["h"]) for t in attr_tiles]
    attr_assemble_from = []
    attr_break_fx = None

    attr_stage = ATTR_STAGE_WHOLE
    attr_t0 = time.time()


# ---------- Mode transitions ----------
state = STATE_ATTRACT


def back_to_lock():
    global state, drag_tile, jig_drag_piece, lock_ui_visible
    global puz_break_fx, jig_break_fx
    state = STATE_ATTRACT
    drag_tile = None
    jig_drag_piece = None
    puz_break_fx = None
    jig_break_fx = None
    lock_ui_visible = False
    start_new_attract_cycle()


def enter_square_puzzle():
    global state, tiles, tile_w, tile_h, slot_positions
    global drag_tile, puz_stage, puz_t0, puz_break_fx

    tiles, tile_w, tile_h, slot_positions = make_tiles(board_surf)
    drag_tile = None

    for t in tiles:
        t["locked"] = False
        t["pos"] = t["correct"]
        t["fall_from"] = t["correct"]
        t["fall_to"] = tray_random_pos(tile_w, tile_h)

    puz_stage = PUZ_STAGE_INTRO
    puz_break_fx = None
    puz_t0 = time.time()
    state = STATE_PUZZLE


def rescramble_square_puzzle():
    for t in tiles:
        if not t.get("locked"):
            t["pos"] = tray_random_pos(tile_w, tile_h)


def enter_jigsaw_select():
    global state
    state = STATE_JIG_SELECT


def enter_jigsaw_mode(cols, rows):
    global state, jig_cols, jig_rows, jig_index, jig_snap_dist
    jig_cols, jig_rows = cols, rows
    jig_snap_dist = calc_jig_snap_dist(cols, rows)  # NEW: compute per-grid snap
    _ensure_jig_order()
    _load_lock_image_by_name(jig_order[jig_index])
    _load_jigsaw_current_image()
    state = STATE_JIGSAW


# Start VM early so it is already booting behind the lock screen
ensure_qemu_running()

# Start attract cycle immediately
start_new_attract_cycle()

# ---------- Main loop ----------
running = True
try:
    while running:
        dt = clock.tick(60) / 1000.0

        # -------- Handle events --------
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False

            # Global: ESC backs out of modes, quits only from lock screen
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                if state == STATE_ATTRACT:
                    running = False
                elif state == STATE_PIN:
                    close_pin_prompt()
                else:
                    back_to_lock()
                continue

            # Lock UI wake behavior (ATTRACT only):
            if state == STATE_ATTRACT and not lock_ui_visible:
                if e.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                    wake_lock_ui()
                    continue

            # If UI is visible, any input refreshes timeout
            if state == STATE_ATTRACT and lock_ui_visible:
                if e.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                    wake_lock_ui()

            # PIN overlay
            if state == STATE_PIN:
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_RETURN:
                        pin_submit()
                    elif e.key == pygame.K_BACKSPACE:
                        pin_input = pin_input[:-1]
                    elif e.unicode.isdigit():
                        if len(pin_input) < 12:
                            pin_input += e.unicode

                if e.type == pygame.MOUSEBUTTONDOWN:
                    if pin_cancel_btn["rect"].collidepoint(e.pos):
                        close_pin_prompt()
                        continue

                    KEYPAD_COLS = 3
                    KEYPAD_ROWS = 4
                    KEYPAD_KEYS = ["1", "2", "3",
                                   "4", "5", "6",
                                   "7", "8", "9",
                                   "C", "0", "OK"]
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
                            if rect.collidepoint(e.pos):
                                key = KEYPAD_KEYS[idx]
                                if key == "C":
                                    pin_input = ""
                                elif key == "OK":
                                    pin_submit()
                                else:
                                    if len(pin_input) < 12:
                                        pin_input += key
                                break
                            idx += 1
                continue

            # ATTRACT clicks
            if state == STATE_ATTRACT:
                if e.type == pygame.MOUSEBUTTONDOWN:
                    if not lock_ui_visible:
                        wake_lock_ui()
                        continue
                    if start_btn["rect"].collidepoint(e.pos):
                        enter_square_puzzle()
                    elif pi_btn["rect"].collidepoint(e.pos):
                        open_pin_prompt(PIN_ACTION_PI, return_state=STATE_ATTRACT)
                    elif solaris_btn["rect"].collidepoint(e.pos):
                        open_pin_prompt(PIN_ACTION_SOLARIS, return_state=STATE_ATTRACT)
                    elif jigsaw_btn["rect"].collidepoint(e.pos):
                        enter_jigsaw_select()

                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_RETURN and lock_ui_visible:
                        enter_square_puzzle()
                continue

            # Square puzzle
            if state == STATE_PUZZLE:
                if e.type == pygame.MOUSEBUTTONDOWN:
                    if home_btn["rect"].collidepoint(e.pos):
                        back_to_lock()
                        continue

                    if pi_btn["rect"].collidepoint(e.pos):
                        open_pin_prompt(PIN_ACTION_PI, return_state=STATE_PUZZLE)
                        continue
                    if solaris_btn["rect"].collidepoint(e.pos):
                        open_pin_prompt(PIN_ACTION_SOLARIS, return_state=STATE_PUZZLE)
                        continue

                    if puz_stage != PUZ_STAGE_PLAY:
                        continue

                    picked = None
                    for t in reversed(tiles):
                        if t.get("locked"):
                            continue
                        if tile_rect(t, tile_w, tile_h).collidepoint(e.pos):
                            picked = t
                            break

                    if picked:
                        tiles.remove(picked)
                        tiles.append(picked)
                        drag_tile = picked
                        drag_ox = e.pos[0] - drag_tile["pos"][0]
                        drag_oy = e.pos[1] - drag_tile["pos"][1]
                        play(snd_pick)
                    else:
                        rescramble_square_puzzle()

                elif e.type == pygame.MOUSEBUTTONUP:
                    if puz_stage != PUZ_STAGE_PLAY:
                        continue
                    if drag_tile:
                        occ = rebuild_slot_occupancy(tiles)
                        locked_now = auto_snap_lock_with_swap(drag_tile, slot_positions, occ, tile_w, tile_h)
                        if locked_now:
                            play(snd_snap)
                        else:
                            play(snd_drop)
                        drag_tile = None

                        if solved_all_locked(tiles):
                            unlock_success_and_enter_vm()

                elif e.type == pygame.MOUSEMOTION and drag_tile and puz_stage == PUZ_STAGE_PLAY:
                    drag_tile["pos"] = (e.pos[0] - drag_ox, e.pos[1] - drag_oy)
                    occ = rebuild_slot_occupancy(tiles)
                    if auto_snap_lock_with_swap(drag_tile, slot_positions, occ, tile_w, tile_h):
                        play(snd_snap)
                        drag_tile = None
                        if solved_all_locked(tiles):
                            unlock_success_and_enter_vm()
                continue

            # Jigsaw select prompt
            if state == STATE_JIG_SELECT:
                if e.type == pygame.MOUSEBUTTONDOWN:
                    if jig_select_back_btn["rect"].collidepoint(e.pos):
                        back_to_lock()
                        continue

                    box_w = min(720, int(W * 0.68))
                    box_x = (W - box_w) // 2
                    box_y = (H - min(520, int(H * 0.62))) // 2
                    option_h = 64
                    gap = 12
                    y = box_y + 90
                    for label, c, r in JIG_DIFFICULTY_CHOICES:
                        rect = pygame.Rect(box_x + 24, y, box_w - 48, option_h)
                        if rect.collidepoint(e.pos):
                            enter_jigsaw_mode(c, r)
                            break
                        y += option_h + gap
                continue

            # Jigsaw mode
            if state == STATE_JIGSAW:
                if e.type == pygame.MOUSEBUTTONDOWN:
                    if home_btn["rect"].collidepoint(e.pos):
                        back_to_lock()
                        continue

                    if jig_stage != JIG_STAGE_PLAY:
                        continue

                    picked = None
                    for p in reversed(jig_pieces):
                        if p.get("locked"):
                            continue
                        px, py = p["pos"]
                        lx = e.pos[0] - px
                        ly = e.pos[1] - py
                        if 0 <= lx < p["surf"].get_width() and 0 <= ly < p["surf"].get_height():
                            if p["mask"].get_at((int(lx), int(ly))):
                                picked = p
                                break

                    if picked:
                        jig_pieces.remove(picked)
                        jig_pieces.append(picked)
                        jig_drag_piece = picked
                        jig_drag_ox = e.pos[0] - picked["pos"][0]
                        jig_drag_oy = e.pos[1] - picked["pos"][1]
                        play(snd_pick)
                    else:
                        for p in jig_pieces:
                            if not p.get("locked"):
                                p["pos"] = tray_random_pos_sized(p["surf"].get_width(), p["surf"].get_height())

                elif e.type == pygame.MOUSEBUTTONUP:
                    if jig_stage != JIG_STAGE_PLAY:
                        continue
                    if jig_drag_piece:
                        p = jig_drag_piece
                        cx, cy = p["correct_pos"]
                        x, y = p["pos"]
                        d = math.hypot(x - cx, y - cy)

                        # NEW: dynamic snap dist
                        if d <= jig_snap_dist:
                            p["pos"] = p["correct_pos"]
                            p["locked"] = True
                            play(snd_snap)
                        else:
                            play(snd_drop)

                        jig_drag_piece = None

                        if jigsaw_all_locked(jig_pieces):
                            jig_stage = JIG_STAGE_SOLVED
                            jig_t0 = time.time()

                elif e.type == pygame.MOUSEMOTION and jig_drag_piece and jig_stage == JIG_STAGE_PLAY:
                    jig_drag_piece["pos"] = (e.pos[0] - jig_drag_ox, e.pos[1] - jig_drag_oy)
                continue

        # -------- Update timers/animations --------
        if state == STATE_ATTRACT:
            update_lock_ui_timeout()

            elapsed = time.time() - attr_t0

            if attr_stage == ATTR_STAGE_WHOLE:
                if elapsed >= ATTR_WHOLE_HOLD_S:
                    attr_stage = ATTR_STAGE_BREAK
                    attr_t0 = time.time()
                    attr_break_fx = start_break_fx(W, H)

            elif attr_stage == ATTR_STAGE_BREAK:
                t = min(1.0, elapsed / max(0.001, ATTR_BREAK_S))
                for i, tile in enumerate(attr_tiles):
                    tile["pos"] = lerp_pos(tile["correct"], attr_scatter_targets[i], t)
                if t >= 1.0:
                    attr_stage = ATTR_STAGE_SCRAMBLE
                    attr_t0 = time.time()

            elif attr_stage == ATTR_STAGE_SCRAMBLE:
                for tile in attr_tiles:
                    px, py = tile["pos"]
                    vx, vy = tile.get("vel", (0.0, 0.0))
                    tw = tile.get("w", 0)
                    th = tile.get("h", 0)

                    px += vx * dt
                    py += vy * dt

                    if px < 0:
                        px = 0
                        vx = abs(vx)
                    elif px > W - tw:
                        px = W - tw
                        vx = -abs(vx)

                    if py < 0:
                        py = 0
                        vy = abs(vy)
                    elif py > H - th:
                        py = H - th
                        vy = -abs(vy)

                    tile["pos"] = (int(px), int(py))
                    tile["vel"] = (vx, vy)

                if elapsed >= ATTR_SCRAMBLE_S:
                    attr_assemble_from = [t["pos"] for t in attr_tiles]
                    attr_stage = ATTR_STAGE_ASSEMBLE
                    attr_t0 = time.time()

            elif attr_stage == ATTR_STAGE_ASSEMBLE:
                t = min(1.0, elapsed / max(0.001, ATTR_ASSEMBLE_S))
                for i, tile in enumerate(attr_tiles):
                    tile["pos"] = lerp_pos(attr_assemble_from[i], tile["correct"], t)
                if t >= 1.0:
                    attr_stage = ATTR_STAGE_HOLD
                    attr_t0 = time.time()

            elif attr_stage == ATTR_STAGE_HOLD:
                if elapsed >= ATTR_POST_ASSEMBLE_S:
                    start_new_attract_cycle()

        if state == STATE_PUZZLE:
            elapsed = time.time() - puz_t0

            if puz_stage == PUZ_STAGE_INTRO:
                if elapsed >= PUZ_INTRO_HOLD_S:
                    puz_stage = PUZ_STAGE_FALL
                    puz_t0 = time.time()
                    puz_break_fx = start_break_fx(W, BOARD_H)

            elif puz_stage == PUZ_STAGE_FALL:
                t = min(1.0, elapsed / max(0.001, PUZ_FALL_S))
                tx = _ease_out_cubic(t)
                ty = _ease_in_quad(t)
                for tile in tiles:
                    x0, y0 = tile["fall_from"]
                    x1, y1 = tile["fall_to"]
                    tile["pos"] = (int(x0 + (x1 - x0) * tx), int(y0 + (y1 - y0) * ty))

                if t >= 1.0:
                    puz_stage = PUZ_STAGE_PLAY
                    puz_t0 = time.time()

        if state == STATE_JIGSAW:
            elapsed = time.time() - jig_t0

            if jig_stage == JIG_STAGE_INTRO:
                if elapsed >= JIG_INTRO_HOLD_S:
                    jig_stage = JIG_STAGE_FALL
                    jig_t0 = time.time()
                    jig_break_fx = start_break_fx(W, BOARD_H)

            elif jig_stage == JIG_STAGE_FALL:
                t = min(1.0, elapsed / max(0.001, JIG_FALL_S))
                tx = _ease_out_cubic(t)
                ty = _ease_in_quad(t)
                for p in jig_pieces:
                    x0, y0 = p["fall_from"]
                    x1, y1 = p["fall_to"]
                    p["pos"] = (int(x0 + (x1 - x0) * tx), int(y0 + (y1 - y0) * ty))
                if t >= 1.0:
                    jig_stage = JIG_STAGE_PLAY
                    jig_t0 = time.time()

            elif jig_stage == JIG_STAGE_SOLVED:
                if elapsed >= JIG_SOLVED_HOLD_S:
                    advance_jigsaw_image()

        # -------- Draw --------
        screen.fill(COLOR_BG)

        # ATTRACT
        if state == STATE_ATTRACT:
            if attr_stage in (ATTR_STAGE_WHOLE, ATTR_STAGE_HOLD):
                screen.blit(lock_surf, (0, 0))
            else:
                # FULL-SCREEN tiles; no unbroken tray region
                screen.fill(COLOR_BG)
                for t in attr_tiles:
                    screen.blit(t["image"], t["pos"])
                if attr_stage == ATTR_STAGE_BREAK:
                    draw_crack_overlay_fade(attr_break_fx)

            draw_status_bar()

            pulse = 0.5 + 0.5 * math.sin(time.time() * 1.5)
            brand_color = (255, 255, int(180 + 60 * pulse))
            bt = font_brand.render(BRAND_TEXT, True, brand_color)
            bs = font_brand2.render(BRAND_SUB, True, (230, 230, 230))
            y0 = STATUS_BAR_H + 10 if LOCK_SHOW_STATUS_BAR else 18
            screen.blit(bt, (W // 2 - bt.get_width() // 2, y0))
            screen.blit(bs, (W // 2 - bs.get_width() // 2, y0 + bt.get_height() + 6))

            if lock_ui_visible:
                mx, my = pygame.mouse.get_pos()
                draw_button(start_btn, active=start_btn["rect"].collidepoint((mx, my)))
                draw_button(pi_btn, active=pi_btn["rect"].collidepoint((mx, my)), small=True)
                draw_button(jigsaw_btn, active=jigsaw_btn["rect"].collidepoint((mx, my)), small=True)
                draw_button(solaris_btn, active=solaris_btn["rect"].collidepoint((mx, my)), small=True)
            else:
                hint = font_small.render("Tap or press any key to show controls", True, (230, 230, 230))
                screen.blit(hint, (W // 2 - hint.get_width() // 2, H - 42))

        # Square puzzle
        elif state == STATE_PUZZLE:
            if puz_stage == PUZ_STAGE_INTRO:
                screen.blit(lock_surf, (0, 0))
                mx, my = pygame.mouse.get_pos()
                draw_button(home_btn, active=home_btn["rect"].collidepoint((mx, my)), small=True)
                msg = font_small.render("Preparing puzzle...", True, (235, 235, 235))
                screen.blit(msg, (W // 2 - msg.get_width() // 2, H - 42))
            else:
                pygame.draw.rect(screen, COLOR_BG, board_rect)

                draw_tray()
                draw_board_frame()

                ox, oy = break_shake_offset(puz_break_fx) if (puz_stage == PUZ_STAGE_FALL) else (0, 0)

                # grid lines
                for x in range(1, GRID_X):
                    pygame.draw.line(screen, (35, 35, 35), (x * tile_w, 0), (x * tile_w, BOARD_H), 1)
                for y in range(1, GRID_Y):
                    pygame.draw.line(screen, (35, 35, 35), (0, y * tile_h), (W, y * tile_h), 1)

                # tiles
                for t in tiles:
                    screen.blit(t["image"], (t["pos"][0] + ox, t["pos"][1] + oy))
                    if t.get("locked"):
                        pygame.draw.rect(
                            screen, (0, 255, 0),
                            pygame.Rect((t["pos"][0] + ox, t["pos"][1] + oy), (tile_w, tile_h)), 3
                        )

                if puz_stage == PUZ_STAGE_FALL:
                    draw_crack_overlay_fade(puz_break_fx)

                mx, my = pygame.mouse.get_pos()
                draw_button(home_btn, active=home_btn["rect"].collidepoint((mx, my)), small=True)
                draw_button(pi_btn, active=pi_btn["rect"].collidepoint((mx, my)), small=True)
                draw_button(solaris_btn, active=solaris_btn["rect"].collidepoint((mx, my)), small=True)

                hint = font_small.render(
                    "Drag to solve. Tap empty to re-scramble." if puz_stage == PUZ_STAGE_PLAY else "Breaking",
                    True, (230, 230, 230)
                )
                screen.blit(hint, (16, BOARD_H - 32))

        # Jigsaw select prompt
        elif state == STATE_JIG_SELECT:
            screen.blit(lock_surf, (0, 0))
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 175))
            screen.blit(overlay, (0, 0))

            mx, my = pygame.mouse.get_pos()
            draw_button(jig_select_back_btn, active=jig_select_back_btn["rect"].collidepoint((mx, my)), small=True)

            box_w = min(720, int(W * 0.68))
            box_h = min(520, int(H * 0.62))
            box_x = (W - box_w) // 2
            box_y = (H - box_h) // 2
            pygame.draw.rect(screen, (35, 35, 35), pygame.Rect(box_x, box_y, box_w, box_h), border_radius=18)
            pygame.draw.rect(screen, (230, 230, 230), pygame.Rect(box_x, box_y, box_w, box_h), 2, border_radius=18)

            title = font.render("JIGSAW DIFFICULTY", True, (255, 255, 255))
            sub = font_small.render("Select a grid size (more pieces = harder)", True, (230, 230, 230))
            screen.blit(title, (W // 2 - title.get_width() // 2, box_y + 20))
            screen.blit(sub, (W // 2 - sub.get_width() // 2, box_y + 60))

            option_h = 64
            gap = 12
            y = box_y + 90
            for label, c, r in JIG_DIFFICULTY_CHOICES:
                rect = pygame.Rect(box_x + 24, y, box_w - 48, option_h)
                btn = make_button(rect, f"{label} | {c} x {r}", color=COLOR_JIGSAW)
                draw_button(btn, active=rect.collidepoint((mx, my)), small=True)
                y += option_h + gap

        # Jigsaw mode
        elif state == STATE_JIGSAW:
            if jig_stage == JIG_STAGE_INTRO:
                screen.blit(lock_surf, (0, 0))
                mx, my = pygame.mouse.get_pos()
                draw_button(home_btn, active=home_btn["rect"].collidepoint((mx, my)), small=True)
            else:
                if jig_stage in (JIG_STAGE_FALL, JIG_STAGE_SOLVED):
                    screen.blit(board_surf, (0, 0))
                else:
                    if JIG_BG_DIM_ALPHA == 0:
                        pygame.draw.rect(screen, (0, 0, 0), board_rect)
                    else:
                        screen.blit(board_surf, (0, 0))
                        dim = pygame.Surface((W, BOARD_H), pygame.SRCALPHA)
                        dim.fill((0, 0, 0, JIG_BG_DIM_ALPHA))
                        screen.blit(dim, (0, 0))

                draw_tray()

                ox, oy = break_shake_offset(jig_break_fx) if (jig_stage == JIG_STAGE_FALL) else (0, 0)

                for p in jig_pieces:
                    screen.blit(p["surf"], (p["pos"][0] + ox, p["pos"][1] + oy))
                    if p.get("locked"):
                        pygame.draw.rect(
                            screen, (0, 180, 0),
                            pygame.Rect((p["pos"][0] + ox, p["pos"][1] + oy), p["surf"].get_size()), 2
                        )

                if jig_stage == JIG_STAGE_FALL:
                    draw_crack_overlay_fade(jig_break_fx)

                mx, my = pygame.mouse.get_pos()
                draw_button(home_btn, active=home_btn["rect"].collidepoint((mx, my)), small=True)

                if jig_stage == JIG_STAGE_PLAY:
                    hint = font_small.render("Drag pieces into place. Tap empty to re-scramble.", True, (230, 230, 230))
                elif jig_stage == JIG_STAGE_FALL:
                    hint = font_small.render("Breaking", True, (230, 230, 230))
                else:
                    hint = font_small.render("Solved. Loading next puzzle", True, (230, 230, 230))
                screen.blit(hint, (16, BOARD_H - 32))

        # PIN overlay draw
        if state == STATE_PIN:
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 205))
            screen.blit(overlay, (0, 0))

            mx, my = pygame.mouse.get_pos()
            draw_button(pin_cancel_btn, active=pin_cancel_btn["rect"].collidepoint((mx, my)), small=True)

            action_label = "OPEN SOLARIS" if pin_action == PIN_ACTION_SOLARIS else "PI DESKTOP"
            title = font.render(f"ADMIN OVERRIDE - {action_label}", True, (255, 255, 255))
            prompt = font_small.render("Enter PIN (keyboard or touchscreen keypad):", True, (230, 230, 230))
            masked = "*" * len(pin_input)
            entry = font.render(masked, True, (255, 255, 0))

            screen.blit(title, (W // 2 - title.get_width() // 2, 80))
            screen.blit(prompt, (W // 2 - prompt.get_width() // 2, 130))
            screen.blit(entry, (W // 2 - entry.get_width() // 2, 165))

            KEYPAD_COLS = 3
            KEYPAD_ROWS = 4
            KEYPAD_KEYS = ["1", "2", "3",
                           "4", "5", "6",
                           "7", "8", "9",
                           "C", "0", "OK"]
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
                label = font.render(KEYPAD_KEYS[i], True, (255, 255, 255))
                screen.blit(label, (r.centerx - label.get_width() // 2, r.centery - label.get_height() // 2))

            if pin_error and (time.time() - pin_error_t0) < 2.0:
                err = font_small.render(pin_error, True, (255, 90, 90))
                screen.blit(err, (W // 2 - err.get_width() // 2, pad_y + pad_h + 18))

            tip = font_small.render("Enter=submit, Backspace=delete, OK=submit. Esc/CANCEL=back.", True,
                                    (230, 230, 230))
            screen.blit(tip, (W // 2 - tip.get_width() // 2, pad_y + pad_h + 50))

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
