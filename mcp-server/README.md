# Trigpoint Agent-Integrity — MCP server

An [MCP](https://modelcontextprotocol.io) server that lets any MCP-capable agent or IDE (Claude Desktop/Code,
Cursor, …) check an AI agent's output for hallucination tells **inline** — including an agent checking its **own**
last message before it ships it.

One tool: **`check_agent_integrity(text)`** → a graded report:

```json
{
  "score": 88, "band": "clean", "messages_scanned": 6, "n_findings": 6,
  "counts": {"unbacked absolute": 6},
  "worst_offender": {"category": "unbacked absolute", "message_index": 1, "snippet": "…"},
  "findings": [ … ],
  "disclaimer": "Heuristic first-pass … a high score is NOT a certificate."
}
```

`text` can be a single message/snippet, or a whole transcript (a `.jsonl` session log — assistant messages are
extracted — or raw text).

## Honest scope (this is the point of the product, so we say it up front)
Regex/heuristic only. **No model, nothing executed, input treated as inert data.** It flags surface tells
(unbacked absolutes, fabricated-shaped citations, invented rules, sourceless precise stats, self-contradiction).
It **cannot** verify a quote against a source, catch a fabricated *action* ("I issued the refund"), or confirm a
success claim — so **a high score does NOT mean the output is safe.** It's a fast first-pass indicator. The
done-for-you [Agent Integrity Audit](https://trigpoint-commits.github.io/trigpoint/) adds the human/panel pass that
catches what a scanner can't.

## Install
```bash
pip install mcp          # the MCP Python SDK (built/tested against mcp 2.2.0)
```
The scan logic is pure-stdlib and imported from the free CLI tool next door
(`../free-quickcheck/agent-integrity-quickcheck.py`) via `integrity_core.py` — no logic is duplicated.

## Add it to an MCP client (stdio)
Point your client's MCP config at `server.py`. Example (Claude Desktop / Cursor `mcp.json` shape):
```json
{
  "mcpServers": {
    "trigpoint-agent-integrity": {
      "command": "python",
      "args": ["/absolute/path/to/MMF/products/mcp-server/server.py"]
    }
  }
}
```
Use the interpreter that has `mcp` installed (e.g. a venv's `python`). Then the tool `check_agent_integrity`
appears in your agent.

## Run / test standalone
```bash
python server.py                       # stdio server (what a client launches)
python integrity_core.py <file|text>   # get the raw JSON report without MCP, for scripting/CI
```

## Files
- `server.py` — the MCP server (mcp 2.x `MCPServer` API).
- `integrity_core.py` — pure `analyze(text) -> dict`; single-sources the scan from the free CLI tool.
- `requirements.txt` — `mcp>=2.2.0`.

MIT. Part of the Trigpoint suite. Status: built + verified (end-to-end MCP client/server test passes). Publishing to
the public repo + MCP-directory submission is gated on the launch (Pages live + Media red-team pass).
