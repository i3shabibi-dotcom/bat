# -*- coding: utf-8 -*-
import hashlib
import os
import sys
import loc_crypto


def key() -> bytes:
    parts = [b"trio", b"of", b"towns", b"arabic", b"hesham"]
    return hashlib.sha256(b"|".join(parts) + b"|USA-v1.1-ROMFS-2026").digest()


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: python build_payload.py <romfs.zip> <patch.enc>")
        return 2
    src, dst = sys.argv[1], sys.argv[2]
    if not os.path.isfile(src):
        raise SystemExit("missing payload zip: " + src)
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    loc_crypto.encrypt_file(src, dst, key())
    print("created", dst, os.path.getsize(dst), "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
