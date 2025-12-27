#!/usr/bin/env bash
set -euo pipefail

DRY_RUN="${DRY_RUN:-0}"
RSYNC_EXTRA=()
if [[ "$DRY_RUN" == "1" ]]; then
  RSYNC_EXTRA+=(--dry-run --itemize-changes)
fi


REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_LOCK="$REPO_ROOT/sparc_lock"
DST_LOCK="/home/pi/sparc_lock"

echo "[deploy] Repo: $REPO_ROOT"
echo "[deploy] Sync $SRC_LOCK -> $DST_LOCK"

# Safety
if [[ ! -d "$SRC_LOCK" ]]; then
  echo "ERROR: missing $SRC_LOCK" >&2
  exit 1
fi

mkdir -p "$DST_LOCK"

# Sync code and scripts. Exclude runtime logs + personal assets.
rsync -av --delete "${RSYNC_EXTRA[@]}" \
  --exclude 'kiosk.log' \
  --exclude '*.log' \
  --exclude 'logs/' \
  --exclude '__pycache__/' \
  --exclude '.DS_Store' \
  --exclude 'images/' \
  --exclude 'sounds/' \
  "$SRC_LOCK/" "$DST_LOCK/"

# Ensure scripts are executable (adjust list to your actual files)
chmod +x "$DST_LOCK/start_lock.sh" || true
chmod +x "$DST_LOCK/start-lock-session.sh" || true
chmod +x "$DST_LOCK/launch_solaris.sh" || true
chmod +x "$DST_LOCK/start_pi_mode.sh" || true
chmod +x "$DST_LOCK/return_to_lock.sh" || true
chmod +x "$DST_LOCK/kiosk_shell.py" 2>/dev/null || true
chmod +x "$DST_LOCK/"*.sh 2>/dev/null || true


echo "[deploy] Done."
