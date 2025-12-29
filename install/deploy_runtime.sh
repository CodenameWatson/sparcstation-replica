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

if [[ ! -d "$SRC_LOCK" ]]; then
  echo "ERROR: missing $SRC_LOCK" >&2
  exit 1
fi

mkdir -p "$DST_LOCK"

rsync -av --delete "${RSYNC_EXTRA[@]}" \
  --exclude 'kiosk.log' \
  --exclude '*.log' \
  --exclude 'logs/' \
  --exclude '_attic/' \
  --exclude '__pycache__/' \
  --exclude '.DS_Store' \
  --exclude 'images/' \
  --exclude 'sounds/' \
  "$SRC_LOCK/" "$DST_LOCK/"

# Normalize line endings (CRLF -> LF) on scripts to prevent 'bash\r' and EOF parsing issues
if [[ "$DRY_RUN" != "1" ]]; then
  find "$DST_LOCK" -maxdepth 1 -type f \( -name "*.sh" -o -name "*.py" \) -print0 \
    | xargs -0 -r sed -i 's/\r$//'
fi

# Ensure key scripts are executable (best-effort)
chmod +x "$DST_LOCK/"*.sh 2>/dev/null || true
chmod +x "$DST_LOCK/kiosk_shell.py" 2>/dev/null || true
chmod +x "$DST_LOCK/puzzle_lock.py" 2>/dev/null || true

# Remove/disable any old systemd user service launcher (prevents starting outside X session)
if [[ "$DRY_RUN" != "1" ]]; then
  rm -f /home/pi/.config/systemd/user/sparc-kiosk.service 2>/dev/null || true
  rm -f /home/pi/.config/systemd/user/default.target.wants/sparc-kiosk.service 2>/dev/null || true
fi

echo "[deploy] Done."
