from django.contrib import admin
from .models import Beacon, ESP32Device, ReportedIncident, BeaconIncident, PanicButtonIncident


@admin.register(Beacon)
class BeaconAdmin(admin.ModelAdmin):
    list_display = ('location_name', 'building', 'floor', 'uuid', 'major', 'minor')
    list_filter = ('building', 'floor')
    search_fields = ('location_name', 'uuid', 'building')
    ordering = ('building', 'floor')
    readonly_fields = ('id', 'created_at')
    fieldsets = (
        ('Location Info', {'fields': ('location_name', 'building', 'floor')}),
        ('Beacon Identifiers', {'fields': ('uuid', 'major', 'minor')}),
        ('Metadata', {'fields': ('id', 'created_at')}),
    )


@admin.register(ESP32Device)
class ESP32DeviceAdmin(admin.ModelAdmin):
    list_display = ('device_id', 'name', 'beacon', 'is_active', 'created_at')
    list_filter = ('is_active', 'beacon__building', 'created_at')
    search_fields = ('device_id', 'name', 'beacon__location_name')
    ordering = ('device_id',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        ('Device Info', {'fields': ('device_id', 'name')}),
        ('Location', {'fields': ('beacon',)}),
        ('Status', {'fields': ('is_active',)}),
        ('Timestamps', {'fields': ('id', 'created_at', 'updated_at')}),
    )


@admin.register(ReportedIncident)
class ReportedIncidentAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'status', 'priority', 'beacon', 'created_at')
    list_filter = ('status', 'priority', 'created_at', 'beacon__building')
    search_fields = ('student__email', 'student__full_name', 'id', 'description')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        ('Reporter', {'fields': ('id', 'student')}),
        ('Location', {'fields': ('beacon',), 'description': 'Optional: Beacon location'}),
        ('Status', {'fields': ('status', 'priority')}),
        ('Description', {'fields': ('description',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(BeaconIncident)
class BeaconIncidentAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'beacon', 'status', 'priority', 'created_at')
    list_filter = ('status', 'priority', 'beacon__building', 'beacon__floor', 'created_at')
    search_fields = ('student__email', 'student__full_name', 'beacon__location_name', 'id')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        ('Detection', {'fields': ('id', 'student', 'beacon')}),
        ('Status', {'fields': ('status', 'priority')}),
        ('Details', {'fields': ('description',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(PanicButtonIncident)
class PanicButtonIncidentAdmin(admin.ModelAdmin):
    list_display = ('id', 'esp32_device', 'student', 'status', 'priority', 'created_at')
    list_filter = ('status', 'priority', 'esp32_device__beacon__building', 'created_at')
    search_fields = ('esp32_device__device_id', 'esp32_device__name', 'student__email', 'id')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        ('Alert', {'fields': ('id', 'esp32_device', 'student')}),
        ('Status', {'fields': ('status', 'priority')}),
        ('Details', {'fields': ('description',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
