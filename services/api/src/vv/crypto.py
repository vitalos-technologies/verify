"""Hashing, sealing and signature helpers. Hashes are not anonymisation."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def random_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def token_hash(token: str) -> str:
    """For high-entropy random tokens (hosted links, cookies)."""
    return hashlib.sha256(token.encode()).hexdigest()


def keyed_hash(pepper: bytes, *parts: str) -> str:
    """Peppered HMAC for low-entropy or linkable values (OTP codes, destinations, API key secrets)."""
    msg = "\x1f".join(parts).encode()
    return hmac.new(pepper, msg, hashlib.sha256).hexdigest()


def constant_time_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def canonical_digest(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def seal(key: bytes, plaintext: bytes, aad: bytes = b"") -> bytes:
    nonce = os.urandom(12)
    return nonce + AESGCM(key).encrypt(nonce, plaintext, aad)


def unseal(key: bytes, sealed: bytes, aad: bytes = b"") -> bytes:
    return AESGCM(key).decrypt(sealed[:12], sealed[12:], aad)


def hmac_sha256_hex(secret: bytes, message: bytes) -> str:
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def sign_webhook(secret: bytes, timestamp: int, raw_body: bytes) -> str:
    """X-Vitalos-Signature value: v1=hex(HMAC-SHA256(secret, f"{timestamp}." + body))."""
    return "v1=" + hmac_sha256_hex(secret, str(timestamp).encode() + b"." + raw_body)


def verify_webhook(secret: bytes, timestamp: int, raw_body: bytes, signature_header: str,
                   now: int, tolerance: int = 300) -> bool:
    if abs(now - timestamp) > tolerance:
        return False
    expected = sign_webhook(secret, timestamp, raw_body)
    candidates = [part.strip() for part in signature_header.split(",")]
    return any(hmac.compare_digest(expected, c) for c in candidates)
