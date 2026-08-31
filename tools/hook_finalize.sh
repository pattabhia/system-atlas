#!/usr/bin/env bash
# Stop-hook entry: finalize any behavior-baseline pack that changed since its last
# MANIFEST.md (emit manifest + run lint gate). Idempotent and cheap — a no-op unless a
# pack was actually produced/modified. NEVER blocks the session (always exit 0).
#
# Wire as a Claude Code Stop hook (see README). Searches the workspace store(s) for packs.
ATLAS="$(cd "$(dirname "$0")/.." && pwd)"
PY="${ATLAS_PYTHON:-python3}"

# Search roots (portable — no estate-specific literals). ATLAS_BASELINES may point at a
# custom store; otherwise use the session's project dir and cwd.
roots=()
[ -n "${ATLAS_BASELINES:-}" ] && roots+=("$ATLAS_BASELINES")
[ -n "${CLAUDE_PROJECT_DIR:-}" ] && roots+=("$CLAUDE_PROJECT_DIR/.haiintel/behavior-baselines")
roots+=("$PWD/.haiintel/behavior-baselines")

seen="|"
for base in "${roots[@]}"; do
  [ -d "$base" ] || continue
  for pack in "$base"/*/; do
    [ -d "${pack}90-evidence" ] || continue
    case "$seen" in *"|$pack|"*) continue;; esac
    seen="$seen$pack|"
    man="${pack}MANIFEST.md"
    if [ ! -f "$man" ] || [ -n "$(find "$pack" -type f -newer "$man" \
          ! -name MANIFEST.md ! -name lint-report.json -print -quit 2>/dev/null)" ]; then
      echo "[atlas-hook] finalizing $pack"
      bash "$ATLAS/tools/finalize_pack.sh" "$pack" "$PY" || true
    fi
  done
done
exit 0
