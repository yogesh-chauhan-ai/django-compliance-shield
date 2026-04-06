from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.views import View

from compliance_shield.models.dsr import DataSubjectRequest


class SubmitDataRequestView(LoginRequiredMixin, View):
    """
    POST endpoint to submit a new data subject request.
    Redirects back to privacy settings on completion.
    """

    def post(self, request):
        jurisdiction   = getattr(request, 'jurisdiction', 'IN')
        request_type   = request.POST.get('request_type', '').strip()
        request_detail = request.POST.get('request_detail', '').strip()

        if not request_type:
            messages.error(request, 'Please select a request type.')
            return redirect('cs_privacy_settings')

        if not request_detail:
            messages.error(request, 'Please describe your request.')
            return redirect('cs_privacy_settings')

        # Block duplicate open requests of same type
        existing = DataSubjectRequest.objects.filter(
            user         = request.user,
            request_type = request_type,
            jurisdiction = jurisdiction,
            status__in   = [
                'received', 'identity_pending',
                'identity_verified', 'in_progress',
            ],
        ).first()

        if existing:
            messages.warning(
                request,
                f'You already have an open '
                f'{request_type.replace("_", " ")} request '
                f'(submitted {existing.received_at.strftime("%d %b %Y")}). '
                f'We will contact you once it is resolved.'
            )
            return redirect('cs_privacy_settings')

        dsr = DataSubjectRequest.submit(
            user           = request.user,
            request_type   = request_type,
            jurisdiction   = jurisdiction,
            request_detail = request_detail,
            request        = request,
        )

        # Fire email notifications
        from compliance_shield.notifications import notify_dsr_submitted
        notify_dsr_submitted(dsr)

        messages.success(
            request,
            f'Your request has been submitted (Ref: DSR-{dsr.pk:06d}). '
            f'We will respond within {dsr.deadline_days} days as required by law.'
        )
        return redirect('cs_privacy_settings')

