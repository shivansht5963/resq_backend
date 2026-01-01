from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Device, PushNotificationLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ('email', 'full_name', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'created_at')
    search_fields = ('email', 'full_name')
    ordering = ('-created_at',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    readonly_fields = ('created_at', 'updated_at', 'last_login')
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('email', 'full_name', 'role', 'password1', 'password2')}),
    )


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    model = Device
    list_display = ('user', 'platform', 'is_active', 'last_seen_at', 'created_at')
    list_filter = ('platform', 'is_active', 'created_at')
    search_fields = ('user__email', 'user__full_name', 'token')
    ordering = ('-created_at',)
    readonly_fields = ('token', 'created_at', 'last_seen_at')
    fieldsets = (
        (None, {'fields': ('user', 'token')}),
        ('Device Info', {'fields': ('platform', 'is_active')}),
        ('Timestamps', {'fields': ('created_at', 'last_seen_at')}),
    )


@admin.register(PushNotificationLog)
class PushNotificationLogAdmin(admin.ModelAdmin):
    """Admin interface for push notification logs."""
    list_display = ('id', 'recipient', 'notification_type', 'status', 'title', 'queued_at', 'sent_at')
    list_filter = ('notification_type', 'status', 'queued_at')
    search_fields = ('recipient__email', 'recipient__full_name', 'title', 'body')
    ordering = ('-queued_at',)
    readonly_fields = ('id', 'queued_at')
    fieldsets = (
        ('Recipient', {'fields': ('recipient', 'device_token')}),
        ('Notification', {'fields': ('notification_type', 'title', 'body', 'data_payload')}),
        ('Context', {'fields': ('incident', 'guard_alert')}),
        ('Delivery Status', {'fields': ('status', 'expo_ticket_id', 'error_message')}),
        ('Retry Info', {'fields': ('retry_count', 'max_retries')}),
        ('Timestamps', {'fields': ('id', 'queued_at', 'sent_at', 'delivered_at', 'failed_at')}),
    )
