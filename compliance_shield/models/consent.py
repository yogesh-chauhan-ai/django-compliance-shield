import hashlib
from django.db import models
from django.conf import settings
from django.utils import timezone


class ConsentRecord(models.Model):
    """
    Immutable record of every consent decision made by a user.
    Stores exact text shown, version, IP, user agent, and timestamp.
    Required for DPDP, GDPR, CCPA, and FCRA compliance.
    """

    CONSENT_TYPES = [
        ('data_collection',       'Collection of Personal Data'),
        ('data_processing',       'Processing for Verification'),
        ('employer_sharing',      'Sharing with Employer'),
        ('third_party_ai',        'Third Party AI Processing'),
        ('marketing',             'Marketing Communications'),
        ('cross_border_transfer', 'Cross Border Data Transfer'),
        ('sensitive_data',        'Processing Sensitive Personal Data'),
        ('automated_decision',    'Automated Decision Making'),
        ('dpdp_nomination',       'DPDP Right to Nominate'),
        ('dpdp_grievance',        'DPDP Grievance Redressal'),
        ('fcra_disclosure',       'FCRA Consumer Report Disclosure'),
        ('fcra_authorization',    'FCRA Authorization for Background Check'),
        ('gdpr_portability',      'GDPR Data Portability'),
        ('gdpr_automated_review', 'GDPR Review of Automated Decision'),
        ('ccpa_opt_out',          'CCPA Opt Out of Sale'),
    ]

    JURISDICTION_CHOICES = [
        ('IN',    'India — DPDP'),
        ('US',    'United States — CCPA / FCRA'),
        ('EU',    'European Union — GDPR'),
        ('UK',    'United Kingdom — UK GDPR'),
        ('CA',    'Canada — PIPEDA'),
        ('AU',    'Australia — Privacy Act'),
        ('AE',    'UAE — PDPL'),
        ('SA',    'Saudi Arabia — PDPL'),
        ('OTHER', 'Other'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete       = models.PROTECT,
        related_name    = 'cs_consent_records',
        help_text       = 'User who gave or withdrew consent',
    )
    consent_type        = models.CharField(max_length=50, choices=CONSENT_TYPES)
    jurisdiction        = models.CharField(max_length=10, choices=JURISDICTION_CHOICES, default='IN')
    consent_text_shown  = models.TextField(help_text='Exact text shown to user at time of consent')
    consent_text_hash   = models.CharField(max_length=64, help_text='SHA256 of consent_text_shown')
    consent_version     = models.CharField(max_length=20, default='v1.0.0')
    granted             = models.BooleanField(default=False)
    granted_at          = models.DateTimeField(null=True, blank=True)
    withdrawn_at        = models.DateTimeField(null=True, blank=True)
    ip_address          = models.GenericIPAddressField(null=True, blank=True)
    user_agent          = models.TextField(blank=True)
    session_id          = models.CharField(max_length=100, blank=True)
    created_at          = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label           = 'compliance_shield'
        verbose_name        = 'Consent Record'
        verbose_name_plural = 'Consent Records'
        ordering            = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'consent_type', 'jurisdiction']),
            models.Index(fields=['user', 'granted']),
        ]

    def __str__(self):
        status = 'Granted' if self.granted else 'Withdrawn'
        return f'{self.user} | {self.consent_type} | {self.jurisdiction} | {status}'

    @classmethod
    def record_consent(cls, user, consent_type, jurisdiction,
                       consent_text, request, version='v1.0.0', granted=True):
        """
        Record a consent decision. Always use this instead of creating directly.

        Example
        -------
            ConsentRecord.record_consent(
                user         = request.user,
                consent_type = 'data_collection',
                jurisdiction = 'IN',
                consent_text = 'I agree to ...',
                request      = request,
            )
        """
        text_hash = hashlib.sha256(consent_text.encode()).hexdigest()
        return cls.objects.create(
            user               = user,
            consent_type       = consent_type,
            jurisdiction       = jurisdiction,
            consent_text_shown = consent_text,
            consent_text_hash  = text_hash,
            consent_version    = version,
            granted            = granted,
            granted_at         = timezone.now() if granted else None,
            ip_address         = _get_client_ip(request),
            user_agent         = request.META.get('HTTP_USER_AGENT', '')[:500],
            session_id         = request.session.session_key or '',
        )

    @classmethod
    def withdraw_consent(cls, user, consent_type, jurisdiction, request):
        """Withdraw an existing consent and trigger a DataDeletionRequest."""
        records = cls.objects.filter(
            user             = user,
            consent_type     = consent_type,
            jurisdiction     = jurisdiction,
            granted          = True,
            withdrawn_at__isnull = True,
        )
        for record in records:
            record.granted      = False
            record.withdrawn_at = timezone.now()
            record.save()

        DataDeletionRequest.objects.create(
            user         = user,
            reason       = 'consent_withdrawn',
            consent_type = consent_type,
            jurisdiction = jurisdiction,
            ip_address   = _get_client_ip(request),
        )

        # Fire email notification to privacy team
        try:
            from compliance_shield.notifications import notify_consent_withdrawn
            notify_consent_withdrawn(user, consent_type, jurisdiction)
        except Exception:
            pass

    @classmethod
    def has_valid_consent(cls, user, consent_type, jurisdiction):
        """
        Returns True if the user has an active consent for this type.

        Example
        -------
            if not ConsentRecord.has_valid_consent(user, 'data_processing', 'IN'):
                return HttpResponseForbidden()
        """
        return cls.objects.filter(
            user             = user,
            consent_type     = consent_type,
            jurisdiction     = jurisdiction,
            granted          = True,
            withdrawn_at__isnull = True,
        ).exists()


class DataDeletionRequest(models.Model):
    """Created automatically when a user withdraws consent."""

    STATUS_CHOICES = [
        ('pending',     'Pending'),
        ('in_progress', 'In Progress'),
        ('completed',   'Completed'),
        ('rejected',    'Rejected'),
    ]

    user         = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete    = models.PROTECT,
        related_name = 'cs_deletion_requests',
    )
    reason       = models.CharField(max_length=100)
    consent_type = models.CharField(max_length=50, blank=True)
    jurisdiction = models.CharField(max_length=10, default='IN')
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    ip_address   = models.GenericIPAddressField(null=True, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes        = models.TextField(blank=True)

    class Meta:
        app_label           = 'compliance_shield'
        verbose_name        = 'Data Deletion Request'
        verbose_name_plural = 'Data Deletion Requests'
        ordering            = ['-requested_at']

    def __str__(self):
        return f'{self.user} | {self.reason} | {self.status}'


def _get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
