#!/usr/bin/env python3
"""
scan_openhands.py — run false-green against REAL, public agent trajectories and report the numbers.

Reproducible real-world check (no API key, public data via the HuggingFace datasets-server):
dataset = nvidia/SWE-Hero-openhands-trajectories (licensed, public) — real OpenHands SWE-agent runs whose
trajectory items are {role, content, tool_calls}, mapping directly onto what falsegreen reads.

    python3 scan_openhands.py [N]      # N trajectories (default 20)

What it measures: the FALSE-POSITIVE behavior on real agent output. These are SWE-bench *solved* runs — the agent
really did run tests (many tool turns) — so a correct detector should stay QUIET. Any flag here is a candidate
false positive to inspect. (A real *catch* needs failure-weighted traces, where agents claim unbacked success; a
success set has none by construction.) We report exactly what we find.
"""
import json, urllib.request, urllib.parse, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import falsegreen as FG

DS = "nvidia/SWE-Hero-openhands-trajectories"

def get(url, timeout=60, tries=4):
    import time
    req = urllib.request.Request(url, headers={"User-Agent": "trigpoint-falsegreen/1.0"})
    last = None
    for a in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            last = e; time.sleep(2 * (a + 1))   # datasets-server rate-limits / warms up; back off and retry
    raise last

def to_blob(traj):
    out = []
    for it in traj:
        c = it.get("content"); text = c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
        o = {"role": it.get("role", ""), "content": text}
        if it.get("tool_calls"): o["tool_calls"] = True
        out.append(json.dumps(o))
    return "\n".join(out)

def main(argv):
    total = int(argv[0]) if argv else 20
    scanned = asst = flags = 0; flagged = []
    off = 0; per = 10
    while scanned < total:
        rr = get("https://datasets-server.huggingface.co/rows?dataset=%s&config=default&split=train&offset=%d&length=%d"
                 % (urllib.parse.quote(DS), off, min(per, total - scanned)))
        batch = rr.get("rows", [])
        if not batch: break
        for rw in batch:
            traj = rw["row"]["trajectory"]
            r = FG.analyze(to_blob(traj))
            scanned += 1
            asst += sum(1 for it in traj if it.get("role") in ("assistant", "ai", "model"))
            if r["findings"]:
                flags += len(r["findings"]); flagged.append((rw["row"].get("instance_id", "?"), r["findings"][0]))
        off += len(batch)
    print("dataset: %s" % DS)
    print("trajectories scanned: %d" % scanned)
    print("assistant turns scanned: %d" % asst)
    print("false-green flags: %d  (trajectories flagged: %d)" % (flags, len(flagged)))
    print("false-positive rate on this real success set: %.4f per assistant turn" % ((flags / asst) if asst else 0))
    for iid, f in flagged[:10]:
        print("  FLAG %s turn %d [%s] %s" % (iid, f["turn"], f["claim"], f["snippet"][:110]))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
