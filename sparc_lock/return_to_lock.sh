#!/usr/bin/env bash
set -euo pipefail

BASE="/home/pi/sparc_lock"
LOGDIR="$BASE/logs"
LOG="$LOGDIR/return_to_lock.log"
mkdir -p "$LOGDIR"

SENTINEL="/tmp/sparc_pi_mode_exit"

{
  echo "---- return_to_lock.sh $(date -Is) ----"
  touch "$SENTINEL"
  echo "Touched sentinel: $SENTINEL"
} >>"$LOG" 2>&1

exit 0
