# Configuration Reference

All settings are namespaced under `COMPLIANCE_SHIELD` in your Django `settings.py`.

## Full settings reference

```python
COMPLIANCE_SHIELD = {

    # ── Encryption keys ─────────────────────────────────────────────────
    # Generate with: python manage.py shell -c
    #   "from compliance_shield.encryption import generate_key; generate_key()"
    # Store in .env — never commit to version control.

    'ENCRYPTION_KEY_IN':    None,  # India
    'ENCRYPTION_KEY_US':    None,  # United States
    'ENCRYPTION_KEY_EU':    None,  # European Union
    'ENCRYPTION_KEY_UK':    None,  # United Kingdom
    'ENCRYPTION_KEY_CA':    None,  # Canada
    'ENCRYPTION_KEY_AU':    None,  # Australia
    'ENCRYPTION_KEY_AE':    None,  # UAE
    'ENCRYPTION_KEY_SA':    None,  # Saudi Arabia
    'ENCRYPTION_KEY_OTHER': None,  # Fallback for all other regions (required)

    # ── Blind index secrets ──────────────────────────────────────────────
    # Different from encryption keys. Used for searchable blind indexes.
    # Generate with: python -c "import secrets; print(secrets.token_hex(32))"

    'BLIND_INDEX_SECRET_IN':    None,
    'BLIND_INDEX_SECRET_US':    None,
    'BLIND_INDEX_SECRET_EU':    None,
    'BLIND_INDEX_SECRET_UK':    None,
    'BLIND_INDEX_SECRET_CA':    None,
    'BLIND_INDEX_SECRET_AU':    None,
    'BLIND_INDEX_SECRET_AE':    None,
    'BLIND_INDEX_SECRET_SA':    None,
    'BLIND_INDEX_SECRET_OTHER': None,  # Fallback (required)

    # ── Policy settings ──────────────────────────────────────────────────

    # Bump this when your privacy policy changes.
    # Existing users will be prompted to re-consent on next login.
    'PRIVACY_POLICY_VERSION': 'v1.0.0',

    # Field on the user profile model that stores the data region code
    # e.g. 'IN', 'US', 'EU'. The middleware reads and writes this field.
    'JURISDICTION_FIELD': 'data_region',

    # Fallback jurisdiction when none can be detected
    'DEFAULT_JURISDICTION': 'IN',

    # Consent types that must be granted before platform access is allowed.
    # The middleware will redirect to /compliance/consent/ if any are missing.
    'REQUIRED_CONSENTS': ['data_collection', 'data_processing'],

    # Additional URL paths to exempt from the consent gate.
    # /admin/, /static/, /media/, and /compliance/ are always exempt.
    'CONSENT_EXEMPT_PATHS': [],

    # Whether to add security and privacy headers to every response.
    # Headers added: X-Data-Region, X-Privacy-Policy-Version,
    # X-Frame-Options, X-Content-Type-Options, Referrer-Policy,
    # Permissions-Policy, Strict-Transport-Security (HTTPS only).
    'ADD_SECURITY_HEADERS': True,

    # Whether to log every read of a sensitive field to SensitiveDataAccessLog.
    # Required for DPDP Section 8, GDPR Article 30, and FCRA audit trails.
    'LOG_SENSITIVE_ACCESS': True,
}
```

## Key rotation

When rotating encryption keys:

1. Generate a new key for the region
2. Update your `.env` file with the new key
3. Run the rotation command to re-encrypt all records:

```bash
python manage.py rotate_keys \
  --model myapp.UserProfile \
  --field pan_number \
  --old-region IN \
  --new-region IN
```

Always run with `--dry-run` first:

```bash
python manage.py rotate_keys --model myapp.UserProfile --field pan_number --dry-run
```

## Overriding templates

All three templates can be overridden by creating files at these paths
in your project's `templates/` directory:

```
templates/
  compliance_shield/
    consent.html          # Override consent page
    privacy_settings.html # Override privacy dashboard
    dsr_confirm.html      # Override DSR confirmation page
```

The context variables available in each template are documented
in the respective view docstrings.
