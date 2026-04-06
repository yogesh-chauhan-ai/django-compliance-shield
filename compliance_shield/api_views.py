"""
DRF API views for django-compliance-shield.

Include in your urls.py alongside or instead of the template views:

    from django.urls import path, include
    from compliance_shield.api_views import ComplianceRouter

    urlpatterns = [
        # Template views
        path('compliance/', include('compliance_shield.urls')),

        # DRF API views
        path('api/compliance/', include('compliance_shield.api_urls')),
    ]

Available endpoints:
    GET    /api/compliance/consent/           — Current consent status
    POST   /api/compliance/consent/grant/     — Grant one or more consents
    POST   /api/compliance/consent/withdraw/  — Withdraw a consent
    GET    /api/compliance/dsr/               — List my DSRs
    POST   /api/compliance/dsr/submit/        — Submit a new DSR
    GET    /api/compliance/access-log/        — Sensitive data access log
    GET    /api/compliance/retention/         — View retention policies
    GET    /api/compliance/jurisdiction/      — Current jurisdiction info
"""

try:
    from rest_framework.views      import APIView
    from rest_framework.response   import Response
    from rest_framework            import status
    from rest_framework.permissions import IsAuthenticated, IsAdminUser
except ImportError:
    raise ImportError(
        'djangorestframework is required for compliance_shield.api_views. '
        'Install it with: pip install djangorestframework'
    )

from compliance_shield.models.consent   import ConsentRecord
from compliance_shield.models.dsr       import DataSubjectRequest
from compliance_shield.models.retention import DataRetentionPolicy
from compliance_shield.models.audit     import SensitiveDataAccessLog
from compliance_shield.conf             import cs_settings, is_jurisdiction_enabled
from compliance_shield.serializers      import (
    ConsentStatusSerializer,
    ConsentActionSerializer,
    DataSubjectRequestSerializer,
    SubmitDSRSerializer,
    SensitiveDataAccessLogSerializer,
    DataRetentionPolicySerializer,
)
from compliance_shield.views.consent import CONSENT_TEXTS
from compliance_shield.views.privacy import JURISDICTION_REQUEST_TYPES


class ConsentStatusView(APIView):
    """
    GET /api/compliance/consent/

    Returns current consent status for the authenticated user.
    Response is suitable for building a consent management UI in React/Vue/mobile.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        jurisdiction = getattr(request, 'jurisdiction', 'IN')
        user         = request.user

        consent_status = []
        for consent_type, label in ConsentRecord.CONSENT_TYPES:
            latest = ConsentRecord.objects.filter(
                user         = user,
                consent_type = consent_type,
                jurisdiction = jurisdiction,
            ).order_by('-created_at').first()

            consent_status.append({
                'consent_type': consent_type,
                'label':        label,
                'is_granted':   latest.granted if latest else False,
                'granted_at':   latest.granted_at if latest else None,
                'withdrawn_at': latest.withdrawn_at if latest else None,
                'is_required':  consent_type in cs_settings.REQUIRED_CONSENTS,
                'can_withdraw': consent_type not in cs_settings.REQUIRED_CONSENTS,
                'text':         CONSENT_TEXTS.get(consent_type, ''),
            })

        return Response({
            'jurisdiction':    jurisdiction,
            'privacy_version': cs_settings.PRIVACY_POLICY_VERSION,
            'consents':        consent_status,
        })


class ConsentGrantView(APIView):
    """
    POST /api/compliance/consent/grant/

    Body: { "consent_type": "marketing", "jurisdiction": "IN" }
    or:   { "consent_types": ["marketing", "employer_sharing"], "jurisdiction": "IN" }

    Grants one or more consents for the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        jurisdiction = getattr(request, 'jurisdiction', 'IN')

        # Support both single and multiple consent types
        consent_types = request.data.get('consent_types') or []
        single        = request.data.get('consent_type')
        if single and single not in consent_types:
            consent_types.append(single)

        if not consent_types:
            return Response(
                {'error': 'Provide consent_type or consent_types.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        granted = []
        for consent_type in consent_types:
            text = CONSENT_TEXTS.get(consent_type, f'I consent to {consent_type}.')
            ConsentRecord.record_consent(
                user         = request.user,
                consent_type = consent_type,
                jurisdiction = jurisdiction,
                consent_text = text,
                request      = request,
                version      = cs_settings.PRIVACY_POLICY_VERSION,
                granted      = True,
            )
            granted.append(consent_type)

        return Response({
            'granted':      granted,
            'jurisdiction': jurisdiction,
            'message':      f'{len(granted)} consent(s) recorded successfully.',
        }, status=status.HTTP_201_CREATED)


class ConsentWithdrawView(APIView):
    """
    POST /api/compliance/consent/withdraw/

    Body: { "consent_type": "marketing", "jurisdiction": "IN" }

    Withdraws a consent. Required consents cannot be withdrawn this way.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ConsentActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        consent_type = serializer.validated_data['consent_type']
        jurisdiction = serializer.validated_data.get(
            'jurisdiction', getattr(request, 'jurisdiction', 'IN')
        )

        if consent_type in cs_settings.REQUIRED_CONSENTS:
            return Response(
                {'error': 'Required consents cannot be withdrawn. '
                          'Contact support to delete your account.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ConsentRecord.withdraw_consent(
            user         = request.user,
            consent_type = consent_type,
            jurisdiction = jurisdiction,
            request      = request,
        )

        return Response({
            'withdrawn':    consent_type,
            'jurisdiction': jurisdiction,
            'message':      'Consent withdrawn. A data deletion request has been created.',
        })


class DSRListView(APIView):
    """
    GET /api/compliance/dsr/

    Returns all data subject requests submitted by the authenticated user.
    Includes available request types for their jurisdiction.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        jurisdiction = getattr(request, 'jurisdiction', 'IN')
        dsrs         = DataSubjectRequest.objects.filter(
            user=request.user
        ).order_by('-received_at')[:50]

        available_types = (
            JURISDICTION_REQUEST_TYPES['universal']
            + JURISDICTION_REQUEST_TYPES.get(jurisdiction, [])
        )

        return Response({
            'jurisdiction':    jurisdiction,
            'requests':        DataSubjectRequestSerializer(dsrs, many=True).data,
            'available_types': [
                {'value': v, 'label': l} for v, l in available_types
            ],
        })


class DSRSubmitView(APIView):
    """
    POST /api/compliance/dsr/submit/

    Body:
    {
        "request_type":   "erasure",
        "jurisdiction":   "IN",
        "request_detail": "Please delete all my data."
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        jurisdiction = getattr(request, 'jurisdiction', 'IN')

        # Inject jurisdiction if not provided
        data = request.data.copy()
        if 'jurisdiction' not in data:
            data['jurisdiction'] = jurisdiction

        serializer = SubmitDSRSerializer(
            data=data, context={'request': request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        dsr = DataSubjectRequest.submit(
            user           = request.user,
            request_type   = serializer.validated_data['request_type'],
            jurisdiction   = serializer.validated_data['jurisdiction'],
            request_detail = serializer.validated_data['request_detail'],
            request        = request,
        )

        from compliance_shield.notifications import notify_dsr_submitted
        notify_dsr_submitted(dsr)

        return Response(
            DataSubjectRequestSerializer(dsr).data,
            status=status.HTTP_201_CREATED
        )


class AccessLogView(APIView):
    """
    GET /api/compliance/access-log/

    Returns the sensitive data access log for the authenticated user.
    Filters by the user's model label automatically.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logs = SensitiveDataAccessLog.objects.filter(
            model_label__icontains=request.user.__class__.__name__,
        ).order_by('-accessed_at')[:50]

        return Response({
            'count': logs.count(),
            'logs':  SensitiveDataAccessLogSerializer(logs, many=True).data,
        })


class RetentionPolicyView(APIView):
    """
    GET /api/compliance/retention/

    Returns active retention policies.
    Filtered by the user's jurisdiction by default.
    Admin users can pass ?jurisdiction=ALL to see all policies.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        jurisdiction = getattr(request, 'jurisdiction', 'IN')
        show_all     = request.user.is_staff and request.query_params.get('jurisdiction') == 'ALL'

        policies = DataRetentionPolicy.objects.filter(is_active=True)
        if not show_all:
            policies = policies.filter(jurisdiction=jurisdiction)

        return Response({
            'jurisdiction': 'ALL' if show_all else jurisdiction,
            'policies':     DataRetentionPolicySerializer(policies, many=True).data,
        })


class JurisdictionInfoView(APIView):
    """
    GET /api/compliance/jurisdiction/

    Returns the detected jurisdiction for the current request,
    enabled jurisdictions, and required consents.
    Useful for frontend apps to adapt their UI.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        jurisdiction     = getattr(request, 'jurisdiction', 'IN')
        enabled          = cs_settings.ENABLED_JURISDICTIONS
        required_consents = cs_settings.REQUIRED_CONSENTS

        missing_consents = [
            ct for ct in required_consents
            if not ConsentRecord.has_valid_consent(
                request.user, ct, jurisdiction
            )
        ]

        return Response({
            'jurisdiction':        jurisdiction,
            'enabled_jurisdictions': enabled or 'ALL',
            'is_active':           is_jurisdiction_enabled(jurisdiction),
            'privacy_version':     cs_settings.PRIVACY_POLICY_VERSION,
            'required_consents':   required_consents,
            'missing_consents':    missing_consents,
            'consent_satisfied':   len(missing_consents) == 0,
        })
