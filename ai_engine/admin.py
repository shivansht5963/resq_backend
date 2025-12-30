from django.contrib import admin
from django.utils.html import format_html
from .models import AIEvent


@admin.register(AIEvent)
class AIEventAdmin(admin.ModelAdmin):
    list_display = ('beacon', 'event_type', 'confidence_score', 'get_description', 'created_at')
    list_filter = ('event_type', 'created_at')
    search_fields = ('beacon__location_name', 'beacon__uuid', 'details__description')
    ordering = ('-created_at',)
    readonly_fields = ('beacon', 'event_type', 'confidence_score', 'created_at', 'details', 'get_description_display')
    fieldsets = (
        ('AI Detection', {'fields': ('beacon', 'event_type')}),
        ('Confidence', {'fields': ('confidence_score',)}),
        ('Description', {'fields': ('get_description_display',)}),
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
