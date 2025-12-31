"""
ViewSets for chat app.
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.db.models import Q
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer, MessageListSerializer
from accounts.push_notifications import PushNotificationService


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Conversations (1-to-1 chats linked to incidents).
    
    GET /api/conversations/ - List conversations
    GET /api/conversations/{id}/ - Get conversation details with messages
    
    GET /api/conversations/{id}/messages/ - Get conversation messages
    POST /api/conversations/{id}/send_message/ - Send message in conversation
    """
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # Users see conversations for incidents they're involved in
        return Conversation.objects.filter(
            incident__student=user
        ) | Conversation.objects.filter(
            incident__guard_assignments__guard__user=user
        )
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def messages(self, request, pk=None):
        """Get all messages in a conversation."""
        conversation = self.get_object()
        messages = conversation.messages.all().order_by('created_at')
        serializer = MessageListSerializer(messages, many=True)
        return Response({
            'conversation_id': conversation.id,
            'incident_id': conversation.incident.id,
            'message_count': messages.count(),
            'messages': serializer.data
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def send_message(self, request, pk=None):
        """Send a message in this conversation."""
        conversation = self.get_object()
        content = request.data.get('content')
        
        if not content or len(content.strip()) == 0:
            return Response(
                {'error': 'Message content cannot be empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content
        )
        
        # Send push notifications to other participants
        try:
            notify_new_message(message, conversation)
        except Exception as e:
            # Log but don't fail the request if notifications fail
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send chat notification: {e}")
        
        return Response(
            MessageSerializer(message).data,
            status=status.HTTP_201_CREATED
        )


class MessageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Messages (read-only, use conversations.send_message to create).
    
    GET /api/messages/ - List messages
    GET /api/messages/{id}/ - Get message details
    """
    serializer_class = MessageListSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # Users see messages in conversations they're involved in
        return Message.objects.filter(
            conversation__incident__student=user
        ) | Message.objects.filter(
            conversation__incident__guard_assignments__guard__user=user
        )

def notify_new_message(message, conversation):
    """
    Send push notifications to conversation participants when a new message arrives.
    
    Args:
        message: Message instance
        conversation: Conversation instance
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Get the incident related to this conversation
    incident = conversation.incident
    
    # Find all participants except the sender
    participants = set()
    
    # Add student (if not sender)
    if incident.student and incident.student != message.sender:
        participants.add(incident.student)
    
    # Add all guards assigned to incident (if not sender)
    for assignment in incident.guard_assignments.all():
        if assignment.guard.user != message.sender:
            participants.add(assignment.guard.user)
    
    # Send notifications to each participant
    for participant in participants:
        try:
            tokens = PushNotificationService.get_guard_tokens(participant)
            if tokens:
                # Truncate message for preview
                message_preview = message.content[:100]
                
                PushNotificationService.notify_new_chat_message(
                    expo_tokens=tokens,
                    incident_id=str(incident.id),
                    conversation_id=conversation.id,
                    sender_name=message.sender.full_name,
                    message_preview=message_preview
                )
                logger.info(f"Sent chat notification to {participant.email} for incident {incident.id}")
        except Exception as e:
            logger.error(f"Failed to send chat notification to {participant.email}: {e}")