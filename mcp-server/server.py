#!/usr/bin/env python3
"""
Trigpoint Agent-Integrity MCP server
====================================
Exposes the free Trigpoint Agent-Integrity Quick-Check as an MCP tool, so any MCP-capable agent or IDE
(Claude Desktop/Code, Cursor, etc.) can check an agent's output for hallucination tells *inline* — including
the agent checking its OWN last output before it ships it.

Tool: `check_agent_integrity(text)` -> structured report {score, band, counts, worst_offender, findings, disclaimer}.

Heuristic + regex only. No model, nothing executed, input treated as inert data. A high score is NOT a
certificate — the tool cannot verify quotes against a source, catch fabricated actions, or confirm success
claims. That's what the done-for-you Agent Integrity Audit adds (https://trigpoint-commits.github.io/trigpoint/).

Run:  python server.py         (stdio transport; how MCP clients launch it)
Requires: pip install mcp      (built/tested against mcp 2.2.0; uses the 2.x MCPServer API)
"""
from typing import Any
from mcp.server import MCPServer   # canonical import path (docs); mcp 2.x — was FastMCP in v1
from integrity_core import analyze

mcp = MCPServer(
    name="trigpoint-agent-integrity",
    title="Trigpoint Agent-Integrity Quick-Check",
    instructions=(
        "Use check_agent_integrity to scan an AI agent's output or transcript for common hallucination tells "
        "(unbacked absolutes, fabricated-shaped citations, invented rules/limits, sourceless precise stats, "
        "success-claimed-without-evidence, self-contradiction). It returns a 0-100 integrity score and the "
        "specific flagged snippets. It is a fast FIRST-PASS indicator, not a verdict: it is regex-only and cannot "
        "verify quotes against a source, detect a fabricated action, or confirm a success claim, so a high score "
        "does NOT mean the output is safe. Good use: an agent self-checking its own last message before sending."
    ),
)


@mcp.tool(
    title="Check agent output for hallucination tells",
    structured_output=True,
)
def check_agent_integrity(text: str) -> dict[str, Any]:
    """Scan agent output or a transcript for hallucination tells and return a graded integrity report.

    Args:
        text: The agent output to check. Either a plain string (one message/snippet) or a whole transcript —
              a JSONL session log (assistant messages are extracted) or raw text.

    Returns:
        A dict: score (0-100), band (clean/watch/poor), messages_scanned, n_findings, counts (per category),
        worst_offender, findings (each with category/weight/message_index/snippet), and a disclaimer about the
        heuristic's limits. A high score is NOT proof of safety.
    """
    return analyze(text)


if __name__ == "__main__":
    mcp.run("stdio")
