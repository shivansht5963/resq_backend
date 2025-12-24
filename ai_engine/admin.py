from django.contrib import admin
from .models import AIEvent


@admin.register(AIEvent)
class AIEventAdmin(admin.ModelAdmin):
    list_display = ('beacon', 'event_type', 'confidence_score', 'created_at')
    list_filter = ('event_type', 'created_at')
    search_fields = ('beacon__uuid', 'beacon__name')
    ordering = ('-created_at',)
    readonly_fields = ('beacon', 'event_type', 'confidence_score', 'created_at', 'details')
    fieldsets = (
        ('AI Detection', {'fields': ('beacon', 'event_type')}),
        ('Confidence', {'fields': ('confidence_score',)}),
        ('Details', {'fields': ('details',)}),
        ('Metadata', {'fields': ('created_at',)}),
    )
    can_delete = False
