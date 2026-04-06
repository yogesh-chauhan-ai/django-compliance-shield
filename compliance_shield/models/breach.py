from datetime import timedelta
from django.db import models
from django.conf import settings
from django.utils import timezone


class DataBreachRecord(models.Model):

    SEVERITY_CHOICES = [
        ('low',      'Low — Internal only, no personal data exposed'),
        ('medium',   'Medium — Limited personal data exposed'),
        ('high',     'High — Sensitive personal data exposed'),
        ('critical', 'Critical — Mass exposure or regulated data confirmed'),
    ]

    BREACH_TYPES = [
        ('unauthorised_access',   'Unauthorised Access'),
        ('data_exfiltration',     'Data Exfiltration'),
        ('ransomware',            'Ransomware / Malware'),
        ('accidental_disclosure', 'Accidental Disclosure'),
        ('insider_threat',        'Insider Threat'),
        ('third_party',           'Third Party / Vendor Breach'),
        ('lost_device',           'Lost or Stolen Device'),
        ('other',                 'Other'),
    ]

    STATUS_CHOICES = [
        ('suspected',     'Suspected — Under Investigation'),
        ('confirmed',     'Confirmed — Breach Verified'),
        ('contained',     'Contained — No Further Exposure'),
        ('resolved',      'Resolved — Remediation Complete'),
        ('false_positive','False Positive — No Breach'),
    ]

    # Authority notification deadlines in hours per jurisdiction
    AUTHORITY_DEADLINES_HOURS = {
        'IN': 72,
        'EU': 72,
        'UK': 72,
        'US': 72,
        'AU': 720,   # 30 days
        'CA': None,  # as soon as feasible
        'AE': 72,
        'SA': 72,
    }

    title                     = models.CharField(max_length=200)
    breach_type               = models.CharField(max_length=30, choices=BREACH_TYPES)
    severity                  = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    status                    = models.CharField(max_length=20, choices=STATUS_CHOICES, default='suspected')
    discovered_at             = models.DateTimeField()
    reported_by               = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='cs_reported_breaches'
    )
    created_at                = models.DateTimeField(auto_now_add=True)
    updated_at                = models.DateTimeField(auto_now=True)
    affected_regions          = models.JSONField(default=list)
    affected_data_categories  = models.JSONField(default=list)
    estimated_affected_users  = models.IntegerField(null=True, blank=True)
    confirmed_affected_users  = models.IntegerField(null=True, blank=True)
    nature_of_breach          = models.TextField()
    likely_consequences       = models.TextField()
    measures_taken            = models.TextField()
    is_contained              = models.BooleanField(default=False)
    contained_at              = models.DateTimeField(null=True, blank=True)
    is_resolved               = models.BooleanField(default=False)
    resolved_at               = models.DateTimeField(null=True, blank=True)
    authority_notified_at     = models.JSONField(default=dict)
    authority_reference       = models.JSONField(default=dict)
    users_notified_at         = models.DateTimeField(null=True, blank=True)
    users_notification_method = models.CharField(max_length=100, blank=True)
    legal_hold                = models.BooleanField(default=False)
    legal_hold_reason         = models.TextField(blank=True)

    class Meta:
        app_label           = 'compliance_shield'
        verbose_name        = 'Data Breach Record'
        verbose_name_plural = 'Data Breach Records'
        ordering            = ['-discovered_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['severity']),
            models.Index(fields=['discovered_at']),
        ]

    def __str__(self):
        return f'{self.title} | {self.severity} | {self.status}'

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            try:
                from compliance_shield.notifications import notify_breach_recorded
                notify_breach_recorded(self)
            except Exception:
                pass

    def get_authority_deadlines(self):
        results = {}
        for region in self.affected_regions:
            hours            = self.AUTHORITY_DEADLINES_HOURS.get(region)
            already_notified = self.authority_notified_at.get(region)
            if already_notified:
                results[region] = {'status': 'notified', 'notified_at': already_notified, 'is_overdue': False}
            elif hours:
                deadline = self.discovered_at + timedelta(hours=hours)
                results[region] = {
                    'status':          'pending',
                    'deadline':        deadline,
                    'is_overdue':      timezone.now() > deadline,
                    'hours_remaining': max(0, (deadline - timezone.now()).total_seconds() / 3600),
                }
            else:
                results[region] = {'status': 'asap', 'deadline': None, 'is_overdue': False}
        return results

    def mark_authority_notified(self, region, reference_number=''):
        self.authority_notified_at[region] = timezone.now().isoformat()
        if reference_number:
            self.authority_reference[region] = reference_number
        self.save()

    def mark_contained(self):
        self.is_contained = True
        self.contained_at = timezone.now()
        self.status       = 'contained'
        self.save()

    def mark_resolved(self):
        self.is_resolved = True
        self.resolved_at = timezone.now()
        self.status      = 'resolved'
        self.save()
