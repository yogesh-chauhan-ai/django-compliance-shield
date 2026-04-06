"""
Email notification system for django-compliance-shield.

Controlled entirely via COMPLIANCE_SHIELD settings:

    COMPLIANCE_SHIELD = {
        'EMAIL_NOTIFICATIONS': True,           # master switch
        'DSR_ALERT_RECIPIENTS': [              # notified on every new DSR
            'privacy@company.com',
        ],
        'BREACH_ALERT_RECIPIENTS': [           # notified on every new breach
            'dpo@company.com',
            'legal@company.com',
        ],
        'OVERDUE_DSR_RECIPIENTS': [            # notified by daily cron
            'privacy@company.com',
        ],
        'EMAIL_FROM': 'compliance@company.com', # defaults to DEFAULT_FROM_EMAIL
        'DSR_USER_CONFIRMATION_EMAIL': True,    # send confirmation to the user
    }

All notifications are silent-fail — a misconfigured email backend
will never crash the compliance system.
"""

from django.core.mail import send_mail, send_mass_mail
from compliance_shield.conf import cs_settings, get_email_from


def _enabled():
    """Returns True if email notifications are switched on."""
    return bool(cs_settings.EMAIL_NOTIFICATIONS)


def _send(subject, body, recipients):
    """
    Internal send helper. Silent fail on any error.
    Skips sending if notifications are disabled or recipient list is empty.
    """
    if not _enabled():
        return
    if not recipients:
        return
    try:
        send_mail(
            subject        = f'[Compliance Shield] {subject}',
            message        = body,
            from_email     = get_email_from(),
            recipient_list = recipients,
            fail_silently  = True,
        )
    except Exception:
        pass


# ── DSR notifications ──────────────────────────────────────────────────────

def notify_dsr_submitted(dsr):
    """
    Called when a user submits a new Data Subject Request.
    Sends:
      1. Confirmation to the user (if DSR_USER_CONFIRMATION_EMAIL is True)
      2. Alert to DSR_ALERT_RECIPIENTS (privacy team)
    """
    user = dsr.user

    # 1. Confirmation to the user
    if cs_settings.DSR_USER_CONFIRMATION_EMAIL:
        _send(
            subject    = f'Your request has been received — Ref DSR-{dsr.pk:06d}',
            body       = (
                f'Hi {user.first_name or user.email},\n\n'
                f'We have received your {dsr.get_request_type_display()} request '
                f'(Reference: DSR-{dsr.pk:06d}).\n\n'
                f'We are required by law to respond within {dsr.deadline_days} days '
                f'(by {dsr.deadline_at.strftime("%d %B %Y")}).\n\n'
                f'If you have questions, please reply to this email.\n\n'
                f'Privacy Team'
            ),
            recipients = [user.email],
        )

    # 2. Alert to privacy team
    _send(
        subject    = f'New DSR received — DSR-{dsr.pk:06d} ({dsr.request_type})',
        body       = (
            f'A new Data Subject Request has been submitted.\n\n'
            f'Reference    : DSR-{dsr.pk:06d}\n'
            f'Type         : {dsr.get_request_type_display()}\n'
            f'Jurisdiction : {dsr.jurisdiction}\n'
            f'User         : {user.email}\n'
            f'Status       : {dsr.get_status_display()}\n'
            f'Deadline     : {dsr.deadline_at.strftime("%d %B %Y")} '
            f'({dsr.deadline_days} days)\n\n'
            f'Request detail:\n{dsr.request_detail}\n\n'
            f'Please log in to your admin panel to action this request.'
        ),
        recipients = cs_settings.DSR_ALERT_RECIPIENTS,
    )


def notify_dsr_completed(dsr):
    """Notify the user when their DSR has been completed."""
    user = dsr.user
    if not cs_settings.DSR_USER_CONFIRMATION_EMAIL:
        return
    _send(
        subject    = f'Your request has been completed — Ref DSR-{dsr.pk:06d}',
        body       = (
            f'Hi {user.first_name or user.email},\n\n'
            f'Your {dsr.get_request_type_display()} request '
            f'(Reference: DSR-{dsr.pk:06d}) has been completed.\n\n'
            f'Response:\n{dsr.response_detail}\n\n'
            f'If you have questions, please reply to this email.\n\n'
            f'Privacy Team'
        ),
        recipients = [user.email],
    )


def notify_dsr_rejected(dsr):
    """Notify the user when their DSR has been rejected."""
    user = dsr.user
    if not cs_settings.DSR_USER_CONFIRMATION_EMAIL:
        return
    _send(
        subject    = f'Update on your request — Ref DSR-{dsr.pk:06d}',
        body       = (
            f'Hi {user.first_name or user.email},\n\n'
            f'We were unable to fulfil your {dsr.get_request_type_display()} request '
            f'(Reference: DSR-{dsr.pk:06d}).\n\n'
            f'Reason:\n{dsr.rejection_reason}\n\n'
            f'You have the right to escalate this decision to the relevant '
            f'regulatory authority in your jurisdiction.\n\n'
            f'Privacy Team'
        ),
        recipients = [user.email],
    )


def notify_overdue_dsrs(overdue_dsrs):
    """
    Called by enforce_retention management command daily.
    Sends a digest of overdue DSRs to OVERDUE_DSR_RECIPIENTS.
    """
    recipients = cs_settings.OVERDUE_DSR_RECIPIENTS
    if not recipients or not overdue_dsrs:
        return

    lines = []
    for dsr in overdue_dsrs:
        lines.append(
            f'  DSR-{dsr.pk:06d} | {dsr.request_type} | '
            f'{dsr.jurisdiction} | {dsr.user.email} | '
            f'Overdue by {abs(dsr.days_remaining)} days'
        )

    _send(
        subject    = f'ACTION REQUIRED — {len(lines)} overdue DSR(s)',
        body       = (
            f'The following Data Subject Requests are past their legal deadline '
            f'and require immediate action:\n\n'
            + '\n'.join(lines)
            + '\n\nPlease log in to your admin panel and resolve these requests.'
        ),
        recipients = recipients,
    )


# ── Breach notifications ───────────────────────────────────────────────────

def notify_breach_recorded(breach):
    """
    Called when a new DataBreachRecord is created.
    Sends urgent alert to BREACH_ALERT_RECIPIENTS with deadline info.
    """
    recipients = cs_settings.BREACH_ALERT_RECIPIENTS
    if not recipients:
        return

    deadlines = breach.get_authority_deadlines()
    deadline_lines = []
    for region, info in deadlines.items():
        if info['status'] == 'pending':
            deadline_lines.append(
                f'  {region}: notify authority by '
                f'{info["deadline"].strftime("%d %b %Y %H:%M UTC")} '
                f'({info["hours_remaining"]:.1f} hours remaining)'
            )
        elif info['status'] == 'asap':
            deadline_lines.append(f'  {region}: notify as soon as feasible')

    _send(
        subject    = f'URGENT — Data breach recorded: {breach.title} [{breach.severity.upper()}]',
        body       = (
            f'A data breach has been recorded and requires immediate attention.\n\n'
            f'Title        : {breach.title}\n'
            f'Severity     : {breach.severity.upper()}\n'
            f'Type         : {breach.get_breach_type_display()}\n'
            f'Status       : {breach.get_status_display()}\n'
            f'Discovered   : {breach.discovered_at.strftime("%d %B %Y %H:%M UTC")}\n'
            f'Affected regions: {", ".join(breach.affected_regions)}\n'
            f'Estimated users : {breach.estimated_affected_users or "Unknown"}\n\n'
            f'Nature of breach:\n{breach.nature_of_breach}\n\n'
            f'Authority notification deadlines:\n'
            + ('\n'.join(deadline_lines) if deadline_lines else '  None required')
            + '\n\nPlease log in to your admin panel immediately to manage this breach.'
        ),
        recipients = recipients,
    )


def notify_breach_authority_deadline_approaching(breach, region, hours_remaining):
    """
    Called by a monitoring task when a breach notification deadline
    is within 12 hours. Sends urgent reminder.
    """
    recipients = cs_settings.BREACH_ALERT_RECIPIENTS
    if not recipients:
        return

    _send(
        subject    = f'URGENT — {region} breach notification deadline in {hours_remaining:.0f} hours',
        body       = (
            f'The regulatory authority notification deadline for the following '
            f'breach is approaching:\n\n'
            f'Breach   : {breach.title}\n'
            f'Region   : {region}\n'
            f'Deadline : {hours_remaining:.1f} hours remaining\n\n'
            f'If you have not yet notified the {region} authority, '
            f'please do so immediately to avoid regulatory penalties.\n\n'
            f'Log in to your admin panel to mark the notification as sent.'
        ),
        recipients = recipients,
    )


# ── Consent notifications ──────────────────────────────────────────────────

def notify_consent_withdrawn(user, consent_type, jurisdiction):
    """
    Notify privacy team when a user withdraws a consent.
    Only sent if DSR_ALERT_RECIPIENTS is configured.
    """
    recipients = cs_settings.DSR_ALERT_RECIPIENTS
    if not recipients:
        return

    _send(
        subject    = f'Consent withdrawn — {consent_type} ({jurisdiction})',
        body       = (
            f'A user has withdrawn their consent.\n\n'
            f'User         : {user.email}\n'
            f'Consent type : {consent_type}\n'
            f'Jurisdiction : {jurisdiction}\n\n'
            f'A DataDeletionRequest has been automatically created. '
            f'Please review and process it in your admin panel.'
        ),
        recipients = recipients,
    )
