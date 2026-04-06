"""
DRF API URL patterns for django-compliance-shield.

Include in your project urls.py:

    from django.urls import path, include

    urlpatterns = [
        # Template-based views (consent page, privacy settings)
        path('compliance/', include('compliance_shield.urls')),

        # DRF API views (for React / Vue / mobile / DRF projects)
        path('api/compliance/', include('compliance_shield.api_urls')),
    ]

Available endpoints:
    GET    /api/compliance/consent/           — Current consent status for user
    POST   /api/compliance/consent/grant/     — Grant one or more consents
    POST   /api/compliance/consent/withdraw/  — Withdraw a consent
    GET    /api/compliance/dsr/               — List my DSRs
    POST   /api/compliance/dsr/submit/        — Submit a new DSR
    GET    /api/compliance/access-log/        — Sensitive data access log
    GET    /api/compliance/retention/         — View retention policies
    GET    /api/compliance/jurisdiction/      — Current jurisdiction info
"""

from django.urls import path
from compliance_shield.api_views import (
    ConsentStatusView,
    ConsentGrantView,
    ConsentWithdrawView,
    DSRListView,
    DSRSubmitView,
    AccessLogView,
    RetentionPolicyView,
    JurisdictionInfoView,
)

app_name = 'compliance_shield_api'

urlpatterns = [
    # Consent
    path('consent/',          ConsentStatusView.as_view(),  name='api_consent_status'),
    path('consent/grant/',    ConsentGrantView.as_view(),   name='api_consent_grant'),
    path('consent/withdraw/', ConsentWithdrawView.as_view(),name='api_consent_withdraw'),

    # Data Subject Requests
    path('dsr/',              DSRListView.as_view(),        name='api_dsr_list'),
    path('dsr/submit/',       DSRSubmitView.as_view(),      name='api_dsr_submit'),

    # Audit and info
    path('access-log/',       AccessLogView.as_view(),      name='api_access_log'),
    path('retention/',        RetentionPolicyView.as_view(),name='api_retention'),
    path('jurisdiction/',     JurisdictionInfoView.as_view(),name='api_jurisdiction'),
]
