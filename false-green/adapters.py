#!/usr/bin/env python3
"""
adapters.py — normalize real agent logs into the {role, content[, tool_calls]} JSONL that falsegreen reads.

Sniffs the format and emits one JSON turn per line on stdout, so you can pipe ANY supported log into the checker:

    python3 adapters.py session.jsonl | python3 falsegreen.py
    python3 adapters.py .aider.chat.history.md | python3 falsegreen.py

Supported now (honest list):
  - Claude Code transcript .jsonl         ({"type":...,"message":{"role","content":[blocks]}})
  - Plain {role,content[,tool_calls]} .jsonl (OpenHands-style, our own format)
  - OpenAI / ChatML  {"messages":[{role,content}, ...]}  .json
  - aider  .aider.chat.history.md         (best-effort: '#### ' = user, prose = assistant, fenced output = evidence)
NOT yet supported (don't pretend): Cursor (opaque workspace sqlite), raw GitHub Actions text logs. TODO.

Windows-safe: text read with universal newlines; no POSIX-only path assumptions.
"""
import json, os, sys, re

def _blocks_text(content):
    """Claude/Anthropic content: str or list of blocks -> (text, had_tool_use, is_tool_result)."""
    if isinstance(content, str):
        return content, False, False
    if not isinstance(content, list):
        return json.dumps(content, ensure_ascii=False), False, False
    parts, tu, tr = [], False, False
    for b in content:
        if not isinstance(b, dict):
            parts.append(str(b)); continue
        t = b.get("type")
        if t == "text": parts.append(b.get("text", ""))
        elif t == "tool_use": tu = True; parts.append("[tool_use %s %s]" % (b.get("name",""), json.dumps(b.get("input",""))[:200]))
        elif t == "tool_result": tr = True; c = b.get("content"); parts.append(c if isinstance(c,str) else json.dumps(c,ensure_ascii=False))
        else: parts.append(json.dumps(b, ensure_ascii=False)[:200])
    return "\n".join(p for p in parts if p), tu, tr

def _claude_code(lines):
    turns = []
    for ln in lines:
        ln = ln.strip()
        if not ln: continue
        try: o = json.loads(ln)
        except Exception: continue
        msg = o.get("message") or {}
        role = msg.get("role") or o.get("role") or o.get("type")
        if role not in ("user","assistant","system","tool"): continue
        text, tu, tr = _blocks_text(msg.get("content", o.get("content","")))
        if tr: turns.append({"role":"tool","content":text})
        else:
            t = {"role":role,"content":text}
            if tu: t["tool_calls"] = True
            turns.append(t)
    return turns

def _plain_jsonl(lines):
    turns = []
    for ln in lines:
        ln = ln.strip()
        if not ln: continue
        try: o = json.loads(ln)
        except Exception: continue
        if not isinstance(o, dict) or "role" not in o: continue
        c = o.get("content"); text = c if isinstance(c,str) else json.dumps(c,ensure_ascii=False)
        t = {"role":o.get("role",""),"content":text}
        if o.get("tool_calls") or o.get("tool_use"): t["tool_calls"] = True
        turns.append(t)
    return turns

def _openai_messages(obj):
    msgs = obj.get("messages") if isinstance(obj, dict) else (obj if isinstance(obj, list) else [])
    turns = []
    for m in msgs or []:
        if not isinstance(m, dict): continue
        c = m.get("content"); text = c if isinstance(c,str) else json.dumps(c,ensure_ascii=False)
        t = {"role":m.get("role",""),"content":text}
        if m.get("tool_calls"): t["tool_calls"] = True
        if m.get("role") == "tool": t["role"] = "tool"
        turns.append(t)
    return turns

def _aider_md(text):
    """aider .aider.chat.history.md: '#### ' prefixes a user line; other prose = assistant; fenced blocks = evidence."""
    turns, cur_role, buf = [], None, []
    def flush():
        if cur_role and buf:
            body = "\n".join(buf).strip()
            if body:
                exec_like = bool(re.search(r"```|^\$ |\bpassed\b|\bexit code\b|Traceback", body, re.M))
                t = {"role":cur_role,"content":body}
                if cur_role == "assistant" and exec_like: t["tool_calls"] = True
                turns.append(t)
    for line in text.splitlines():
        if line.startswith("#### "):
            flush(); turns_role = "user"; cur_role = "user"; buf = [line[5:]]
        elif line.startswith("# ") or line.startswith("> "):
            continue
        else:
            if cur_role is None: cur_role = "assistant"
            buf.append(line)
            # a user '#### ' block is a single line; switch back to assistant after it
            if cur_role == "user" and len(buf) >= 1 and not line.startswith("#### "):
                flush(); cur_role = "assistant"; buf = [line] if line else []
    flush()
    return [t for t in turns if t.get("content")]

def sniff_and_load(path):
    data = open(path, encoding="utf-8", errors="replace").read()
    name = os.path.basename(path).lower()
    if name.endswith(".md") or "aider" in name:
        return "aider-md", _aider_md(data)
    lines = data.splitlines()
    first = next((l for l in lines if l.strip()), "")
    if name.endswith(".json") and not name.endswith(".jsonl"):
        try:
            obj = json.loads(data)
            if (isinstance(obj, dict) and "messages" in obj) or isinstance(obj, list):
                return "openai-messages", _openai_messages(obj)
        except Exception:
            pass
    # jsonl family: decide claude-code vs plain by the first object's shape
    try:
        o0 = json.loads(first)
        if isinstance(o0, dict) and ("message" in o0 or o0.get("type") in ("user","assistant","system")):
            return "claude-code", _claude_code(lines)
        if isinstance(o0, dict) and "role" in o0:
            return "plain-jsonl", _plain_jsonl(lines)
    except Exception:
        pass
    # last resort: treat as plain text single assistant turn
    return "raw-text", [{"role":"assistant","content":data}]

def to_blob(turns):
    return "\n".join(json.dumps(t) for t in turns)

def main(argv):
    show_fmt = False
    if argv and argv[0] == "--format":
        show_fmt = True; argv = argv[1:]
    if not argv:
        print("usage: adapters.py [--format] <log file>  (emits normalized JSONL on stdout)", file=sys.stderr); return 1
    fmt, turns = sniff_and_load(argv[0])
    if show_fmt:
        ex = sum(1 for t in turns if t["role"] == "tool" or t.get("tool_calls"))
        print("format=%s turns=%d exec/tool=%d" % (fmt, len(turns), ex), file=sys.stderr)
    sys.stdout.write(to_blob(turns) + ("\n" if turns else ""))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
