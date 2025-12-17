
from django.contrib import admin
from .models import PatientSession, MessageLog, ClinicianAvailability, EscalationQueue


@admin.register(PatientSession)
class PatientSessionAdmin(admin.ModelAdmin):
    """Admin interface for patient sessions"""
    
    list_display = [
        'phone_number', 'state', 'age', 'gender',
        'escalated_to_clinician', 'assigned_clinician',
        'created_at', 'last_message_at'
    ]
    
    list_filter = [
        'state', 'escalated_to_clinician', 'gender',
        'created_at', 'assigned_clinician'
    ]
    
    search_fields = ['phone_number', 'escalation_reason']
    
    readonly_fields = ['created_at', 'updated_at', 'last_message_at']
    
    fieldsets = (
        ('Contact Information', {
            'fields': ('phone_number', 'state')
        }),
        ('Patient Profile', {
            'fields': ('age', 'gender', 'weight', 'medical_history')
        }),
        ('Session Data', {
            'fields': ('session_data', 'ai_overview', 'recommendation_plan'),
            'classes': ('collapse',)
        }),
        ('Escalation', {
            'fields': (
                'escalated_to_clinician', 'assigned_clinician',
                'escalation_reason'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_message_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('assigned_clinician')


@admin.register(MessageLog)
class MessageLogAdmin(admin.ModelAdmin):
    """Admin interface for message logs"""
    
    list_display = [
        'session', 'get_phone_number', 'is_from_user',
        'is_from_clinician', 'get_clinician_name',
        'get_message_preview', 'created_at'
    ]
    
    list_filter = [
        'is_from_user', 'is_from_clinician', 'created_at'
    ]
    
    search_fields = [
        'session__phone_number', 'content',
        'clinician__username', 'clinician__first_name', 'clinician__last_name'
    ]
    
    readonly_fields = ['created_at']
    
    date_hierarchy = 'created_at'
    
    def get_phone_number(self, obj):
        return obj.session.phone_number
    get_phone_number.short_description = 'Phone Number'
    get_phone_number.admin_order_field = 'session__phone_number'
    
    def get_clinician_name(self, obj):
        if obj.clinician:
            return obj.clinician.get_full_name()
        return '-'
    get_clinician_name.short_description = 'Clinician'
    
    def get_message_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    get_message_preview.short_description = 'Message'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('session', 'clinician')


@admin.register(EscalationQueue)
class EscalationQueueAdmin(admin.ModelAdmin):
    """Admin interface for escalation queue"""
    
    list_display = [
        'get_phone_number', 'priority', 'get_assigned_to',
        'is_resolved', 'created_at', 'assigned_at'
    ]
    
    list_filter = [
        'priority', 'is_resolved', 'created_at', 'assigned_to'
    ]
    
    search_fields = [
        'session__phone_number', 'reason', 'ai_assessment',
        'assigned_to__username', 'assigned_to__first_name', 'assigned_to__last_name'
    ]
    
    readonly_fields = ['created_at', 'assigned_at', 'resolved_at']
    
    fieldsets = (
        ('Escalation Details', {
            'fields': ('session', 'priority', 'reason')
        }),
        ('AI Assessment', {
            'fields': ('ai_assessment',),
            'classes': ('collapse',)
        }),
        ('Assignment', {
            'fields': ('assigned_to', 'is_resolved')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'assigned_at', 'resolved_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_phone_number(self, obj):
        return obj.session.phone_number
    get_phone_number.short_description = 'Patient'
    get_phone_number.admin_order_field = 'session__phone_number'
    
    def get_assigned_to(self, obj):
        if obj.assigned_to:
            return obj.assigned_to.get_full_name()
        return 'Unassigned'
    get_assigned_to.short_description = 'Assigned To'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('session', 'assigned_to')


@admin.register(ClinicianAvailability)
class ClinicianAvailabilityAdmin(admin.ModelAdmin):
    """Admin interface for clinician availability"""
    
    list_display = [
        'get_clinician_name', 'is_available', 'current_active_cases',
        'max_concurrent_cases', 'specialization', 'last_active'
    ]
    
    list_filter = ['is_available', 'specialization']
    
    search_fields = [
        'clinician__username', 'clinician__first_name',
        'clinician__last_name', 'specialization'
    ]
    
    readonly_fields = ['last_active']
    
    def get_clinician_name(self, obj):
        return obj.clinician.get_full_name()
    get_clinician_name.short_description = 'Clinician'
    get_clinician_name.admin_order_field = 'clinician__first_name'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('clinician')