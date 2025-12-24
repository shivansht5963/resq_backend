from rest_framework import serializers
from .models import Conversation, Message


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for Conversation model."""

    reported_incident = serializers.StringRelatedField(read_only=True)
    beacon_incident = serializers.StringRelatedField(read_only=True)
    panic_incident = serializers.StringRelatedField(read_only=True)
    reported_incident_id = serializers.PrimaryKeyRelatedField(
        queryset=__import__('incidents.models', fromlist=['ReportedIncident']).ReportedIncident.objects.all(),
        source='reported_incident',
        write_only=True,
        required=False
    )
    beacon_incident_id = serializers.PrimaryKeyRelatedField(
        queryset=__import__('incidents.models', fromlist=['BeaconIncident']).BeaconIncident.objects.all(),
        source='beacon_incident',
        write_only=True,
        required=False
    )
    panic_incident_id = serializers.PrimaryKeyRelatedField(
        queryset=__import__('incidents.models', fromlist=['PanicButtonIncident']).PanicButtonIncident.objects.all(),
        source='panic_incident',
        write_only=True,
        required=False
    )
    message_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Conversation
        fields = ('reported_incident', 'reported_incident_id', 'beacon_incident', 'beacon_incident_id', 'panic_incident', 'panic_incident_id', 'message_count', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')

    def get_message_count(self, obj):
        return obj.messages.count()


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model."""

    sender = serializers.SerializerMethodField(read_only=True)
    conversation = serializers.StringRelatedField(read_only=True)
    conversation_id = serializers.PrimaryKeyRelatedField(
        queryset=Conversation.objects.all(),
        source='conversation',
        write_only=True
    )
    sender_id = serializers.PrimaryKeyRelatedField(
        queryset=__import__('accounts.models', fromlist=['User']).User.objects.all(),
        source='sender',
        write_only=True
    )

    class Meta:
        model = Message
        fields = ('id', 'conversation', 'conversation_id', 'sender', 'sender_id', 'message_text', 'created_at')
        read_only_fields = ('id', 'created_at')

    def get_sender(self, obj):
        return {
            'id': obj.sender.id,
            'email': obj.sender.email,
            'full_name': obj.sender.full_name,
            'role': obj.sender.role
        }


class MessageListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for message lists."""

    sender = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Message
        fields = ('id', 'sender', 'message_text', 'created_at')
        read_only_fields = ('id', 'created_at')
