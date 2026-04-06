"""
Tests for compliance_shield.encryption
"""

import pytest
from unittest.mock import patch


MOCK_SETTINGS = {
    'ENCRYPTION_KEY_IN':    None,
    'ENCRYPTION_KEY_OTHER': None,
    'BLIND_INDEX_SECRET_IN':    None,
    'BLIND_INDEX_SECRET_OTHER': None,
}


@pytest.fixture(autouse=True)
def fresh_encryption():
    """Reset encryption cache between tests."""
    from compliance_shield.encryption import RegionalEncryption
    RegionalEncryption.invalidate_cache()
    yield
    RegionalEncryption.invalidate_cache()


@pytest.fixture
def fernet_key():
    from cryptography.fernet import Fernet
    return Fernet.generate_key().decode()


@pytest.fixture
def blind_secret():
    import secrets
    return secrets.token_hex(32)


def test_encrypt_decrypt_roundtrip(fernet_key, blind_secret):
    from compliance_shield.encryption import RegionalEncryption
    from compliance_shield.conf import cs_settings

    with patch.object(cs_settings, 'ENCRYPTION_KEY_IN', fernet_key), \
         patch.object(cs_settings, 'ENCRYPTION_KEY_OTHER', fernet_key), \
         patch.object(cs_settings, 'BLIND_INDEX_SECRET_IN', blind_secret), \
         patch.object(cs_settings, 'BLIND_INDEX_SECRET_OTHER', blind_secret):

        RegionalEncryption.invalidate_cache()

        original  = 'ABCDE1234F'
        encrypted = RegionalEncryption.encrypt(original, 'IN')
        decrypted = RegionalEncryption.decrypt(encrypted, 'IN')

        assert encrypted != original
        assert encrypted.startswith('gAAAAA')
        assert decrypted == original


def test_encrypt_none_returns_none(fernet_key):
    from compliance_shield.encryption import RegionalEncryption
    from compliance_shield.conf import cs_settings

    with patch.object(cs_settings, 'ENCRYPTION_KEY_OTHER', fernet_key):
        RegionalEncryption.invalidate_cache()
        assert RegionalEncryption.encrypt(None, 'IN') is None
        assert RegionalEncryption.encrypt('', 'IN') is None


def test_decrypt_none_returns_none(fernet_key):
    from compliance_shield.encryption import RegionalEncryption
    from compliance_shield.conf import cs_settings

    with patch.object(cs_settings, 'ENCRYPTION_KEY_OTHER', fernet_key):
        RegionalEncryption.invalidate_cache()
        assert RegionalEncryption.decrypt(None, 'IN') is None
        assert RegionalEncryption.decrypt('', 'IN') is None


def test_blind_index_is_deterministic(fernet_key, blind_secret):
    from compliance_shield.encryption import RegionalEncryption
    from compliance_shield.conf import cs_settings

    with patch.object(cs_settings, 'ENCRYPTION_KEY_OTHER', fernet_key), \
         patch.object(cs_settings, 'BLIND_INDEX_SECRET_IN', blind_secret), \
         patch.object(cs_settings, 'BLIND_INDEX_SECRET_OTHER', blind_secret):

        idx1 = RegionalEncryption.make_blind_index('ABCDE1234F', 'IN')
        idx2 = RegionalEncryption.make_blind_index('abcde1234f', 'IN')
        idx3 = RegionalEncryption.make_blind_index('ABCDE1234F', 'IN')

        assert idx1 == idx2  # case-insensitive
        assert idx1 == idx3  # deterministic
        assert len(idx1) == 64  # SHA256 hex


def test_blind_index_differs_by_region(fernet_key, blind_secret):
    import secrets as _secrets
    from compliance_shield.encryption import RegionalEncryption
    from compliance_shield.conf import cs_settings

    secret_us = _secrets.token_hex(32)

    with patch.object(cs_settings, 'ENCRYPTION_KEY_OTHER', fernet_key), \
         patch.object(cs_settings, 'BLIND_INDEX_SECRET_IN', blind_secret), \
         patch.object(cs_settings, 'BLIND_INDEX_SECRET_US', secret_us), \
         patch.object(cs_settings, 'BLIND_INDEX_SECRET_OTHER', blind_secret):

        idx_in = RegionalEncryption.make_blind_index('TEST', 'IN')
        idx_us = RegionalEncryption.make_blind_index('TEST', 'US')
        assert idx_in != idx_us


def test_is_encrypted(fernet_key, blind_secret):
    from compliance_shield.encryption import RegionalEncryption
    from compliance_shield.conf import cs_settings

    with patch.object(cs_settings, 'ENCRYPTION_KEY_IN', fernet_key), \
         patch.object(cs_settings, 'ENCRYPTION_KEY_OTHER', fernet_key), \
         patch.object(cs_settings, 'BLIND_INDEX_SECRET_OTHER', blind_secret):

        RegionalEncryption.invalidate_cache()
        enc = RegionalEncryption.encrypt('HELLO', 'IN')

        assert RegionalEncryption.is_encrypted(enc) is True
        assert RegionalEncryption.is_encrypted('HELLO') is False
        assert RegionalEncryption.is_encrypted(None) is False


def test_unknown_region_falls_back_to_other(fernet_key, blind_secret):
    from compliance_shield.encryption import RegionalEncryption
    from compliance_shield.conf import cs_settings

    with patch.object(cs_settings, 'ENCRYPTION_KEY_OTHER', fernet_key), \
         patch.object(cs_settings, 'BLIND_INDEX_SECRET_OTHER', blind_secret):

        RegionalEncryption.invalidate_cache()
        enc = RegionalEncryption.encrypt('TEST', 'MARS')  # unknown region
        dec = RegionalEncryption.decrypt(enc, 'MARS')
        assert dec == 'TEST'
