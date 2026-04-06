"""
Shared utility functions for django-compliance-shield.
"""


def get_client_ip(request):
    """Extract real client IP respecting X-Forwarded-For."""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def mask_value(value, keep_last=4, mask_char='*'):
    """
    Mask a string keeping only the last N characters.

    mask_value('ABCDE1234F', keep_last=4)  → '******234F'
    mask_value('123-45-6789', keep_last=4) → '*******6789'
    """
    if not value:
        return None
    value = str(value)
    if len(value) <= keep_last:
        return value
    return mask_char * (len(value) - keep_last) + value[-keep_last:]


def detect_jurisdiction_from_country(country_name):
    """
    Map a country name string to a jurisdiction code.
    Returns 'OTHER' if not recognised.
    """
    from compliance_shield.middleware import COUNTRY_TO_JURISDICTION
    if not country_name:
        return 'OTHER'
    return COUNTRY_TO_JURISDICTION.get(country_name.strip().lower(), 'OTHER')


def record_registration_consents(user, request, jurisdiction='IN',
                                  consent_texts=None, version=None):
    """
    Convenience function to record mandatory consents at registration.

    Call this in your registration view after creating the user:

        from compliance_shield.utils import record_registration_consents
        record_registration_consents(user, request, jurisdiction='IN')

    Parameters
    ----------
    user        : Django User instance
    request     : Django HttpRequest
    jurisdiction: str  (default 'IN')
    consent_texts: dict mapping consent_type -> text (optional override)
    version     : str  privacy policy version (optional, uses settings default)
    """
    from compliance_shield.models.consent import ConsentRecord
    from compliance_shield.conf import cs_settings
    from compliance_shield.views.consent import CONSENT_TEXTS

    texts   = consent_texts or CONSENT_TEXTS
    ver     = version or cs_settings.PRIVACY_POLICY_VERSION

    for consent_type in cs_settings.REQUIRED_CONSENTS:
        text = texts.get(consent_type, f'I consent to {consent_type.replace("_", " ")}.')
        ConsentRecord.record_consent(
            user         = user,
            consent_type = consent_type,
            jurisdiction = jurisdiction,
            consent_text = text,
            request      = request,
            version      = ver,
            granted      = True,
        )
