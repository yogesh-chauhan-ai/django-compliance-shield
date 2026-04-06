"""
Regional field-level encryption for django-compliance-shield.

Uses Fernet symmetric encryption with separate keys per jurisdiction.
MultiFernet enables zero-downtime key rotation.
"""

import hmac
import hashlib
from cryptography.fernet import Fernet, MultiFernet

from compliance_shield.conf import cs_settings


SUPPORTED_REGIONS = ['IN', 'US', 'EU', 'UK', 'CA', 'AU', 'AE', 'SA', 'OTHER']


class RegionalEncryption:
    """
    Encrypts and decrypts field values using region-specific Fernet keys.
    Each region has its own key so a breach of one region does not
    compromise another.

    Usage
    -----
        enc = RegionalEncryption.encrypt('ABCDE1234F', 'IN')
        dec = RegionalEncryption.decrypt(enc, 'IN')
        idx = RegionalEncryption.make_blind_index('ABCDE1234F', 'IN')
    """

    _instances = {}

    @classmethod
    def _resolve_region(cls, region):
        if region not in SUPPORTED_REGIONS:
            return 'OTHER'
        return region

    @classmethod
    def _get_fernet(cls, region):
        region = cls._resolve_region(region)

        if region not in cls._instances:
            primary_key  = getattr(cs_settings, f'ENCRYPTION_KEY_{region}', None)
            fallback_key = cs_settings.ENCRYPTION_KEY_OTHER

            if not primary_key and not fallback_key:
                raise ValueError(
                    f'django-compliance-shield: No encryption key found for '
                    f'region {region!r}. Set ENCRYPTION_KEY_{region} (or '
                    f'ENCRYPTION_KEY_OTHER as fallback) in your '
                    f'COMPLIANCE_SHIELD settings.'
                )

            keys = []
            if primary_key:
                keys.append(Fernet(primary_key.encode()
                                   if isinstance(primary_key, str)
                                   else primary_key))
            if fallback_key and fallback_key != primary_key:
                keys.append(Fernet(fallback_key.encode()
                                   if isinstance(fallback_key, str)
                                   else fallback_key))

            cls._instances[region] = MultiFernet(keys)

        return cls._instances[region]

    @classmethod
    def encrypt(cls, value, region='IN'):
        """Encrypt a plaintext string. Returns encrypted string or None."""
        if not value:
            return None
        region = cls._resolve_region(region)
        f = cls._get_fernet(region)
        raw = value.strip() if isinstance(value, str) else str(value)
        return f.encrypt(raw.encode()).decode()

    @classmethod
    def decrypt(cls, encrypted_value, region='IN'):
        """Decrypt an encrypted string. Returns plaintext or None."""
        if not encrypted_value:
            return None
        region = cls._resolve_region(region)
        try:
            f = cls._get_fernet(region)
            return f.decrypt(encrypted_value.encode()).decode()
        except Exception:
            return None

    @classmethod
    def make_blind_index(cls, value, region='IN'):
        """
        Create a one-way HMAC hash for searching encrypted fields.
        Same input always produces the same index regardless of case.

        Use this to search:
            MyModel.objects.filter(pan_index=RegionalEncryption.make_blind_index('ABCDE1234F', 'IN'))
        """
        if not value:
            return None
        region = cls._resolve_region(region)
        secret = getattr(cs_settings, f'BLIND_INDEX_SECRET_{region}', None) \
                 or cs_settings.BLIND_INDEX_SECRET_OTHER

        if not secret:
            raise ValueError(
                f'django-compliance-shield: No blind index secret found for '
                f'region {region!r}. Set BLIND_INDEX_SECRET_{region} (or '
                f'BLIND_INDEX_SECRET_OTHER) in your COMPLIANCE_SHIELD settings.'
            )

        normalised = value.strip().upper() if isinstance(value, str) else str(value)
        return hmac.new(
            secret.encode() if isinstance(secret, str) else secret,
            normalised.encode(),
            hashlib.sha256
        ).hexdigest()

    @classmethod
    def is_encrypted(cls, value):
        """Returns True if the value looks like a Fernet-encrypted string."""
        if not value:
            return False
        return str(value).startswith('gAAAAA')

    @classmethod
    def rotate_key(cls, encrypted_value, region, old_region=None):
        """
        Decrypt with old region key, re-encrypt with new region key.
        Use during key rotation migrations.
        """
        source = old_region or region
        plain  = cls.decrypt(encrypted_value, source)
        if plain:
            # Clear instance cache so new key is loaded
            cls._instances.pop(region, None)
            return cls.encrypt(plain, region)
        return None

    @classmethod
    def invalidate_cache(cls):
        """Force reload of all Fernet instances (call after key rotation)."""
        cls._instances.clear()


def generate_key():
    """
    Generate a new Fernet encryption key.

    Run this once per region and store the output in your settings:
        python manage.py shell -c "from compliance_shield.encryption import generate_key; generate_key()"
    """
    key = Fernet.generate_key().decode()
    print(f'\nGenerated Fernet key:\n{key}')
    print('\nStore this in your COMPLIANCE_SHIELD settings as:')
    print('    ENCRYPTION_KEY_<REGION> = "<key>"')
    print('\nNEVER commit this key to version control.\n')
    return key
