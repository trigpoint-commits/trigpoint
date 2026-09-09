"""
integrity_core — pure, importable wrapper around the Trigpoint Agent-Integrity Quick-Check.

Loads the existing free tool (agent-integrity-quickcheck.py) via importlib and exposes ONE pure function,
`analyze(text) -> dict`, that returns structured findings instead of printing. This keeps the scan logic
single-sourced (no duplication, no edits to the reviewed CLI file) and gives the MCP server / any programmatic
caller machine-readable output.

The scoring formula here MUST match the CLI's main(): score = max(3, 100 - min(97, total_weight)),
total_weight = sum of CATS[cat][weight] over every hit. If the CLI changes its formula, update this in lockstep.
"""
import importlib.util, os

_HERE = os.path.dirname(os.path.abspath(__file__))
# Resolve the single-file checker across layouts: dev tree (../free-quickcheck/), published repo (repo root = ../),
# or co-located (same dir). First existing wins so the MCP server works whether cloned from the repo or run in-tree.
_CANDIDATES = [
    os.path.join(_HERE, "..", "free-quickcheck", "agent-integrity-quickcheck.py"),  # dev tree
    os.path.join(_HERE, "..", "agent-integrity-quickcheck.py"),                     # published repo root
    os.path.join(_HERE, "agent-integrity-quickcheck.py"),                           # co-located
]

def _resolve_checker():
    for p in _CANDIDATES:
        p = os.path.normpath(p)
        if os.path.isfile(p):
            return p
    raise FileNotFoundError(
        "agent-integrity-quickcheck.py not found next to the MCP server. Looked in: "
        + ", ".join(os.path.normpath(p) for p in _CANDIDATES))

_CHECKER_PATH = _resolve_checker()

def _load_checker():
    spec = importlib.util.spec_from_file_location("aiqc", _CHECKER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)          # safe: the file is guarded by if __name__ == "__main__"
    return mod

_QC = _load_checker()

def analyze(text):
    """Scan a transcript / snippet. Returns a dict: score, n_findings, counts{cat:n}, worst{...}, findings[...]."""
    if not isinstance(text, str):
        text = str(text or "")
    msgs = _QC.messages_from(text)
    counts, findings, worst = {}, [], None
    total_weight = 0
    for i, msg in enumerate(msgs, 1):
        for ln in (msg.splitlines() or [msg]):
            for cat, frag in _QC.scan_line(ln):
                counts[cat] = counts.get(cat, 0) + 1
                w = _QC.CATS[cat][1]
                total_weight += w
                snippet = _QC.sanitize(ln)
                findings.append({"category": cat, "weight": w, "message_index": i, "snippet": snippet})
                if worst is None or w > worst["weight"]:
                    worst = {"category": cat, "weight": w, "message_index": i, "snippet": snippet}
    n_findings = sum(counts.values())
    score = max(3, 100 - min(97, total_weight))
    band = "clean" if score >= 85 else ("watch" if score >= 55 else "poor")
    return {
        "score": score,
        "band": band,
        "messages_scanned": len(msgs),
        "n_findings": n_findings,
        "counts": counts,
        "worst_offender": worst,
        "findings": findings,
        "disclaimer": ("Heuristic first-pass, not a verdict. Regex-only, no model — it cannot verify quotes against a "
                       "source, catch fabricated actions, or confirm success claims. A high score is NOT a "
                       "certificate. The done-for-you Agent Integrity Audit adds a human/panel pass."),
    }

if __name__ == "__main__":
    import json, sys
    raw = sys.stdin.read() if len(sys.argv) < 2 else (
        open(sys.argv[1], encoding="utf-8", errors="replace").read() if os.path.isfile(sys.argv[1])
        else " ".join(sys.argv[1:]))
    print(json.dumps(analyze(raw), indent=2))
