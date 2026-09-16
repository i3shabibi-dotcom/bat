# -*- coding: utf-8 -*-
import hashlib
import os

MAGIC = b"HLOC1"


def _keystream(seed: bytes, n: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(seed + counter.to_bytes(8, "little")).digest()
        counter += 1
    return bytes(out[:n])


def _xor(a: bytes, b: bytes) -> bytes:
    return (int.from_bytes(a, "big") ^ int.from_bytes(b, "big")).to_bytes(len(a), "big")


def encrypt(plain: bytes, key: bytes) -> bytes:
    nonce = os.urandom(16)
    ct = _xor(plain, _keystream(key + nonce, len(plain)))
    mac = hashlib.sha256(key + nonce + ct).digest()[:16]
    return MAGIC + nonce + mac + ct


def decrypt(blob: bytes, key: bytes) -> bytes:
    if blob[:5] != MAGIC:
        raise ValueError("bad container")
    nonce, mac, ct = blob[5:21], blob[21:37], blob[37:]
    expected = hashlib.sha256(key + nonce + ct).digest()[:16]
    if expected != mac:
        raise ValueError("bad key or corrupted data")
    return _xor(ct, _keystream(key + nonce, len(ct)))


def encrypt_file(src: str, dst: str, key: bytes) -> None:
    with open(src, "rb") as f:
        plain = f.read()
    with open(dst, "wb") as f:
        f.write(encrypt(plain, key))
