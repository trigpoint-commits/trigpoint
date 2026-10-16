# false-green — catch the AI agent that *claims* a success it never performed

> The sharpest, most **verifiable** integrity check Trigpoint ships (chosen independently by Opus 5.5 + Fable 5.1,
> 2026-10-16). It's a painkiller, not a vitamin: anyone running Claude Code / Cursor / Codex agents in a pipeline
> has had an agent say *"tests pass, deployed, fixed"* — having run nothing. This fails that.

## What it does
For every **success claim** in an assistant turn (`tests pass`, `it works`, `deployed`, `verified`, `fixed`,
`build succeeded`, `done & working`) it looks for **execution evidence** in a nearby turn (a tool call / command
+ its output — `pytest`, `N passed`, `exit code 0`, `git push`, `docker build`, a traceback, …). A claim with **no
backing evidence** is a *false green* and the run is failed.

It is **not** a truth oracle and does not judge whether the evidence is correct — it checks, verifiably, that a
claimed action has matching evidence in the log. That's what makes it stronger than tell-detection heuristics: the
finding is checkable against the transcript itself. Intent/plans ("I'll make sure tests pass") are not claims and
are not flagged.

## Use as a CI gate
```
python3 falsegreen.py agent-session.jsonl      # exit 1 if any unbacked success claim
cat session.jsonl | python3 falsegreen.py       # stdin
python3 falsegreen.py --json session.jsonl       # machine-readable findings
```
Exit code is the gate: `0` = clean, `1` = false green found. Drop it in a pre-merge step / GitHub Action so a PR
whose agent transcript claims a success it never ran gets blocked.

Input: `.jsonl` (one `{"role","content"}` per line; tool turns = role in tool/tool_result/function, or a
tool_use/tool_calls field, or command-output in the text), or plain text (coarser).

## Trust / honesty
- Deterministic, local, no network, no model, no API key — you can read every rule in `falsegreen.py`.
- Regression-locked: `./selftest.sh` (3 fixtures: unbacked→fail, real→pass, intent→pass).
- Hosted upsell (optional): the same finding, ed25519-signed and bound to `sha256(your transcript)`, independently
  verifiable at trigpoint-commits.github.io/trigpoint/verify.html — an attestation you can show a user or sponsor.

## Status
v1 detector + fixtures + selftest (ALL GREEN). Next: ship as a GitHub Action + publish a real catch on an external
transcript (the one external proof the bench says we need before chasing sponsors).
