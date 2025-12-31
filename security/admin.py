from django.contrib import admin
from .models import GuardProfile, GuardAssignment, GuardAlert


@admin.register(GuardProfile)
class GuardProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_active', 'is_available', 'current_beacon', 'last_active_at')
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
    Shows alert status, priority ranking, and assignment linkage.
    """
    list_display = ('id', 'incident', 'guard', 'status', 'priority_rank', 'alert_sent_at')
    list_filter = ('status', 'priority_rank', 'alert_sent_at', 'incident__beacon__building')
    search_fields = ('guard__user__email', 'guard__user__full_name', 'incident__id')
    ordering = ('-alert_sent_at',)
    readonly_fields = ('id', 'alert_sent_at', 'updated_at')
    fieldsets = (
        ('Alert Info', {'fields': ('id', 'incident', 'guard')}),
        ('Status', {'fields': ('status', 'priority_rank', 'distance_km')}),
        ('Assignment', {'fields': ('assignment',)}),
        ('Timestamps', {'fields': ('alert_sent_at', 'updated_at')}),
    )

