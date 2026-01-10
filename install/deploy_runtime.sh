#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------------------------------
# deploy_runtime.sh - sync repo sparc_lock/ -> /home/pi/sparc_lock
#
# Defaults are conservative:
# - preserves kiosk_config.yaml on the device unless UPDATE_CONFIG=1
# - preserves images/ and sounds/ unless SYNC_ASSETS=1
# - preserves sparc_media/ (persistent library content) unless SYNC_MEDIA=1
# - atomic-ish swap via a staging directory (unless ATOMIC=0)
#
# Usage examples:
#   DRY_RUN=1 ./install/deploy_runtime.sh
#   UPDATE_CONFIG=1 ./install/deploy_runtime.sh
#   SYNC_ASSETS=1 ./install/deploy_runtime.sh
#   SYNC_MEDIA=1 ./install/deploy_runtime.sh   # ONLY if you intentionally version sparc_media
# -----------------------------------------------------------------------------

DRY_RUN="${DRY_RUN:-0}"
UPDATE_CONFIG="${UPDATE_CONFIG:-0}"   # 1 = overwrite kiosk_config.yaml from repo
SYNC_ASSETS="${SYNC_ASSETS:-0}"       # 1 = sync images/ and sounds/
SYNC_MEDIA="${SYNC_MEDIA:-0}"         # 1 = sync sparc_media/ (normally leave 0)
ATOMIC="${ATOMIC:-1}"                 # 1 = stage then swap
VERBOSE="${VERBOSE:-1}"

log() {
  if [[ "$VERBOSE" == "1" ]]; then
    echo "[deploy] $*"
  fi
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "ERROR: missing required command: $1" >&2; exit 1; }
}

need_cmd rsync
need_cmd find
need_cmd xargs
need_cmd sed

RSYNC_EXTRA=()
if [[ "$DRY_RUN" == "1" ]]; then
  RSYNC_EXTRA+=(--dry-run --itemize-changes)
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_LOCK="$REPO_ROOT/sparc_lock"
DST_LOCK="/home/pi/sparc_lock"

# Stage directory for atomic swap
STAGE_PARENT="/home/pi/.deploy_staging"
STAGE_LOCK="$STAGE_PARENT/sparc_lock.next"

log "Repo: $REPO_ROOT"
log "Sync: $SRC_LOCK -> $DST_LOCK"

if [[ ! -d "$SRC_LOCK" ]]; then
  echo "ERROR: missing $SRC_LOCK" >&2
  exit 1
fi

# Build rsync excludes
EXCLUDES=(
  --exclude 'kiosk.log'
  --exclude '*.log'
  --exclude 'logs/'
  --exclude '_attic/'
  --exclude '__pycache__/'
  --exclude '.DS_Store'
)

# Preserve local device assets unless explicitly asked
if [[ "$SYNC_ASSETS" != "1" ]]; then
  EXCLUDES+=(--exclude 'images/' --exclude 'sounds/')
fi

# Preserve sparc_media unless explicitly asked (this is persistent runtime content)
if [[ "$SYNC_MEDIA" != "1" ]]; then
  EXCLUDES+=(--exclude 'sparc_media/')
fi

# Preserve device config unless explicitly asked
if [[ "$UPDATE_CONFIG" != "1" ]]; then
  EXCLUDES+=(--exclude 'kiosk_config.yaml')
fi

# Decide destination (atomic staging or direct)
if [[ "$ATOMIC" == "1" ]]; then
  if [[ "$DRY_RUN" == "1" ]]; then
    # In dry-run mode, compare directly against the live destination
    DEST="$DST_LOCK"
    log "DRY_RUN: comparing against live destination ($DEST); no changes will be made"
  else
    mkdir -p "$STAGE_PARENT"
    rm -rf "$STAGE_LOCK"
    mkdir -p "$STAGE_LOCK"
    DEST="$STAGE_LOCK"
    log "Atomic deploy: staging to $DEST then swapping into $DST_LOCK"
  fi
else
  mkdir -p "$DST_LOCK"
  DEST="$DST_LOCK"
  log "Non-atomic deploy: syncing directly into $DEST"
fi

# Rsync the tree
rsync -a --delete "${RSYNC_EXTRA[@]}" \
  "${EXCLUDES[@]}" \
  "$SRC_LOCK/" "$DEST/"

# Normalize line endings (CRLF -> LF) on scripts
if [[ "$DRY_RUN" != "1" ]]; then
  find "$DEST" -type f \( -name "*.sh" -o -name "*.py" \) -print0 \
    | xargs -0 -r sed -i 's/\r$//'
fi

# Ensure key scripts are executable (best-effort)
if [[ "$DRY_RUN" != "1" ]]; then
  chmod +x "$DEST/"*.sh 2>/dev/null || true
  chmod +x "$DEST/kiosk_shell.py" 2>/dev/null || true
  chmod +x "$DEST/puzzle_lock.py" 2>/dev/null || true
fi

# Remove/disable any old systemd user service launcher (prevents starting outside X session)
if [[ "$DRY_RUN" != "1" ]]; then
  rm -f /home/pi/.config/systemd/user/sparc-kiosk.service 2>/dev/null || true
  rm -f /home/pi/.config/systemd/user/default.target.wants/sparc-kiosk.service 2>/dev/null || true
fi

# Swap staged deploy into place
if [[ "$ATOMIC" == "1" && "$DRY_RUN" != "1" ]]; then
  mkdir -p "$DST_LOCK"

  # If kiosk_config.yaml is excluded, preserve existing config by copying it into stage
  if [[ "$UPDATE_CONFIG" != "1" && -f "$DST_LOCK/kiosk_config.yaml" && ! -f "$STAGE_LOCK/kiosk_config.yaml" ]]; then
    cp -a "$DST_LOCK/kiosk_config.yaml" "$STAGE_LOCK/kiosk_config.yaml" || true
  fi

  # Preserve existing assets if excluded and stage doesn’t have them
  if [[ "$SYNC_ASSETS" != "1" ]]; then
    if [[ -d "$DST_LOCK/images" && ! -d "$STAGE_LOCK/images" ]]; then
      cp -a "$DST_LOCK/images" "$STAGE_LOCK/images" || true
    fi
    if [[ -d "$DST_LOCK/sounds" && ! -d "$STAGE_LOCK/sounds" ]]; then
      cp -a "$DST_LOCK/sounds" "$STAGE_LOCK/sounds" || true
    fi
  fi

  # Preserve sparc_media across atomic swap if excluded
  MEDIA_TMP=""
  if [[ "$SYNC_MEDIA" != "1" ]]; then
    if [[ -d "$DST_LOCK/sparc_media" && ! -e "$STAGE_LOCK/sparc_media" ]]; then
      MEDIA_TMP="$STAGE_PARENT/sparc_media.keep.$(date +%Y%m%d_%H%M%S)"
      log "Preserving sparc_media/: moving to $MEDIA_TMP"
      mv "$DST_LOCK/sparc_media" "$MEDIA_TMP"
    fi
  fi

  # Swap
  BACKUP="$STAGE_PARENT/sparc_lock.prev.$(date +%Y%m%d_%H%M%S)"
  mv "$DST_LOCK" "$BACKUP"
  mv "$STAGE_LOCK" "$DST_LOCK"

  # Restore sparc_media into the new deployed tree (if we temporarily moved it out)
  if [[ -n "$MEDIA_TMP" && -d "$MEDIA_TMP" && ! -e "$DST_LOCK/sparc_media" ]]; then
    mv "$MEDIA_TMP" "$DST_LOCK/sparc_media"
    MEDIA_TMP=""
  fi

  log "Swapped. Backup saved at: $BACKUP"
fi
