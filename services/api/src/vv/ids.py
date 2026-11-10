"""Opaque, time-ordered identifiers with type prefixes (e.g. ver_01J...)."""

from __future__ import annotations

import os
import time

_ALPHABET = "0123456789abcdefghjkmnpqrstvwxyz"  # Crockford base32, lowercase


def _encode(value: int, length: int) -> str:
    out = []
    for _ in range(length):
        out.append(_ALPHABET[value & 31])
        value >>= 5
    return "".join(reversed(out))


def new_id(prefix: str) -> str:
    millis = int(time.time() * 1000)
    rand = int.from_bytes(os.urandom(10), "big")
    return f"{prefix}_{_encode(millis, 10)}{_encode(rand, 16)}"
