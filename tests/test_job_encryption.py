"""Encryption-at-rest for persisted job credentials (TD-085)."""
from __future__ import annotations

import logging
import os
import stat
import sys
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from src.web import crypto
from src.web.config import web_config
from src.web.jobs import JOB_SCHEMA_VERSION, Job


@pytest.fixture
def isolated_crypto(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Redirect key storage under ``tmp_path`` and clear env + caches per test."""
    monkeypatch.setattr(web_config, "data_root", str(tmp_path))
    monkeypatch.delenv("GOL_SECRET_KEY", raising=False)
    crypto.reset_cache()
    yield tmp_path
    crypto.reset_cache()


def _sample_job(**overrides) -> Job:
    defaults = dict(
        id="job-123",
        model_name="gpt-4o-mini",
        testset_path="data/testsets/foo.json.gz",
        provider="openai",
        api_key="sk-abc123xyz",
        api_base="https://api.openai.com/v1",
    )
    defaults.update(overrides)
    return Job(**defaults)


def test_roundtrip_encrypts_credentials(isolated_crypto):
    job = _sample_job()
    stored = job.to_storable_dict()

    assert stored["schema_version"] == JOB_SCHEMA_VERSION
    assert "api_key" not in stored
    assert "api_base" not in stored

    token_key = stored["api_key_enc"]
    token_base = stored["api_base_enc"]
    assert isinstance(token_key, str) and token_key
    assert isinstance(token_base, str) and token_base
    assert "sk-abc123xyz" not in token_key
    assert "openai.com" not in token_base

    restored = Job.from_stored_dict(stored)
    assert restored.api_key == "sk-abc123xyz"
    assert restored.api_base == "https://api.openai.com/v1"
    assert restored.id == job.id
    assert restored.model_name == job.model_name


def test_empty_credentials_emit_null(isolated_crypto):
    job = _sample_job(api_key="", api_base="")
    stored = job.to_storable_dict()

    assert stored["api_key_enc"] is None
    assert stored["api_base_enc"] is None

    restored = Job.from_stored_dict(stored)
    assert restored.api_key == ""
    assert restored.api_base == ""


def test_legacy_plaintext_record_still_loads(isolated_crypto):
    legacy = {
        "id": "job-legacy",
        "model_name": "gpt-4o",
        "testset_path": "data/testsets/bar.json.gz",
        "state": "paused",
        "api_key": "sk-legacy-plaintext",
        "api_base": "https://legacy.example.com/v1",
    }
    restored = Job.from_stored_dict(legacy)
    assert restored.api_key == "sk-legacy-plaintext"
    assert restored.api_base == "https://legacy.example.com/v1"


def test_tampered_ciphertext_degrades_gracefully(
    isolated_crypto, caplog: pytest.LogCaptureFixture
):
    job = _sample_job()
    stored = job.to_storable_dict()

    # Flip the last body byte (the final char before any padding) to invalidate
    # the Fernet HMAC without breaking the base64 framing.
    token = stored["api_key_enc"]
    tampered_list = list(token)
    idx = len(tampered_list) - 2
    tampered_list[idx] = "A" if tampered_list[idx] != "A" else "B"
    stored["api_key_enc"] = "".join(tampered_list)

    with caplog.at_level(logging.WARNING, logger="src.web.crypto"):
        restored = Job.from_stored_dict(stored)

    assert restored.api_key == ""
    assert restored.api_base == "https://api.openai.com/v1"  # untampered
    assert any("decrypt" in rec.message.lower() for rec in caplog.records)


def test_missing_key_file_auto_generates(isolated_crypto):
    fernet = crypto.get_fernet()
    key_path = Path(isolated_crypto) / ".secret_key"

    assert key_path.exists()
    mode = stat.S_IMODE(os.stat(key_path).st_mode)
    if sys.platform != "win32":
        assert mode == 0o600, f"expected 0600, got {oct(mode)}"

    # Key file contents must be Fernet-compatible — sanity check by round-trip.
    token = fernet.encrypt(b"hello")
    assert fernet.decrypt(token) == b"hello"

    # Second call reuses the same key (cached and/or read from disk).
    crypto.reset_cache()
    fernet2 = crypto.get_fernet()
    assert fernet2.decrypt(token) == b"hello"


def test_env_var_beats_file(isolated_crypto, monkeypatch: pytest.MonkeyPatch):
    # Seed a different key on disk first.
    disk_key = Fernet.generate_key()
    (Path(isolated_crypto) / ".secret_key").write_bytes(disk_key)

    env_key = Fernet.generate_key()
    monkeypatch.setenv("GOL_SECRET_KEY", env_key.decode("ascii"))
    crypto.reset_cache()

    fernet = crypto.get_fernet()
    env_fernet = Fernet(env_key)
    disk_fernet = Fernet(disk_key)

    token = fernet.encrypt(b"secret")
    assert env_fernet.decrypt(token) == b"secret"

    with pytest.raises(Exception):  # InvalidToken — disk key must not decrypt env-encrypted data
        disk_fernet.decrypt(token)
