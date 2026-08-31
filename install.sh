#!/usr/bin/env bash
# install.sh — self-locating installer for system-atlas. Run once per machine, from
# wherever you cloned the repo. Makes /atlas + the skills + the Stop hook available in
# ANY repo, with absolute paths pinned to THIS clone location (via $ATLAS_HOME).
#
#   git clone <repo> && cd system-atlas && ./install.sh
set -euo pipefail
ATLAS_HOME="$(cd "$(dirname "$0")" && pwd)"
CLAUDE="$HOME/.claude"
mkdir -p "$CLAUDE/skills" "$CLAUDE/commands"

echo "system-atlas at: $ATLAS_HOME"

# 1) skills (all 9 — orchestrator is the entry point; workers are routed by it)
cp -R "$ATLAS_HOME/.claude/skills/"* "$CLAUDE/skills/"
echo "  ✓ skills -> $CLAUDE/skills"

# 2) /atlas command (uses $ATLAS_HOME, set as an env var below)
cp "$ATLAS_HOME/.claude/commands/atlas.md" "$CLAUDE/commands/atlas.md"
echo "  ✓ /atlas -> $CLAUDE/commands/atlas.md"

# 3) settings.json — set env.ATLAS_HOME (so $ATLAS_HOME resolves in every Bash call)
#    and register the Stop hook with an absolute path. Merge; never clobber.
python3 - "$CLAUDE/settings.json" "$ATLAS_HOME" <<'PY'
import json, os, sys
p, home = sys.argv[1], sys.argv[2]
d = json.load(open(p)) if os.path.exists(p) else {}
d.setdefault("env", {})["ATLAS_HOME"] = home
hook = f"{home}/tools/hook_finalize.sh"
stop = d.setdefault("hooks", {}).setdefault("Stop", [])
# drop any prior atlas hook entry, then add the current one
stop = [s for s in stop if "hook_finalize.sh" not in json.dumps(s)]
stop.append({"hooks": [{"type": "command", "command": hook}]})
d["hooks"]["Stop"] = stop
if os.path.exists(p):
    os.replace(p, p + ".bak")
json.dump(d, open(p, "w"), indent=2)
print(f"  ✓ settings.json: env.ATLAS_HOME set; Stop hook -> {hook} (backup .bak)")
PY

# 4) python deps for the analyzers (idempotent)
echo "==> python deps (tree-sitter, tree-sitter-java, pyyaml)"
python3 -m pip install --quiet --user tree-sitter tree-sitter-java pyyaml 2>/dev/null \
  && echo "  ✓ deps installed" || echo "  ! install manually: pip install tree-sitter tree-sitter-java pyyaml"

# 5) build the Stage-B symbol-solver jar (optional; needs mvn + JDK 21 + first-build network)
if command -v mvn >/dev/null 2>&1; then
  echo "==> building Stage-B call-graph jar (optional)"
  ( cd "$ATLAS_HOME/adapters/java-maven/callgraph-jvm" && mvn -q -DskipTests package >/dev/null 2>&1 ) \
    && echo "  ✓ callgraph.jar built" || echo "  ! jar build skipped (offline?) — Stage A heuristic still works"
fi

# 6) smoke test — verify the install works generically (target-leak + portability guards).
#    Run the portable Python harness directly (no shell temp-path assumptions).
echo "==> smoke test (non-MOSIP fixture)"
SMOKE_LOG="$(python3 -c 'import tempfile,os;print(os.path.join(tempfile.gettempdir(),"atlas-smoke.log"))')"
if python3 "$ATLAS_HOME/tools/smoke/smoke_test.py" >"$SMOKE_LOG" 2>&1; then
  echo "  ✓ smoke: PASS"
else
  echo "  ! smoke: FAIL — see $SMOKE_LOG (investigate before client use)"
fi

echo
echo "Done. Restart your Claude Code session so ATLAS_HOME + hook load."
echo "Then, from ANY repo:   /atlas ./that-repo [OperationName]"
