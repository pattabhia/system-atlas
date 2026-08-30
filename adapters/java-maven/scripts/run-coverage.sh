#!/usr/bin/env bash
# run-coverage.sh — produce the closure-driven coverage substrate for a Java/Maven run.
# Chains: source model -> call graph (Stage B if the jar exists, else Stage A) -> reachability.
# The orchestrator invokes this after Skill 03 (entry points), then Skill 04 visits every
# reachable method and marks visited status in <out>/coverage inputs.
#
# Usage:
#   run-coverage.sh <src-root> "<entry1,entry2,...>" <out-dir> [python] [callgraph-jar] [classpath-file]
#
# Outputs into <out-dir>: source-model.json, callgraph.json, reachability.json
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="${1:?src root}"; ENTRY="${2:?comma-separated entry method names}"; OUT="${3:?out dir}"
PY="${4:-python3}"; JAR="${5:-$HERE/../callgraph-jvm/target/callgraph.jar}"; CP="${6:-}"
mkdir -p "$OUT"

echo "[1/3] source model (tree-sitter)…"
"$PY" "$HERE/java_ast.py" --root "$SRC" --model > "$OUT/source-model.json"

echo "[2/3] call graph…"
if [ -f "$JAR" ]; then
  if [ -n "$CP" ] && [ -f "$CP" ]; then
    java -jar "$JAR" --src "$SRC" --classpath "$CP" > "$OUT/callgraph.json"
  else
    java -jar "$JAR" --src "$SRC" > "$OUT/callgraph.json"
  fi
  echo "      Stage B (symbol-solved + override edges)"
else
  "$PY" "$HERE/java_ast.py" --root "$SRC" --callgraph > "$OUT/callgraph.json"
  echo "      Stage A (heuristic — build callgraph-jvm for Stage B)"
fi

echo "[3/3] reachability closure…"
"$PY" "$HERE/reachability.py" --model "$OUT/source-model.json" \
     --callgraph "$OUT/callgraph.json" --entry "$ENTRY" > "$OUT/reachability.json"

"$PY" - "$OUT/reachability.json" <<'PYEOF'
import json,sys
d=json.load(open(sys.argv[1]));c=d["counts"]
print(f"\ncoverage substrate ready: {c['total_methods']} methods | reachable {c['reachable']} | "
      f"accessors {c['accessors']} | unreached {c['unreached']}")
print("→ Skill 04 must now VISIT every reachable method and CLASSIFY the unreached set "
      "(framework entry points are new operations).")
PYEOF
