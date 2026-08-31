#!/usr/bin/env bash
# finalize_pack.sh — mandatory end-of-run step for every system-atlas run.
# 1) emit the self-documenting MANIFEST.md   2) run the self-consistency lint gate.
# Prints the lint verdict; exits non-zero if the pack has FAIL findings.
#
# Usage: finalize_pack.sh <pack-dir> [python]
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PACK="${1:?pack dir}"; PY="${2:-python3}"

"$PY" "$HERE/pack_manifest.py" "$PACK"
"$PY" "$HERE/pack_lint.py" "$PACK" > "$PACK/90-evidence/lint-report.json"; RC=$?
"$PY" - "$PACK/90-evidence/lint-report.json" <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1])); c = d["counts"]
print(f"lint: {'PASS' if d['ok'] else 'FAIL'} — {c['fail']} fail, {c['warn']} warn")
for f in d["findings"]:
    print(f"  [{f['severity']}] {f['check']}: {f['message'][:100]}")
if c["fail"]:
    print("\n>> FAIL findings block completion. Fix them (or the evidence), then re-finalize.")
PYEOF
exit $RC
