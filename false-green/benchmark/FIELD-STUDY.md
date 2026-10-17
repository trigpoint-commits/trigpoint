# false-green field study — ~800 public agent transcripts (2026-10-17)

Method: ran the false-green detector over ~800 real public transcripts from 6 open datasets via the HuggingFace
datasets-server (python urllib; no API key). 6 scan agents in parallel + 1 synthesis agent. Honest by design — we
are the anti-fabrication product, so a null result gets reported as a null result.

## Results
| Category | Datasets (n) | Fired | Verdict |
|---|---|---|---|
| **Tool-grounded agents** | SWE-Hero/OpenHands 150, SWE-smith 150, cleanroom 50, AgentInstruct/ReAct 150 = **500** | **0 / 500 (0.00%)** | correct silence — every success claim sits next to real tool/command output |
| **Tool-less chat (control)** | WildChat-1M 150, no_robots 150 = **300** | 4 / 300 (1.33%) | **all 4 false positives** (narrative trigger words in prose) |
| **TOTAL** | **~800** | **4**, all FP | **0 genuine catches** |

**Specificity (the number that matters):** on the 500 tool-grounded agent transcripts the detector raised **zero**
false alarms. In SWE-smith specifically, 117/150 trajectories carried ≥1 asserted success claim — **228 real success
claims** (tests-pass 82, verified 77, fixed 39, it-works 30) — and **all 228 were backed by execution within ±2 turns →
0 false positives across 228 real claims.** That is meaningful specificity, not vacuous silence: it does not cry wolf
on real agent traces.

**No wild catch (honest):** 0 genuine false greens in ~800 transcripts. Expected, and we say so: success-oriented and
tool-grounded corpora contain no *unbacked* success claims by construction — even failed SWE runs fail by submitting a
wrong patch, not by fabricating that they ran tests. Surfacing a real over-claim needs **failure-weighted / step-limited**
traces (or a non-tool-enforced chat agent), which no clean public dataset provides. The "send us a transcript that
breaks it" ask stands.

**The 4 false positives (for the record), all in tool-less prose:** (1) WildChat "deployed" in reality-shifting
roleplay; (2) WildChat "it works" explaining pasted scraper output; (3) no_robots "confirmed/verified" in a creative
letter; (4) no_robots "this works" in a brainstorm. All `had_tools=no`.

## Product action from the study
The entire FP class is confined to sessions with **no tool channel at all** (free prose / tool-less chat). So:
- Added an **opt-in `--require-tools`** flag: only fire in a session that contains ≥1 execution/tool turn. This
  eliminates the free-prose FP class for users who run false-green over mixed content. It is **off by default** on
  purpose — the starkest false green (an agent that claims "tests pass" having run *nothing*, zero tool turns in the
  whole session) must still fire, and `--require-tools` would suppress exactly that. CI users on structured agent logs
  can turn it on to kill prose noise.
- Reaffirmed scope: false-green belongs on **structured agent transcripts with a tool channel** (see README + REAL-TRACES.md).

## Publishable summary (honest, for site/HN)
> We ran Trigpoint's false-green detector across ~800 public agent transcripts from six open datasets — three
> tool-grounded SWE-agent sets (NVIDIA SWE-Hero/OpenHands, SWE-smith, a cleanroom SWE set), one multi-step ReAct set
> (AgentInstruct), and two human-chat controls (WildChat-1M, no_robots). On the 500 tool-grounded agent transcripts,
> where every success claim can be checked against adjacent execution output, the detector fired **zero** times — no
> false alarms across hundreds of real "tests pass / fixed / verified" claims. It fired only 4 times total, all on the
> tool-less chat sets, every one a false positive on a narrative trigger word — not an agent over-claiming. We found
> **no genuine false green** in this corpus: zero real catches. That's the honest, expected result — and a scope, not a
> victory: the tool belongs on structured agent transcripts with a tool channel, where across 500 of them it didn't cry
> wolf once.
