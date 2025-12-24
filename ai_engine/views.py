"""
ViewSets for ai_engine app.
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from .models import AIEvent
from .serializers import AIEventSerializer, AIEventDetailSerializer
from accounts.permissions import IsAdmin


class AIEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for AI Events (computer vision, audio analysis results).
    
    GET /api/ai-events/ - List AI events
    GET /api/ai-events/{id}/ - Get event details
    POST /api/ai-events/ - Create event (internal, requires authentication)
    """
    serializer_class = AIEventSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AIEventDetailSerializer
        return AIEventSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        # Admins see all events
        if user.role == 'ADMIN':
            return AIEvent.objects.all()
        
        # Guards see events for incidents they're assigned to
        if user.role == 'GUARD':
            from security.models import GuardAssignment
            try:
                assigned_reported = GuardAssignment.objects.filter(
                    guard=user.guard_profile, is_active=True
                ).values_list('reported_incident', flat=True)
                assigned_beacon = GuardAssignment.objects.filter(
                    guard=user.guard_profile, is_active=True
                ).values_list('beacon_incident', flat=True)
                assigned_panic = GuardAssignment.objects.filter(
                    guard=user.guard_profile, is_active=True
                ).values_list('panic_incident', flat=True)
                
                from django.db.models import Q
                return AIEvent.objects.filter(
                    Q(reported_incident__in=assigned_reported) |
                    Q(beacon_incident__in=assigned_beacon) |
                    Q(panic_incident__in=assigned_panic)
                )
            except Exception:
                # Guard profile doesn't exist
                return AIEvent.objects.none()
        
        # Students see events for their own incidents
        if user.role == 'STUDENT':
            from django.db.models import Q
            return AIEvent.objects.filter(
                Q(reported_incident__student=user) |
                Q(beacon_incident__student=user) |
                Q(panic_incident__student=user)
            )
        
        return AIEvent.objects.none()
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def log_event(self, request):
        """
        Log a new AI event.
        
        Expected payload (choose one incident type):
        {
            "reported_incident_id": "uuid",
            "event_type": "VISION",
            "confidence_score": 0.95,
            "details": {...}
        }
        """
        from incidents.models import ReportedIncident, BeaconIncident, PanicButtonIncident
        
        reported_incident_id = request.data.get('reported_incident_id')
        beacon_incident_id = request.data.get('beacon_incident_id')
        panic_incident_id = request.data.get('panic_incident_id')
        event_type = request.data.get('event_type')
        confidence_score = request.data.get('confidence_score')
        details = request.data.get('details', {})
        
        incident_count = sum([bool(reported_incident_id), bool(beacon_incident_id), bool(panic_incident_id)])
        if incident_count != 1:
            return Response(
                {'error': 'Exactly one incident type must be provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            if reported_incident_id:
                incident_obj = ReportedIncident.objects.get(id=reported_incident_id)
                ai_event = AIEvent.objects.create(
                    reported_incident=incident_obj,
                    event_type=event_type,
                    confidence_score=confidence_score,
                    details=details
                )
            elif beacon_incident_id:
                incident_obj = BeaconIncident.objects.get(id=beacon_incident_id)
                ai_event = AIEvent.objects.create(
                    beacon_incident=incident_obj,
                    event_type=event_type,
                    confidence_score=confidence_score,
                    details=details
                )
            else:  # panic_incident_id
                incident_obj = PanicButtonIncident.objects.get(id=panic_incident_id)
                ai_event = AIEvent.objects.create(
                    panic_incident=incident_obj,
                    event_type=event_type,
                    confidence_score=confidence_score,
                    details=details
                )
        except ReportedIncident.DoesNotExist:
            return Response(
                {'error': 'Reported incident not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except BeaconIncident.DoesNotExist:
            return Response(
                {'error': 'Beacon incident not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except PanicButtonIncident.DoesNotExist:
            return Response(
                {'error': 'Panic incident not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(
            AIEventDetailSerializer(ai_event).data,
            status=status.HTTP_201_CREATED
        )
