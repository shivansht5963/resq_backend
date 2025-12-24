from django.contrib import admin
from .models import Beacon, ESP32Device, Incident, IncidentSignal


@admin.register(Beacon)
class BeaconAdmin(admin.ModelAdmin):
    list_display = ('location_name', 'building', 'floor', 'uuid', 'major', 'minor', 'is_active')
    list_filter = ('building', 'floor', 'is_active')
    search_fields = ('location_name', 'uuid', 'building')
    ordering = ('building', 'floor')
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        ('Location Info', {'fields': ('location_name', 'building', 'floor')}),
        ('Beacon Identifiers', {'fields': ('uuid', 'major', 'minor', 'beacon_id')}),
        ('Coordinates', {'fields': ('latitude', 'longitude')}),
        ('Status', {'fields': ('is_active',)}),
        ('Timestamps', {'fields': ('id', 'created_at', 'updated_at')}),
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


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ('id', 'beacon', 'status', 'priority', 'signal_count', 'first_signal_time')
    list_filter = ('status', 'priority', 'created_at', 'beacon__building')
    search_fields = ('id', 'beacon__location_name', 'description')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'first_signal_time', 'last_signal_time', 'created_at', 'updated_at')
    fieldsets = (
        ('Location', {'fields': ('beacon',)}),
        ('Status', {'fields': ('status', 'priority')}),
        ('Description', {'fields': ('description',)}),
        ('Signals', {'fields': ('signal_count',), 'classes': ('readonly',)}),
        ('Timestamps', {'fields': ('first_signal_time', 'last_signal_time', 'created_at', 'updated_at')}),
    )
    
    def signal_count(self, obj):
        return obj.signals.count()
    signal_count.short_description = 'Signal Count'


@admin.register(IncidentSignal)
class IncidentSignalAdmin(admin.ModelAdmin):
    list_display = ('id', 'incident', 'signal_type', 'source_user', 'source_device', 'created_at')
    list_filter = ('signal_type', 'created_at', 'incident__beacon__building')
    search_fields = ('incident__id', 'source_user__full_name', 'source_device__device_id')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        ('Incident', {'fields': ('incident',)}),
        ('Signal', {'fields': ('signal_type', 'details')}),
        ('Sources', {'fields': ('source_user', 'source_device', 'ai_event')}),
        ('Timestamps', {'fields': ('id', 'created_at', 'updated_at')}),
    )
    fieldsets = (
        ('Alert', {'fields': ('id', 'esp32_device', 'student')}),
        ('Status', {'fields': ('status', 'priority')}),
        ('Details', {'fields': ('description',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
