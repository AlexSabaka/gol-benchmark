"""Encryption-at-rest helpers for persisted credentials (TD-085).

Currently used by :class:`src.web.jobs.Job` to encrypt ``api_key`` / ``api_base``
before they land in ``data/jobs/<job_id>.json``.

Key resolution order (first match wins, cached per-process):
    1. ``GOL_SECRET_KEY`` env var — Fernet-format (32 url-safe base64 bytes).
    2. ``<data_root>/.secret_key`` file — created on first run with mode 0600.
    3. Auto-generate a fresh key, persist it to that file, log a WARNING.

The goal is zero friction on a dev machine while still letting operators pin
key material via env for container / 12-factor deploys.

Encryption is best-effort at-rest obfuscation: a Fernet token defeats casual
inspection (``cat``, backup grep, agent reading ``data/``) but does not protect
against an attacker who already has read access to both the ciphertext and the
key file. For that, rotate the key or externalise it to a real KMS — both out
of scope for this module.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from src.web.config import web_config

logger = logging.getLogger(__name__)

_ENV_VAR = "GOL_SECRET_KEY"
_KEY_FILENAME = ".secret_key"


def _key_file_path() -> Path:
    return Path(web_config.data_root) / _KEY_FILENAME


def _load_or_create_key() -> bytes:
    env_val = os.environ.get(_ENV_VAR)
    if env_val:
        return env_val.encode("utf-8") if isinstance(env_val, str) else env_val

    path = _key_file_path()
    if path.exists():
        return path.read_bytes().strip()

    path.parent.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key()
    # O_EXCL so two processes racing the first-run path can't both create.
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, key)
    finally:
        os.close(fd)
    logger.warning(
        "Generated new Fernet key at %s — preserve this file to keep decrypting "
        "existing jobs, or set %s to pin it.",
        path,
        _ENV_VAR,
    )
    return key


@lru_cache(maxsize=1)
def get_fernet() -> Fernet:
    """Return the process-wide Fernet instance. Cached after first resolution."""
    return Fernet(_load_or_create_key())


def reset_cache() -> None:
    """Drop the cached Fernet. Only intended for tests that swap env / key file."""
    get_fernet.cache_clear()


def encrypt_str(plaintext: str | None) -> str | None:
    """Encrypt a UTF-8 string. Returns ``None`` for empty / ``None`` input."""
    if not plaintext:
        return None
    token = get_fernet().encrypt(plaintext.encode("utf-8"))
    return token.decode("ascii")


def decrypt_str(token: str | None) -> str:
    """Decrypt a Fernet token back to a UTF-8 string.

    Returns ``""`` for ``None`` / empty input. On ``InvalidToken`` (tampered
    ciphertext, wrong key), logs a WARNING and returns ``""`` so the containing
    record can still load — the user will need to re-enter credentials to
    resume the affected job. Matches :meth:`JobStore.load_all`'s existing
    skip-corrupt-record posture.
    """
    if not token:
        return ""
    try:
        return get_fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken:
        logger.warning(
            "Could not decrypt credential field (tampered token or wrong key); "
            "treating as empty. Set %s or restore the previous key file to recover.",
            _ENV_VAR,
        )
        return ""
