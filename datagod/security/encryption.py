"""
Field-Level Encryption (DNA Strand Gene 2.5)

Provides Fernet symmetric encryption for PII fields at rest.
"""

import logging
import os
import base64
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class FieldEncryptor:
    """
    Encrypts and decrypts sensitive field values using Fernet (AES-128-CBC).

    Key management:
    - ENCRYPTION_KEY env var holds the base64-encoded 32-byte key
    - If not set, generates an ephemeral key (dev mode only, logs warning)
    """

    def __init__(self, key: Optional[str] = None):
        raw_key = key or os.getenv("ENCRYPTION_KEY")
        if raw_key:
            # Ensure proper Fernet key format (url-safe base64, 32 bytes)
            try:
                self._fernet = Fernet(raw_key.encode() if isinstance(raw_key, str) else raw_key)
            except Exception:
                # Try treating it as a raw 32-byte key and encode it
                padded = raw_key.ljust(32, "0")[:32]
                key_bytes = base64.urlsafe_b64encode(padded.encode())
                self._fernet = Fernet(key_bytes)
            self._ephemeral = False
        else:
            logger.warning(
                "ENCRYPTION_KEY not set. Using ephemeral key — "
                "encrypted data will NOT survive restarts. Set ENCRYPTION_KEY for production."
            )
            self._fernet = Fernet(Fernet.generate_key())
            self._ephemeral = True

    @property
    def is_ephemeral(self) -> bool:
        """True if using a generated (non-persistent) key."""
        return self._ephemeral

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string value.

        Returns:
            Base64-encoded ciphertext string (safe for DB storage)
        """
        if not plaintext:
            return plaintext
        token = self._fernet.encrypt(plaintext.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a previously encrypted value.

        Returns:
            Original plaintext string

        Raises:
            ValueError: If decryption fails (wrong key or corrupted data)
        """
        if not ciphertext:
            return ciphertext
        try:
            plaintext = self._fernet.decrypt(ciphertext.encode("utf-8"))
            return plaintext.decode("utf-8")
        except InvalidToken:
            raise ValueError(
                "Decryption failed — wrong key or corrupted ciphertext. "
                "Ensure ENCRYPTION_KEY matches the key used for encryption."
            )

    def rotate_key(self, old_ciphertext: str, new_encryptor: "FieldEncryptor") -> str:
        """
        Re-encrypt a value with a new key.

        Args:
            old_ciphertext: Value encrypted with this encryptor's key
            new_encryptor: Encryptor initialized with the new key

        Returns:
            Value encrypted with the new key
        """
        plaintext = self.decrypt(old_ciphertext)
        return new_encryptor.encrypt(plaintext)

    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet key suitable for ENCRYPTION_KEY env var."""
        return Fernet.generate_key().decode("utf-8")


# Module-level default instance
_default_encryptor: Optional[FieldEncryptor] = None


def get_encryptor() -> FieldEncryptor:
    """Get or create the default field encryptor."""
    global _default_encryptor
    if _default_encryptor is None:
        _default_encryptor = FieldEncryptor()
    return _default_encryptor


def encrypt_field(value: str) -> str:
    """Convenience function to encrypt a field value."""
    return get_encryptor().encrypt(value)


def decrypt_field(value: str) -> str:
    """Convenience function to decrypt a field value."""
    return get_encryptor().decrypt(value)
