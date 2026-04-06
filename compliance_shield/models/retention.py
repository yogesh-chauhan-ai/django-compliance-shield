from django.db import models


class DataRetentionPolicy(models.Model):

    DATA_CATEGORIES = [
        ('employment_records',  'Employment Verification Records'),
        ('pan_aadhaar',         'PAN and Aadhaar Numbers'),
        ('ssn',                 'Social Security Numbers'),
        ('financial_signals',   'Financial Signal Data'),
        ('consent_records',     'Consent Records'),
        ('audit_logs',          'Audit Logs'),
        ('offer_commitments',   'Offer Commitment Notes'),
        ('derogatory_reports',  'Derogatory Reports'),
        ('session_data',        'Session and Cookie Data'),
        ('communication_logs',  'Email and Notification Logs'),
        ('agent_run_logs',      'AI Agent Run Logs'),
        ('custom',              'Custom Category'),
    ]

    JURISDICTION_CHOICES = [
        ('IN',    'India — DPDP'),
        ('US',    'United States — FCRA / CCPA'),
        ('EU',    'European Union — GDPR'),
        ('UK',    'United Kingdom — UK GDPR'),
        ('CA',    'Canada — PIPEDA'),
        ('AU',    'Australia — Privacy Act'),
        ('AE',    'UAE — PDPL'),
        ('SA',    'Saudi Arabia — PDPL'),
        ('OTHER', 'Other'),
    ]

    ACTION_CHOICES = [
        ('anonymise', 'Anonymise Record'),
        ('delete',    'Hard Delete Record'),
        ('archive',   'Archive to Cold Storage'),
        ('review',    'Flag for Manual Review'),
    ]

    data_category    = models.CharField(max_length=50, choices=DATA_CATEGORIES)
    jurisdiction     = models.CharField(max_length=10, choices=JURISDICTION_CHOICES)
    retention_days   = models.IntegerField()
    action_on_expiry = models.CharField(max_length=20, choices=ACTION_CHOICES, default='anonymise')
    legal_basis      = models.TextField()
    is_active        = models.BooleanField(default=True)
    last_reviewed    = models.DateField(auto_now=True)
    reviewed_by      = models.CharField(max_length=100, blank=True)
    notes            = models.TextField(blank=True)

    class Meta:
        app_label           = 'compliance_shield'
        unique_together     = ('data_category', 'jurisdiction')
        verbose_name        = 'Data Retention Policy'
        verbose_name_plural = 'Data Retention Policies'
        ordering            = ['jurisdiction', 'data_category']

    def __str__(self):
        return f'{self.jurisdiction} | {self.data_category} | {self.retention_days}d | {self.action_on_expiry}'


class DataRetentionLog(models.Model):

    ACTION_CHOICES = [
        ('anonymised', 'Anonymised'),
        ('deleted',    'Hard Deleted'),
        ('archived',   'Archived'),
        ('flagged',    'Flagged for Review'),
        ('skipped',    'Skipped — Active Legal Hold'),
    ]

    data_category    = models.CharField(max_length=50)
    jurisdiction     = models.CharField(max_length=10)
    action_taken     = models.CharField(max_length=20, choices=ACTION_CHOICES)
    records_affected = models.IntegerField(default=0)
    policy           = models.ForeignKey(
        DataRetentionPolicy, on_delete=models.PROTECT, null=True, blank=True
    )
    run_at           = models.DateTimeField(auto_now_add=True)
    run_by           = models.CharField(max_length=100, default='system')
    detail           = models.TextField(blank=True)
    errors           = models.TextField(blank=True)

    class Meta:
        app_label           = 'compliance_shield'
        verbose_name        = 'Data Retention Log'
        verbose_name_plural = 'Data Retention Logs'
        ordering            = ['-run_at']

    def __str__(self):
        return f'{self.jurisdiction} | {self.data_category} | {self.action_taken} | {self.records_affected} records'
