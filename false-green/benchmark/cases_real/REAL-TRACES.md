# false-green on REAL public agent traces

Reproduce: `python3 scan_openhands.py 20` (public data via the HuggingFace datasets-server; no API key).

## Source
`nvidia/SWE-Hero-openhands-trajectories` — a public, licensed dataset of **real OpenHands SWE-agent runs**. Each
trajectory is a list of `{role, content, tool_calls}` turns, which maps directly onto what `falsegreen` reads. These
are SWE-bench **solved** instances: the agent genuinely ran tests (many `tool` turns), so when it claims success the
evidence is right there in the log.

## Result (2026-10-16)
```
trajectories scanned:      20
assistant turns scanned: 1242
false-green flags:          0   (trajectories flagged: 0)
false-positive rate:     0.0000 per assistant turn
```

## What this does — and does NOT — show
- **Shows (the credibility-critical part):** on **real** agent output — 1,242 assistant turns across 20 real runs —
  false-green stayed **silent**. It does not cry wolf on legitimate, test-backed agent success. For an
  anti-fabrication tool, a low false-positive rate on real data is the property that matters most, and this is a real
  measurement of it, not an assertion.
- **Does NOT show a "catch."** A success set has **no** false greens by construction (the agent really did run the
  tests), so finding zero is the *expected, correct* outcome — it is not evidence the tool catches lies. A genuine
  catch needs **failure-weighted** traces (runs where an agent claimed an unbacked success); sourcing a public set of
  those, source-neutrally, is the next step. We will report those numbers plainly, and they will not be zero.
- No operator is implicated: zero flags means the opposite of naming-and-shaming.

Honesty note: `falsegreen` checks claim-vs-evidence, so on a truncated trace (evidence outside the fetched turns) it
could in principle miss or misfire; here the full trajectories were scanned.

## Failure-weighted scan (looking for a genuine catch)
To find a real catch, we scanned the **unresolved (failed)** runs of `chilomax/SWE-smith-trajectories` (it carries a
`resolved` bool): **12 failed trajectories, 302 assistant turns → still 0 false greens.** Across ~32 real public SWE
trajectories total (20 solved + 12 failed, ~1,544 assistant turns): **0 false greens.**

### What we learned (honest ICP finding, not a catch)
Tool-enforced agent frameworks (SWE-agent, OpenHands) make the agent *actually run* the tool — so even when they
**fail**, the failure is "ran the tests, patch didn't resolve the hidden test," which is **not** a false green
(evidence of execution exists). A false green — *claimed* success with **no** execution in the log — is rare in
tool-enforced traces by design. It is common in **non-tool-enforced / chat-style** coding assistants, where the model
simply asserts "I ran it, it works" in prose. That is false-green's real ICP, and there is no clean public dataset of
those to scan — which is why this honest report shows strong FP-validation but not yet a published catch. We'd rather
state that than manufacture one.
