import pygame
import random
import os
import subprocess
import sys
import time
import math
import shutil
import signal

# ---------------- CONFIG ----------------
GRID_X = 4
GRID_Y = 4

# “General area” snap/lock (touch-friendly)
SNAP_DIST = 190  # px from slot to auto-snap+lock (bigger = easier)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "images")

# QEMU control
QEMU_PIDFILE = "/home/pi/sparc_vm/qemu-sparc.pid"
RUN_QEMU_CMD = ["/home/pi/sparc_vm/run_sol8.sh"]  # headless QEMU that serves VNC :1

# VNC target (must match your QEMU -vnc setting)
VM_VNC_TARGET = "127.0.0.1:1"   # if your QEMU uses -vnc :1, this still works locally

# Auto re-lock after inactivity while VM is shown (milliseconds)
VM_IDLE_LOCK_MS = 5 * 60 * 1000  # 5 minutes; adjust as desired

# Attract-mode timing (seconds)
WHOLE_HOLD_S = 1.2
BREAK_S = 0.55
SCRAMBLE_S = 10.0
ASSEMBLE_S = 1.0
POST_ASSEMBLE_S = 0.6

# Motion tuning (attract scramble drift)
DRIFT_SPEED_MIN = 90
DRIFT_SPEED_MAX = 210

# Layout: board (top) + tray (bottom)
TRAY_H_FRAC = 0.28
TRAY_MARGIN = 14

# Sounds (optional; place wav files in ./sounds/)
SOUNDS_DIR = os.path.join(BASE_DIR, "sounds")
SND_PICK = "pick.wav"
SND_DROP = "drop.wav"
SND_SNAP = "snap.wav"
SND_ERROR = "error.wav"

# Branding
BRAND_TEXT = "Sun SPARCstation"
BRAND_SUB = "Puzzle Unlock"

ADMIN_PIN = "113093"
# ----------------------------------------

# ---------- Utilities ----------
def now_ms() -> int:
    return int(time.time() * 1000)

def safe_int(s, default=0):
    try:
        return int(s)
    except Exception:
        return default

def qemu_is_running() -> bool:
    try:
        with open(QEMU_PIDFILE, "r") as f:
            pid_str = f.read().strip()
        if not pid_str:
            return False
        pid = int(pid_str)
        os.kill(pid, 0)  # existence check
        return True
    except FileNotFoundError:
        return False
    except ProcessLookupError:
        # stale pidfile
        try:
            os.remove(QEMU_PIDFILE)
        except OSError:
            pass
        return False
    except Exception:
        return False

def ensure_qemu_running():
    # Start QEMU if not running. Do not hard-fail if it is already running.
    if qemu_is_running():
        return

    # Best effort: run the script, do not block.
    try:
        subprocess.Popen(
            RUN_QEMU_CMD,
            cwd="/home/pi/sparc_vm",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        # give QEMU a moment to come up
        time.sleep(1.0)
    except Exception:
        pass

def find_vncviewer_cmd():
    # TigerVNC on Debian often provides "xtigervncviewer"
    for bin_name in ("xtigervncviewer", "vncviewer"):
        path = shutil.which(bin_name)
        if path:
            return path
    return None

def get_idle_ms():
    """
    Returns idle time in ms, or None if it cannot be determined.
    Primary: xprintidle (X11/XWayland).
    """
    xpi = shutil.which("xprintidle")
    if xpi:
        try:
            out = subprocess.check_output([xpi], stderr=subprocess.DEVNULL, timeout=0.2).strip()
            return int(out)
        except Exception:
            return None
    return None

# ---------- Pygame init ----------
pygame.init()
try:
    pygame.mixer.init()
except Exception:
    # Audio not required; continue silently
    pass

# IMPORTANT: Use NOFRAME “fullscreen-like” so other fullscreen windows (VNC viewer) can take focus cleanly.
info = pygame.display.Info()
screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.NOFRAME)
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

# ---------- Images ----------
def load_images():
    imgs = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith((".jpg", ".png"))]
    if not imgs:
        print(f"No images found in {IMAGE_DIR}")
        sys.exit(1)
    return imgs

images = load_images()

def pick_image_surface():
    fname = random.choice(images)
    surf = pygame.image.load(os.path.join(IMAGE_DIR, fname)).convert()
    surf = pygame.transform.scale(surf, (W, BOARD_H))
    return surf, fname

def make_tiles(img_surf):
    tile_w = W // GRID_X
    tile_h = BOARD_H // GRID_Y

    tiles = []
    slot_positions = []

    for y in range(GRID_Y):
        for x in range(GRID_X):
            slot_positions.append((x * tile_w, y * tile_h))

    for slot_idx, (sx, sy) in enumerate(slot_positions):
        rect = pygame.Rect(sx, sy, tile_w, tile_h)
        tile_img = img_surf.subsurface(rect).copy()
        tiles.append({
            "image": tile_img,
            "correct": (sx, sy),
            "slot": slot_idx,
            "pos": (sx, sy),
            "vel": (0.0, 0.0),
            "locked": False
        })

    return tiles, tile_w, tile_h, slot_positions

def tray_random_pos(tile_w, tile_h):
    x0 = TRAY_MARGIN
    x1 = W - TRAY_MARGIN - tile_w
    y0 = tray_rect.top + TRAY_MARGIN
    y1 = tray_rect.bottom - TRAY_MARGIN - tile_h
    if x1 < x0: x1 = x0
    if y1 < y0: y1 = y0
    return (random.randint(x0, x1), random.randint(y0, y1))

def board_scatter_pos(tile_w, tile_h):
    x0 = TRAY_MARGIN
    x1 = W - TRAY_MARGIN - tile_w
    y0 = TRAY_MARGIN
    y1 = BOARD_H - TRAY_MARGIN - tile_h
    if x1 < x0: x1 = x0
    if y1 < y0: y1 = y0
    return (random.randint(x0, x1), random.randint(y0, y1))

def set_random_vel(tile):
    vx = random.uniform(DRIFT_SPEED_MIN, DRIFT_SPEED_MAX) * random.choice([-1, 1])
    vy = random.uniform(DRIFT_SPEED_MIN, DRIFT_SPEED_MAX) * random.choice([-1, 1])
    tile["vel"] = (vx, vy)

def lerp(a, b, t):
    return a + (b - a) * t

def lerp_pos(p0, p1, t):
    return (int(lerp(p0[0], p1[0], t)), int(lerp(p0[1], p1[1], t)))

def tile_rect(tile, tile_w, tile_h):
    return pygame.Rect(tile["pos"], (tile_w, tile_h))

def draw_tray():
    pygame.draw.rect(screen, (18, 18, 18), tray_rect)
    pygame.draw.line(screen, (70, 70, 70), (0, tray_rect.top), (W, tray_rect.top), 2)
    txt = font_small.render("TRAY", True, (210, 210, 210))
    screen.blit(txt, (16, tray_rect.top + 10))

def draw_board_frame():
    pygame.draw.rect(screen, (70, 70, 70), board_rect, 2)

# ---------- Slot snapping ----------
def dist2(a, b):
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return dx*dx + dy*dy

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

    # Require correct slot for that tile
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

# ---------- “Glass shatter” effect ----------
def make_crack_overlay(w, h, lines=18, seed=None):
    rnd = random.Random(seed if seed is not None else random.randint(0, 10_000_000))
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    cx = rnd.randint(int(w*0.35), int(w*0.65))
    cy = rnd.randint(int(h*0.25), int(h*0.75))

    for _ in range(lines):
        ang = rnd.uniform(0, math.tau)
        length = rnd.uniform(w*0.25, w*0.75)
        x = cx
        y = cy
        pts = [(x, y)]
        steps = rnd.randint(6, 12)
        for i in range(steps):
            frac = (i+1)/steps
            jx = rnd.uniform(-10, 10)
            jy = rnd.uniform(-10, 10)
            x = cx + math.cos(ang) * length * frac + jx
            y = cy + math.sin(ang) * length * frac + jy
            pts.append((x, y))
        pygame.draw.lines(surf, (255, 255, 255, 110), False, pts, 2)
        pygame.draw.lines(surf, (255, 255, 255, 50),  False, pts, 4)

    return surf

# ---------- PIN keypad ----------
KEYPAD_COLS = 3
KEYPAD_ROWS = 4
KEYPAD_KEYS = [
    "1","2","3",
    "4","5","6",
    "7","8","9",
    "C","0","OK"
]

def keypad_layout():
    pad_w = min(520, int(W * 0.42))
    pad_h = min(520, int(H * 0.62))
    pad_x = (W - pad_w) // 2
    pad_y = (H - pad_h) // 2 + 40
    cell_w = pad_w // KEYPAD_COLS
    cell_h = pad_h // KEYPAD_ROWS
    rects = []
    for r in range(KEYPAD_ROWS):
        for c in range(KEYPAD_COLS):
            x = pad_x + c * cell_w + 8
            y = pad_y + r * cell_h + 8
            rects.append(pygame.Rect(x, y, cell_w - 16, cell_h - 16))
    return rects, (pad_x, pad_y, pad_w, pad_h)

# ---------- UI buttons ----------
def make_button(rect, label):
    return {"rect": rect, "label": label}

def draw_button(btn, active=False, small=False):
    r = btn["rect"]
    bg = (90, 90, 90) if not active else (120, 120, 120)
    pygame.draw.rect(screen, bg, r, border_radius=16)
    pygame.draw.rect(screen, (200, 200, 200), r, 2, border_radius=16)
    f = font_small if small else font
    t = f.render(btn["label"], True, (255, 255, 255))
    screen.blit(t, (r.centerx - t.get_width()//2, r.centery - t.get_height()//2))

# ---------- VM viewer control ----------
STATE_ATTRACT = "ATTRACT"
STATE_PUZZLE  = "PUZZLE"
STATE_PIN     = "PIN"
STATE_VM      = "VM"

PIN_ACTION_SOLARIS = "SOLARIS"
PIN_ACTION_PI      = "PI"

state = STATE_ATTRACT
pin_action = PIN_ACTION_SOLARIS

vm_viewer_proc = None
last_idle_lock_check_ms = 0

toast = ""
toast_until_ms = 0

def set_toast(msg, seconds=2.0):
    global toast, toast_until_ms
    toast = msg
    toast_until_ms = now_ms() + int(seconds * 1000)

def open_pi_desktop():
    # Return user to Pi desktop for maintenance (add images, files, etc.)
    global vm_viewer_proc
    try:
        if vm_viewer_proc and vm_viewer_proc.poll() is None:
            vm_viewer_proc.terminate()
    except Exception:
        pass
    pygame.quit()
    sys.exit(0)

def enter_vm_mode():
    global state, vm_viewer_proc

    ensure_qemu_running()
    if not qemu_is_running():
        set_toast("Solaris VM not running. Check run_sol8.sh / QEMU.", seconds=3.0)
        return

    viewer = find_vncviewer_cmd()
    if not viewer:
        set_toast("No VNC viewer found. Install: sudo apt install tigervnc-viewer", seconds=4.0)
        return

    # If already viewing, do nothing
    if vm_viewer_proc and vm_viewer_proc.poll() is None:
        state = STATE_VM
        return

    # Launch local fullscreen VNC viewer to the running QEMU display
    try:
        vm_viewer_proc = subprocess.Popen(
            [viewer, "-FullScreen", VM_VNC_TARGET],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        state = STATE_VM
    except Exception:
        set_toast("Failed to launch VNC viewer.", seconds=3.0)

def exit_vm_mode_to_lock():
    global state, vm_viewer_proc
    try:
        if vm_viewer_proc and vm_viewer_proc.poll() is None:
            vm_viewer_proc.terminate()
    except Exception:
        pass
    vm_viewer_proc = None
    state = STATE_ATTRACT
    start_new_attract_cycle()

# ---------- State init ----------
img_surf, img_name = pick_image_surface()
tiles, tile_w, tile_h, slot_positions = make_tiles(img_surf)
scatter_targets = [board_scatter_pos(tile_w, tile_h) for _ in tiles]

drag_tile = None
drag_ox = drag_oy = 0

pin_input = ""
pin_error = ""
pin_error_t0 = 0.0

start_btn = make_button(
    pygame.Rect(W//2 - 140, int(BOARD_H*0.78), 280, 92),
    "START"
)

pi_btn = make_button(
    pygame.Rect(16, BOARD_H - 76, 180, 56),
    "PI MODE"
)

crack_overlay = None
shake_amp = 0
shake_until = 0.0

STAGE_WHOLE    = "WHOLE"
STAGE_BREAK    = "BREAK"
STAGE_SCRAMBLE = "SCRAMBLE"
STAGE_ASSEMBLE = "ASSEMBLE"
STAGE_HOLD     = "HOLD"

stage = STAGE_WHOLE
stage_t0 = time.time()

def start_new_attract_cycle():
    global img_surf, img_name, tiles, tile_w, tile_h, slot_positions
    global stage, stage_t0, scatter_targets
    global crack_overlay, shake_amp, shake_until

    img_surf, img_name = pick_image_surface()
    tiles, tile_w, tile_h, slot_positions = make_tiles(img_surf)

    for t in tiles:
        t["pos"] = t["correct"]
        t["locked"] = False
        set_random_vel(t)

    stage = STAGE_WHOLE
    stage_t0 = time.time()
    scatter_targets = [board_scatter_pos(tile_w, tile_h) for _ in tiles]

    crack_overlay = None
    shake_amp = 0
    shake_until = 0.0

def begin_break():
    global stage, stage_t0, scatter_targets
    global crack_overlay, shake_amp, shake_until

    scatter_targets = [board_scatter_pos(tile_w, tile_h) for _ in tiles]
    for t in tiles:
        set_random_vel(t)

    crack_overlay = make_crack_overlay(W, BOARD_H, lines=20)
    shake_amp = 10
    shake_until = time.time() + BREAK_S

    stage = STAGE_BREAK
    stage_t0 = time.time()

def begin_scramble():
    global stage, stage_t0
    stage = STAGE_SCRAMBLE
    stage_t0 = time.time()

def begin_assemble():
    global stage, stage_t0
    stage = STAGE_ASSEMBLE
    stage_t0 = time.time()

def begin_hold():
    global stage, stage_t0
    stage = STAGE_HOLD
    stage_t0 = time.time()

def enter_puzzle_mode():
    global state, drag_tile
    state = STATE_PUZZLE
    drag_tile = None
    for t in tiles:
        t["locked"] = False
        t["pos"] = tray_random_pos(tile_w, tile_h)

def rescramble_puzzle():
    for t in tiles:
        t["locked"] = False
        t["pos"] = tray_random_pos(tile_w, tile_h)

def open_pin_prompt(action):
    global state, pin_input, pin_error, pin_action
    state = STATE_PIN
    pin_input = ""
    pin_error = ""
    pin_action = action

def pin_submit():
    global pin_input, pin_error, pin_error_t0, state
    if pin_input == ADMIN_PIN:
        if pin_action == PIN_ACTION_SOLARIS:
            state = STATE_ATTRACT
            enter_vm_mode()
        elif pin_action == PIN_ACTION_PI:
            open_pi_desktop()
    else:
        pin_error = "Incorrect PIN"
        pin_error_t0 = time.time()
        pin_input = ""
        play(snd_error)

# Start VM early so it’s already “booted” behind the lock screen
ensure_qemu_running()

# ---------- Main loop ----------
running = True
while running:
    # Reduce CPU load while VM is showing
    fps = 60 if state != STATE_VM else 10
    dt = clock.tick(fps) / 1000.0
    now = time.time()

    # VM mode: monitor viewer and idle time
    if state == STATE_VM:
        # If viewer closed, return to lock
        if vm_viewer_proc and vm_viewer_proc.poll() is not None:
            exit_vm_mode_to_lock()
            continue

        # If we can measure idle, re-lock after threshold
        if now_ms() - last_idle_lock_check_ms >= 500:
            last_idle_lock_check_ms = now_ms()
            idle = get_idle_ms()
            if idle is not None and idle >= VM_IDLE_LOCK_MS:
                exit_vm_mode_to_lock()
                continue

        # Keep pygame alive, but do not process lock UI while VM is active
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
        # Minimal draw (optional)
        screen.fill((0, 0, 0))
        pygame.display.flip()
        continue

    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False

        # Global key handling (when not in VM)
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_p:
                # Admin: open Solaris directly
                open_pin_prompt(PIN_ACTION_SOLARIS)

            if e.key == pygame.K_m:
                # Admin: exit to Pi desktop
                open_pin_prompt(PIN_ACTION_PI)

            # dev exit only (remove later if desired)
            if e.key == pygame.K_ESCAPE and state != STATE_PIN:
                running = False

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
                rects, _ = keypad_layout()
                for i, r in enumerate(rects):
                    if r.collidepoint(e.pos):
                        key = KEYPAD_KEYS[i]
                        if key == "C":
                            pin_input = ""
                        elif key == "OK":
                            pin_submit()
                        else:
                            if len(pin_input) < 12:
                                pin_input += key
                        break
            continue

        # ATTRACT
        if state == STATE_ATTRACT:
            if e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
                enter_puzzle_mode()
                continue
            if e.type == pygame.MOUSEBUTTONDOWN:
                if start_btn["rect"].collidepoint(e.pos):
                    enter_puzzle_mode()
                elif pi_btn["rect"].collidepoint(e.pos):
                    open_pin_prompt(PIN_ACTION_PI)
            continue

        # PUZZLE
        if state == STATE_PUZZLE:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_r:
                    rescramble_puzzle()

            if e.type == pygame.MOUSEBUTTONDOWN:
                if pi_btn["rect"].collidepoint(e.pos):
                    open_pin_prompt(PIN_ACTION_PI)
                    continue

                picked = None
                for t in reversed(tiles):
                    if t.get("locked"):
                        continue
                    r = tile_rect(t, tile_w, tile_h)
                    if r.collidepoint(e.pos):
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
                    rescramble_puzzle()

            elif e.type == pygame.MOUSEBUTTONUP:
                if drag_tile:
                    occ = rebuild_slot_occupancy(tiles)
                    locked_now = auto_snap_lock_with_swap(drag_tile, slot_positions, occ, tile_w, tile_h)
                    if locked_now:
                        play(snd_snap)
                    else:
                        play(snd_drop)

                    drag_tile = None

                    if solved_all_locked(tiles):
                        enter_vm_mode()

            elif e.type == pygame.MOUSEMOTION and drag_tile:
                drag_tile["pos"] = (e.pos[0] - drag_ox, e.pos[1] - drag_oy)
                occ = rebuild_slot_occupancy(tiles)
                if auto_snap_lock_with_swap(drag_tile, slot_positions, occ, tile_w, tile_h):
                    play(snd_snap)
                    drag_tile = None
                    if solved_all_locked(tiles):
                        enter_vm_mode()

    # ---------- Update attract animation ----------
    if state == STATE_ATTRACT:
        elapsed = now - stage_t0

        if stage == STAGE_WHOLE:
            if elapsed >= WHOLE_HOLD_S:
                begin_break()

        elif stage == STAGE_BREAK:
            t = min(1.0, elapsed / BREAK_S)
            for i, tile in enumerate(tiles):
                tile["pos"] = lerp_pos(tile["correct"], scatter_targets[i], t)
            if t >= 1.0:
                begin_scramble()

        elif stage == STAGE_SCRAMBLE:
            for tile in tiles:
                px, py = tile["pos"]
                vx, vy = tile["vel"]
                px += vx * dt
                py += vy * dt

                if px < 0:
                    px = 0
                    vx = abs(vx)
                elif px > W - tile_w:
                    px = W - tile_w
                    vx = -abs(vx)
                if py < 0:
                    py = 0
                    vy = abs(vy)
                elif py > BOARD_H - tile_h:
                    py = BOARD_H - tile_h
                    vy = -abs(vy)

                tile["pos"] = (int(px), int(py))
                tile["vel"] = (vx, vy)

            if elapsed >= SCRAMBLE_S:
                begin_assemble()

        elif stage == STAGE_ASSEMBLE:
            t = min(1.0, elapsed / ASSEMBLE_S)
            for i, tile in enumerate(tiles):
                tile["pos"] = lerp_pos(scatter_targets[i], tile["correct"], t)
            if t >= 1.0:
                begin_hold()

        elif stage == STAGE_HOLD:
            if elapsed >= POST_ASSEMBLE_S:
                start_new_attract_cycle()

    # ---------- Draw ----------
    screen.fill((0, 0, 0))
    draw_tray()

    ox, oy = 0, 0
    if state == STATE_ATTRACT and stage == STAGE_BREAK and now <= shake_until:
        frac = max(0.0, (shake_until - now) / BREAK_S)
        amp = int(shake_amp * frac)
        ox = random.randint(-amp, amp)
        oy = random.randint(-amp, amp)

    pygame.draw.rect(screen, (0, 0, 0), board_rect)

    if state == STATE_ATTRACT:
        pulse = 0.5 + 0.5 * math.sin(now * 1.5)
        brand_color = (255, 255, int(180 + 60 * pulse))
        bt = font_brand.render(BRAND_TEXT, True, brand_color)
        bs = font_brand2.render(BRAND_SUB, True, (220, 220, 220))
        screen.blit(bt, (W//2 - bt.get_width()//2, 18))
        screen.blit(bs, (W//2 - bs.get_width()//2, 18 + bt.get_height() + 6))

        if stage in (STAGE_WHOLE, STAGE_HOLD):
            screen.blit(img_surf, (ox, oy))
        else:
            for t in tiles:
                screen.blit(t["image"], (t["pos"][0] + ox, t["pos"][1] + oy))

        if crack_overlay and stage in (STAGE_BREAK, STAGE_SCRAMBLE):
            alpha = 170
            if stage == STAGE_SCRAMBLE:
                alpha = max(0, 170 - int((now - stage_t0) * 18))
            ov = crack_overlay.copy()
            ov.set_alpha(alpha)
            screen.blit(ov, (ox, oy))

        mx, my = pygame.mouse.get_pos()
        active = start_btn["rect"].collidepoint((mx, my))
        draw_button(start_btn, active=active)

        # PI MODE button (admin, requires PIN)
        active_pi = pi_btn["rect"].collidepoint((mx, my))
        draw_button(pi_btn, active=active_pi, small=True)

        hint = font_small.render("Press START or Enter. Admin: P (Solaris) / M (Pi).", True, (210, 210, 210))
        screen.blit(hint, (16, BOARD_H - 32))

    elif state == STATE_PUZZLE:
        draw_board_frame()

        for x in range(1, GRID_X):
            pygame.draw.line(screen, (35, 35, 35), (x * tile_w, 0), (x * tile_w, BOARD_H), 1)
        for y in range(1, GRID_Y):
            pygame.draw.line(screen, (35, 35, 35), (0, y * tile_h), (W, y * tile_h), 1)

        for t in tiles:
            screen.blit(t["image"], t["pos"])
            if t.get("locked"):
                pygame.draw.rect(screen, (0, 255, 0), pygame.Rect(t["pos"], (tile_w, tile_h)), 3)

        mx, my = pygame.mouse.get_pos()
        active_pi = pi_btn["rect"].collidepoint((mx, my))
        draw_button(pi_btn, active=active_pi, small=True)

        hint = font_small.render(
            "Drag pieces to board to unlock. Tap empty to re-scramble. R = re-scramble. Admin: P / M.",
            True, (220, 220, 220)
        )
        screen.blit(hint, (16, BOARD_H - 32))

    # PIN overlay
    if state == STATE_PIN:
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 205))
        screen.blit(overlay, (0, 0))

        action_label = "OPEN SOLARIS" if pin_action == PIN_ACTION_SOLARIS else "PI DESKTOP"
        title = font.render(f"ADMIN OVERRIDE — {action_label}", True, (255, 255, 255))
        prompt = font_small.render("Enter PIN (keyboard or touchscreen keypad):", True, (230, 230, 230))
        masked = "*" * len(pin_input)
        entry = font.render(masked, True, (255, 255, 0))

        screen.blit(title, (W//2 - title.get_width()//2, 80))
        screen.blit(prompt, (W//2 - prompt.get_width()//2, 130))
        screen.blit(entry, (W//2 - entry.get_width()//2, 165))

        rects, (pad_x, pad_y, pad_w, pad_h) = keypad_layout()
        pygame.draw.rect(screen, (35, 35, 35), pygame.Rect(pad_x, pad_y, pad_w, pad_h), border_radius=12)

        for i, r in enumerate(rects):
            pygame.draw.rect(screen, (70, 70, 70), r, border_radius=10)
            label = font.render(KEYPAD_KEYS[i], True, (255, 255, 255))
            screen.blit(label, (r.centerx - label.get_width()//2, r.centery - label.get_height()//2))

        if pin_error and (time.time() - pin_error_t0) < 2.0:
            err = font_small.render(pin_error, True, (255, 90, 90))
            screen.blit(err, (W//2 - err.get_width()//2, pad_y + pad_h + 18))

        tip = font_small.render("Enter=submit, Backspace=delete, tap OK=submit.", True, (230, 230, 230))
        screen.blit(tip, (W//2 - tip.get_width()//2, pad_y + pad_h + 50))

    # Toast message
    if toast and now_ms() <= toast_until_ms:
        t = font_small.render(toast, True, (255, 220, 80))
        screen.blit(t, (16, H - 28))

    pygame.display.flip()

pygame.quit()
