from rest_framework import serializers
from .models import Conversation, Message


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for Conversation model."""

    incident = serializers.StringRelatedField(read_only=True)
    incident_id = serializers.PrimaryKeyRelatedField(
        queryset=__import__('incidents.models', fromlist=['Incident']).Incident.objects.all(),
        source='incident',
        write_only=True,
        required=True
    )
    message_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Conversation
        fields = ('id', 'incident', 'incident_id', 'message_count', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

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
            'phone_number': obj.sender.phone_number,
            'role': obj.sender.role
        }


class MessageListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for message lists."""

    sender = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Message
        fields = ('id', 'sender', 'message_text', 'created_at')
        read_only_fields = ('id', 'created_at')
