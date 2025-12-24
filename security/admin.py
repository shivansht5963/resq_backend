from django.contrib import admin
from .models import GuardProfile, GuardAssignment, DeviceToken


@admin.register(GuardProfile)
class GuardProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_available', 'last_active_at', 'created_at')
    list_filter = ('is_available', 'created_at')
    search_fields = ('user__email', 'user__full_name')
    ordering = ('-last_active_at',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Guard Info', {'fields': ('user',)}),
        ('Status', {'fields': ('is_available', 'last_active_at')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(GuardAssignment)
class GuardAssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'guard', 'reported_incident', 'beacon_incident', 'panic_incident', 'is_active', 'assigned_at')
    list_filter = ('is_active', 'assigned_at')
    search_fields = ('guard__email', 'reported_incident__id', 'beacon_incident__id', 'panic_incident__id')
    ordering = ('-assigned_at',)
    readonly_fields = ('id', 'assigned_at', 'updated_at')
    fieldsets = (
        ('Assignment', {'fields': ('id', 'guard', 'reported_incident', 'beacon_incident', 'panic_incident')}),
        ('Status', {'fields': ('is_active',)}),
        ('Timestamps', {'fields': ('assigned_at', 'updated_at')}),
    )


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'platform', 'is_active', 'created_at')
    list_filter = ('platform', 'is_active', 'created_at')
    search_fields = ('user__email', 'token')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at', 'token')
    fieldsets = (
        ('Device Info', {'fields': ('user', 'token', 'platform')}),
        ('Status', {'fields': ('is_active',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
