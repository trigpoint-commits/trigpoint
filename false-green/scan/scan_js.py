#!/usr/bin/env python3
"""
scan_js.py — false-green REPO scan for JavaScript/TypeScript: find tests (and test setups) that pass without testing.

The JS/TS sibling of scan.py. Most "vibe-coded" / AI-generated apps are JS/TS, and that's exactly where an agent
fakes green. Static, deterministic, no Node needed, no network, no API key. Runs on the visitor's own repo.

    python3 scan_js.py <path>          # exit 1 if any HIGH-confidence fake-pass is found (CI gate)
    python3 scan_js.py --json <path>

What it flags:
  HIGH  test-script-noop     package.json "test"/"test:*" script that force-greens: `exit 0`, `|| true`, bare `echo`,
                             `--passWithNoTests` (jest/vitest pass with zero tests run)
  HIGH  ci-continue-on-error GitHub Actions step that runs tests with `continue-on-error: true` (red suite -> green job)
  HIGH  only-focus           it.only / test.only / describe.only / fit / fdescribe — silently SKIPS every other test
  HIGH  tautological-assert  expect(true).toBe(true) / expect(1).toBe(1) / expect(true).toBeTruthy() — always passes
  HIGH  empty-test           a test with an empty body (it('x', () => {}))  -> passes by doing nothing
  MED   no-assertion         a test block with no expect(/assert/.should/throw anywhere (may be a smoke test)
  LOW   skipped-test         it.skip / xit / xdescribe / test.todo / it.todo — silently not run

Honest scope: regex + lightweight brace-matching (not a full JS parser). HIGH findings are unambiguous; MED/LOW are
weaker signals, labelled as such. Handles .js/.jsx/.ts/.tsx/.mjs/.cjs test files + package.json + GH Actions yml.
"""
import json, os, re, sys

TEST_EXT = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")
SKIP_DIRS = {"node_modules", ".git", "dist", "build", "coverage", ".next", ".nuxt", "out", "vendor", ".turbo"}

def _is_test_file(path):
    b = path.replace("\\", "/")
    name = b.rsplit("/", 1)[-1]
    if not name.endswith(TEST_EXT):
        return False
    low = b.lower()
    return (".test." in name or ".spec." in name or "/__tests__/" in low
            or re.search(r"/tests?/", low) is not None and name.endswith(TEST_EXT))

# ---- package.json test-script noop ----
NOOP_SCRIPT = re.compile(r"(^|[\s&|;])exit\s+0\b|\|\|\s*true\b|--passWithNoTests\b|^\s*echo\b|&&\s*true\b|\bno test specified\b", re.I)

def scan_package_json(path):
    out = []
    try:
        pj = json.load(open(path, encoding="utf-8", errors="replace"))
    except Exception:
        return out
    scripts = pj.get("scripts", {}) if isinstance(pj, dict) else {}
    if not isinstance(scripts, dict):
        return out
    for k, v in scripts.items():
        if not isinstance(v, str):
            continue
        if k == "test" or k.startswith("test:") or k.startswith("test-") or k in ("ci", "check"):
            if NOOP_SCRIPT.search(v):
                out.append({"file": path, "line": 1, "test": k, "severity": "HIGH", "category": "test-script-noop",
                            "detail": v[:120]})
    return out

# ---- GitHub Actions continue-on-error on a test-ish step ----
def scan_workflow(path):
    out = []
    try:
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    except Exception:
        return out
    # find `continue-on-error: true` lines, and if a nearby run/name mentions test, flag
    for i, ln in enumerate(lines):
        if re.search(r"continue-on-error:\s*true", ln, re.I):
            ctx = " ".join(lines[max(0, i - 4): i + 5]).lower()
            if re.search(r"\b(test|jest|vitest|mocha|pytest|npm (run )?test|yarn test|ci)\b", ctx):
                out.append({"file": path, "line": i + 1, "test": "(workflow step)", "severity": "HIGH",
                            "category": "ci-continue-on-error", "detail": ln.strip()[:120]})
    return out

# ---- JS/TS test-file patterns ----
# .only is unambiguous. Bare fit()/fdescribe() (Jasmine focus) collide with ordinary functions named `fit`
# (curve-fit / fit-to-screen) — a real focused test takes a DESCRIPTION STRING first arg: fit("desc", fn).
# Require that string literal so `fit(phone, ...)` (a function under test) is not a false positive.
ONLY_RE = re.compile(r"\b(it|test|describe)\.only\s*\(|\b(fit|fdescribe)\s*\(\s*['\"`]")
SKIP_RE = re.compile(r"\b(it|test|describe)\.(skip|todo)\s*\(|\b(xit|xdescribe|xtest)\s*\(")
TAUTO_RE = re.compile(r"expect\s*\(\s*(true|1|!0|'.'|\"\w\")\s*\)\s*\.\s*(toBe\s*\(\s*(true|1)\s*\)|toBeTruthy\s*\(\s*\))"
                      r"|expect\s*\(\s*(false|0)\s*\)\s*\.\s*toBeFalsy\s*\(\s*\)")
TESTDECL_RE = re.compile(r"\b(it|test)(\.each\s*\([^)]*\))?\s*\(\s*(['\"`])(?P<name>.*?)\3\s*,\s*(async\s*)?(\([^)]*\)|\w+)\s*=>\s*\{")
ASSERT_TOKENS = re.compile(r"\bexpect\s*\(|\bassert\b|\.should\b|\bchai\b|\bthrow\b|\.toThrow\b|\bdone\s*\(")

def _balanced_body(src, open_brace_idx):
    """Return the substring of the function body starting at the '{' at open_brace_idx (inclusive of inner braces)."""
    depth = 0
    i = open_brace_idx
    n = len(src)
    while i < n:
        c = src[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return src[open_brace_idx: i + 1]
        i += 1
    return src[open_brace_idx: open_brace_idx + 600]  # unbalanced/truncated; best-effort

def _lineno(src, idx):
    return src.count("\n", 0, idx) + 1

def scan_js_file(path):
    try:
        src = open(path, encoding="utf-8", errors="replace").read()
    except Exception:
        return []
    out = []
    for m in ONLY_RE.finditer(src):
        out.append({"file": path, "line": _lineno(src, m.start()), "test": m.group(0).rstrip("("),
                    "severity": "HIGH", "category": "only-focus"})
    for m in TAUTO_RE.finditer(src):
        out.append({"file": path, "line": _lineno(src, m.start()), "test": "expect(...)",
                    "severity": "HIGH", "category": "tautological-assert"})
    for m in SKIP_RE.finditer(src):
        out.append({"file": path, "line": _lineno(src, m.start()), "test": m.group(0).rstrip("("),
                    "severity": "LOW", "category": "skipped-test"})
    # per-test body: empty / no-assertion
    for m in TESTDECL_RE.finditer(src):
        brace = src.find("{", m.end() - 1)
        if brace < 0:
            continue
        body = _balanced_body(src, brace)
        inner = body[1:-1].strip()
        name = (m.group("name") or "")[:50]
        if inner == "" or inner in ("// TODO", "/* TODO */"):
            out.append({"file": path, "line": _lineno(src, m.start()), "test": name or "(test)",
                        "severity": "HIGH", "category": "empty-test"})
        elif not ASSERT_TOKENS.search(body):
            out.append({"file": path, "line": _lineno(src, m.start()), "test": name or "(test)",
                        "severity": "MED", "category": "no-assertion"})
    return out

def scan_path(root):
    res = []
    if os.path.isfile(root):
        b = os.path.basename(root)
        if b == "package.json": return scan_package_json(root)
        if _is_test_file(root): return scan_js_file(root)
        return []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            full = os.path.join(dp, fn)
            if fn == "package.json":
                res += scan_package_json(full)
            elif (fn.endswith((".yml", ".yaml")) and ".github" in full.replace("\\", "/")):
                res += scan_workflow(full)
            elif _is_test_file(full):
                res += scan_js_file(full)
    return res

def main(argv):
    as_json = False
    if argv and argv[0] == "--json":
        as_json = True; argv = argv[1:]
    root = argv[0] if argv else "."
    res = scan_path(root)
    high = [r for r in res if r["severity"] == "HIGH"]
    if as_json:
        print(json.dumps({"root": root, "fake_passing": res, "high": len(high), "total": len(res),
                          "fail": len(high) > 0}, indent=2))
        return 1 if high else 0
    if not res:
        print("✓ No fake-passing tests found under %s (scanned JS/TS test files, package.json, workflows)." % root)
        return 0
    order = {"HIGH": 0, "MED": 1, "LOW": 2}
    print("✗ Found %d fake-passing signal(s) (%d HIGH) — tests/CI that pass without testing:\n" % (len(res), len(high)))
    for r in sorted(res, key=lambda r: (order[r["severity"]], r["file"], r["line"])):
        d = ("  " + r["detail"][:70]) if r.get("detail") else ""
        print("  [%-4s] %-20s %s:%d  %s%s" % (r["severity"], r["category"], r["file"], r["line"], r["test"], d))
    print("\n  HIGH = unambiguous (noop script / continue-on-error / .only / tautology / empty). MED/LOW = weaker signals.")
    return 1 if high else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
