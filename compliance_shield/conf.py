"""
Settings wrapper for django-compliance-shield.

All settings are namespaced under COMPLIANCE_SHIELD in Django settings.py.

Full example
------------
COMPLIANCE_SHIELD = {

    # ── Encryption keys (one per region) ──────────────────────────────────
    # Generate: python manage.py shell -c
    #   "from compliance_shield.encryption import generate_key; generate_key()"
    'ENCRYPTION_KEY_IN':    env('ENCRYPTION_KEY_IN'),
    'ENCRYPTION_KEY_US':    env('ENCRYPTION_KEY_US'),
    'ENCRYPTION_KEY_EU':    env('ENCRYPTION_KEY_EU'),
    'ENCRYPTION_KEY_UK':    env('ENCRYPTION_KEY_UK'),
    'ENCRYPTION_KEY_CA':    env('ENCRYPTION_KEY_CA'),
    'ENCRYPTION_KEY_AU':    env('ENCRYPTION_KEY_AU'),
    'ENCRYPTION_KEY_AE':    env('ENCRYPTION_KEY_AE'),
    'ENCRYPTION_KEY_SA':    env('ENCRYPTION_KEY_SA'),
    'ENCRYPTION_KEY_OTHER': env('ENCRYPTION_KEY_OTHER'),  # required fallback

    # ── Blind index secrets (one per region, different from encryption keys) ──
    # Generate: python -c "import secrets; print(secrets.token_hex(32))"
    'BLIND_INDEX_SECRET_IN':    env('BLIND_INDEX_SECRET_IN'),
    'BLIND_INDEX_SECRET_US':    env('BLIND_INDEX_SECRET_US'),
    'BLIND_INDEX_SECRET_EU':    env('BLIND_INDEX_SECRET_EU'),
    'BLIND_INDEX_SECRET_OTHER': env('BLIND_INDEX_SECRET_OTHER'),  # required fallback

    # ── Policy ────────────────────────────────────────────────────────────
    # Bump when privacy policy changes — prompts existing users to re-consent
    'PRIVACY_POLICY_VERSION': 'v1.0.0',

    # Field on user profile model storing region code (e.g. 'IN', 'US')
    'JURISDICTION_FIELD': 'data_region',

    # Fallback jurisdiction when none can be detected
    'DEFAULT_JURISDICTION': 'IN',

    # Consent types required before platform access
    'REQUIRED_CONSENTS': ['data_collection', 'data_processing'],

    # Additional URL paths exempt from consent gate
    'CONSENT_EXEMPT_PATHS': [],

    # Add privacy and security headers to every response
    'ADD_SECURITY_HEADERS': True,

    # Log every read of a sensitive encrypted field to SensitiveDataAccessLog
    'LOG_SENSITIVE_ACCESS': True,

    # ── Jurisdiction control ──────────────────────────────────────────────
    # Restrict compliance enforcement to specific jurisdictions.
    # None (default) = all jurisdictions active.
    # When set, only these jurisdictions:
    #   - have retention policies seeded by compliance_setup
    #   - trigger the consent gate in middleware
    #   - show jurisdiction-specific DSR types in the privacy settings page
    # Example: activate only India and US
    'ENABLED_JURISDICTIONS': ['IN', 'US'],   # or None for all

    # ── Email notifications ───────────────────────────────────────────────
    # Master on/off switch. Default is False (silent mode).
    'EMAIL_NOTIFICATIONS': True,

    # From address for all compliance emails
    # Defaults to Django's DEFAULT_FROM_EMAIL if not set
    'EMAIL_FROM': 'compliance@yourcompany.com',

    # Privacy team — notified when a user submits a new DSR
    'DSR_ALERT_RECIPIENTS': [
        'privacy@yourcompany.com',
    ],

    # DPO and legal — notified immediately when a new breach is recorded
    'BREACH_ALERT_RECIPIENTS': [
        'dpo@yourcompany.com',
        'legal@yourcompany.com',
    ],

    # Privacy team — receives daily digest of overdue DSRs (from cron)
    'OVERDUE_DSR_RECIPIENTS': [
        'privacy@yourcompany.com',
    ],

    # Send confirmation email to the user when they submit a DSR
    # Also sends completion and rejection emails when staff action the request
    'DSR_USER_CONFIRMATION_EMAIL': True,
}
"""

from django.conf import settings


DEFAULTS = {
    'ENCRYPTION_KEY_IN':    None,
    'ENCRYPTION_KEY_US':    None,
    'ENCRYPTION_KEY_EU':    None,
    'ENCRYPTION_KEY_UK':    None,
    'ENCRYPTION_KEY_CA':    None,
    'ENCRYPTION_KEY_AU':    None,
    'ENCRYPTION_KEY_AE':    None,
    'ENCRYPTION_KEY_SA':    None,
    'ENCRYPTION_KEY_OTHER': None,

    'BLIND_INDEX_SECRET_IN':    None,
    'BLIND_INDEX_SECRET_US':    None,
    'BLIND_INDEX_SECRET_EU':    None,
    'BLIND_INDEX_SECRET_UK':    None,
    'BLIND_INDEX_SECRET_CA':    None,
    'BLIND_INDEX_SECRET_AU':    None,
    'BLIND_INDEX_SECRET_AE':    None,
    'BLIND_INDEX_SECRET_SA':    None,
    'BLIND_INDEX_SECRET_OTHER': None,

    'PRIVACY_POLICY_VERSION': 'v1.0.0',
    'JURISDICTION_FIELD':     'data_region',
    'DEFAULT_JURISDICTION':   'IN',
    'REQUIRED_CONSENTS':      ['data_collection', 'data_processing'],
    'CONSENT_EXEMPT_PATHS':   [],
    'ADD_SECURITY_HEADERS':   True,
    'LOG_SENSITIVE_ACCESS':   True,

    # ── Jurisdiction control ───────────────────────────────────────────────
    # List of jurisdiction codes to activate. None means all supported.
    # Controls: retention policies seeded, DSR types shown, consent gate,
    # middleware enforcement, and breach deadline tracking.
    # Example: ['IN', 'US', 'EU']
    'ENABLED_JURISDICTIONS': None,

    # ── Email notifications ────────────────────────────────────────────────
    # Master switch for all compliance email notifications
    'EMAIL_NOTIFICATIONS': False,

    # Recipients for DSR submitted alerts (privacy team)
    'DSR_ALERT_RECIPIENTS': [],

    # Recipients for breach discovered alerts (DPO, legal)
    'BREACH_ALERT_RECIPIENTS': [],

    # Recipients for overdue DSR daily digest
    'OVERDUE_DSR_RECIPIENTS': [],

    # From address for compliance emails (falls back to DEFAULT_FROM_EMAIL)
    'EMAIL_FROM': None,

    # Send confirmation email to the user who submitted a DSR
    'DSR_USER_CONFIRMATION_EMAIL': True,
}


class ComplianceShieldSettings:
    """
    Lazy settings object. Access any setting via cs_settings.KEY.
    Falls back to DEFAULTS if not set by the developer.
    """

    def __init__(self, user_settings=None, defaults=None):
        self._defaults      = defaults or DEFAULTS
        self._user_settings = user_settings

    @property
    def user_settings(self):
        if self._user_settings is None:
            self._user_settings = getattr(settings, 'COMPLIANCE_SHIELD', {})
        return self._user_settings

    def __getattr__(self, attr):
        if attr not in self._defaults:
            raise AttributeError(f'Invalid ComplianceShield setting: {attr!r}')
        val = self.user_settings.get(attr, self._defaults[attr])
        setattr(self, attr, val)
        return val

    def reload(self):
        self._user_settings = None
        for key in self._defaults:
            try:
                delattr(self, key)
            except AttributeError:
                pass


cs_settings = ComplianceShieldSettings()


def is_jurisdiction_enabled(jurisdiction):
    """
    Returns True if the given jurisdiction is active.
    If ENABLED_JURISDICTIONS is None (default), all are active.

    Usage:
        from compliance_shield.conf import is_jurisdiction_enabled
        if is_jurisdiction_enabled('US'):
            # show FCRA-specific options
    """
    enabled = cs_settings.ENABLED_JURISDICTIONS
    if enabled is None:
        return True
    return jurisdiction in enabled


def get_email_from():
    """Returns the configured FROM address for compliance emails."""
    from django.conf import settings as django_settings
    return cs_settings.EMAIL_FROM or getattr(
        django_settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'
    )
