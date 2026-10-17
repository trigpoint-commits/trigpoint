#!/usr/bin/env python3
"""
cc_adapter.py — normalize a Claude Code (or Claude-Code-style) session transcript .jsonl into the
{role, content, tool_calls} turn format that falsegreen reads.

Claude Code writes one JSON object per line; the shapes we handle (tolerantly):
  {"type":"user","message":{"role":"user","content":"..."}}
  {"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"..."},{"type":"tool_use",...}]}}
  {"type":"user","message":{"role":"user","content":[{"type":"tool_result","content":"..."}]}}   # tool output
Anything unrecognized is skipped. Honest note: Claude Code's transcript schema can change between versions —
this adapter is tolerant but verify on your version (run it on a real session file and eyeball the turns).
"""
import json, sys


def _text_of(content):
    """content may be a str or a list of blocks; return (text, had_tool_use, is_tool_result)."""
    if isinstance(content, str):
        return content, False, False
    if not isinstance(content, list):
        return json.dumps(content, ensure_ascii=False), False, False
    parts, had_tool_use, is_tool_result = [], False, False
    for b in content:
        if not isinstance(b, dict):
            parts.append(str(b)); continue
        t = b.get("type")
        if t == "text":
            parts.append(b.get("text", ""))
        elif t == "tool_use":
            had_tool_use = True
            parts.append("[tool_use %s %s]" % (b.get("name", ""), json.dumps(b.get("input", ""))[:200]))
        elif t == "tool_result":
            is_tool_result = True
            c = b.get("content")
            parts.append(c if isinstance(c, str) else json.dumps(c, ensure_ascii=False))
        else:
            parts.append(json.dumps(b, ensure_ascii=False)[:200])
    return "\n".join(p for p in parts if p), had_tool_use, is_tool_result


def cc_to_turns(path):
    turns = []
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        msg = o.get("message") or {}
        role = msg.get("role") or o.get("role") or o.get("type")
        if role not in ("user", "assistant", "system", "tool"):
            continue
        content = msg.get("content", o.get("content", ""))
        text, had_tool_use, is_tool_result = _text_of(content)
        if is_tool_result:
            turns.append({"role": "tool", "content": text})          # tool output = execution evidence turn
        else:
            t = {"role": role, "content": text}
            if had_tool_use:
                t["tool_calls"] = True
            turns.append(t)
    return turns


def cc_blob_from_transcript(path):
    return "\n".join(json.dumps(t) for t in cc_to_turns(path))


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else None
    if not p:
        print("usage: cc_adapter.py <transcript.jsonl>"); sys.exit(1)
    ts = cc_to_turns(p)
    print("turns:", len(ts), "| exec/tool turns:", sum(1 for t in ts if t["role"] == "tool" or t.get("tool_calls")))
    print(cc_blob_from_transcript(p)[:500])
