# Trigpoint — catch the tells that your AI agent is making things up

**No source docs. No judge model. No API key.** Point it at your agent's transcript and it grades the *shape of
fabrication* — the tells that show up when an agent invents a rule, claims "tests pass" without running them, cites a
source that isn't real, or states a confident absolute it can't back.

Most hallucination tools are *groundedness scorers*: they need the source document you're checking against, plus a
second LLM to judge. Useful — but they can't help when there's **nothing to compare against** (an agent asserting
"the refund window is 30 days" with no doc in sight). That gap is what Trigpoint checks.

> **Honest by design.** This is a fast **first-pass** — it catches the *tells*, not every lie. A confident,
> plausible falsehood with no stylistic tell will slip past it (we show one doing exactly that in a
> [sample audit](sample-audit.html)). A high score is **not** a certificate. We tell you what it catches and what it
> doesn't — because selling false confidence is the failure this exists to catch.

---

## The free tool (zero dependencies, MIT)

**One command, no clone, no install** (needs [uv](https://docs.astral.sh/uv/)):

```bash
uvx --from git+https://github.com/trigpoint-commits/trigpoint trigpoint your-agent-session.jsonl
```

Or grab the single file and run it — it has **zero dependencies**, so paste it anywhere:

```bash
git clone https://github.com/trigpoint-commits/trigpoint && cd trigpoint
python3 agent-integrity-quickcheck.py your-agent-session.jsonl
```

Point it at a `.jsonl` session log (it extracts the assistant turns) or any text, or pipe into it:

```bash
some_agent | python3 agent-integrity-quickcheck.py
python3 agent-integrity-quickcheck.py "definitely the fastest, 100% secure. Studies show 47.3% better. See arXiv:9999.1"
```

You get a graded **Integrity Report** — a 0–100 score plus the specific flagged snippets, categorised:
unbacked absolutes · fabricated-shaped citations · invented rules/limits · sourceless precise stats ·
success-claimed-without-evidence · self-contradiction.

## Fail the build when your agent starts lying — GitHub Action

Drop it into CI so a pull request that makes your agent's output *less* honest (invented rules, false "it works",
fabricated-shaped citations) fails the check — the same "reports work it didn't do" failure, caught before merge:

```yaml
# .github/workflows/integrity.yml
- uses: trigpoint-commits/trigpoint@main
  with:
    path: "agent-logs/*.jsonl"   # your captured agent transcripts
    min-score: "70"              # fail the build below this integrity score
```

Or run the same check locally / in any CI:

```bash
python3 ci_check.py --min-score 70 "agent-logs/*.jsonl"
```

It prints a per-file PASS/FAIL, GitHub `::warning::` annotations for the offending files, and exits non-zero if any
transcript is below the threshold. A regression tripwire, not a certificate — it catches the *tells*, not every lie.

## Check your agent *inline* — the MCP server

Wire it into any MCP client (Claude Desktop/Code, Cursor…) so an agent can check its **own** last message *before it
sends it* — catching the tell at the source, not in the wreckage:

One command (no clone):

```jsonc
// in your MCP client config (Claude Desktop / Cursor / …)
"trigpoint-agent-integrity": {
  "command": "uvx",
  "args": ["--from", "trigpoint-agent-integrity[mcp] @ git+https://github.com/trigpoint-commits/trigpoint", "trigpoint-mcp"]
}
```

Or from a clone: `pip install "mcp"` then point the config's `command` at `mcp-server/server.py`.

Tool: `check_agent_integrity(text)` → structured `{score, findings, worst_offender, disclaimer}`. Details in
[`mcp-server/README.md`](mcp-server/README.md).

## See what a full audit looks like

The free tool is the first pass. The **[Agent Integrity Audit](sample-audit.html)** is a person reading your actual
transcripts and handing back a scorecard: every fabricated claim quoted, severity-ranked, with a reproduction prompt
and a fix for each. Three real sample scorecards (coding agent, support bot, RAG app) show the format — and honestly
show the tool *missing* a failure that the human pass caught.

## Why trust this

Built and dogfooded by a real autonomous agent fleet that runs 24/7 — the tells it checks for are the exact ways our
*own* agents lied to us (a fabricated "15-minute rule," a "sent" message that reached no one, a verifier that passed
a dead script). We run these checks on ourselves. We report what we find and what we can't check.

---

MIT licensed. Free tool is free forever. Paid kits + the done-for-you audit: see the [site](index.html).
`integrity you can verify`
