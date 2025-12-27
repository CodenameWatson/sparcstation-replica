#!/usr/bin/env bash
set -euo pipefail

cd /home/pi/sparc_lock

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-/home/pi/.Xauthority}"
export HOME="/home/pi"
export USER="pi"
export LOGNAME="pi"

# Prevent blanking / DPMS (only if xset exists)
if command -v xset >/dev/null 2>&1; then
  xset s off || true
  xset -dpms || true
  xset s noblank || true
fi

CFG="/home/pi/sparc_lock/kiosk_config.yaml"
POST_UNLOCK="solaris"

# Read feature_flags.post_unlock safely (defaults to "solaris" if missing)
if [[ -f "$CFG" ]]; then
  POST_UNLOCK="$(
    CFG="$CFG" python3 - <<'PY' 2>/dev/null || echo solaris
import os
try:
    import yaml
except Exception:
    print("solaris")
    raise SystemExit(0)

cfg_path = os.environ.get("CFG", "/home/pi/sparc_lock/kiosk_config.yaml")
try:
    cfg = yaml.safe_load(open(cfg_path, "r")) or {}
    ff = cfg.get("feature_flags", {}) or {}
    v = (ff.get("post_unlock","solaris") or "solaris").strip().lower()
    print(v if v in ("menu","solaris") else "solaris")
except Exception:
    print("solaris")
PY
  )"
fi

if [[ "$POST_UNLOCK" == "menu" && -f /home/pi/sparc_lock/kiosk_shell.py ]]; then
  mkdir -p /home/pi/sparc_lock/logs
  exec python3 -u /home/pi/sparc_lock/kiosk_shell.py >> /home/pi/sparc_lock/logs/kiosk_shell.log 2>&1
else
  # Legacy behavior: lock app controls post-unlock (enter_vm_mode()).
  exec python3 -u /home/pi/sparc_lock/puzzle_lock.py
fi