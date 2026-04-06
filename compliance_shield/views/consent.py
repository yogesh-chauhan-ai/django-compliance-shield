from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import render, redirect
from django.views import View

from compliance_shield.models.consent import ConsentRecord
from compliance_shield.conf import cs_settings


CONSENT_TEXTS = {
    'data_collection': (
        'I consent to this application collecting my personal data including '
        'name, email, and profile information for the purpose of providing '
        'the service. I understand I can withdraw this consent at any time.'
    ),
    'data_processing': (
        'I consent to this application processing my personal data to deliver '
        'its core features and services. I understand this processing is '
        'necessary to use the platform.'
    ),
    'employer_sharing': (
        'I consent to sharing my verified profile with employers or third '
        'parties I explicitly authorise. I control what each party sees.'
    ),
    'third_party_ai': (
        'I consent to this application using third-party AI services to '
        'assist in processing my data under strict confidentiality agreements.'
    ),
    'marketing': (
        'I consent to receiving occasional updates and communications. '
        'I can unsubscribe at any time.'
    ),
    'cross_border_transfer': (
        'I consent to my personal data being transferred to servers in other '
        'countries where it will be protected under equivalent safeguards.'
    ),
    'automated_decision': (
        'I consent to automated processing and decision-making about my '
        'profile. I understand I have the right to request human review '
        'of any automated decision.'
    ),
}


class ConsentView(LoginRequiredMixin, View):
    """
    Shown when required consents are missing or when user visits
    privacy settings to manage consent preferences.

    Template: compliance_shield/consent.html (overridable)
    """

    template_name = 'compliance_shield/consent.html'

    def get(self, request):
        jurisdiction = getattr(request, 'jurisdiction', 'IN')
        pending      = request.session.get('cs_pending_consents', [])
        next_url     = request.GET.get(
            'next',
            request.session.get('cs_consent_redirect', '/')
        )

        consent_items = self._build_consent_items(
            request.user, jurisdiction, pending
        )

        return render(request, self.template_name, {
            'consent_items':   consent_items,
            'jurisdiction':    jurisdiction,
            'next_url':        next_url,
            'pending':         pending,
            'privacy_version': cs_settings.PRIVACY_POLICY_VERSION,
        })

    def post(self, request):
        jurisdiction  = getattr(request, 'jurisdiction', 'IN')
        next_url      = request.POST.get('next_url', '/')
        granted_types = request.POST.getlist('consents')

        for consent_type, text in CONSENT_TEXTS.items():
            if consent_type in granted_types:
                ConsentRecord.record_consent(
                    user         = request.user,
                    consent_type = consent_type,
                    jurisdiction = jurisdiction,
                    consent_text = text,
                    request      = request,
                    version      = cs_settings.PRIVACY_POLICY_VERSION,
                    granted      = True,
                )

        request.session.pop('cs_pending_consents', None)
        request.session.pop('cs_consent_redirect', None)

        still_missing = [
            c for c in cs_settings.REQUIRED_CONSENTS
            if not ConsentRecord.has_valid_consent(
                request.user, c, jurisdiction
            )
        ]

        if still_missing:
            messages.error(
                request,
                'Please grant the required consents to continue.'
            )
            return redirect(f'/compliance/consent/?next={next_url}')

        messages.success(request, 'Your consent preferences have been saved.')
        return redirect(next_url)

    def _build_consent_items(self, user, jurisdiction, pending):
        items = []
        for consent_type, text in CONSENT_TEXTS.items():
            already_granted = ConsentRecord.has_valid_consent(
                user, consent_type, jurisdiction
            )
            items.append({
                'type':            consent_type,
                'label':           dict(ConsentRecord.CONSENT_TYPES).get(
                    consent_type, consent_type.replace('_', ' ').title()
                ),
                'text':            text,
                'already_granted': already_granted,
                'is_required':     consent_type in cs_settings.REQUIRED_CONSENTS,
                'is_pending':      consent_type in pending,
            })
        return items


class WithdrawConsentView(LoginRequiredMixin, View):
    """
    POST endpoint to withdraw a specific consent type.
    Automatically triggers a DataDeletionRequest.
    """

    def post(self, request):
        consent_type = request.POST.get('consent_type')
        jurisdiction = getattr(request, 'jurisdiction', 'IN')

        if not consent_type:
            messages.error(request, 'No consent type specified.')
            return redirect('cs_privacy_settings')

        if consent_type in cs_settings.REQUIRED_CONSENTS:
            messages.warning(
                request,
                'Withdrawing a required consent requires account deletion. '
                'Please contact support.'
            )
            return redirect('cs_privacy_settings')

        ConsentRecord.withdraw_consent(
            user         = request.user,
            consent_type = consent_type,
            jurisdiction = jurisdiction,
            request      = request,
        )

        messages.success(
            request,
            f'Your consent for "{consent_type.replace("_", " ")}" '
            f'has been withdrawn.'
        )
        return redirect('cs_privacy_settings')
