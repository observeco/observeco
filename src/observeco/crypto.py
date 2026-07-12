"""Shared encryption layer for config secrets.

Uses Fernet (AES-128-CBC) symmetric encryption with key stored in OS keychain.

Why Fernet vs alternatives:
- AES-GCM via cryptography: equivalent security but more API surface
- keyring only: stores raw secrets in keychain but not portable to CI/Docker
- env vars only: no persistence
Fernet + keychain handles both local dev and production deployment.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# Keychain service name
_KEYCHAIN_SERVICE = "observeco"
_KEYCHAIN_KEY_NAME = "encryption-key"

# Fallback file (only used when keychain unavailable, e.g., CI/Docker)
_FALLBACK_KEY_DIR = Path.home() / ".config" / "observeco"
_FALLBACK_KEY_FILE = _FALLBACK_KEY_DIR / ".encryption.key"


def _keyring_get_with_timeout(service: str, key: str) -> str | None:
    """Read a keyring secret with a hard timeout.

    macOS Keychain (keyring.backends.macOS) calls Security.framework
    directly and HANGS indefinitely in headless contexts — no GUI security
    session to authorize the unlock, so the call blocks on mach_msg forever.
    A bare try/except never fires because it doesn't raise, it deadlocks.
    Isolate the call in a child process and kill it on timeout so headless
    hosts fall through to the file/env fallback.
    ponytail: ceiling = 3s hard kill per call; mount the login keychain or
    set OBSERVECO_ENCRYPTION_KEY to avoid the keychain path entirely.
    """
    import multiprocessing

    def _target(q: "multiprocessing.Queue") -> None:
        try:
            import keyring
            q.put(keyring.get_password(service, key))
        except Exception:
            q.put(None)

    q: multiprocessing.Queue = multiprocessing.Queue()
    p = multiprocessing.Process(target=_target, args=(q,), daemon=True)
    p.start()
    p.join(timeout=3)
    if p.is_alive():
        p.kill()
        return None
    try:
        return q.get_nowait()
    except Exception:
        return None


def _keyring_set_with_timeout(service: str, key: str, value: str) -> bool:
    """Set a keyring secret with a hard timeout (mirror of the get guard)."""
    import multiprocessing

    def _target() -> None:
        try:
            import keyring
            keyring.set_password(service, key, value)
        except Exception:
            pass

    p = multiprocessing.Process(target=_target, daemon=True)
    p.start()
    p.join(timeout=3)
    if p.is_alive():
        p.kill()
        return False
    return True


def _get_key() -> bytes:
    """Get or generate a Fernet-compatible encryption key.

    Precedence:
    1. Environment variable OBSERVECO_ENCRYPTION_KEY
    2. OS keychain (via keyring, timeout-guarded for headless)
    3. Fallback file at ~/.config/observeco/.encryption.key

    Returns base64-encoded 32-byte key suitable for Fernet.
    """
    # 1. Environment variable (for CI/Docker)
    env_key = os.environ.get("OBSERVECO_ENCRYPTION_KEY")
    if env_key:
        try:
            # Validate it's a valid Fernet key
            Fernet(env_key.encode())
            return env_key.encode()
        except Exception:
            logger.warning("OBSERVECO_ENCRYPTION_KEY invalid, ignoring")

    # 2. OS keychain (timeout-guarded — headless boxes would otherwise hang)
    try:
        stored = _keyring_get_with_timeout(_KEYCHAIN_SERVICE, _KEYCHAIN_KEY_NAME)
        if stored:
            return stored.encode()
    except Exception:
        pass

    # 3. Fallback file
    if _FALLBACK_KEY_FILE.exists():
        try:
            key = _FALLBACK_KEY_FILE.read_text().strip().encode()
            Fernet(key)  # validate
            return key
        except Exception:
            logger.warning("Fallback encryption key corrupted, regenerating")

    # Generate new key and store
    key = Fernet.generate_key()
    _store_key(key)
    return key


def _store_key(key: bytes) -> None:
    """Store an encryption key."""
    # Try keychain first (timeout-guarded)
    try:
        if _keyring_set_with_timeout(_KEYCHAIN_SERVICE, _KEYCHAIN_KEY_NAME, key.decode()):
            logger.info("Encryption key stored in OS keychain")
            return
    except Exception:
        pass

    # Fallback to file
    _FALLBACK_KEY_DIR.mkdir(parents=True, exist_ok=True)
    _FALLBACK_KEY_FILE.write_text(key.decode())
    _FALLBACK_KEY_FILE.chmod(0o600)
    logger.info(f"Encryption key stored at {_FALLBACK_KEY_FILE}")


def _get_fernet() -> Fernet:
    """Get a Fernet instance using the stored key."""
    return Fernet(_get_key())


def encrypt(data: str) -> str:
    """Encrypt a string.

    Returns base64-encoded ciphertext (URL-safe, JSON-printable).
    """
    if not data:
        return ""
    f = _get_fernet()
    return f.encrypt(data.encode()).decode()


def decrypt(token: str) -> str:
    """Decrypt a previously encrypted string.

    Returns empty string on failure (graceful degradation).
    """
    if not token:
        return ""
    f = _get_fernet()
    try:
        return f.decrypt(token.encode()).decode()
    except InvalidToken:
        logger.error("Decryption failed — token may be corrupted or key has changed")
        return ""
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        return ""


def encrypt_dict(data: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    """Encrypt specific fields of a dict in-place.

    Returns the same dict with specified fields encrypted.
    """
    for field in fields:
        if field in data and data[field]:
            data[field] = encrypt(str(data[field]))
    return data


def decrypt_dict(data: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    """Decrypt specific fields of a dict in-place.

    Returns the same dict with specified fields decrypted.
    """
    for field in fields:
        if field in data and data[field]:
            decrypted = decrypt(str(data[field]))
            if decrypted:
                data[field] = decrypted
    return data
