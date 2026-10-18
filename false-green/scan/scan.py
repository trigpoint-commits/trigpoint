#!/usr/bin/env python3
"""
scan.py — false-green REPO scan: find tests that PASS without actually testing anything ("fake-passing tests").

The self-demo / trial engine: point it at a repo and it returns an instant "found N fake-passing tests" — the
moment that sells the gate. Static (AST) analysis of Python test files; deterministic, no model, no network, no
API key. Runs on the visitor's OWN code.

    python3 scan.py <path>            # exit 1 if any high-confidence fake-passing test is found (CI gate)
    python3 scan.py --json <path>

What it flags (Python: files named test_*.py / *_test.py, or under a tests/ dir; functions test_* and
unittest TestCase methods test*):
  HIGH  empty-test          body is only pass / ... / a docstring            -> passes by doing nothing
  HIGH  tautological-assert  assert True / assert 1 / assertTrue(True) / assert "x"  -> always true
  HIGH  swallows-failure    the whole test body is wrapped in try/except that passes on any exception
  MED   no-assertion        no assert / pytest.raises / self.assert* / mock .assert_* anywhere in the test
                            (could be a deliberate "doesn't raise" smoke test — labeled, not asserted as fake)
  LOW   unconditional-skip  @skip / @pytest.mark.skip / @pytest.mark.xfail with no condition -> hidden, not run

Honest scope: Python only for now (JS/TS planned); it reads TEST code, not agent transcripts (that's the CLI/Action).
HIGH findings are unambiguous fake-passes; MED/LOW are flagged honestly as weaker signals.
"""
import ast, os, sys, json

TESTFILE = lambda n: (n.startswith("test_") or n.endswith("_test.py")) and n.endswith(".py")

def _in_tests_dir(path):
    parts = path.replace("\\", "/").split("/")
    return any(p in ("test", "tests") for p in parts)

def _is_test_func(node):
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    return node.name.startswith("test_") or node.name.startswith("test")

ASSERT_CALLS = ("assert_", "assertEqual", "assertTrue", "assertFalse", "assertRaises", "assertIn",
                "assertIs", "assertIsNone", "assertIsNotNone", "assertAlmostEqual", "assertListEqual",
                "assertDictEqual", "assertGreater", "assertLess", "assert_called", "assert_any_call",
                "assert_has_calls", "assert_not_called", "assert_awaited")

def _decorator_names(node):
    out = []
    for d in node.decorator_list:
        t = d.func if isinstance(d, ast.Call) else d
        out.append(ast.unparse(t) if hasattr(ast, "unparse") else getattr(t, "attr", getattr(t, "id", "")))
    return out

def _skip_only(node):
    for dn in _decorator_names(node):
        dl = dn.lower()
        if "skip" in dl or "xfail" in dl:
            # a bare skip/xfail (no 'if' condition arg) hides the test
            return True
    return False

def _body_sans_doc(node):
    b = node.body
    if b and isinstance(b[0], ast.Expr) and isinstance(getattr(b[0], "value", None), ast.Constant) and isinstance(b[0].value.value, str):
        b = b[1:]
    return b

def _is_empty(body):
    return all(isinstance(s, ast.Pass) or (isinstance(s, ast.Expr) and isinstance(getattr(s, "value", None), ast.Constant) and (s.value.value is Ellipsis or isinstance(s.value.value, str))) for s in body) if body else True

def _tautological(node):
    for s in ast.walk(node):
        if isinstance(s, ast.Assert):
            t = s.test
            if isinstance(t, ast.Constant) and bool(t.value):          # assert True / assert 1 / assert "x"
                return True
        elif isinstance(s, ast.Call):
            fn = s.func.attr if isinstance(s.func, ast.Attribute) else getattr(s.func, "id", "")
            a = s.args
            if fn == "assertTrue" and a and isinstance(a[0], ast.Constant) and bool(a[0].value):
                return True
            if fn == "assertFalse" and a and isinstance(a[0], ast.Constant) and not bool(a[0].value):
                return True
            if fn in ("assertEqual", "assertIs") and len(a) >= 2 and isinstance(a[0], ast.Constant) \
               and isinstance(a[1], ast.Constant) and a[0].value == a[1].value:
                return True
    return False

def _has_assertion(node):
    for s in ast.walk(node):
        if isinstance(s, ast.Assert):
            return True
        if isinstance(s, ast.Call):
            fn = s.func.attr if isinstance(s.func, ast.Attribute) else getattr(s.func, "id", "")
            if fn and (fn in ASSERT_CALLS or fn.startswith("assert") or fn == "raises" or fn == "fail"):
                return True
        if isinstance(s, ast.Raise):
            return True
    return False

def _swallows(node):
    """True only for a CATCH-ALL try/except wrapping the whole test whose handler neither re-raises, asserts, skips,
    nor fails — i.e. genuinely hides failures. A handler that catches a SPECIFIC exception, or that skips / re-raises
    / fails, is legitimate and is NOT flagged (that was a false-positive source — e.g. `except FooError: pytest.skip`)."""
    body = _body_sans_doc(node)
    if len(body) != 1 or not isinstance(body[0], ast.Try):
        return False
    for h in body[0].handlers:
        et = h.type
        catchall = (et is None
                    or (isinstance(et, ast.Name) and et.id in ("Exception", "BaseException"))
                    or (isinstance(et, ast.Tuple) and any(isinstance(x, ast.Name) and x.id in ("Exception", "BaseException") for x in et.elts)))
        if not catchall:
            continue
        handled = False
        for s in ast.walk(h):
            if isinstance(s, (ast.Raise, ast.Assert)):
                handled = True; break
            if isinstance(s, ast.Call):
                fn = s.func.attr if isinstance(s.func, ast.Attribute) else getattr(s.func, "id", "")
                if fn in ("skip", "skipTest", "fail", "xfail"):
                    handled = True; break
        if not handled:
            return True
    return False

def scan_file(path):
    try:
        src = open(path, encoding="utf-8", errors="replace").read()
        tree = ast.parse(src, filename=path)
    except Exception:
        return []
    out = []
    for node in ast.walk(tree):
        if not _is_test_func(node):
            continue
        body = _body_sans_doc(node)
        sev = cat = None
        if _is_empty(body):
            sev, cat = "HIGH", "empty-test"
        elif _tautological(node):
            sev, cat = "HIGH", "tautological-assert"
        elif _swallows(node):
            sev, cat = "HIGH", "swallows-failure"
        elif _skip_only(node):
            sev, cat = "LOW", "unconditional-skip"
        elif not _has_assertion(node):
            sev, cat = "MED", "no-assertion"
        if cat:
            out.append({"file": path, "line": node.lineno, "test": node.name, "severity": sev, "category": cat})
    return out

def scan_path(root):
    findings = []
    if os.path.isfile(root):
        return scan_file(root)
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in (".git", "node_modules", ".venv", "venv", "__pycache__", ".tox", "dist", "build")]
        for fn in fns:
            full = os.path.join(dp, fn)
            if TESTFILE(fn) or (fn.endswith(".py") and _in_tests_dir(full) and ("test" in fn)):
                findings.append(full)
    res = []
    for f in findings:
        res.extend(scan_file(f))
    return res

def main(argv):
    as_json = False
    if argv and argv[0] == "--json":
        as_json = True; argv = argv[1:]
    root = argv[0] if argv else "."
    res = scan_path(root)
    high = [r for r in res if r["severity"] == "HIGH"]
    if as_json:
        print(json.dumps({"root": root, "fake_passing": res, "high": len(high),
                          "total": len(res), "fail": len(high) > 0}, indent=2))
        return 1 if high else 0
    if not res:
        print("✓ No fake-passing tests found under %s (scanned Python test files)." % root)
        return 0
    order = {"HIGH": 0, "MED": 1, "LOW": 2}
    bycat = {}
    for r in sorted(res, key=lambda r: order[r["severity"]]):
        bycat.setdefault(r["category"], 0)
        bycat[r["category"]] += 1
    print("✗ Found %d fake-passing test(s) (%d HIGH-confidence) — tests that pass without testing:\n" % (len(res), len(high)))
    for r in sorted(res, key=lambda r: (order[r["severity"]], r["file"], r["line"])):
        print("  [%-4s] %-18s %s:%d  %s()" % (r["severity"], r["category"], r["file"], r["line"], r["test"]))
    print("\n  by category:", ", ".join("%s=%d" % (k, v) for k, v in bycat.items()))
    print("  HIGH = unambiguous fake-pass (empty / always-true / swallows failures). MED/LOW = weaker signals.")
    return 1 if high else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
