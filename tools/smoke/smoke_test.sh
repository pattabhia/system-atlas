#!/usr/bin/env bash
# smoke_test.sh — regression guards that catch the target-leak + portability bug class
# a code review found (specifics of one validation target leaking into generic paths).
# Uses the non-MOSIP com.acme fixture. Run after install.sh and in CI.
#
#   tools/smoke/smoke_test.sh
# Exit 0 if all guards pass; non-zero otherwise.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ATLAS="$(cd "$HERE/../.." && pwd)"
PY="${ATLAS_PYTHON:-python3}"
FIX="$HERE/fixtures/acme/src/main/java"
JAR="$ATLAS/adapters/java-maven/callgraph-jvm/target/callgraph.jar"
fails=0
pass(){ echo "  ✓ $1"; }
fail(){ echo "  ✗ $1"; fails=$((fails+1)); }

echo "== system-atlas smoke test (non-MOSIP fixture) =="

# ensure the Stage-B jar exists
if [ ! -f "$JAR" ] && command -v mvn >/dev/null 2>&1; then
  ( cd "$ATLAS/adapters/java-maven/callgraph-jvm" && mvn -q -DskipTests package >/dev/null 2>&1 ) || true
fi

# GUARD 1 — target-leak: interface->impl override edges must emit on a non-MOSIP package
if [ -f "$JAR" ]; then
  java -jar "$JAR" --src "$FIX" > /tmp/atlas-smoke-cg.json 2>/dev/null
  n=$("$PY" -c "import json;print(json.load(open('/tmp/atlas-smoke-cg.json'))['counts']['override_edges'])" 2>/dev/null || echo 0)
  edge=$("$PY" -c "import json;print(any(e.get('dispatch')=='override' and e['callee']['owner_fqn']=='com.acme.RepoImpl' for e in json.load(open('/tmp/atlas-smoke-cg.json'))['edges']))" 2>/dev/null || echo False)
  [ "$n" -ge 1 ] && [ "$edge" = "True" ] \
    && pass "override edges emit on com.acme (interface->impl, generic)" \
    || fail "override edges NOT emitted on com.acme (target-leak regression!) override_edges=$n"
else
  fail "callgraph.jar missing and mvn unavailable — cannot run GUARD 1"
fi

# GUARD 2 — seq_diagram must infer the project package (no hardcoded MOSIP default)
if [ -f /tmp/atlas-smoke-cg.json ]; then
  out=$("$PY" "$ATLAS/tools/seq_diagram.py" /tmp/atlas-smoke-cg.json "Svc#run" --depth 2 2>&1)
  echo "$out" | grep -q "inferred --project=com.acme" \
    && pass "seq_diagram infers --project=com.acme (no MOSIP default)" \
    || fail "seq_diagram did not infer com.acme"
fi

# GUARD 3 — portability: finalize must survive a degraded pack with no 90-evidence/ dir
TMP="$(mktemp -d)/behavior-baselines/toy-pack"; mkdir -p "$TMP/03-operations"
bash "$ATLAS/tools/finalize_pack.sh" "$TMP" "$PY" >/dev/null 2>&1
rc=$?
[ $rc -eq 0 ] && [ -f "$TMP/MANIFEST.md" ] \
  && pass "finalize survives a degraded/non-Java pack (mkdir 90-evidence)" \
  || fail "finalize crashed on a degraded pack (rc=$rc)"

echo
if [ "$fails" -eq 0 ]; then echo "SMOKE: PASS"; exit 0; else echo "SMOKE: FAIL ($fails)"; exit 1; fi
