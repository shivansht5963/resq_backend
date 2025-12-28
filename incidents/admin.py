from django.contrib import admin
from django.utils.html import format_html
from .models import Beacon, BeaconProximity, ESP32Device, Incident, IncidentSignal, IncidentImage


class BeaconProximityInline(admin.TabularInline):
    """Inline admin for managing nearby beacons from a beacon."""
    model = BeaconProximity
    fk_name = 'from_beacon'
    extra = 1
    fields = ('to_beacon', 'priority')
    ordering = ('priority',)


class IncidentImageInline(admin.TabularInline):
    """Inline admin for displaying images attached to an incident."""
    model = IncidentImage
    extra = 1
    fields = ('image', 'description', 'uploaded_by', 'uploaded_at')
    readonly_fields = ('uploaded_by', 'uploaded_at')
    can_delete = True


class IncidentSignalInline(admin.TabularInline):
    """Inline admin for displaying signals related to an incident."""
    model = IncidentSignal
    extra = 0
    fields = ('signal_type', 'source_user', 'source_device', 'ai_event', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Beacon)
class BeaconAdmin(admin.ModelAdmin):
    list_display = ('location_name', 'building', 'floor', 'uuid', 'major', 'minor', 'is_active')
    list_filter = ('building', 'floor', 'is_active')
    search_fields = ('location_name', 'uuid', 'building')
    ordering = ('building', 'floor')
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines = [BeaconProximityInline]
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
    list_display = ('id', 'beacon_id', 'beacon_location', 'status', 'priority', 'report_type', 'location', 'signal_count', 'image_count', 'first_signal_time')
    list_filter = ('status', 'priority', 'report_type', 'created_at', 'beacon__building')
    search_fields = ('id', 'beacon__location_name', 'beacon__beacon_id', 'description', 'location', 'report_type')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'first_signal_time', 'last_signal_time', 'created_at', 'updated_at')
    inlines = [IncidentSignalInline, IncidentImageInline]
    fieldsets = (
        ('Location', {'fields': ('beacon', 'location')}),
        ('Report Info', {'fields': ('report_type', 'description')}),
        ('Status', {'fields': ('status', 'priority')}),
        ('Timestamps', {'fields': ('first_signal_time', 'last_signal_time', 'created_at', 'updated_at')}),
    )
    
    def beacon_id(self, obj):
        return obj.beacon.beacon_id if obj.beacon else "N/A"
    beacon_id.short_description = 'Beacon ID'
    
    def beacon_location(self, obj):
        return obj.beacon.location_name if obj.beacon else "N/A"
    beacon_location.short_description = 'Beacon Location'
    
    def signal_count(self, obj):
        return obj.signals.count()
    signal_count.short_description = 'Signals'
    
    def image_count(self, obj):
        return obj.images.count()
    image_count.short_description = 'Images'


@admin.register(BeaconProximity)
class BeaconProximityAdmin(admin.ModelAdmin):
    """
    Admin interface for managing beacon proximity relationships.
    Used for expanding-radius guard search in incident assignment.
    """
    list_display = ('from_beacon', 'to_beacon', 'priority')
    list_filter = ('priority', 'from_beacon__building')
    search_fields = ('from_beacon__location_name', 'to_beacon__location_name')
    ordering = ('from_beacon', 'priority')
    readonly_fields = ('id',)
    fieldsets = (
        ('Beacon Relationship', {'fields': ('from_beacon', 'to_beacon')}),
        ('Priority', {
            'fields': ('priority',),
            'description': 'Lower = higher priority. 1=same floor, 2=adjacent floor, 3+=far zones'
        }),
    )
    
    def get_search_results(self, request, queryset, search_term):
        """Enhanced search to find by either beacon."""
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        return queryset, use_distinct


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


@admin.register(IncidentImage)
class IncidentImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'incident', 'uploaded_by', 'uploaded_at', 'image_preview')
    list_filter = ('uploaded_at', 'incident__beacon__building')
    search_fields = ('incident__id', 'uploaded_by__full_name', 'description')
    ordering = ('-uploaded_at',)
    readonly_fields = ('id', 'uploaded_at', 'uploaded_by', 'image_preview')
    fieldsets = (
        ('Image Info', {'fields': ('incident', 'image', 'image_preview')}),
        ('Metadata', {'fields': ('uploaded_by', 'description')}),
        ('Timestamps', {'fields': ('id', 'uploaded_at')}),
    )
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="300" height="200" style="max-width: 100%; height: auto;" alt="Incident image" />',
                obj.image.url
            )
        return "No image"
    image_preview.short_description = 'Preview'
    image_preview.allow_tags = True
    image_preview.short_description = 'Preview'
