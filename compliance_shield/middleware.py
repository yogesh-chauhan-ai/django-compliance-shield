"""
ComplianceMiddleware for django-compliance-shield.

Automatically:
1. Detects user jurisdiction on every request
2. Syncs data_region to user profile
3. Gates access if required consents are missing
4. Adds privacy and security headers to every response
"""

from django.http import JsonResponse
from django.shortcuts import redirect
from compliance_shield.conf import cs_settings, is_jurisdiction_enabled


COUNTRY_TO_JURISDICTION = {
    'india': 'IN',
    'united states': 'US', 'usa': 'US', 'us': 'US',
    'germany': 'EU', 'france': 'EU', 'italy': 'EU', 'spain': 'EU',
    'netherlands': 'EU', 'belgium': 'EU', 'sweden': 'EU', 'poland': 'EU',
    'denmark': 'EU', 'finland': 'EU', 'austria': 'EU', 'portugal': 'EU',
    'ireland': 'EU', 'greece': 'EU', 'czechia': 'EU', 'romania': 'EU',
    'hungary': 'EU', 'slovakia': 'EU', 'croatia': 'EU', 'bulgaria': 'EU',
    'united kingdom': 'UK', 'uk': 'UK',
    'canada': 'CA',
    'australia': 'AU',
    'uae': 'AE', 'united arab emirates': 'AE',
    'saudi arabia': 'SA', 'ksa': 'SA',
    'singapore': 'OTHER', 'japan': 'OTHER', 'south korea': 'OTHER',
}

DEFAULT_EXEMPT_PATHS = {
    '/admin/',
    '/static/',
    '/media/',
    '/compliance/consent/',
    '/compliance/privacy/',
    '/compliance/dsr/',
}


class ComplianceMiddleware:
    """
    Drop-in compliance middleware. Add to MIDDLEWARE after AuthenticationMiddleware:

        MIDDLEWARE = [
            ...
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'compliance_shield.middleware.ComplianceMiddleware',
            ...
        ]
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # Step 1: Detect jurisdiction
        request.jurisdiction = self._detect_jurisdiction(request)

        # Step 2: Sync data_region to profile
        if request.user.is_authenticated:
            self._sync_data_region(request)

        # Step 3: Consent gate
        if self._requires_consent_check(request):
            missing = self._get_missing_consents(request)
            if missing:
                return self._handle_missing_consent(request, missing)

        # Step 4: Process
        response = self.get_response(request)

        # Step 5: Compliance headers
        if cs_settings.ADD_SECURITY_HEADERS:
            self._add_headers(request, response)

        return response

    def _detect_jurisdiction(self, request):
        if request.user.is_authenticated:
            jurisdiction_field = cs_settings.JURISDICTION_FIELD
            for profile_attr in ('employeeprofile', 'userprofile', 'profile'):
                try:
                    profile = getattr(request.user, profile_attr, None)
                    if profile:
                        region = getattr(profile, jurisdiction_field, None)
                        if region:
                            return region
                except Exception:
                    pass

        session_region = request.session.get('cs_data_region')
        if session_region:
            return session_region

        return cs_settings.DEFAULT_JURISDICTION

    def _sync_data_region(self, request):
        if request.session.get('cs_region_synced'):
            return
        try:
            jurisdiction_field = cs_settings.JURISDICTION_FIELD
            for profile_attr in ('employeeprofile', 'userprofile', 'profile'):
                profile = getattr(request.user, profile_attr, None)
                if not profile:
                    continue
                country = getattr(profile, 'country', None)
                if country:
                    jurisdiction = COUNTRY_TO_JURISDICTION.get(
                        country.strip().lower(), 'OTHER'
                    )
                    current = getattr(profile, jurisdiction_field, None)
                    if current != jurisdiction:
                        setattr(profile, jurisdiction_field, jurisdiction)
                        profile.__class__.objects.filter(
                            pk=profile.pk
                        ).update(**{jurisdiction_field: jurisdiction})
                        request.jurisdiction = jurisdiction
                break
            request.session['cs_region_synced'] = True
        except Exception:
            pass

    def _requires_consent_check(self, request):
        if not request.user.is_authenticated:
            return False
        if request.user.is_staff or request.user.is_superuser:
            return False

        # Skip consent gate if this jurisdiction is not enabled
        if not is_jurisdiction_enabled(getattr(request, 'jurisdiction', 'IN')):
            return False

        path         = request.path_info
        exempt_paths = DEFAULT_EXEMPT_PATHS | set(cs_settings.CONSENT_EXEMPT_PATHS)
        for exempt in exempt_paths:
            if path.startswith(exempt):
                return False
        return True

    def _get_missing_consents(self, request):
        try:
            from compliance_shield.models.consent import ConsentRecord
            return [
                ct for ct in cs_settings.REQUIRED_CONSENTS
                if not ConsentRecord.has_valid_consent(
                    request.user, ct, request.jurisdiction
                )
            ]
        except Exception:
            return []

    def _handle_missing_consent(self, request, missing_consents):
        request.session['cs_pending_consents']  = missing_consents
        request.session['cs_consent_redirect']  = request.path

        if self._is_api_request(request):
            return JsonResponse({
                'error':            'consent_required',
                'message':          'Required consent not provided.',
                'missing_consents': missing_consents,
                'consent_url':      '/compliance/consent/',
            }, status=403)

        return redirect(f'/compliance/consent/?next={request.path}')

    def _add_headers(self, request, response):
        response['X-Data-Region']            = request.jurisdiction
        response['X-Privacy-Policy-Version'] = cs_settings.PRIVACY_POLICY_VERSION
        response['X-Content-Type-Options']   = 'nosniff'
        response['X-Frame-Options']          = 'DENY'
        response['Referrer-Policy']          = 'strict-origin-when-cross-origin'
        response['Permissions-Policy']       = (
            'camera=(), microphone=(), geolocation=(), '
            'payment=(), usb=(), interest-cohort=()'
        )
        if request.is_secure():
            response['Strict-Transport-Security'] = (
                'max-age=31536000; includeSubDomains; preload'
            )
        return response

    @staticmethod
    def _is_api_request(request):
        return (
            request.headers.get('Accept') == 'application/json'
            or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            or request.path.startswith('/api/')
        )
