#!/usr/bin/env python3
"""Generate RSA keypair for signing v2 license files.

IMPORTANT:
- Keep the private key secret (server-side only).
- Distribute only the public key with the installer (license_public_key.pem).

Usage:
  python tools/license_keygen.py --out-dir .

Outputs:
  - license_private_key.pem (DO NOT ship)
  - license_public_key.pem  (ship with installer)
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-dir', default='.', help='Output directory')
    ap.add_argument('--bits', type=int, default=3072, help='RSA key size (default 3072)')
    args = ap.parse_args()

    try:
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
    except Exception:
        print('ERROR: cryptography is required. Install with: pip install cryptography')
        return 2

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=args.bits)

    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    pub_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    (out_dir / 'license_private_key.pem').write_bytes(priv_pem)
    (out_dir / 'license_public_key.pem').write_bytes(pub_pem)

    print('Wrote: license_private_key.pem (KEEP SECRET)')
    print('Wrote: license_public_key.pem (ship with installer)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
