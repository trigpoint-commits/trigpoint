# Repo benchmark — fake-passing tests in public Python repos (2026-10-18)

Method: sampled 24 public Python repos (unauthenticated GitHub search), fetched their Python test files
(134 files total), ran `scan/scan.py`, then **verified HIGH-confidence hits by reading the actual code**.

## Result (honest)
- **0 verified HIGH-confidence fake-passing tests across 24 repos.**
- The scanner's *first* pass flagged 1 HIGH (`javyduck/ChatScene`, a `swallows-failure`). On verification it was a
  **false positive**: the test catches a *specific* `TriangulationError` and calls `pytest.skip()` — a legitimate
  conditional skip, not swallowing failures. Same story for 2 initial hits in `psf/requests`.
- 66 MED `no-assertion` findings — overwhelmingly legitimate smoke tests ("does not raise"), not fake-passes. Not
  a sellable signal; reported as the weak signal it is.

## What verification changed (and why it matters)
The FP taught us the scanner over-flagged. **Fixed `scan.py`:** `swallows-failure` now fires only on a genuine
**catch-all** (`except:` / `except Exception:`) whose handler neither re-raises, asserts, skips, nor fails. Specific
exceptions and `pytest.skip`/`fail` are no longer flagged. Fixture selftest stays green (a real `except Exception:
pass` still caught); ChatScene and requests now correctly show 0 HIGH. Our own trial tool must not cry wolf on a
visitor's real repo — being the anti-fabrication product, shipping FPs would discredit us.

## Honest conclusion + strategic takeaway
**Mature public repos are clean — the fake-pass problem is not there.** That's the expected result: maintained code
has maintained tests. The compelling "N% of test suites fake-pass" acquisition stat requires **AI-generated code
specifically** (vibe-coded repos, agent PRs, agent output), which this general sample does not capture — consistent
with the transcript field study (0 catches in tool-grounded research sets; the failure lives in loosely-built AI code).

**Next for a real asset:** a corpus of AI-generated code/tests (e.g., the fleet's own anonymized agent runs, or
repos tagged/known AI-built) + a larger scan — which needs a GitHub token with `search`+`public_repo` scope (the
current pages-scoped token 401s on general API; unauth caps at ~60 tree-calls/hr). Flagged to Valy.
