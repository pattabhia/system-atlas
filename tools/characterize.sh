#!/usr/bin/env bash
# characterize.sh — attempt to run the target's own tests as a CHARACTERIZATION ORACLE
# (Skill 08 layer 3). The current/legacy implementation's actual outputs are the oracle;
# this avoids the anti-circularity trap (model predicting its own expected values).
#
# Usage: characterize.sh <project-dir> [<mvn-args...>]
# Emits a JSON-ish summary. Requires a buildable project (deps + a JDK); when the build
# cannot run offline (missing deps, no DB, external services), it says so — that is the
# honest 'not executed' result, recorded as capability gap CG-04, not a silent skip.
set -uo pipefail
PROJ="${1:?project dir}"; shift || true
cd "$PROJ"
LOG="$(mktemp)"
echo "running: mvn -o test $* (offline first)"
if mvn -o test "$@" >"$LOG" 2>&1; then
  RESULT=passed
elif mvn test "$@" >"$LOG" 2>&1; then
  RESULT=passed-online
else
  RESULT=failed-or-unbuildable
fi
TESTS=$(grep -Eo 'Tests run: [0-9]+' "$LOG" | tail -1 || true)
FAILS=$(grep -Eo 'Failures: [0-9]+, Errors: [0-9]+' "$LOG" | tail -1 || true)
echo "{"
echo "  \"result\": \"$RESULT\","
echo "  \"tests\": \"${TESTS:-unknown}\", \"failures\": \"${FAILS:-unknown}\","
echo "  \"oracle\": \"the current implementation's observed test outcomes\","
echo "  \"note\": \"if result is failed-or-unbuildable offline, record CG-04 (no executed oracle) and keep structural+BDD verification; do NOT fabricate expected values.\","
echo "  \"log\": \"$LOG\""
echo "}"
[ "$RESULT" = "failed-or-unbuildable" ] && echo ">> tail of build log:" && tail -8 "$LOG"
