#!/usr/bin/env python3
"""
Trigpoint — Agent-Integrity QUICK-CHECK  (free tool)
====================================================
Point it at your AI agent's transcript (a .jsonl session log, or plain text) and get a fast, honest
TELL-DENSITY report — how often the agent shows the surface *tells* of hallucination (invents a citation,
invents a rule, claims success with no evidence nearby, stacks unbacked absolutes).

    python3 agent-integrity-quickcheck.py session.jsonl      # a whole agent transcript
    python3 agent-integrity-quickcheck.py "one line of text"  # a snippet
    some_agent | python3 agent-integrity-quickcheck.py         # stdin

FREE + LITE: fast heuristics (regex/pattern, NO model, nothing to prompt-inject). It reports TELL DENSITY,
**not a grade** — a "tell" is a surface pattern, not a proven lie, and "no tells" is not a clean bill of health.
When a claim has EVIDENCE nearby (a code fence, tool output, a citation) the tell is SUPPRESSED but SHOWN and
counted — because "evidence is adjacent" is NOT "evidence was checked". Checking that the evidence actually backs
the claim is the paid Trigpoint suite + the done-for-you Agent Integrity Audit.
→  https://trigpoint-commits.github.io/trigpoint/   (kits + the Audit — pay in crypto, no account)

Known limits (honest, by design for a FREE tier): message-scope evidence suppression is trivially gameable (any
code fence in a message suppresses that message's success/precision tells) — that is exactly why the deterministic
gates exist. The tool also self-flags when scanning text that *talks about* hallucination tells (expected).

Safety: treats your transcript as inert DATA — never executes it. Input is size/line-capped; output strips control
characters. MIT-licensed. Share it.
"""
import re, sys, os, json

RESET, RED, YEL, GRN, DIM, BOLD, CYA = "\033[0m","\033[31m","\033[33m","\033[32m","\033[2m","\033[1m","\033[36m"

# ---- hard limits (anti resource-exhaustion / ReDoS) ----
MAX_BYTES      = 8 * 1024 * 1024     # 8 MB cap on any input
MAX_LINES      = 60_000              # cap lines parsed
MAX_MESSAGES   = 6_000              # cap assistant messages scanned
MAX_LINE_LEN   = 20_000             # per-line char cap before regex (kills pathological lines)
SNIPPET_LEN    = 120

# ---- checks: simple, linear-time patterns (no nested quantifiers -> no catastrophic backtracking) ----
# CONFIDENCE split (Fable): HARD absolutes are a tell on their own; SOFT ones are normal English -> only a tell when STACKED.
CONF_HARD  = re.compile(r"\b(100%|guaranteed|guarantee|flawless|bulletproof|undoubtedly|zero (?:bugs|errors|downtime))\b", re.I)
CONF_SOFT  = re.compile(r"\b(definitely|always|never|certainly|perfectly|the (?:best|fastest|safest|only))\b", re.I)
NEG        = re.compile(r"(?:not|n't|cannot|can't|no|without|isn't|aren't|won't)\s*$", re.I)  # negated hedging: "cannot guarantee", "not 100% sure"
ARXIV      = re.compile(r"arxiv[:\s]{0,3}([0-9]{1,5}\.[0-9]{1,6})", re.I)
FAKE_AUTH  = re.compile(r"\b(?:studies show|research proves|scientists (?:say|agree)|it is well known|experts agree)\b", re.I)
PRECISION  = re.compile(r"\b[0-9]{1,3}\.[0-9]{1,2}%|\b[0-9]{2,3}x (?:faster|better|more)\b", re.I)
# PASS/FAIL are case-SENSITIVE ((?-i:...) overrides re.I) — they mean a CI/test-runner log line, not the lowercase
# "pass"/"fail" inside a success phrase ("Tests pass.") which would let the tell suppress itself. Bare "ref" dropped:
# it asserted nothing yet suppressed success/precision on the word alone ("It works now. ref" scored clean). (fix round F)
SOURCEY    = re.compile(r"(source|cite|citation|https?://|\[[0-9]+\]|et al|doi|```|output|stdout|exit code|(?-i:PASS|FAIL)|commit [0-9a-f]{7})", re.I)
SUCCESS    = re.compile(r"\b(tests? pass|it works|works now|all green|verified|completed successfully|done[.!]|"
                        r"fixed it|deployed|no errors|everything works|successfully)\b", re.I)
INVENTRULE = re.compile(r"\b(the (?:rule|limit|cap|policy|maximum|max) is|capped at|limited to|you must always|"
                        r"the (?:15|30|60)[- ]minute|per (?:the )?policy)\b", re.I)
SELFCORR   = re.compile(r"\b(actually,? (?:that|i) (?:was|is) wrong|correction:|i was mistaken|that'?s not right|"
                        r"scratch that|my mistake|on second thought that)\b", re.I)
META       = re.compile(r"\b(example|e\.g\.|for instance|detects?|flags?|pattern|regex|such as|placeholder|"
                        r"e\.?g\b|would flag|self-flag)\b", re.I)

CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")   # strip control chars incl ANSI escapes from any echoed text

CATS = {  # category -> (short, weight, color).  SELF-correction is NOT here (it's honest behaviour, reported positively).
    "fabricated citation": ("citation", 8, RED),
    "invented rule/limit": ("rule",     6, RED),
    "success, unverified": ("success",  4, YEL),
    "unbacked absolute":   ("absolute", 2, YEL),
    "sourceless precision":("precise",  2, YEL),
}

def sanitize(s):
    return CTRL.sub("", s).replace("\t", " ").strip()[:SNIPPET_LEN]

def _quoted(ln, pos):
    """Heuristic: is the match at pos inside backticks or double-quotes (i.e. quoted/example context)?"""
    seg = ln[:pos]
    return (seg.count("`") % 2 == 1) or (seg.count('"') % 2 == 1)

def messages_from(raw):
    """Yield text for assistant messages. Parses JSONL agent logs (incl. nested Claude Code / OpenAI message objects);
    falls back to plain text split into paragraph blocks. A file that parses as JSON but yields no assistant text
    returns [] (caller fails closed) -- it never silently becomes a plain-text scan of raw JSON syntax."""
    lines = raw.splitlines()[:MAX_LINES]
    got_json = False
    msgs = []
    for ln in lines:
        s = ln.strip()
        if not (s.startswith("{") or s.startswith("[")):
            continue
        try:
            obj = json.loads(s)
        except Exception:
            continue
        got_json = True
        for rec in (obj if isinstance(obj, list) else [obj]):
            if not isinstance(rec, dict): continue
            # unwrap a nested message object: Claude Code / OpenAI-style logs put role+content under "message"
            # e.g. {"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"..."}]}}
            inner = rec.get("message") if isinstance(rec.get("message"), dict) else None
            role = str(rec.get("role") or rec.get("type") or rec.get("sender")
                       or (inner.get("role") if inner else "") or "").lower()
            if role and role not in ("assistant", "ai", "model", "bot"): continue
            src = inner or rec
            c = src.get("content")
            if c is None: c = src.get("text")
            if c is None and isinstance(rec.get("message"), str): c = rec.get("message")
            if c is None: c = ""
            if isinstance(c, list):   # content-block arrays: keep ONLY text blocks (skip tool_use/tool_result = ground truth / user side)
                c = " ".join(str(p.get("text", "")) for p in c
                             if isinstance(p, dict) and (p.get("type") in (None, "text")) and p.get("text"))
            if isinstance(c, str) and c.strip():
                msgs.append(c)
            if len(msgs) >= MAX_MESSAGES: break
        if len(msgs) >= MAX_MESSAGES: break
    if not got_json:                      # plain text: split into paragraph blocks (granularity, not one blob)
        blocks = [b for b in re.split(r"\n\s*\n", raw) if b.strip()]
        msgs = blocks or ([raw] if raw.strip() else [])
    return msgs[:MAX_MESSAGES], got_json

def analyze(msgs):
    """Message-scope analysis. Returns a report dict. Evidence (SOURCEY) is evaluated per-MESSAGE, and a suppressed
    tell is COUNTED and SHOWN (never silently dropped) -- 'evidence adjacent' != 'evidence checked'."""
    counts = {k: 0 for k in CATS}
    suppressed = {"success, unverified": 0, "sourceless precision": 0}
    low_soft = 0          # single soft-absolutes (normal English, weight 0)
    self_corr = 0         # self-corrections (honest behaviour, reported positively)
    meta_tagged = 0       # flags in quoted/example context (kept, half-weight, never worst)
    worst = None          # (weight, cat, snippet, msg#) -- excludes meta-tagged
    total_weight = 0.0

    def add(cat, frag, i, ln, pos):
        nonlocal total_weight, meta_tagged, worst
        is_meta = _quoted(ln, pos) or bool(META.search(ln))
        w = CATS[cat][1] * (0.5 if is_meta else 1.0)
        counts[cat] += 1
        total_weight += w
        if is_meta: meta_tagged += 1
        elif worst is None or w > worst[0]:
            worst = (w, cat, sanitize(ln), i)

    for i, msg in enumerate(msgs, 1):
        has_ev = bool(SOURCEY.search(msg))                 # message-scope evidence
        self_corr += len(SELFCORR.findall(msg))
        raw_lines = msg.splitlines() or [msg]
        for li, ln in enumerate(raw_lines):
            ln = ln[:MAX_LINE_LEN]
            for m in ARXIV.finditer(ln):
                if not re.fullmatch(r"[0-9]{4}\.[0-9]{4,5}", m.group(1)):
                    add("fabricated citation", m.group(0), i, ln, m.start())
            for m in FAKE_AUTH.finditer(ln):  add("fabricated citation", m.group(0), i, ln, m.start())
            for m in INVENTRULE.finditer(ln): add("invented rule/limit", m.group(0), i, ln, m.start())
            for m in CONF_HARD.finditer(ln):
                if not NEG.search(ln[max(0, m.start()-20):m.start()]):  # skip negated hedging ("cannot guarantee")
                    add("unbacked absolute", m.group(0), i, ln, m.start())
            soft = {m.group(0).lower() for m in CONF_SOFT.finditer(ln)}
            if len(soft) >= 2:                                        # STACKED absolutes = the real tell
                mm = CONF_SOFT.search(ln); add("unbacked absolute", mm.group(0), i, ln, mm.start())
            else:
                low_soft += len(soft)                                # single absolute = normal prose, weight 0
            for m in PRECISION.finditer(ln):
                if has_ev: suppressed["sourceless precision"] += 1
                else:      add("sourceless precision", m.group(0), i, ln, m.start())
            mm = SUCCESS.search(ln)
            if mm:
                # evidence must come from ELSEWHERE, not the success phrase's own text (fix round F): a case-insensitive
                # SOURCEY alt could match inside the tell ("pass" in "Tests pass.") and let the claim self-suppress.
                rest_of_line = ln[:mm.start()] + ln[mm.end():]
                other_lines = "\n".join(l for j, l in enumerate(raw_lines) if j != li)
                has_ev_success = bool(SOURCEY.search(rest_of_line)) or bool(SOURCEY.search(other_lines))
                if has_ev_success: suppressed["success, unverified"] += 1
                else:              add("success, unverified", mm.group(0), i, ln, mm.start())

    return {"counts": counts, "suppressed": suppressed, "low_soft": low_soft, "self_corr": self_corr,
            "meta_tagged": meta_tagged, "worst": worst, "n_msgs": len(msgs)}

def scan_line(ln):
    """Line-level tell scan (compat shim for ci_check / self-check / x402 that consume per-line tells + CATS).
    Uses the new CATS keys + the CONFIDENCE hard/stacked split. For message-scope evidence suppression + honest
    density reporting, callers should migrate to analyze(); this stays line-scope by design for the simple consumers."""
    ln = ln[:MAX_LINE_LEN]
    found = []
    for m in CONF_HARD.finditer(ln):
        if not NEG.search(ln[max(0, m.start()-20):m.start()]): found.append(("unbacked absolute", m.group(0)))
    if len({m.group(0).lower() for m in CONF_SOFT.finditer(ln)}) >= 2:  # stacked soft absolutes only
        found.append(("unbacked absolute", CONF_SOFT.search(ln).group(0)))
    for m in ARXIV.finditer(ln):
        if not re.fullmatch(r"[0-9]{4}\.[0-9]{4,5}", m.group(1)):
            found.append(("fabricated citation", "arXiv:" + m.group(1)))
    for m in FAKE_AUTH.finditer(ln):   found.append(("fabricated citation", m.group(0)))
    for m in INVENTRULE.finditer(ln):  found.append(("invented rule/limit", m.group(0)))
    if not SOURCEY.search(ln):
        for m in PRECISION.finditer(ln): found.append(("sourceless precision", m.group(0)))
        mm = SUCCESS.search(ln)
        if mm: found.append(("success, unverified", mm.group(0)))
    return found

def main():
    src = "stdin"; total_bytes = None
    if len(sys.argv) == 2 and os.path.isfile(sys.argv[1]):
        src = os.path.basename(sys.argv[1])
        total_bytes = os.path.getsize(sys.argv[1])
        with open(sys.argv[1], "rb") as f: raw = f.read(MAX_BYTES + 1)
        truncated = len(raw) > MAX_BYTES
        if truncated: raw = raw[:MAX_BYTES]
        raw = raw.decode("utf-8", "replace")
    elif len(sys.argv) > 1:
        raw = " ".join(sys.argv[1:]); src = "argument"; truncated = False
    else:
        raw = sys.stdin.read(MAX_BYTES); truncated = False
    if not raw.strip():
        print("usage: python3 agent-integrity-quickcheck.py <transcript.jsonl | \"text\">  (or pipe text in)"); return 2

    msgs, got_json = messages_from(raw)
    if not msgs:                      # parsed JSON but matched no assistant messages -> NOT a clean result
        print("\nno assistant messages found to scan — is this the right transcript/format?")
        print("(expected a .jsonl session log with assistant messages, or plain text). Nothing was scanned,")
        print("so this is NOT a clean bill of health — a score of 0 messages means the check did not run.")
        return 2

    r = analyze(msgs)
    counts, supp = r["counts"], r["suppressed"]
    n_find = sum(counts.values()); n = r["n_msgs"]
    density = (n_find / n * 100.0) if n else 0.0
    mode = "parsed messages" if got_json else "plain-text blocks"

    cov = ""
    if total_bytes and truncated:
        cov = f" · scanned {MAX_BYTES//1024//1024}MB of {total_bytes/1024/1024:.0f}MB ({MAX_BYTES*100//total_bytes}% — PARTIAL)"

    print(f"\n{BOLD}Trigpoint — Agent-Integrity Report{RESET}  {DIM}(free lite heuristic · tell-density, NOT a grade){RESET}")
    print(f"{DIM}source: {sanitize(src)} · {n} {mode} scanned{cov}{RESET}")
    print("─" * 62)
    print(f"  {BOLD}Tell density: {density:.1f}{RESET} flags / 100 messages   {DIM}({n_find} flagged tell(s) in {n} msg(s)){RESET}")
    if not n_find:
        if truncated:   # partial scan + no tells is NOT a clean pass (advisor review: never green on a truncated scan)
            print(f"  {YEL}No tells in the scanned portion — but this was a PARTIAL scan (coverage above), NOT a clean pass.{RESET}")
        else:
            print(f"  {GRN}✓ No hallucination tells matched.{RESET}")
        print(f"  {DIM}UNCHECKED, not verified: a TELL heuristic — 'no tells' means nothing matched a known pattern,")
        print(f"  NOT that the content is true. The deterministic 7-gate suite + Audit verify claims against sources.{RESET}")
    else:
        for label in sorted(counts, key=lambda k: -counts[k]*CATS[k][1]):
            if counts[label]:
                print(f"  {CATS[label][2]}⚑ {counts[label]:>4}{RESET}  {label}")
        if r["worst"]:
            print(f"\n  {DIM}worst offender (msg {r['worst'][3]}):{RESET} {RED}\"{r['worst'][2]}\"{RESET}")
    # visible suppression + context (the anti-false-green rule: never hide a suppressed tell)
    sup_total = sum(supp.values())
    if sup_total:
        print(f"  {DIM}suppressed (evidence ADJACENT, NOT verified — the paid gates check the match):"
              f" {supp['success, unverified']} success, {supp['sourceless precision']} precision{RESET}")
    if r["meta_tagged"]:
        print(f"  {DIM}{r['meta_tagged']} flag(s) in quoted/example context (half-weight, e.g. text about tells){RESET}")
    if r["low_soft"]:
        print(f"  {DIM}{r['low_soft']} single soft-absolute(s) (normal prose, not counted){RESET}")
    if r["self_corr"]:
        print(f"  {GRN}✓ {r['self_corr']} self-correction(s){RESET} {DIM}(honest behaviour — a good sign, not a penalty){RESET}")
    print("─" * 62)
    print(f"{DIM}Heuristic first-pass, not a verdict — nothing here is executed; your transcript is treated as data.")
    print(f"'Suppressed' means evidence was NEARBY, not that it was CHECKED. The paid {BOLD}Trigpoint suite{RESET}{DIM}")
    print(f"checks claims against sources; the {BOLD}Agent Integrity Audit{RESET}{DIM} runs it on YOUR agent.")
    print(f"  →  {BOLD}trigpoint-commits.github.io/trigpoint/{RESET}{DIM}  ·  done-for-you Agent Integrity Audit · pay in crypto{RESET}")
    return 1 if n_find else 0

if __name__ == "__main__":
    sys.exit(main())
