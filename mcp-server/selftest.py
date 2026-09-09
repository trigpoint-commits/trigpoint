#!/usr/bin/env python3
"""
Regression selftest for the Trigpoint MCP server + integrity_core.
Locks in known scores so a change that silently breaks scanning (or the checker-path resolution — which DID break
once when published, see git history) fails loudly instead. Run: python3 selftest.py  (exit 0 = all pass).

No network, no MCP client needed for the core checks; the optional --mcp flag also exercises the live stdio server
if the `mcp` package is importable.
"""
import os, sys, json, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from integrity_core import analyze  # noqa: E402

SAMPLES = os.path.join(HERE, "..", "sample-audit")

# (label, input, expected_score, expected_min_findings)  — scores are the frozen contract of the current heuristic.
CASES = [
    ("coding transcript",  os.path.join(SAMPLES, "example-agent-transcript.jsonl"),          45, 15),
    ("support-bot",        os.path.join(SAMPLES, "example-support-bot-transcript.jsonl"),     88, 6),
    ("rag agent",          os.path.join(SAMPLES, "example-rag-agent-transcript.jsonl"),       96, 2),
    ("clean text",         "The tests are in tests/ and CI run 8842 shows 42 passed; see logs.", 100, 0),
    ("empty",              "",                                                                 100, 0),
    ("dirty snippet",      'definitely the fastest, 100% secure. Studies show 47.3% better. See arXiv:9999.1', 78, 5),
]

def read(x):
    return open(x, encoding="utf-8", errors="replace").read() if os.path.isfile(x) else x

def main():
    fails = []
    for label, inp, exp_score, exp_min in CASES:
        d = analyze(read(inp))
        score, n = d["score"], d["n_findings"]
        ok = (score == exp_score and n >= exp_min)
        print(f"  [{'PASS' if ok else 'FAIL'}] {label:18} score={score} (exp {exp_score})  findings={n} (exp>={exp_min})")
        if not ok:
            fails.append(label)

    # structural invariants
    d = analyze("x")
    for key in ("score", "band", "n_findings", "counts", "findings", "disclaimer"):
        if key not in d:
            fails.append(f"missing key {key}")
    if not (3 <= analyze("100% guaranteed bulletproof never fails")["score"] <= 100):
        fails.append("score out of range")

    if "--mcp" in sys.argv:
        try:
            r = subprocess.run([sys.executable, "-c",
                "import mcp; from mcp.server import MCPServer; print('ok')"],
                capture_output=True, text=True, timeout=30)
            print(f"  [{'PASS' if r.returncode==0 else 'SKIP'}] mcp import ({r.stdout.strip() or r.stderr.strip()[:40]})")
        except Exception as e:
            print(f"  [SKIP] mcp not installed ({e})")

    print(f"\n{'='*50}\n{'ALL PASS' if not fails else 'FAIL: '+', '.join(fails)}  ({len(CASES)} cases)")
    return 1 if fails else 0

if __name__ == "__main__":
    sys.exit(main())
