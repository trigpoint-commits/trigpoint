# false-green scan — find tests that pass without testing anything

AI coding agents love to make the bar go green: they write tests that pass by doing **nothing** — empty bodies,
`assert True`, a `try/except: pass` that swallows every failure, a silent `@skip`. Point this at your repo and it
tells you instantly:

```
python3 scan.py .            # or: uvx --from git+https://github.com/trigpoint-commits/trigpoint false-green-scan .
✗ Found 7 fake-passing test(s) (5 HIGH-confidence) — tests that pass without testing:
  [HIGH] empty-test          tests/test_x.py:3   test_empty()
  [HIGH] tautological-assert  tests/test_x.py:9   test_true()
  ...
```

Static AST analysis — deterministic, local, **no model, no API key, no network**. Runs on your own code.

**Flags:** `empty-test`, `tautological-assert`, `swallows-failure` (HIGH, unambiguous) · `no-assertion` (MED — could
be a deliberate smoke test, flagged honestly) · `unconditional-skip` (LOW). Exit 1 on any HIGH = drop-in CI gate.

**Honest scope:** Python test files for now (JS/TS planned); it reads your **test code**. Its siblings: the
[CLI/Action](../) reads agent **transcripts** (claimed-success vs evidence), and the [enforce pack](../enforce/)
**prevents** false "done" at the source in Claude Code/Cursor. Three angles on one problem: agents reporting success
they didn't earn. MIT.
