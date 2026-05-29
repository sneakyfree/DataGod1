"""
Tests for PII Field-Level Encryption (Gap P5)
"""

import os

import pytest

from datagod.security.encryption import (
    FieldEncryptor,
    decrypt_field,
    encrypt_field,
    get_encryptor,
)


class TestFieldEncryptor:
    """Test the FieldEncryptor class."""

    def setup_method(self):
        # Generate a fresh key for testing
        from cryptography.fernet import Fernet

        self.test_key = Fernet.generate_key().decode()
        self.encryptor = FieldEncryptor(key=self.test_key)

    def test_encrypt_decrypt_roundtrip(self):
        original = "John Doe"
        encrypted = self.encryptor.encrypt(original)
        assert encrypted != original
        decrypted = self.encryptor.decrypt(encrypted)
        assert decrypted == original

    def test_encrypt_produces_different_ciphertext(self):
        """Fernet uses random IV, so same plaintext → different ciphertext."""
        text = "sensitive_data"
        e1 = self.encryptor.encrypt(text)
        e2 = self.encryptor.encrypt(text)
        assert e1 != e2  # Different IVs

    def test_decrypt_invalid_token_raises(self):
        with pytest.raises(Exception):
            self.encryptor.decrypt("not_a_valid_token")

    def test_encrypt_empty_string(self):
        encrypted = self.encryptor.encrypt("")
        decrypted = self.encryptor.decrypt(encrypted)
        assert decrypted == ""

    def test_encrypt_unicode(self):
        original = "名前：太郎"
        encrypted = self.encryptor.encrypt(original)
        decrypted = self.encryptor.decrypt(encrypted)
        assert decrypted == original

    def test_encrypt_long_string(self):
        original = "A" * 10000
        encrypted = self.encryptor.encrypt(original)
        decrypted = self.encryptor.decrypt(encrypted)
        assert decrypted == original


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    def setup_method(self):
        from cryptography.fernet import Fernet

        os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

    def teardown_method(self):
        os.environ.pop("ENCRYPTION_KEY", None)

    def test_encrypt_field_roundtrip(self):
        original = "555-12-3456"
        encrypted = encrypt_field(original)
        assert encrypted != original
        decrypted = decrypt_field(encrypted)
        assert decrypted == original

    def test_get_encryptor_returns_instance(self):
        enc = get_encryptor()
        assert isinstance(enc, FieldEncryptor)

    def test_get_encryptor_singleton(self):
        """Same key should return same-quality encryptor."""
        enc1 = get_encryptor()
        enc2 = get_encryptor()
        # Both should work on same data
        ct = enc1.encrypt("test")
        pt = enc2.decrypt(ct)
        assert pt == "test"
