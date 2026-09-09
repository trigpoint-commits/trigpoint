#!/usr/bin/env python3
"""
Repo selftest: packaging sanity + drift guard. Run before every push.  python3 selftest.py  (exit 0 = ok)

The free tool exists in two names in this repo — the single-file "paste it in" version (agent-integrity-quickcheck.py,
what the landing links) and the importable package module (trigpoint_quickcheck.py, what `uvx`/`pip` ship). They MUST
stay byte-identical; this fails loudly if they drift.
"""
import os, sys, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
SINGLE = os.path.join(HERE, "agent-integrity-quickcheck.py")
MODULE = os.path.join(HERE, "trigpoint_quickcheck.py")

def main():
    fails = []
    # 1. drift guard: the two tool copies must be byte-identical
    a = open(SINGLE, "rb").read()
    b = open(MODULE, "rb").read()
    if a == b:
        print("  [PASS] tool copies byte-identical (no drift)")
    else:
        fails.append("DRIFT: agent-integrity-quickcheck.py != trigpoint_quickcheck.py")
        print("  [FAIL] tool copies have DRIFTED — re-sync before shipping")

    # 2. package module imports + exposes main()
    spec = importlib.util.spec_from_file_location("trigpoint_quickcheck", MODULE)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    if callable(getattr(m, "main", None)):
        print("  [PASS] trigpoint_quickcheck.main() present (console-script entry)")
    else:
        fails.append("no main() in trigpoint_quickcheck")

    # 3. known-score smoke (guards the scan logic itself)
    import io, contextlib
    for arg, needle in [("100% guaranteed, studies show 47.3%, see arXiv:9999.1", "Integrity score")]:
        sys.argv = ["trigpoint", arg]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try: m.main()
            except SystemExit: pass
        out = buf.getvalue()
        print(f"  [{'PASS' if needle in out else 'FAIL'}] scan smoke ('{arg[:24]}...')")
        if needle not in out: fails.append("scan smoke")

    print("=" * 46)
    print("ALL PASS" if not fails else "FAIL: " + "; ".join(fails))
    return 1 if fails else 0

if __name__ == "__main__":
    sys.exit(main())
