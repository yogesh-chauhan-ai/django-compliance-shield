from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from compliance_shield.models.consent   import ConsentRecord
from compliance_shield.models.dsr       import DataSubjectRequest
from compliance_shield.models.audit     import SensitiveDataAccessLog
from compliance_shield.conf             import cs_settings


JURISDICTION_REQUEST_TYPES = {
    'universal': [
        ('access',      'Request a copy of my data'),
        ('correction',  'Correct inaccurate data'),
        ('erasure',     'Delete my data'),
        ('restriction', 'Restrict how my data is used'),
        ('portability', 'Export my data in machine-readable format'),
    ],
    'IN': [
        ('dpdp_nomination', 'Nominate someone to exercise my rights'),
        ('dpdp_grievance',  'Submit a grievance'),
    ],
    'US': [
        ('ccpa_opt_out_sale',    'Opt out of sale of my data'),
        ('ccpa_limit_sensitive', 'Limit use of sensitive data'),
        ('fcra_dispute',         'Dispute inaccurate background check information'),
        ('fcra_report_copy',     'Request a copy of my consumer report'),
    ],
    'EU': [
        ('objection',            'Object to processing'),
        ('gdpr_automated_review','Request review of automated decision'),
    ],
    'UK': [
        ('objection',            'Object to processing'),
        ('gdpr_automated_review','Request review of automated decision'),
    ],
}


class PrivacySettingsView(LoginRequiredMixin, View):
    """
    Central privacy dashboard for authenticated users.

    Shows:
    - Consent status for all consent types
    - Data subject requests submitted
    - Sensitive data access log
    - Form to submit new data rights requests

    Template: compliance_shield/privacy_settings.html (overridable)
    """

    template_name = 'compliance_shield/privacy_settings.html'

    def get(self, request):
        jurisdiction = getattr(request, 'jurisdiction', 'IN')
        user         = request.user

        # Build consent status rows
        consent_status = []
        for consent_type, label in ConsentRecord.CONSENT_TYPES:
            latest = ConsentRecord.objects.filter(
                user         = user,
                consent_type = consent_type,
                jurisdiction = jurisdiction,
            ).order_by('-created_at').first()

            consent_status.append({
                'type':         consent_type,
                'label':        label,
                'is_granted':   latest.granted if latest else False,
                'granted_at':   latest.granted_at if latest else None,
                'withdrawn_at': latest.withdrawn_at if latest else None,
                'is_required':  consent_type in cs_settings.REQUIRED_CONSENTS,
                'can_withdraw': consent_type not in cs_settings.REQUIRED_CONSENTS,
            })

        # DSR list
        dsr_list = DataSubjectRequest.objects.filter(
            user=user
        ).order_by('-received_at')[:20]

        # Access log — works with any model that has object_id
        access_log = SensitiveDataAccessLog.objects.filter(
            model_label__icontains=user.__class__.__name__,
        ).order_by('-accessed_at')[:20]

        # Available request types for this jurisdiction
        available_types = (
            JURISDICTION_REQUEST_TYPES['universal']
            + JURISDICTION_REQUEST_TYPES.get(jurisdiction, [])
        )

        return render(request, self.template_name, {
            'consent_status':          consent_status,
            'dsr_list':                dsr_list,
            'access_log':              access_log,
            'jurisdiction':            jurisdiction,
            'available_request_types': available_types,
            'privacy_version':         cs_settings.PRIVACY_POLICY_VERSION,
        })
