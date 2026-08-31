#!/usr/bin/env bash
# run-coverage.sh — produce the closure-driven coverage substrate for a Java/Maven run.
# Chains: source model -> call graph (Stage B if the jar exists, else Stage A) -> reachability.
# The orchestrator invokes this after Skill 03 (entry points), then Skill 04 visits every
# reachable method and marks visited status in <out>/coverage inputs.
#
# Usage:
#   run-coverage.sh <src-root> "<entry1,entry2,...>" <out-dir> [python] [callgraph-jar] [classpath-file]
#
# Outputs into <out-dir>: source-model, callgraph, reachability, branches, exceptions,
# errorcodes, config (.json each).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="${1:?src root}"; ENTRY="${2:?comma-separated entry method names}"; OUT="${3:?out dir}"
PY="${4:-python3}"; JAR="${5:-$HERE/../callgraph-jvm/target/callgraph.jar}"; CP="${6:-}"
mkdir -p "$OUT"

echo "[1/7] source model (tree-sitter)…"
"$PY" "$HERE/java_ast.py" --root "$SRC" --model > "$OUT/source-model.json"

echo "[2/7] call graph…"
# On git-bash/MSYS (Windows), native java.exe needs Windows-form paths; MSYS otherwise
# mangles POSIX/comma-list args. cygpath -m converts; no-op elsewhere. Convert each --src
# root (comma-separated) so multi-root is honored, plus the jar and classpath file.
winpath() { if command -v cygpath >/dev/null 2>&1; then cygpath -m "$1"; else printf '%s' "$1"; fi; }
# Multi-module: Stage-B needs one JavaParserTypeSolver PER real source root, else
# com.foo.Bar resolves against the wrong base (symptom: low resolution %, 0 override
# edges). Discover every src/main/java under SRC (excluding target/); fall back to SRC.
discover_roots() {
  local rs; rs=$(find "$1" -type d -path '*/src/main/java' -not -path '*/target/*' 2>/dev/null | sort -u)
  [ -n "$rs" ] && printf '%s\n' "$rs" || printf '%s\n' "$1"
}
if [ -f "$JAR" ]; then
  JARW="$(winpath "$JAR")"
  SRCW=""; while IFS= read -r r; do [ -n "$r" ] && SRCW="$SRCW,$(winpath "$r")"; done <<EOF
$(discover_roots "$SRC")
EOF
  SRCW="${SRCW#,}"
  if [ -n "$CP" ] && [ -f "$CP" ]; then
    java -jar "$JARW" --src "$SRCW" --classpath "$(winpath "$CP")" > "$OUT/callgraph.json"
  else
    java -jar "$JARW" --src "$SRCW" > "$OUT/callgraph.json"
  fi
  echo "      Stage B (symbol-solved + override edges)"
else
  "$PY" "$HERE/java_ast.py" --root "$SRC" --callgraph > "$OUT/callgraph.json"
  echo "      Stage A (heuristic — build callgraph-jvm for Stage B)"
fi

echo "[3/7] reachability closure…"
"$PY" "$HERE/reachability.py" --model "$OUT/source-model.json" \
     --callgraph "$OUT/callgraph.json" --entry "$ENTRY" > "$OUT/reachability.json"

echo "[4/7] branch inventory (branch-completeness)…"
"$PY" "$HERE/java_ast.py" --root "$SRC" --branches > "$OUT/branches.json"

echo "[5/7] exception handlers (silent-failure detection)…"
"$PY" "$HERE/java_ast.py" --root "$SRC" --exceptions > "$OUT/exceptions.json"

echo "[6/7] error/status code catalog…"
"$PY" "$HERE/java_ast.py" --root "$SRC" --errorcodes > "$OUT/errorcodes.json"

echo "[7/7] config keys + feature flags…"
"$PY" "$HERE/java_ast.py" --root "$SRC" --config > "$OUT/config.json"

"$PY" - "$OUT/reachability.json" <<'PYEOF'
import json,sys
d=json.load(open(sys.argv[1]));c=d["counts"]
print(f"\ncoverage substrate ready: {c['total_methods']} methods | reachable {c['reachable']} | "
      f"accessors {c['accessors']} | unreached {c['unreached']}")
print("→ Skill 04 must now VISIT every reachable method and CLASSIFY the unreached set "
      "(framework entry points are new operations).")
b=json.load(open(sys.argv[1].replace('reachability.json','branches.json')))
bc=b["counts"]
print(f"→ branch-completeness: {bc['branches']} branches / {bc['arms']} arms across "
      f"{bc['methods_with_branches']} methods — Skill 06 must reconcile each branch arm.")
ex=json.load(open(sys.argv[1].replace('reachability.json','exceptions.json')))
print(f"→ silent-failure handlers: {ex['counts']['silent_failures']} of {ex['counts']['handlers']} "
      "catch blocks swallow (log-only/empty/return-null) — each is a behavior (Skill 06/07), not noise.")
ec=json.load(open(sys.argv[1].replace('reachability.json','errorcodes.json')))
print(f"→ code catalog: {ec['counts']['constants']} enum constants across {ec['counts']['enums']} "
      "enums (error/status/reason/endpoint codes) — semantic evidence for Skill 06.")
PYEOF
