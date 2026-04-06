"""
Django system checks for django-compliance-shield.
Run automatically when Django starts. Warns developers of
missing configuration before they hit runtime errors.
"""

from django.core.checks import Warning, Error, register


@register()
def check_encryption_keys(app_configs, **kwargs):
    errors = []
    try:
        from compliance_shield.conf import cs_settings

        if not cs_settings.ENCRYPTION_KEY_OTHER:
            errors.append(
                Warning(
                    'COMPLIANCE_SHIELD: ENCRYPTION_KEY_OTHER is not set. '
                    'This is the fallback key used when a region-specific key '
                    'is missing. Set it in your COMPLIANCE_SHIELD settings.',
                    hint='Generate a key: python manage.py shell -c '
                         '"from compliance_shield.encryption import generate_key; generate_key()"',
                    id='compliance_shield.W001',
                )
            )

        if not cs_settings.BLIND_INDEX_SECRET_OTHER:
            errors.append(
                Warning(
                    'COMPLIANCE_SHIELD: BLIND_INDEX_SECRET_OTHER is not set. '
                    'Blind index search will fail for regions without a specific secret.',
                    hint='Generate a secret: python -c "import secrets; print(secrets.token_hex(32))"',
                    id='compliance_shield.W002',
                )
            )

    except Exception as e:
        errors.append(
            Error(
                f'COMPLIANCE_SHIELD: Could not load settings — {e}',
                id='compliance_shield.E001',
            )
        )

    return errors


@register()
def check_middleware(app_configs, **kwargs):
    errors = []
    try:
        from django.conf import settings
        middleware = getattr(settings, 'MIDDLEWARE', [])
        if 'compliance_shield.middleware.ComplianceMiddleware' not in middleware:
            errors.append(
                Warning(
                    'COMPLIANCE_SHIELD: ComplianceMiddleware is not in MIDDLEWARE. '
                    'Jurisdiction detection, consent gating, and security headers '
                    'will not be active.',
                    hint="Add 'compliance_shield.middleware.ComplianceMiddleware' "
                         "to MIDDLEWARE after AuthenticationMiddleware.",
                    id='compliance_shield.W003',
                )
            )
    except Exception:
        pass
    return errors


@register()
def check_required_consents(app_configs, **kwargs):
    errors = []
    try:
        from compliance_shield.conf import cs_settings
        required = cs_settings.REQUIRED_CONSENTS
        if not required:
            errors.append(
                Warning(
                    'COMPLIANCE_SHIELD: REQUIRED_CONSENTS is empty. '
                    'No consent will be required before platform access.',
                    hint="Set REQUIRED_CONSENTS = ['data_collection', 'data_processing'] "
                         "in your COMPLIANCE_SHIELD settings.",
                    id='compliance_shield.W004',
                )
            )
    except Exception:
        pass
    return errors
