#!/usr/bin/env python3
"""
Trigpoint badge verifier — OFFLINE, no network, no call back to us. Anyone (an agent, a buyer, a platform) verifies a
signed badge against the published public key. This closes the consumer loop: the badge is trustworthy because it's
independently checkable, not because you trust our server.

    python3 verify_badge.py badge.json [--pubkey badge_pubkey.pem]
    echo "$BADGE_JSON" | python3 verify_badge.py --pubkey badge_pubkey.pem

Exit 0 = signature valid (and prints the payload). Exit 1 = INVALID/tampered. Exit 2 = usage/malformed.
It verifies the SIGNATURE only — i.e. "this verdict was really issued by the holder of this key, unaltered." It does
NOT re-run the checks; the payload's verdict is what was attested at issue time.
"""
import os, sys, json, base64
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.exceptions import InvalidSignature

def canon(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

def main(argv):
    pub_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "badge_pubkey.pem")
    args = []
    i = 0
    while i < len(argv):
        if argv[i] == "--pubkey": pub_path = argv[i+1]; i += 2
        else: args.append(argv[i]); i += 1
    raw = open(args[0]).read() if args and os.path.isfile(args[0]) else sys.stdin.read()
    if not raw.strip():
        print("usage: verify_badge.py badge.json [--pubkey PEM]"); return 2
    try:
        badge = json.loads(raw)
        payload, sig = badge["payload"], base64.b64decode(badge["sig"])
    except Exception as e:
        print(f"INVALID: malformed badge ({e})"); return 2
    if badge.get("alg") != "ed25519":
        print(f"INVALID: unexpected alg {badge.get('alg')!r}"); return 1
    try:
        pub = load_pem_public_key(open(pub_path, "rb").read())
        pub.verify(sig, canon(payload))
    except InvalidSignature:
        print("INVALID: signature does not verify — badge is forged or tampered."); return 1
    except Exception as e:
        print(f"INVALID: {e}"); return 1
    print("VALID ✓  signature verifies against the published key.")
    print(json.dumps(payload, indent=2)[:1200])
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
