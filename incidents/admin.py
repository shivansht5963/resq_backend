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
    list_display = ('id', 'beacon_id', 'beacon_location', 'status', 'priority_display', 'has_ai_detection', 'image_count_display', 'signal_count', 'buzzer_status_display', 'created_at')
    list_filter = ('status', 'priority', 'buzzer_status', 'report_type', 'resolution_type', 'created_at', 'beacon__building')
    search_fields = ('id', 'beacon__location_name', 'beacon__beacon_id', 'description', 'location', 'report_type')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'first_signal_time', 'last_signal_time', 'created_at', 'updated_at', 'total_alerts_sent', 'total_alerts_declined', 'buzzer_last_updated', 'ai_detection_info', 'images_summary')
    inlines = [IncidentSignalInline, IncidentImageInline]
    fieldsets = (
        ('Location', {'fields': ('beacon', 'location')}),
        ('Report Info', {'fields': ('report_type', 'description')}),
        ('Status', {'fields': ('status', 'priority')}),
        ('AI Detection', {'fields': ('ai_detection_info',), 'classes': ('collapse',)}),
        ('Images', {'fields': ('images_summary',)}),
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
    beacon_location.short_description = 'Location'
    
    def signal_count(self, obj):
        count = obj.signals.count()
        return format_html(
            '<span style="background: #17a2b8; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">📡 {}</span>',
            count
        )
    signal_count.short_description = 'Signals'
    
    def image_count(self, obj):
        return obj.images.count()
    image_count.short_description = 'Images'
    
    def image_count_display(self, obj):
        """Display image count with indicator."""
        count = obj.images.count()
        if count > 0:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 5px 10px; border-radius: 4px; font-weight: bold;">📷 {} image{}</span>',
                count,
                's' if count != 1 else ''
            )
        return format_html('<span style="color: #999;">No images</span>')
    image_count_display.short_description = '📷 Images'
    
    def has_ai_detection(self, obj):
        """Check if this incident was triggered by AI detection."""
        ai_signals = obj.signals.filter(
            signal_type__in=['VIOLENCE_DETECTED', 'SCREAM_DETECTED']
        )
        if ai_signals.exists():
            signal = ai_signals.first()
            if signal.ai_event:
                return format_html(
                    '<span style="background: #6f42c1; color: white; padding: 5px 10px; border-radius: 4px; font-weight: bold;">🤖 AI: {}</span>',
                    signal.ai_event.get_event_type_display()
                )
        return format_html('<span style="color: #999;">Manual Report</span>')
    has_ai_detection.short_description = '🤖 AI Detection'
    
    def ai_detection_info(self, obj):
        """Display AI detection information if this incident was triggered by AI."""
        ai_signals = obj.signals.filter(
            signal_type__in=['VIOLENCE_DETECTED', 'SCREAM_DETECTED']
        )
        
        if not ai_signals.exists():
            return format_html(
                '<div style="background: #f5f5f5; padding: 10px; border-radius: 5px; color: #999;">'
                'This incident was created manually, not by AI detection.'
                '</div>'
            )
        
        html = '<div style="background: #f5f5f5; padding: 10px; border-radius: 5px;">'
        
        for signal in ai_signals:
            if signal.ai_event:
                ai = signal.ai_event
                confidence_color = '#28a745' if ai.confidence_score >= 0.8 else '#ffc107' if ai.confidence_score >= 0.75 else '#dc3545'
                
                html += f'''
                <div style="background: white; padding: 10px; margin: 5px 0; border-left: 4px solid {confidence_color}; border-radius: 3px;">
                    <strong>🤖 AI Event #{ai.id}</strong><br>
                    <strong>Type:</strong> {ai.get_event_type_display()}<br>
                    <strong>Confidence:</strong> <span style="background: {confidence_color}; color: white; padding: 3px 6px; border-radius: 3px;">{ai.confidence_score:.1%}</span><br>
                    <strong>Device:</strong> {ai.details.get('device_id', 'Unknown')}<br>
                    <strong>Description:</strong> {ai.details.get('description', 'N/A')}<br>
                    <strong>Detected:</strong> {ai.created_at.strftime('%Y-%m-%d %H:%M:%S')}
                </div>
                '''
        
        html += '</div>'
        return format_html(html)
    ai_detection_info.short_description = '🤖 AI Detection Details'
    
    def images_summary(self, obj):
        """Display summary of images attached to this incident."""
        images = obj.images.all().order_by('-uploaded_at')
        
        if not images.exists():
            return format_html(
                '<div style="background: #f5f5f5; padding: 10px; border-radius: 5px; color: #999;">'
                'No images attached to this incident.'
                '</div>'
            )
        
        html = '<div style="background: #f5f5f5; padding: 10px; border-radius: 5px;">'
        html += f'<strong>📷 {images.count()} image{"s" if images.count() != 1 else ""} attached:</strong><br><br>'
        
        for img in images[:5]:  # Show first 5
            source = '🤖 AI Detection' if not img.uploaded_by else f'👤 {img.uploaded_by.email}'
            try:
                url = img.image.url
                html += f'''
                <div style="background: white; padding: 8px; margin: 5px 0; border-left: 4px solid #28a745; border-radius: 3px;">
                    <strong>#{img.id}</strong> - {source}<br>
                    <small>{img.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')}</small><br>
                    <a href="{url}" target="_blank" style="color: #007bff; text-decoration: none; font-size: 12px;">📥 View Full Image</a>
                </div>
                '''
            except Exception as e:
                html += f'<div style="color: #dc3545;">Error: {str(e)}</div>'
        
        if images.count() > 5:
            html += f'<div style="color: #999; margin-top: 10px;">... and {images.count() - 5} more</div>'
        
        html += '</div>'
        return format_html(html)
    images_summary.short_description = '📷 Images Summary'
    
    def priority_display(self, obj):
        """Display priority with color."""
        priority_colors = {
            1: '#ffc107',  # LOW - yellow
            2: '#17a2b8',  # MEDIUM - blue
            3: '#fd7e14',  # HIGH - orange
            4: '#dc3545',  # CRITICAL - red
        }
        color = priority_colors.get(obj.priority, '#999')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 4px; font-weight: bold;">{}</span>',
            color,
            obj.get_priority_display()
        )
    priority_display.short_description = '⚠️ Priority'
    
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
    list_display = ('id', 'incident_link', 'get_incident_priority', 'uploaded_by', 'image_source', 'uploaded_at', 'image_preview')
    list_filter = ('uploaded_at', 'incident__beacon__building', 'incident__priority')
    search_fields = ('incident__id', 'uploaded_by__full_name', 'description')
    ordering = ('-uploaded_at',)
    readonly_fields = ('id', 'uploaded_at', 'uploaded_by', 'image_preview', 'image_url_display', 'file_info')
    fieldsets = (
        ('Image Info', {'fields': ('incident', 'image', 'image_preview')}),
        ('Image URL', {'fields': ('image_url_display',)}),
        ('Metadata', {'fields': ('uploaded_by', 'description', 'image_source')}),
        ('File Details', {'fields': ('file_info',), 'classes': ('collapse',)}),
        ('Timestamps', {'fields': ('id', 'uploaded_at')}),
    )
    
    def image_preview(self, obj):
        if obj.image:
            # Ensure we have a proper file stored
            try:
                image_url = obj.image.url
                return format_html(
                    '<img src="{}" width="400" height="300" style="max-width: 100%; height: auto; border-radius: 5px; border: 2px solid #007bff;" alt="Incident image" />',
                    image_url
                )
            except Exception as e:
                return f"Error loading image: {str(e)}"
        return "No image"
    image_preview.short_description = 'Preview'
    
    def image_url_display(self, obj):
        """Display the public GCS URL."""
        if obj.image:
            try:
                url = obj.image.url
                return format_html(
                    '<div style="word-break: break-all; font-family: monospace; background: #f5f5f5; padding: 10px; border-radius: 5px;">'
                    '<strong>Public URL:</strong><br>'
                    '<a href="{}" target="_blank" style="color: #007bff; text-decoration: none;">{}</a>'
                    '<br><br>'
                    '<button onclick="navigator.clipboard.writeText(\'{}\');" style="padding: 5px 10px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">📋 Copy URL</button>'
                    '</div>',
                    url,
                    url,
                    url
                )
            except Exception as e:
                return f"Error: {str(e)}"
        return "No URL available"
    image_url_display.short_description = 'GCS URL'
    
    def file_info(self, obj):
        """Display file information."""
        if obj.image:
            try:
                file_size = obj.image.size
                file_name = obj.image.name
                storage = obj.image.storage.__class__.__name__
                
                # Format file size
                if file_size < 1024:
                    size_str = f"{file_size} bytes"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.2f} KB"
                else:
                    size_str = f"{file_size / (1024 * 1024):.2f} MB"
                
                return format_html(
                    '<div style="font-family: monospace; background: #f5f5f5; padding: 10px; border-radius: 5px;">'
                    '<strong>File Name:</strong> {}<br>'
                    '<strong>File Size:</strong> {}<br>'
                    '<strong>Storage:</strong> {}<br>'
                    '<strong>Path:</strong> {}'
                    '</div>',
                    file_name.split('/')[-1],
                    size_str,
                    storage,
                    file_name
                )
            except Exception as e:
                return f"Error: {str(e)}"
        return "No file"
    file_info.short_description = 'File Information'
    
    def incident_link(self, obj):
        """Display clickable link to incident."""
        incident_url = f'/admin/incidents/incident/{obj.incident.id}/change/'
        return format_html(
            '<a href="{}" style="color: #007bff; text-decoration: none; font-weight: bold;">🔗 {}</a>',
            incident_url,
            str(obj.incident.id)[:8]
        )
    incident_link.short_description = 'Incident'
    
    def get_incident_priority(self, obj):
        """Display incident priority with color."""
        priority_colors = {
            1: '#ffc107',  # LOW - yellow
            2: '#17a2b8',  # MEDIUM - blue
            3: '#fd7e14',  # HIGH - orange
            4: '#dc3545',  # CRITICAL - red
        }
        color = priority_colors.get(obj.incident.priority, '#999')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 4px; font-weight: bold;">{}</span>',
            color,
            obj.incident.get_priority_display()
        )
    get_incident_priority.short_description = '⚠️ Priority'
    
    def image_source(self, obj):
        """Show if image was uploaded by user or AI detection."""
        if obj.uploaded_by:
            return format_html(
                '<span style="background: #007bff; color: white; padding: 3px 8px; border-radius: 3px;">👤 User: {}</span>',
                obj.uploaded_by.email
            )
        else:
            return format_html(
                '<span style="background: #6f42c1; color: white; padding: 3px 8px; border-radius: 3px;">🤖 AI Detection</span>'
            )
    image_source.short_description = 'Source'


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
