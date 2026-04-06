from datetime import timedelta
from django.db import models
from django.conf import settings
from django.utils import timezone


class DataSubjectRequest(models.Model):
    """
    Tracks all data subject rights requests across jurisdictions.
    Auto-calculates legal response deadlines per jurisdiction and request type.
    """

    REQUEST_TYPES = [
        ('access',                  'Right of Access'),
        ('correction',              'Right to Correction'),
        ('erasure',                 'Right to Erasure / Be Forgotten'),
        ('restriction',             'Right to Restrict Processing'),
        ('objection',               'Right to Object to Processing'),
        ('portability',             'Right to Data Portability'),
        ('dpdp_nomination',         'DPDP Right to Nominate'),
        ('dpdp_grievance',          'DPDP Grievance Redressal'),
        ('ccpa_opt_out_sale',       'CCPA Opt Out of Sale of Data'),
        ('ccpa_non_discrimination', 'CCPA Right to Non Discrimination'),
        ('ccpa_limit_sensitive',    'CCPA Limit Use of Sensitive Data'),
        ('fcra_dispute',            'FCRA Dispute of Inaccurate Information'),
        ('fcra_adverse_action',     'FCRA Adverse Action Notice Response'),
        ('fcra_report_copy',        'FCRA Request Copy of Consumer Report'),
        ('gdpr_automated_review',   'GDPR Review of Automated Decision'),
    ]

    STATUS_CHOICES = [
        ('received',          'Received'),
        ('identity_pending',  'Awaiting Identity Verification'),
        ('identity_verified', 'Identity Verified'),
        ('in_progress',       'In Progress'),
        ('completed',         'Completed'),
        ('rejected',          'Rejected'),
        ('extended',          'Extended — Complex Request'),
        ('withdrawn',         'Withdrawn by User'),
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

    # Legal deadline in days per jurisdiction and request type
    DEADLINE_MAP = {
        'IN': {'default': 30, 'dpdp_grievance': 30},
        'US': {'default': 45, 'fcra_dispute': 30, 'fcra_report_copy': 15},
        'EU': {'default': 30},
        'UK': {'default': 30},
        'CA': {'default': 30},
        'AU': {'default': 30},
        'AE': {'default': 30},
        'SA': {'default': 30},
        'OTHER': {'default': 30},
    }

    HIGH_SENSITIVITY_TYPES = [
        'erasure', 'portability', 'fcra_dispute',
        'fcra_report_copy', 'ccpa_opt_out_sale',
    ]

    user               = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete    = models.PROTECT,
        related_name = 'cs_dsr_requests',
    )
    request_type       = models.CharField(max_length=50, choices=REQUEST_TYPES)
    jurisdiction       = models.CharField(max_length=10, choices=JURISDICTION_CHOICES, default='IN')
    status             = models.CharField(max_length=20, choices=STATUS_CHOICES, default='received')
    request_detail     = models.TextField()
    supporting_document = models.FileField(
        upload_to='cs_dsr_documents/', null=True, blank=True
    )
    received_at        = models.DateTimeField(auto_now_add=True)
    identity_verified_at = models.DateTimeField(null=True, blank=True)
    in_progress_at     = models.DateTimeField(null=True, blank=True)
    completed_at       = models.DateTimeField(null=True, blank=True)
    deadline_at        = models.DateTimeField(null=True, blank=True)
    extended_deadline_at = models.DateTimeField(null=True, blank=True)
    deadline_days      = models.IntegerField(default=30)
    response_detail    = models.TextField(blank=True)
    rejection_reason   = models.TextField(blank=True)
    handled_by         = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete    = models.SET_NULL,
        null         = True,
        blank        = True,
        related_name = 'cs_handled_dsr',
    )
    disputed_information  = models.TextField(blank=True)
    dispute_resolution    = models.TextField(blank=True)
    ip_address            = models.GenericIPAddressField(null=True, blank=True)
    user_agent            = models.TextField(blank=True)

    class Meta:
        app_label           = 'compliance_shield'
        verbose_name        = 'Data Subject Request'
        verbose_name_plural = 'Data Subject Requests'
        ordering            = ['-received_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['jurisdiction', 'status']),
            models.Index(fields=['deadline_at']),
        ]

    def __str__(self):
        return f'{self.user} | {self.request_type} | {self.jurisdiction} | {self.status}'

    def save(self, *args, **kwargs):
        if not self.deadline_at:
            self.deadline_at = self._calculate_deadline()
        super().save(*args, **kwargs)

    def _calculate_deadline(self):
        jmap  = self.DEADLINE_MAP.get(self.jurisdiction, self.DEADLINE_MAP['OTHER'])
        days  = jmap.get(self.request_type, jmap.get('default', 30))
        self.deadline_days = days
        return timezone.now() + timedelta(days=days)

    @property
    def effective_deadline(self):
        return self.extended_deadline_at or self.deadline_at

    @property
    def is_overdue(self):
        if self.status in ('completed', 'rejected', 'withdrawn'):
            return False
        return timezone.now() > self.effective_deadline

    @property
    def days_remaining(self):
        delta = self.effective_deadline - timezone.now()
        return max(0, delta.days)

    @property
    def requires_identity_verification(self):
        return self.request_type in self.HIGH_SENSITIVITY_TYPES

    def mark_in_progress(self, handled_by=None):
        self.status         = 'in_progress'
        self.in_progress_at = timezone.now()
        if handled_by:
            self.handled_by = handled_by
        self.save()

    def mark_completed(self, response_detail, handled_by=None):
        self.status          = 'completed'
        self.completed_at    = timezone.now()
        self.response_detail = response_detail
        if handled_by:
            self.handled_by = handled_by
        self.save()
        try:
            from compliance_shield.notifications import notify_dsr_completed
            notify_dsr_completed(self)
        except Exception:
            pass

    def mark_rejected(self, reason, handled_by=None):
        self.status           = 'rejected'
        self.rejection_reason = reason
        self.completed_at     = timezone.now()
        if handled_by:
            self.handled_by = handled_by
        self.save()
        try:
            from compliance_shield.notifications import notify_dsr_rejected
            notify_dsr_rejected(self)
        except Exception:
            pass

    def extend_deadline(self, additional_days, reason=''):
        from_date = self.extended_deadline_at or self.deadline_at
        self.extended_deadline_at = from_date + timedelta(days=additional_days)
        self.status = 'extended'
        if reason:
            self.response_detail = f'{self.response_detail}\nExtension: {reason}'.strip()
        self.save()

    @classmethod
    def submit(cls, user, request_type, jurisdiction, request_detail, request,
               supporting_document=None):
        """Central method to submit a new DSR. Always use this."""
        x_fwd = request.META.get('HTTP_X_FORWARDED_FOR')
        ip    = x_fwd.split(',')[0].strip() if x_fwd else request.META.get('REMOTE_ADDR')

        obj = cls(
            user                = user,
            request_type        = request_type,
            jurisdiction        = jurisdiction,
            request_detail      = request_detail,
            supporting_document = supporting_document,
            ip_address          = ip,
            user_agent          = request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        obj.status = (
            'identity_pending'
            if request_type in cls.HIGH_SENSITIVITY_TYPES
            else 'received'
        )
        obj.save()
        return obj

    @classmethod
    def get_overdue(cls):
        """Returns all open requests past their deadline."""
        open_statuses = [
            'received', 'identity_pending',
            'identity_verified', 'in_progress', 'extended',
        ]
        now = timezone.now()
        return cls.objects.filter(
            status__in=open_statuses,
            deadline_at__lt=now,
            extended_deadline_at__isnull=True,
        ) | cls.objects.filter(
            status__in=open_statuses,
            extended_deadline_at__lt=now,
        )
