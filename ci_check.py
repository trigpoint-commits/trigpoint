#!/usr/bin/env python3
"""
Trigpoint CI check — run the agent-integrity scan in CI and fail the build if the integrity score falls below a
threshold. Emits GitHub Actions annotations (::warning::) for each flagged file. Zero dependencies.

    python3 ci_check.py --min-score 70 path/to/transcript.jsonl [more paths...]
    python3 ci_check.py --min-score 70 "logs/*.jsonl"          # globs expanded here for portability

Exit 0 = all files >= min-score. Exit 1 = at least one below (build fails). Exit 2 = usage/no files.

Honest scope: this is the same regex first-pass as the free tool — it catches hallucination TELLS, not every lie.
Use it as a regression tripwire (did integrity get WORSE), not a certificate.
"""
import os, sys, glob, importlib.util, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
_CANDIDATES = [
    os.path.join(HERE, "trigpoint_quickcheck.py"),
    os.path.join(HERE, "agent-integrity-quickcheck.py"),
]

def _load():
    for p in _CANDIDATES:
        if os.path.isfile(p):
            spec = importlib.util.spec_from_file_location("aiqc", p)
            m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
            return m
    raise FileNotFoundError("scanner not found next to ci_check.py")

QC = _load()

def score_text(raw):
    msgs = QC.messages_from(raw)
    counts, total = {}, 0
    worst = None
    for i, msg in enumerate(msgs, 1):
        for ln in (msg.splitlines() or [msg]):
            for cat, frag in QC.scan_line(ln):
                counts[cat] = counts.get(cat, 0) + 1
                total += QC.CATS[cat][1]
                w = QC.CATS[cat][1]
                if worst is None or w > worst[0]:
                    worst = (w, cat, QC.sanitize(ln), i)
    score = max(3, 100 - min(97, total))
    return score, sum(counts.values()), counts, worst

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-score", type=int, default=70)
    ap.add_argument("paths", nargs="+")
    a = ap.parse_args()

    files = []
    for p in a.paths:
        files.extend(glob.glob(p)) if any(c in p for c in "*?[") else files.append(p)
    files = [f for f in files if os.path.isfile(f)]
    if not files:
        print("::error::trigpoint: no input files matched"); return 2

    worst_overall = 100
    failed = []
    for f in files:
        raw = open(f, "rb").read(8*1024*1024).decode("utf-8", "replace")
        score, n, counts, worst = score_text(raw)
        worst_overall = min(worst_overall, score)
        status = "PASS" if score >= a.min_score else "FAIL"
        line = f"{status}  {f}  score={score}/100  flags={n}"
        print(line)
        if score < a.min_score:
            failed.append(f)
            cats = ", ".join(f"{k}:{v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1]))
            wtxt = f' worst: "{worst[2]}"' if worst else ""
            print(f"::warning file={f}::integrity {score}/100 (min {a.min_score}); {cats}.{wtxt}")

    print(f"\ntrigpoint: {len(files)-len(failed)}/{len(files)} passed; worst score {worst_overall} (min {a.min_score})")
    if failed:
        print(f"::error::trigpoint: {len(failed)} file(s) below integrity threshold {a.min_score}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
