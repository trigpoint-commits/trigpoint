# false-green — benchmark

Run it yourself: `python3 benchmark/bench.py`. Every case is inline and readable in that file — audit it.

## What this measures
Accuracy on a **labeled corpus of 13 realistic agent-transcript cases**: 5 that contain a *false green* (a success
claimed with no execution evidence — the thing we should catch) and 8 that should **not** be flagged — four where
the success is backed by a tool/command (`pytest`, `npm test`, `git push`, inline test output), two plans/intent
("I'll make sure the tests pass…"), one question ("do the tests pass?"), one that merely mentions "tests" with no
success claim. The 8 negatives exist to measure the **false-positive rate**, which matters most on an
anti-fabrication tool.

## Result (2026-10-16)
```
cases=13  TP=5 FP=0 FN=0 TN=8
precision=1.00  recall=1.00  accuracy=1.00  false-positive-rate=0.00
```
All 5 false greens caught; none of the 8 legitimate cases flagged.

## Honest caveats — read these
- **This is a constructed corpus, not a universal catch-rate.** 1.00/1.00 means the detector handles the canonical
  false-green patterns and does not trip on backed success, intent, or questions *on these 13 cases*. It is **not** a
  claim that it catches 100% of false greens in the wild, and it won't — a success claim phrased with no tell, or
  evidence the detector can't recognize, will slip or misfire.
- **It checks claim-vs-evidence, not whether the evidence is correct.** A fabricated test log that *looks* like a
  pass counts as evidence here; this catches the "claimed but never ran" case, not the "ran but lied about the
  result" case.
- **Real public traces:** measured — see [`cases_real/REAL-TRACES.md`](cases_real/REAL-TRACES.md). On 20 real public
  OpenHands SWE-agent trajectories (**1,242 assistant turns**), false-green raised **0 flags** → a real-data
  false-positive validation (it stays quiet on legitimate test-backed success). That is *not* a catch — a success set
  has no false greens by construction; a genuine catch needs failure-weighted traces, which is the next step and whose
  numbers will be reported plainly.

## Method
`bench.py` runs `falsegreen.analyze()` on each case and compares the boolean verdict to the label. precision = of
what we flagged, how much was a real false green; recall = of real false greens, how many we caught; FP-rate = of
legitimate cases, how many we wrongly flagged. Exit non-zero if any case is wrong (so it's a regression gate too).
