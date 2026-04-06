"""
DRF serializers for django-compliance-shield.

Only loaded if djangorestframework is installed.
Works alongside the existing template-based views — both can coexist.

Usage in your DRF project:
    from compliance_shield.serializers import (
        ConsentRecordSerializer,
        DataSubjectRequestSerializer,
        SubmitDSRSerializer,
        ConsentActionSerializer,
    )
"""

try:
    from rest_framework import serializers
except ImportError:
    raise ImportError(
        'djangorestframework is required for compliance_shield.serializers. '
        'Install it with: pip install djangorestframework'
    )

from compliance_shield.models.consent   import ConsentRecord, DataDeletionRequest
from compliance_shield.models.dsr       import DataSubjectRequest
from compliance_shield.models.retention import DataRetentionPolicy
from compliance_shield.models.audit     import SensitiveDataAccessLog
from compliance_shield.models.breach    import DataBreachRecord


class ConsentRecordSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model  = ConsentRecord
        fields = [
            'id', 'user_email', 'consent_type', 'jurisdiction',
            'consent_version', 'granted', 'granted_at', 'withdrawn_at',
            'created_at',
        ]
        read_only_fields = fields


class ConsentStatusSerializer(serializers.Serializer):
    """
    Returns current consent status for a user across all consent types.
    Used by GET /compliance/api/consent/
    """
    consent_type    = serializers.CharField()
    label           = serializers.CharField()
    is_granted      = serializers.BooleanField()
    granted_at      = serializers.DateTimeField(allow_null=True)
    withdrawn_at    = serializers.DateTimeField(allow_null=True)
    is_required     = serializers.BooleanField()
    can_withdraw    = serializers.BooleanField()


class ConsentActionSerializer(serializers.Serializer):
    """
    POST /compliance/api/consent/grant/
    POST /compliance/api/consent/withdraw/
    """
    consent_type  = serializers.ChoiceField(
        choices=[c[0] for c in ConsentRecord.CONSENT_TYPES]
    )
    jurisdiction  = serializers.CharField(max_length=10, default='IN')


class DataSubjectRequestSerializer(serializers.ModelSerializer):
    user_email          = serializers.EmailField(source='user.email', read_only=True)
    request_type_label  = serializers.CharField(
        source='get_request_type_display', read_only=True
    )
    status_label        = serializers.CharField(
        source='get_status_display', read_only=True
    )
    effective_deadline  = serializers.DateTimeField(read_only=True)
    is_overdue          = serializers.BooleanField(read_only=True)
    days_remaining      = serializers.IntegerField(read_only=True)

    class Meta:
        model  = DataSubjectRequest
        fields = [
            'id', 'user_email', 'request_type', 'request_type_label',
            'jurisdiction', 'status', 'status_label',
            'request_detail', 'response_detail', 'rejection_reason',
            'received_at', 'deadline_at', 'effective_deadline',
            'deadline_days', 'is_overdue', 'days_remaining',
        ]
        read_only_fields = [
            'id', 'user_email', 'request_type_label', 'status_label',
            'status', 'response_detail', 'rejection_reason',
            'received_at', 'deadline_at', 'effective_deadline',
            'deadline_days', 'is_overdue', 'days_remaining',
        ]


class SubmitDSRSerializer(serializers.Serializer):
    """
    POST /compliance/api/dsr/submit/
    """
    request_type   = serializers.ChoiceField(
        choices=[r[0] for r in DataSubjectRequest.REQUEST_TYPES]
    )
    jurisdiction   = serializers.CharField(max_length=10, default='IN')
    request_detail = serializers.CharField(min_length=10, max_length=2000)

    def validate(self, data):
        request = self.context.get('request')
        if not request:
            return data

        # Block duplicate open requests
        existing = DataSubjectRequest.objects.filter(
            user         = request.user,
            request_type = data['request_type'],
            jurisdiction = data['jurisdiction'],
            status__in   = [
                'received', 'identity_pending',
                'identity_verified', 'in_progress',
            ],
        ).first()

        if existing:
            raise serializers.ValidationError(
                f'You already have an open {data["request_type"]} request '
                f'(DSR-{existing.pk:06d}). '
                f'We will contact you once it is resolved.'
            )
        return data


class SensitiveDataAccessLogSerializer(serializers.ModelSerializer):
    action_label = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model  = SensitiveDataAccessLog
        fields = [
            'id', 'model_label', 'object_id', 'field_name',
            'field_type', 'action', 'action_label', 'accessed_at',
        ]
        read_only_fields = fields


class DataRetentionPolicySerializer(serializers.ModelSerializer):
    retention_years = serializers.SerializerMethodField()

    class Meta:
        model  = DataRetentionPolicy
        fields = [
            'id', 'data_category', 'jurisdiction', 'retention_days',
            'retention_years', 'action_on_expiry', 'legal_basis',
            'is_active', 'last_reviewed',
        ]
        read_only_fields = fields

    def get_retention_years(self, obj):
        return round(obj.retention_days / 365, 1)


class DataBreachRecordSerializer(serializers.ModelSerializer):
    reported_by_email    = serializers.EmailField(
        source='reported_by.email', read_only=True
    )
    severity_display     = serializers.CharField(
        source='get_severity_display', read_only=True
    )
    status_display       = serializers.CharField(
        source='get_status_display', read_only=True
    )
    authority_deadlines  = serializers.SerializerMethodField()

    class Meta:
        model  = DataBreachRecord
        fields = [
            'id', 'title', 'breach_type', 'severity', 'severity_display',
            'status', 'status_display', 'discovered_at',
            'reported_by_email', 'affected_regions',
            'affected_data_categories', 'estimated_affected_users',
            'is_contained', 'is_resolved', 'authority_deadlines',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_authority_deadlines(self, obj):
        deadlines = obj.get_authority_deadlines()
        result    = {}
        for region, info in deadlines.items():
            result[region] = {
                'status':     info['status'],
                'is_overdue': info.get('is_overdue', False),
                'deadline':   info['deadline'].isoformat()
                              if info.get('deadline') else None,
                'hours_remaining': round(info.get('hours_remaining', 0), 1)
                                   if info.get('hours_remaining') else None,
            }
        return result
