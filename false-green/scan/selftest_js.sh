#!/usr/bin/env bash
set -u; cd "$(dirname "$0")"; fail=0
n=$(python3 scan_js.py --json tjs/fake | python3 -c "import sys,json;print(json.load(sys.stdin)['total'])")
h=$(python3 scan_js.py --json tjs/fake | python3 -c "import sys,json;print(json.load(sys.stdin)['high'])")
[ "$n" = 8 ] && echo "ok   fake: 8 signals" || { echo "FAIL fake total=$n want 8"; fail=1; }
[ "$h" = 6 ] && echo "ok   fake: 6 HIGH" || { echo "FAIL fake high=$h want 6"; fail=1; }
python3 scan_js.py tjs/real >/dev/null 2>&1 && echo "ok   real: clean (exit 0)" || { echo "FAIL real not clean"; fail=1; }
[ "$fail" = 0 ] && echo ALL GREEN || echo REGRESSIONS; exit $fail
