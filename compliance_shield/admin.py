from django.contrib import admin
from django.utils.html import format_html

from compliance_shield.models.consent   import ConsentRecord, DataDeletionRequest
from compliance_shield.models.dsr       import DataSubjectRequest
from compliance_shield.models.retention import DataRetentionPolicy, DataRetentionLog
from compliance_shield.models.audit     import SensitiveDataAccessLog
from compliance_shield.models.breach    import DataBreachRecord


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    list_display  = ['user', 'consent_type', 'jurisdiction', 'granted',
                     'consent_version', 'granted_at', 'withdrawn_at']
    list_filter   = ['consent_type', 'jurisdiction', 'granted', 'consent_version']
    search_fields = ['user__email', 'consent_type']
    readonly_fields = [f.name for f in ConsentRecord._meta.fields]
    ordering      = ['-created_at']

    def has_add_permission(self, request):    return False
    def has_delete_permission(self, request, obj=None): return False
    def has_change_permission(self, request, obj=None): return False


@admin.register(DataDeletionRequest)
class DataDeletionRequestAdmin(admin.ModelAdmin):
    list_display  = ['user', 'reason', 'consent_type', 'jurisdiction', 'status', 'requested_at']
    list_filter   = ['status', 'jurisdiction']
    search_fields = ['user__email', 'reason']
    readonly_fields = ['user', 'reason', 'consent_type', 'jurisdiction', 'ip_address', 'requested_at']
    ordering      = ['-requested_at']


@admin.register(DataSubjectRequest)
class DataSubjectRequestAdmin(admin.ModelAdmin):
    list_display  = ['user', 'request_type', 'jurisdiction', 'status',
                     'deadline_indicator', 'received_at']
    list_filter   = ['status', 'jurisdiction', 'request_type']
    search_fields = ['user__email', 'request_detail']
    readonly_fields = ['user', 'request_type', 'jurisdiction', 'received_at',
                       'deadline_at', 'ip_address', 'user_agent']
    ordering      = ['deadline_at']
    actions       = ['mark_in_progress', 'mark_completed']

    def deadline_indicator(self, obj):
        if obj.status in ('completed', 'rejected', 'withdrawn'):
            return format_html('<span style="color:green;">Done</span>')
        if obj.is_overdue:
            return format_html('<span style="color:red;font-weight:bold;">OVERDUE</span>')
        return format_html('<span style="color:orange;">{} days left</span>', obj.days_remaining)
    deadline_indicator.short_description = 'Deadline'

    def mark_in_progress(self, request, queryset):
        for dsr in queryset:
            dsr.mark_in_progress(handled_by=request.user)
        self.message_user(request, f'{queryset.count()} requests marked in progress.')
    mark_in_progress.short_description = 'Mark selected as In Progress'

    def mark_completed(self, request, queryset):
        for dsr in queryset:
            dsr.mark_completed('Completed via bulk admin action.', handled_by=request.user)
        self.message_user(request, f'{queryset.count()} requests marked completed.')
    mark_completed.short_description = 'Mark selected as Completed'


@admin.register(DataRetentionPolicy)
class DataRetentionPolicyAdmin(admin.ModelAdmin):
    list_display  = ['jurisdiction', 'data_category', 'retention_years',
                     'action_on_expiry', 'is_active', 'last_reviewed']
    list_filter   = ['jurisdiction', 'action_on_expiry', 'is_active']
    search_fields = ['data_category', 'legal_basis']
    ordering      = ['jurisdiction', 'data_category']

    def retention_years(self, obj):
        return f'{round(obj.retention_days / 365, 1)} years'
    retention_years.short_description = 'Retention'


@admin.register(DataRetentionLog)
class DataRetentionLogAdmin(admin.ModelAdmin):
    list_display  = ['jurisdiction', 'data_category', 'action_taken',
                     'records_affected', 'run_by', 'run_at']
    list_filter   = ['jurisdiction', 'action_taken']
    readonly_fields = [f.name for f in DataRetentionLog._meta.fields]
    ordering      = ['-run_at']

    def has_add_permission(self, request):    return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(SensitiveDataAccessLog)
class SensitiveDataAccessLogAdmin(admin.ModelAdmin):
    list_display  = ['model_label', 'object_id', 'field_name', 'field_type',
                     'action', 'accessed_at']
    list_filter   = ['action', 'field_type', 'model_label']
    search_fields = ['object_id', 'field_name', 'model_label']
    readonly_fields = [f.name for f in SensitiveDataAccessLog._meta.fields]
    ordering      = ['-accessed_at']
    date_hierarchy = 'accessed_at'

    def has_add_permission(self, request):    return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(DataBreachRecord)
class DataBreachRecordAdmin(admin.ModelAdmin):
    list_display  = ['title', 'breach_type', 'severity', 'status',
                     'notification_status', 'estimated_affected_users', 'discovered_at']
    list_filter   = ['severity', 'status', 'breach_type']
    search_fields = ['title', 'nature_of_breach']
    readonly_fields = ['created_at', 'updated_at', 'contained_at', 'resolved_at']
    ordering      = ['-discovered_at']
    actions       = ['mark_contained', 'mark_resolved']

    fieldsets = (
        ('Breach Details',  {'fields': ('title', 'breach_type', 'severity', 'status', 'discovered_at', 'reported_by')}),
        ('Scope',           {'fields': ('affected_regions', 'affected_data_categories', 'estimated_affected_users', 'confirmed_affected_users')}),
        ('Description',     {'fields': ('nature_of_breach', 'likely_consequences', 'measures_taken')}),
        ('Containment',     {'fields': ('is_contained', 'contained_at', 'is_resolved', 'resolved_at')}),
        ('Notifications',   {'fields': ('authority_notified_at', 'authority_reference', 'users_notified_at', 'users_notification_method')}),
        ('Legal Hold',      {'fields': ('legal_hold', 'legal_hold_reason')}),
        ('Audit',           {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def notification_status(self, obj):
        deadlines = obj.get_authority_deadlines()
        overdue   = [r for r, d in deadlines.items() if d.get('is_overdue')]
        pending   = [r for r, d in deadlines.items() if d.get('status') == 'pending']
        if overdue:
            return format_html('<span style="color:red;font-weight:bold;">OVERDUE: {}</span>', ', '.join(overdue))
        if pending:
            return format_html('<span style="color:orange;">Pending: {}</span>', ', '.join(pending))
        return format_html('<span style="color:green;">All notified</span>')
    notification_status.short_description = 'Notification Status'

    def mark_contained(self, request, queryset):
        for b in queryset: b.mark_contained()
        self.message_user(request, f'{queryset.count()} breaches marked contained.')
    mark_contained.short_description = 'Mark selected as Contained'

    def mark_resolved(self, request, queryset):
        for b in queryset: b.mark_resolved()
        self.message_user(request, f'{queryset.count()} breaches marked resolved.')
    mark_resolved.short_description = 'Mark selected as Resolved'
