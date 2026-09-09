#!/usr/bin/env python3
"""
Trigpoint Agent-Integrity MCP server (packaged entry point).
Installed form of mcp-server/server.py: `uvx --from "trigpoint-agent-integrity[mcp] @ git+https://github.com/trigpoint-commits/trigpoint" trigpoint-mcp`
Imports the installed `trigpoint_quickcheck` module for the scan logic (single source, no path fragility).

Tool: check_agent_integrity(text) -> structured integrity report. Regex-only, inert-data, honest first-pass.
Requires the [mcp] extra:  pip install "trigpoint-agent-integrity[mcp]"
"""
from typing import Any
import trigpoint_quickcheck as QC


def analyze(text: str) -> dict:
    if not isinstance(text, str):
        text = str(text or "")
    msgs = QC.messages_from(text)
    counts, findings, worst, total = {}, [], None, 0
    for i, msg in enumerate(msgs, 1):
        for ln in (msg.splitlines() or [msg]):
            for cat, frag in QC.scan_line(ln):
                counts[cat] = counts.get(cat, 0) + 1
                w = QC.CATS[cat][1]; total += w
                snip = QC.sanitize(ln)
                findings.append({"category": cat, "weight": w, "message_index": i, "snippet": snip})
                if worst is None or w > worst["weight"]:
                    worst = {"category": cat, "weight": w, "message_index": i, "snippet": snip}
    n = sum(counts.values())
    score = max(3, 100 - min(97, total))
    band = "clean" if score >= 85 else ("watch" if score >= 55 else "poor")
    return {"score": score, "band": band, "messages_scanned": len(msgs), "n_findings": n,
            "counts": counts, "worst_offender": worst, "findings": findings,
            "disclaimer": ("Heuristic first-pass, not a verdict. Regex-only, no model — cannot verify quotes against "
                           "a source, catch fabricated actions, or confirm success claims. A high score is NOT a "
                           "certificate. The done-for-you Agent Integrity Audit adds a human/panel pass.")}


def main():
    from mcp.server import MCPServer
    mcp = MCPServer(
        name="trigpoint-agent-integrity",
        title="Trigpoint Agent-Integrity Quick-Check",
        instructions=("Use check_agent_integrity to scan an AI agent's output or transcript for hallucination tells "
                      "(unbacked absolutes, fabricated-shaped citations, invented rules/limits, sourceless stats, "
                      "success-claimed-without-evidence, self-contradiction). Returns a 0-100 score + flagged "
                      "snippets. FIRST-PASS indicator, not a verdict: regex-only, cannot verify quotes against a "
                      "source or detect a fabricated action, so a high score does NOT mean the output is safe. Good "
                      "use: an agent self-checking its own last message before sending."),
    )

    @mcp.tool(title="Check agent output for hallucination tells", structured_output=True)
    def check_agent_integrity(text: str) -> dict[str, Any]:
        """Scan agent output or a transcript for hallucination tells; return a graded integrity report.

        Args:
            text: agent output — a plain string, or a whole transcript (.jsonl session log or raw text).
        Returns:
            dict with score (0-100), band, messages_scanned, n_findings, counts, worst_offender, findings, disclaimer.
            A high score is NOT proof of safety.
        """
        return analyze(text)

    mcp.run("stdio")


if __name__ == "__main__":
    main()
