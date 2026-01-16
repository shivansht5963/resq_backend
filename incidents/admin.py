from django.contrib import admin
from django.utils.html import format_html
from django import forms
from .models import Beacon, BeaconProximity, PhysicalDevice, Incident, IncidentSignal, IncidentImage, IncidentEvent


class BeaconProximityInline(admin.TabularInline):
    """Inline admin for managing nearby beacons from a beacon."""
    model = BeaconProximity
    fk_name = 'from_beacon'
    extra = 1
    fields = ('to_beacon', 'priority')
    ordering = ('priority',)


class IncidentImageInline(admin.StackedInline):
    """Inline admin for displaying images attached to an incident."""
    model = IncidentImage
    extra = 0  # Don't show empty add rows
    fields = ('image', 'image_preview', 'description', 'uploaded_by', 'uploaded_at')
    readonly_fields = ('image_preview', 'uploaded_by', 'uploaded_at')
    can_delete = True
    
    def image_preview(self, obj):
        """Show image preview in inline."""
        if obj.image:
            return format_html(
                '<img src="{}" width="300" height="300" style="max-width: 100%; height: auto; object-fit: cover; border-radius: 5px;" />',
                obj.image.url
            )
        return "No image"
    image_preview.short_description = 'Preview'


class IncidentSignalInlineForm(forms.ModelForm):
    """Custom form for IncidentSignal inline that allows entering description as text."""
    
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
        help_text='Optional description for this signal'
    )
    
    class Meta:
        model = IncidentSignal
        fields = ('signal_type', 'source_user', 'source_device', 'ai_event', 'description')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # For existing signals, show description from details
            self.fields['description'].initial = self.instance.details.get('description', '')
            self.fields['description'].widget.attrs['readonly'] = True
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Store description in details JSON
        if not instance.details:
            instance.details = {}
        if self.cleaned_data.get('description'):
            instance.details['description'] = self.cleaned_data['description']
        if commit:
            instance.save()
        return instance


class IncidentSignalInline(admin.TabularInline):
    """Inline admin for displaying signals related to an incident."""
    model = IncidentSignal
    form = IncidentSignalInlineForm
    extra = 1
    fields = ('signal_type', 'source_user', 'source_device', 'ai_event', 'description', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Beacon)
class BeaconAdmin(admin.ModelAdmin):
    list_display = ('location_name', 'building', 'floor', 'uuid', 'major', 'minor', 'buzzer_status_display', 'is_active')
    list_filter = ('building', 'floor', 'is_active')
    search_fields = ('location_name', 'uuid', 'building', 'beacon_id')
    ordering = ('building', 'floor')
    readonly_fields = ('id', 'created_at', 'updated_at', 'active_incidents_display')
    inlines = [BeaconProximityInline]
    fieldsets = (
        ('Location Info', {'fields': ('location_name', 'building', 'floor')}),
        ('Beacon Identifiers', {'fields': ('uuid', 'major', 'minor', 'beacon_id')}),
        ('Coordinates', {'fields': ('latitude', 'longitude')}),
        ('Status', {'fields': ('is_active',)}),
        ('Active Incidents & Buzzer', {'fields': ('active_incidents_display',)}),
        ('Timestamps', {'fields': ('id', 'created_at', 'updated_at')}),
    )
    
    def buzzer_status_display(self, obj):
        """Display buzzer ON/OFF status - Green=ON, Red=OFF."""
        active_incidents = obj.incidents.filter(
            status__in=[Incident.Status.CREATED, Incident.Status.ASSIGNED, Incident.Status.IN_PROGRESS]
        )
        
        if not active_incidents.exists():
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 8px 12px; border-radius: 4px; font-weight: bold;">OFF</span>'
            )
        
        # Get most recent incident
        incident = active_incidents.order_by('-created_at').first()
        
        # Check if buzzer should be active
        should_buzz = incident.buzzer_status in [
            Incident.BuzzerStatus.PENDING,
            Incident.BuzzerStatus.ACTIVE
        ]
        
        if should_buzz:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 8px 12px; border-radius: 4px; font-weight: bold;">ON</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 8px 12px; border-radius: 4px; font-weight: bold;">OFF</span>'
            )
    buzzer_status_display.short_description = 'Buzzer'
    
    def active_incidents_display(self, obj):
        """Display all active incidents at this beacon with clickable links."""
        active_incidents = obj.incidents.filter(
            status__in=[Incident.Status.CREATED, Incident.Status.ASSIGNED, Incident.Status.IN_PROGRESS]
        ).order_by('-created_at')
        
        if not active_incidents.exists():
            return '<p style="color: #28a745;"><strong>✓ No active incidents at this beacon</strong></p>'
        
        html = '<div style="background: #f5f5f5; padding: 10px; border-radius: 5px;"><strong>Active Incidents:</strong><br><br>'
        
        for incident in active_incidents:
            status_emoji = '🔴' if incident.buzzer_status in [Incident.BuzzerStatus.PENDING, Incident.BuzzerStatus.ACTIVE] else '✓'
            
            incident_url = f'/admin/incidents/incident/{incident.id}/change/'
            html += f'''
            <div style="background: white; padding: 8px; margin: 5px 0; border-left: 4px solid #007bff;">
                {status_emoji} <a href="{incident_url}" style="color: #007bff; text-decoration: none;"><strong>{str(incident.id)[:8]}...</strong></a>
                <br>
                <small>Status: <strong>{incident.get_status_display()}</strong> | Priority: <strong>{incident.priority}</strong></small>
                <br>
                <small>Buzzer: <strong style="color: #dc3545;">{incident.get_buzzer_status_display()}</strong> | Created: <strong>{incident.created_at.strftime('%Y-%m-%d %H:%M')}</strong></small>
            </div>
            '''
        
        html += '</div>'
        return format_html(html)
    active_incidents_display.short_description = '📊 Active Incidents & Buzzer Status'


@admin.register(PhysicalDevice)
class PhysicalDeviceAdmin(admin.ModelAdmin):
    list_display = ('device_id', 'device_type', 'name', 'beacon', 'is_active', 'created_at')
    list_filter = ('device_type', 'is_active', 'beacon__building', 'created_at')
    search_fields = ('device_id', 'name', 'beacon__location_name')
    ordering = ('device_id',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        ('Device Info', {'fields': ('device_id', 'device_type', 'name')}),
        ('Location', {'fields': ('beacon',)}),
        ('Status', {'fields': ('is_active',)}),
        ('Timestamps', {'fields': ('id', 'created_at', 'updated_at')}),
    )


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ('id', 'beacon_id', 'beacon_location', 'status', 'priority', 'buzzer_status_display', 'report_type', 'location', 'signal_count', 'image_count', 'resolved_at')
    list_filter = ('status', 'priority', 'buzzer_status', 'report_type', 'resolution_type', 'created_at', 'beacon__building')
    search_fields = ('id', 'beacon__location_name', 'beacon__beacon_id', 'description', 'location', 'report_type')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'first_signal_time', 'last_signal_time', 'created_at', 'updated_at', 'total_alerts_sent', 'total_alerts_declined', 'buzzer_last_updated')
    inlines = [IncidentSignalInline, IncidentImageInline]
    fieldsets = (
        ('Location', {'fields': ('beacon', 'location')}),
        ('Report Info', {'fields': ('report_type', 'description')}),
        ('Status', {'fields': ('status', 'priority')}),
        ('Assignment', {'fields': ('current_assigned_guard', 'assigned_at')}),
        ('Buzzer Control', {
            'fields': ('buzzer_status', 'buzzer_last_updated'),
            'description': '🔔 Control buzzer status for IoT devices: INACTIVE (silent), PENDING (just reported), ACTIVE (guard assigned), ACKNOWLEDGED (guard en route), RESOLVED (complete)'
        }),
        ('Resolution', {'fields': ('resolved_by', 'resolved_at', 'resolution_type', 'resolution_notes')}),
        ('Alert Stats', {'fields': ('total_alerts_sent', 'total_alerts_declined')}),
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
    
    def buzzer_status_display(self, obj):
        """Display buzzer status with color indicator."""
        status_colors = {
            Incident.BuzzerStatus.INACTIVE: '#28a745',      # Green
            Incident.BuzzerStatus.PENDING: '#ffc107',        # Amber/Yellow
            Incident.BuzzerStatus.ACTIVE: '#dc3545',         # Red
            Incident.BuzzerStatus.ACKNOWLEDGED: '#fd7e14',   # Orange
            Incident.BuzzerStatus.RESOLVED: '#6c757d',       # Gray
        }
        
        status_icons = {
            Incident.BuzzerStatus.INACTIVE: '✓',             # Check mark
            Incident.BuzzerStatus.PENDING: '⏳',              # Hourglass
            Incident.BuzzerStatus.ACTIVE: '🔴',              # Red dot
            Incident.BuzzerStatus.ACKNOWLEDGED: '🟠',        # Orange dot
            Incident.BuzzerStatus.RESOLVED: '✓',             # Check mark
        }
        
        color = status_colors.get(obj.buzzer_status, '#999')
        icon = status_icons.get(obj.buzzer_status, '?')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 4px; font-weight: bold;">{} {}</span>',
            color,
            icon,
            obj.get_buzzer_status_display()
        )
    buzzer_status_display.short_description = '🔔 Buzzer'


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
    list_display = ('id', 'incident', 'signal_type', 'source_user', 'source_device', 'get_description', 'created_at')
    list_filter = ('signal_type', 'created_at', 'incident__beacon__building')
    search_fields = ('incident__id', 'source_user__full_name', 'source_device__device_id', 'details__description')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        ('Incident', {'fields': ('incident',)}),
        ('Signal', {'fields': ('signal_type', 'details')}),
        ('Sources', {'fields': ('source_user', 'source_device', 'ai_event')}),
        ('Timestamps', {'fields': ('id', 'created_at', 'updated_at')}),
    )
    
    def get_description(self, obj):
        """Extract description from details JSON for list view."""
        description = obj.details.get('description', '')
        if description:
            return description[:50] + '...' if len(description) > 50 else description
        return '—'
    get_description.short_description = 'Description'


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
            # Ensure we have a proper file stored
            try:
                image_url = obj.image.url
                return format_html(
                    '<img src="{}" width="300" height="200" style="max-width: 100%; height: auto; border-radius: 5px;" alt="Incident image" />',
                    image_url
                )
            except Exception as e:
                return f"Error loading image: {str(e)}"
        return "No image"
    image_preview.short_description = 'Preview'


@admin.register(IncidentEvent)
class IncidentEventAdmin(admin.ModelAdmin):
    """Admin interface for incident audit trail events."""
    list_display = ('id', 'incident', 'event_type', 'actor', 'target_guard', 'created_at')
    list_filter = ('event_type', 'created_at')
    search_fields = ('incident__id', 'actor__full_name', 'target_guard__full_name')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at')
    fieldsets = (
        ('Event Info', {'fields': ('incident', 'event_type')}),
        ('Participants', {'fields': ('actor', 'target_guard')}),
        ('State Changes', {'fields': ('previous_status', 'new_status', 'previous_priority', 'new_priority')}),
        ('Details', {'fields': ('details',)}),
        ('Timestamps', {'fields': ('id', 'created_at')}),
    )
