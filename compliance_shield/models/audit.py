from django.db import models


class SensitiveDataAccessLog(models.Model):
    """
    Immutable log of every read of a sensitive encrypted field.
    Created automatically by the @sensitive_field descriptor.
    Required for DPDP Section 8, GDPR Article 30, and FCRA audit trails.
    Never delete these records.
    """

    ACTION_CHOICES = [
        ('READ',   'Field Read / Decrypted'),
        ('WRITE',  'Field Written / Encrypted'),
        ('SEARCH', 'Blind Index Search'),
    ]

    model_label = models.CharField(
        max_length = 100,
        db_index   = True,
        help_text  = 'e.g. accounts.EmployeeProfile',
    )
    object_id   = models.CharField(
        max_length = 100,
        db_index   = True,
        help_text  = 'PK of the object whose field was accessed',
    )
    field_name  = models.CharField(max_length=100, help_text='e.g. pan_number')
    field_type  = models.CharField(max_length=50,  help_text='e.g. pan, ssn, passport')
    action      = models.CharField(max_length=10, choices=ACTION_CHOICES)
    accessed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label           = 'compliance_shield'
        verbose_name        = 'Sensitive Data Access Log'
        verbose_name_plural = 'Sensitive Data Access Logs'
        ordering            = ['-accessed_at']
        indexes = [
            models.Index(fields=['model_label', 'object_id']),
            models.Index(fields=['accessed_at']),
            models.Index(fields=['field_type', 'action']),
        ]

    def __str__(self):
        return f'{self.model_label}:{self.object_id} | {self.field_name} | {self.action} | {self.accessed_at}'
