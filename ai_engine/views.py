"""
ViewSets for ai_engine app.
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from .models import AIEvent
from .serializers import AIEventSerializer, AIEventDetailSerializer
from accounts.permissions import IsAdmin


class AIEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for AI Events (computer vision, audio analysis results).
    
    GET /api/ai-events/ - List AI events
    GET /api/ai-events/{id}/ - Get event details
    """
    queryset = AIEvent.objects.all()
    serializer_class = AIEventSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AIEventDetailSerializer
        return AIEventSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def ai_detection_endpoint(request):
    """
    AI Detection Endpoint - Log AI detection and trigger incident if high confidence.
    
    POST /api/ai-detection/
    
    Request:
    {
        "beacon_id": "uuid",
        "event_type": "VISION" | "AUDIO",
        "confidence_score": 0.92,
        "details": {
            "detected_class": "weapon" | "fight" | "scream",
            "scream_intensity": 0.92
        }
    }
    
    Response:
    {
        "status": "incident_created" | "signal_added_to_existing" | "logged_only",
        "ai_event_id": 123,
        "incident_id": "uuid" (if created/merged),
        "signal_id": 456 (if created/merged)
    }
    """
    from incidents.models import Beacon, IncidentSignal
    from incidents.services import get_or_create_incident_with_signals, alert_guards_for_incident
    
    beacon_id = request.data.get('beacon_id')
    event_type = request.data.get('event_type')
    confidence_score = request.data.get('confidence_score')
    details = request.data.get('details', {})
    
    if not all([beacon_id, event_type, confidence_score is not None]):
        return Response(
            {'error': 'beacon_id, event_type, and confidence_score are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate beacon
    try:
        beacon = Beacon.objects.get(id=beacon_id, is_active=True)
    except Beacon.DoesNotExist:
        return Response(
            {'error': f'Beacon {beacon_id} not found or inactive'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Step 1: Always log the AI event (for analytics/audit)
    ai_event = AIEvent.objects.create(
        beacon=beacon,
        event_type=event_type,
        confidence_score=confidence_score,
        details=details
    )
    
    # Step 2: Determine confidence threshold
    thresholds = {
        'VISION': 0.75,
        'AUDIO': 0.80
    }
    threshold = thresholds.get(event_type, 0.8)
    
    # If confidence is below threshold, return logged_only
    if confidence_score < threshold:
        return Response({
            'status': 'logged_only',
            'ai_event_id': ai_event.id,
            'message': f'Confidence {confidence_score:.2f} below threshold {threshold}'
        }, status=status.HTTP_200_OK)
    
    # Step 3: Create incident signal
    signal_type_map = {
        'VISION': IncidentSignal.SignalType.AI_VISION,
        'AUDIO': IncidentSignal.SignalType.AI_AUDIO
    }
    signal_type = signal_type_map.get(event_type)
    
    try:
        incident, created, signal = get_or_create_incident_with_signals(
            beacon_id=beacon_id,
            signal_type=signal_type,
            ai_event_id=ai_event.id,
            details=details
        )
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    # Step 4: Alert guards only if incident was newly created
    if created:
        alert_guards_for_incident(incident)
    
    response_data = {
        'status': 'incident_created' if created else 'signal_added_to_existing',
        'ai_event_id': ai_event.id,
        'incident_id': str(incident.id),
        'signal_id': signal.id,
        'location': beacon.location_name
    }
    
    return Response(response_data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
