"""
URL patterns for django-compliance-shield.

Template-based views (consent page, privacy settings dashboard):

    from django.urls import path, include
    urlpatterns = [
        path('compliance/', include('compliance_shield.urls')),
    ]

DRF API views (React / Vue / mobile / headless projects):

    urlpatterns = [
        path('api/compliance/', include('compliance_shield.api_urls')),
    ]

Both can coexist in the same project.
"""

from django.urls import path
from compliance_shield.views.consent import ConsentView, WithdrawConsentView
from compliance_shield.views.privacy import PrivacySettingsView
from compliance_shield.views.dsr     import SubmitDataRequestView

app_name = 'compliance_shield'

urlpatterns = [
    path('consent/',          ConsentView.as_view(),           name='cs_consent'),
    path('consent/withdraw/', WithdrawConsentView.as_view(),   name='cs_withdraw_consent'),
    path('privacy/',          PrivacySettingsView.as_view(),   name='cs_privacy_settings'),
    path('dsr/submit/',       SubmitDataRequestView.as_view(), name='cs_submit_dsr'),
]
