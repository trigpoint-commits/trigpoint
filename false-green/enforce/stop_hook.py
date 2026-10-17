#!/usr/bin/env python3
"""
stop_hook.py — Claude Code Stop hook: "no done without proof."

When the agent tries to end its turn, this checks the session transcript for a FALSE GREEN near the end —
a completion claim ("tests pass / deployed / fixed / verified") with no execution evidence within ~2 turns —
and BLOCKS the stop, feeding the reason back so the agent must run the command and cite its output (or correct
the claim). It fires only when the claim is genuinely unbacked, so on a normal session where the agent actually
ran its tools it stays silent (see the field study: 0 false positives across 500 real tool-grounded transcripts).

Install (in .claude/settings.json):
  { "hooks": { "Stop": [ { "hooks": [ {
      "type": "command",
      "command": "python3 /ABS/PATH/PRODUCT/false-green/enforce/stop_hook.py"
  } ] } ] } }

Hook I/O (verify against your Claude Code version): receives a JSON object on stdin that includes
`transcript_path`; to block the stop, prints {"decision":"block","reason":"..."} and exits 0. On any error it
exits 0 and allows the stop (fail-open — an integrity gate must never wedge your session).
"""
import sys, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))   # falsegreen.py
sys.path.insert(0, HERE)                        # cc_adapter.py

def allow():
    sys.exit(0)   # no output → stop proceeds

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        allow()
    # avoid infinite loops: if we already blocked once this stop, let it through
    if data.get("stop_hook_active"):
        allow()
    tp = data.get("transcript_path")
    if not tp or not os.path.isfile(tp):
        allow()
    try:
        import falsegreen as FG
        from cc_adapter import cc_blob_from_transcript
        blob = cc_blob_from_transcript(tp)
        if not blob.strip():
            allow()
        turns = blob.count("\n") + 1
        r = FG.analyze(blob)
        # only act on claims near the END of the session (the completion message), not stale mid-session ones
        near_end = [f for f in r.get("findings", []) if f.get("turn", 0) >= turns - 3]
        if r.get("false_green") and near_end:
            f = near_end[0]
            reason = ("Trigpoint false-green: you ended with a success claim (\"%s\") but the transcript shows no "
                      "execution evidence within ~2 turns of it. Before finishing, actually run it and cite the "
                      "command + its output (e.g. 'pytest -> 12 passed, exit 0'), or correct the claim. "
                      "Flagged: \"%s\"" % (f.get("claim", ""), (f.get("snippet", "") or "")[:200]))
            print(json.dumps({"decision": "block", "reason": reason}))
            sys.exit(0)
    except Exception:
        allow()
    allow()

if __name__ == "__main__":
    main()
