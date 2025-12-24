from django.contrib import admin
from .models import AIEvent


@admin.register(AIEvent)
class AIEventAdmin(admin.ModelAdmin):
    list_display = ('reported_incident', 'beacon_incident', 'panic_incident', 'event_type', 'confidence_score', 'created_at')
    list_filter = ('event_type', 'created_at')
    search_fields = ('reported_incident__id', 'beacon_incident__id', 'panic_incident__id')
    ordering = ('-created_at',)
    readonly_fields = ('reported_incident', 'beacon_incident', 'panic_incident', 'event_type', 'confidence_score', 'created_at', 'details')
    fieldsets = (
        ('AI Detection', {'fields': ('reported_incident', 'beacon_incident', 'panic_incident', 'event_type')}),
        ('Confidence', {'fields': ('confidence_score',)}),
        ('Details', {'fields': ('details',)}),
        ('Metadata', {'fields': ('created_at',)}),
    )
    can_delete = False
