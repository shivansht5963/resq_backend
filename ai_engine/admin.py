from django.contrib import admin
from django.utils.html import format_html
from .models import AIEvent


@admin.register(AIEvent)
class AIEventAdmin(admin.ModelAdmin):
    list_display = ('beacon', 'event_type', 'confidence_score', 'get_description', 'image_count_display', 'incident_created', 'created_at')
    list_filter = ('event_type', 'created_at', 'beacon__building')
    search_fields = ('beacon__location_name', 'beacon__uuid', 'beacon__beacon_id', 'details__description')
    ordering = ('-created_at',)
    readonly_fields = ('beacon', 'event_type', 'confidence_score', 'created_at', 'details', 'get_description_display', 'image_count_display', 'incident_link', 'device_info')
    fieldsets = (
        ('AI Detection', {'fields': ('beacon', 'event_type')}),
        ('Confidence', {'fields': ('confidence_score',)}),
        ('Description', {'fields': ('get_description_display',)}),
        ('Images & Incident', {'fields': ('image_count_display', 'incident_link')}),
        ('Device Info', {'fields': ('device_info',), 'classes': ('collapse',)}),
        ('Details', {'fields': ('details',), 'classes': ('collapse',)}),
        ('Metadata', {'fields': ('created_at',)}),
    )
    can_delete = False
    
    def get_description(self, obj):
        """Extract description from details JSON for list view."""
        description = obj.details.get('description', 'N/A')
        if description:
            return description[:50] + '...' if len(description) > 50 else description
        return '—'
    get_description.short_description = 'Description'
    
    def get_description_display(self, obj):
        """Display full description in detail view."""
        description = obj.details.get('description', 'N/A')
        if description:
            return format_html('<pre style="white-space: pre-wrap; word-wrap: break-word;">{}</pre>', description)
        return '—'
    get_description_display.short_description = 'Description'
    
    def image_count_display(self, obj):
        """Show count of images attached to related incident."""
        images_in_details = obj.details.get('images_count', 0)
        
        # Try to find related incident through signal
        related_incident = None
        if hasattr(obj, 'signal_set'):
            signal = obj.signal_set.first()
            if signal:
                related_incident = signal.incident
        
        if related_incident:
            image_count = related_incident.images.count()
            if image_count > 0:
                return format_html(
                    '<span style="background-color: #28a745; color: white; padding: 5px 10px; border-radius: 4px; font-weight: bold;">📷 {} image{}</span>',
                    image_count,
                    's' if image_count != 1 else ''
                )
        
        if images_in_details > 0:
            return format_html(
                '<span style="background-color: #ffc107; color: black; padding: 5px 10px; border-radius: 4px; font-weight: bold;">📷 {} image{}</span>',
                images_in_details,
                's' if images_in_details != 1 else ''
            )
        
        return format_html('<span style="color: #999;">No images</span>')
    image_count_display.short_description = '📷 Images'
    
    def incident_created(self, obj):
        """Show if this AI event triggered an incident."""
        if hasattr(obj, 'signal_set'):
            signal = obj.signal_set.first()
            if signal:
                incident = signal.incident
                incident_url = f'/admin/incidents/incident/{incident.id}/change/'
                priority_colors = {
                    1: '#ffc107',  # LOW - yellow
                    2: '#17a2b8',  # MEDIUM - blue
                    3: '#fd7e14',  # HIGH - orange
                    4: '#dc3545',  # CRITICAL - red
                }
                color = priority_colors.get(incident.priority, '#999')
                return format_html(
                    '<a href="{}" style="background-color: {}; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none; font-weight: bold;">🔴 {}</a>',
                    incident_url,
                    color,
                    incident.get_priority_display()
                )
        return format_html('<span style="color: #999;">—</span>')
    incident_created.short_description = '🚨 Incident'
    
    def device_info(self, obj):
        """Display device information from details."""
        device_id = obj.details.get('device_id', 'Not provided')
        ai_type = obj.details.get('ai_type', 'Unknown')
        raw_confidence = obj.details.get('raw_confidence', obj.confidence_score)
        
        return format_html(
            '<div style="font-family: monospace; background: #f5f5f5; padding: 10px; border-radius: 5px;">'
            '<strong>Device ID:</strong> {}<br>'
            '<strong>AI Type:</strong> {}<br>'
            '<strong>Raw Confidence:</strong> {:.2f}</div>',
            device_id,
            ai_type,
            raw_confidence
        )
    device_info.short_description = 'Device Info'
    
    def incident_link(self, obj):
        """Display link to related incident if it exists."""
        if hasattr(obj, 'signal_set'):
            signal = obj.signal_set.first()
            if signal:
                incident = signal.incident
                incident_url = f'/admin/incidents/incident/{incident.id}/change/'
                return format_html(
                    '<a href="{}" style="color: #007bff; text-decoration: none; font-weight: bold;">View Incident {}</a>',
                    incident_url,
                    str(incident.id)[:8]
                )
        return format_html('<span style="color: #999;">No incident created (below threshold)</span>')
    incident_link.short_description = '🔗 Related Incident'
