"""Cryptographic storage engine and key derivation for the Sovereign Vault.

Local-first, air-gapped cryptographic utilities:
- PBKDF2-HMAC-SHA256 key derivation from Owner PIN and random device salt.
- AES-256-GCM authenticated encryption for database-at-rest protection.
- Zero cloud telemetry, zero remote network calls.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Optional, Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag


class VaultLockedError(Exception):
    """Raised when sovereign vault data is accessed while the vault is locked."""
    pass


class VaultDecryptionError(Exception):
    """Raised when vault ciphertext cannot be decrypted or authenticated."""
    pass


class VaultCrypto:
    """Cryptographic operations for the sovereign vault."""

    DEFAULT_ITERATIONS: int = 100_000
    SALT_SIZE: int = 16
    NONCE_SIZE: int = 12
    KEY_SIZE: int = 32  # 256 bits
    MAGIC_HEADER: bytes = b"SOV_VAULT_V1\x00"  # 12 bytes
    DEFAULT_OWNER_PIN: str = "0000"

    @classmethod
    def get_configured_pin(cls) -> str:
        """Return the active owner PIN from environment or default."""
        return os.environ.get("COPILOT_OWNER_PIN", cls.DEFAULT_OWNER_PIN)

    @classmethod
    def generate_salt(cls, length: int = SALT_SIZE) -> bytes:
        """Generate cryptographically secure random salt."""
        return os.urandom(length)

    @classmethod
    def generate_nonce(cls, length: int = NONCE_SIZE) -> bytes:
        """Generate cryptographically secure random nonce for AES-GCM."""
        return os.urandom(length)

    @classmethod
    def derive_key(
        cls,
        pin: str,
        salt: bytes,
        iterations: int = DEFAULT_ITERATIONS,
    ) -> bytes:
        """Derive 256-bit AES key from Owner PIN and device salt via PBKDF2-HMAC-SHA256."""
        if not pin:
            raise ValueError("Owner PIN cannot be empty")
        if not salt or len(salt) < 8:
            raise ValueError("Salt must be at least 8 bytes")
        return hashlib.pbkdf2_hmac(
            hash_name="sha256",
            password=pin.encode("utf-8"),
            salt=salt,
            iterations=iterations,
            dklen=cls.KEY_SIZE,
        )

    @classmethod
    def encrypt(
        cls,
        data: bytes,
        key: bytes,
        salt: Optional[bytes] = None,
    ) -> bytes:
        """Encrypt plaintext bytes with AES-256-GCM and pack into envelope.

        Envelope layout:
        [MAGIC_HEADER: 12 bytes] + [SALT: 16 bytes] + [NONCE: 12 bytes] + [CIPHERTEXT + 16-byte TAG]
        """
        if salt is None:
            salt = cls.generate_salt()
        nonce = cls.generate_nonce()
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        return cls.MAGIC_HEADER + salt + nonce + ciphertext

    @classmethod
    def decrypt(
        cls,
        envelope: bytes,
        key: Optional[bytes] = None,
        pin: Optional[str] = None,
    ) -> Tuple[bytes, bytes]:
        """Decrypt payload from envelope using provided key or pin.

        Returns (plaintext_bytes, salt).
        Raises VaultDecryptionError if header is invalid or authentication tag check fails.
        """
        header_len = len(cls.MAGIC_HEADER)
        min_len = header_len + cls.SALT_SIZE + cls.NONCE_SIZE + 16
        if len(envelope) < min_len:
            raise VaultDecryptionError("Envelope payload is too short or malformed")

        magic = envelope[:header_len]
        if magic != cls.MAGIC_HEADER:
            raise VaultDecryptionError("Unrecognized vault envelope header")

        salt_start = header_len
        salt_end = salt_start + cls.SALT_SIZE
        salt = envelope[salt_start:salt_end]

        nonce_start = salt_end
        nonce_end = nonce_start + cls.NONCE_SIZE
        nonce = envelope[nonce_start:nonce_end]
        ciphertext = envelope[nonce_end:]

        if key is None:
            if pin is None:
                raise ValueError("Either key or pin must be provided for decryption")
            key = cls.derive_key(pin, salt)

        try:
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext, salt
        except InvalidTag as e:
            raise VaultDecryptionError("Authentication failed: invalid PIN or corrupted vault payload") from e
        except Exception as e:
            raise VaultDecryptionError(f"Decryption failed: {e}") from e

    @classmethod
    def verify_pin(cls, envelope: bytes, pin: str) -> bool:
        """Check whether the provided PIN successfully decrypts the envelope."""
        try:
            cls.decrypt(envelope, pin=pin)
            return True
        except Exception:
            return False

    @classmethod
    def encrypt_to_file(
        cls,
        data: bytes,
        pin: str,
        dest_path: Path | str,
        salt: Optional[bytes] = None,
    ) -> None:
        """Encrypt data and atomically write to file with mode 0600."""
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        if salt is None:
            salt = cls.generate_salt()
        key = cls.derive_key(pin, salt)
        envelope = cls.encrypt(data, key=key, salt=salt)

        tmp_dest = dest.with_suffix(f"{dest.suffix}.tmp.{os.getpid()}")
        try:
            fd = os.open(str(tmp_dest), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(envelope)
            os.replace(str(tmp_dest), str(dest))
        except Exception:
            if tmp_dest.exists():
                try:
                    tmp_dest.unlink()
                except OSError:
                    pass
            raise

    @classmethod
    def decrypt_from_file(cls, source_path: Path | str, pin: str) -> bytes:
        """Read encrypted envelope from file and decrypt using pin."""
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Vault database file not found: {source}")
        payload = source.read_bytes()
        plaintext, _ = cls.decrypt(payload, pin=pin)
        return plaintext
