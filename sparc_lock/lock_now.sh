#!/usr/bin/env bash
set -euo pipefail

# Closing the viewer is the cleanest way to return to the lock flow
pkill -x vncviewer 2>/dev/null || true
pkill -x xtigervncviewer 2>/dev/null || true

exit 0
