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
