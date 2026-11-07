#!/usr/bin/env bash
# Every software test of STONE OS (rebuild), F0. Prints PASS or FAIL.
#   scripts/test-all.sh
#   PYTHON=python3.12 scripts/test-all.sh
# Uses pytest when it is installed (CI, dev container), each test file as a script otherwise.
# With STONE_REQUIRE_ALL=1 a test that cannot run is a failure, not a skip.
# Passing means CODE TESTED. Nothing here touches or verifies real BC-250 hardware.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
PY="${PYTHON:-python3}"
if "$PY" -c "import pytest" 2>/dev/null; then
    "$PY" -m pytest -q
    rc=$?
else
    rc=0
    for t in tests/test_*.py; do
        echo "=== ${t}"
        "$PY" "$t" || rc=1
    done
fi
echo
if [[ $rc -eq 0 ]]; then echo "TEST-ALL: PASS"; else echo "TEST-ALL: FAIL"; fi
exit "$rc"
