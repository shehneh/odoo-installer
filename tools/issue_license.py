#!/usr/bin/env python3
"""Issue a signed v2 license bundle JSON.

This is an ADMIN/SERVER tool.
Do NOT ship the private key with the installer.

Usage:
  python tools/issue_license.py \
    --private-key ./license_private_key.pem \
    --out ./license.oml \
    --expires-at 2026-12-26T00:00:00 \
    --hardware-id <HWID> \
    --issued-to user@example.com \
    --plan professional

The installer can validate this offline using license_public_key.pem.
"""

from __future__ import annotations

import argparse
import base64
import json
import secrets
from datetime import datetime
from pathlib import Path


def canonical_json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--private-key', required=True, help='Path to RSA private key PEM')
    ap.add_argument('--out', required=True, help='Output license file path')
    ap.add_argument('--expires-at', required=True, help='ISO datetime, e.g. 2026-12-26T00:00:00')
    ap.add_argument('--hardware-id', default='', help='Optional HWID binding (recommended)')
    ap.add_argument('--issued-to', default='', help='Email/phone/customer id')
    ap.add_argument('--plan', default='professional', help='Plan id/name')
    ap.add_argument('--license-id', default='', help='Optional license id (defaults to random)')
    args = ap.parse_args()

    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
    except Exception:
        print('ERROR: cryptography is required. Install with: pip install cryptography')
        return 2

    priv_path = Path(args.private_key)
    out_path = Path(args.out)

    private_key = load_pem_private_key(priv_path.read_bytes(), password=None)

    license_id = args.license_id.strip() or secrets.token_hex(12)

    payload = {
        'v': 2,
        'license_id': license_id,
        'plan': args.plan.strip(),
        'issued_to': args.issued_to.strip(),
        'hardware_id': args.hardware_id.strip(),
        'expires_at': args.expires_at.strip(),
        'issued_at': datetime.utcnow().replace(microsecond=0).isoformat() + 'Z',
        'nonce': secrets.token_hex(8),
    }

    message = canonical_json_bytes(payload)
    sig = private_key.sign(
        message,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )

    bundle = dict(payload)
    bundle['sig'] = base64.b64encode(sig).decode('utf-8')

    out_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote license file: {out_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
