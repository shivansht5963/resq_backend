from django.contrib import admin
from .models import GuardProfile, GuardAssignment, GuardAlert


@admin.register(GuardProfile)
class GuardProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_active', 'is_available', 'is_assigned', 'current_beacon', 'last_active_at')
    
    @admin.display(boolean=True, description='Assigned?')
    def is_assigned(self, obj):
        return obj.is_assigned
    list_filter = ('is_active', 'is_available', 'created_at')
    search_fields = ('user__email', 'user__full_name', 'current_beacon__location_name')
    ordering = ('-last_active_at',)
    readonly_fields = ('created_at', 'updated_at', 'last_beacon_update')
    fieldsets = (
        ('Guard Info', {'fields': ('user', 'is_active', 'is_available')}),
        ('Location', {'fields': ('current_beacon', 'last_beacon_update')}),
        ('Activity', {'fields': ('last_active_at',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(GuardAssignment)
class GuardAssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'guard', 'incident', 'is_active', 'assigned_at')
    list_filter = ('is_active', 'assigned_at')
    search_fields = ('guard__user__email', 'incident__id', 'incident__beacon__location_name')
    ordering = ('-assigned_at',)
    readonly_fields = ('id', 'assigned_at', 'updated_at')
    fieldsets = (
        ('Assignment', {'fields': ('id', 'guard', 'incident')}),
        ('Status', {'fields': ('is_active',)}),
        ('Timestamps', {'fields': ('assigned_at', 'updated_at')}),
    )


@admin.register(GuardAlert)
class GuardAlertAdmin(admin.ModelAdmin):
    """
    Admin for monitoring guard alerts in incident response.
    Shows alert status, type, priority ranking, and push notification tracking.
    """
    list_display = ('id', 'incident', 'guard', 'alert_type', 'status', 'priority_rank', 'requires_response', 'alert_sent_at')
    list_filter = ('status', 'alert_type', 'requires_response', 'priority_rank', 'alert_sent_at', 'incident__beacon__building')
    search_fields = ('guard__email', 'guard__full_name', 'incident__id')
    ordering = ('-alert_sent_at',)
    readonly_fields = ('id', 'alert_sent_at', 'updated_at', 'responded_at')
    fieldsets = (
        ('Alert Info', {'fields': ('id', 'incident', 'guard', 'alert_type')}),
        ('Response', {'fields': ('status', 'requires_response', 'priority_rank', 'distance_km', 'response_deadline')}),
        ('Assignment', {'fields': ('assignment',)}),
        ('Push Notification', {'fields': ('push_notification_sent', 'push_notification_sent_at', 'push_notification_delivered', 'push_notification_error')}),
        ('Response Tracking', {'fields': ('responded_at', 'decline_reason')}),
        ('Timestamps', {'fields': ('alert_sent_at', 'updated_at')}),
    )
