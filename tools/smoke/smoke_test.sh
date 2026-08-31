#!/usr/bin/env bash
# Thin wrapper — the real harness is smoke_test.py (portable: all file I/O in Python,
# no /tmp literal, no path handed across the bash<->python boundary). Kept for CI/manual use.
exec "${ATLAS_PYTHON:-python3}" "$(cd "$(dirname "$0")" && pwd)/smoke_test.py" "$@"
