# no-done-without-proof — stop your agent claiming success it never ran

The enforcement half of [false-green](../). The CLI/Action *catches* a false green after the fact; this *prevents*
it, at the source, in Claude Code / Cursor / your own agent loop — which is where the pain actually is (CI can
re-run tests; it can't re-run "deployed" or "verified manually"). Three layers, use any or all:

### 1. Prompt rule (works everywhere, 0 install)
Drop [`no-done-without-proof.md`](no-done-without-proof.md) into your system prompt / `CLAUDE.md` / `.cursorrules`.
The agent must cite the command + output for any success claim. Cheapest possible fix.

### 2. Claude Code Stop hook (hard gate)
[`stop_hook.py`](stop_hook.py) blocks the agent from ending its turn on an unbacked completion claim and tells it to
run-and-cite or correct itself. Install in `.claude/settings.json`:
```json
{ "hooks": { "Stop": [ { "hooks": [
  { "type": "command", "command": "python3 /ABS/PATH/to/PRODUCT/false-green/enforce/stop_hook.py" }
] } ] } }
```
It fires only when the end-of-session claim is genuinely unbacked (0 false positives across 500 real tool-grounded
transcripts in our field study), and fails OPEN on any error — it will never wedge your session. Uses
[`cc_adapter.py`](cc_adapter.py) to read Claude Code's transcript format.

### 3. CI gate (catch regressions)
The [false-green GitHub Action](../) on your captured agent logs — fails the build when a merged change's transcript
claims a success with no execution evidence.

---
Deterministic, local, MIT, no model, no API key. Honest scope: layer 2's adapter targets Claude Code's transcript
schema (tolerant, but verify on your version); the prompt rule is model-agnostic. This is prevention — pair it with
the CLI for after-the-fact auditing.
