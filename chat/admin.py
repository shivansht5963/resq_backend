from django.contrib import admin
from .models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('reported_incident', 'beacon_incident', 'panic_incident', 'created_at', 'updated_at')
    list_filter = ('created_at',)
    search_fields = ('reported_incident__id', 'beacon_incident__id', 'panic_incident__id')
    ordering = ('-created_at',)
    readonly_fields = ('reported_incident', 'beacon_incident', 'panic_incident', 'created_at', 'updated_at')
    fieldsets = (
        ('Conversation Info', {'fields': ('reported_incident', 'beacon_incident', 'panic_incident')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('sender', 'message_text', 'created_at')
    fields = ('sender', 'message_text', 'created_at')
    can_delete = False


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'created_at')
    list_filter = ('created_at', 'sender')
    search_fields = ('conversation__incident__id', 'sender__email', 'message_text')
    ordering = ('-created_at',)
    readonly_fields = ('conversation', 'sender', 'message_text', 'created_at')
    fieldsets = (
        ('Message Info', {'fields': ('conversation', 'sender')}),
        ('Content', {'fields': ('message_text',)}),
        ('Metadata', {'fields': ('created_at',)}),
    )
    can_delete = False
