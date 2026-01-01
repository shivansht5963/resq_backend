"""
ViewSets for security app.
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.utils import timezone
from .models import GuardProfile, GuardAssignment, GuardAlert
from .serializers import GuardProfileSerializer, GuardAssignmentSerializer, GuardAlertSerializer, GuardAlertDetailSerializer, GuardLocationUpdateSerializer
from .utils import get_top_n_nearest_guards
from accounts.permissions import IsGuard, IsAdmin


class GuardProfileViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Guard Profiles (read-only).
    
    GET /api/guards/ - List all guards
    GET /api/guards/{id}/ - Get guard details
    
    POST /api/guards/{id}/set_beacon/ - Assign guard to a beacon location (DEPRECATED)
    POST /api/guards/update_location/ - Update guard's current beacon (new)
    """
    queryset = GuardProfile.objects.all()
    serializer_class = GuardProfileSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def update_location(self, request):
        """
        Update guard's current beacon location.
        
        Called periodically by mobile app (every 10-15 seconds).
        Idempotent & lightweight - updates GuardProfile.current_beacon and last_beacon_update.
        
        Endpoint: POST /api/guards/update_location/
        
        Request:
        {
            "nearest_beacon_id": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2025-12-25T10:30:00Z"  // optional
        }
        
        Response:
        {
            "status": "location_updated",
            "guard": {...},
            "current_beacon": {...}
        }
        """
        serializer = GuardLocationUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Get guard's profile
        try:
            guard_profile = request.user.guard_profile
        except GuardProfile.DoesNotExist:
            return Response(
                {'error': 'User does not have a guard profile'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update beacon and timestamp
        beacon = serializer.validated_data['nearest_beacon_id']
        guard_profile.current_beacon = beacon
        guard_profile.last_beacon_update = timezone.now()
        guard_profile.last_active_at = timezone.now()
        guard_profile.save(update_fields=['current_beacon', 'last_beacon_update', 'last_active_at'])
        
        return Response({
            'status': 'location_updated',
            'guard': GuardProfileSerializer(guard_profile).data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def set_beacon(self, request, pk=None):
        """
        DEPRECATED: Use /api/guards/update_location/ instead.
        
        Assign guard to a beacon location (beacon-based positioning).
        """
        from incidents.models import Beacon
        
        guard_profile = self.get_object()
        beacon_id = request.data.get('beacon_id')
        
        if not beacon_id:
            return Response(
                {'error': 'beacon_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            beacon = Beacon.objects.get(beacon_id=beacon_id)
        except Beacon.DoesNotExist:
            return Response(
                {'error': f'Beacon with ID {beacon_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not beacon.is_active:
            return Response(
                {'error': f'Beacon {beacon_id} is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        guard_profile.current_beacon = beacon
        guard_profile.last_beacon_update = timezone.now()
        guard_profile.save()
        
        return Response({
            'detail': f'Guard assigned to beacon {beacon.location_name}',
            'guard': GuardProfileSerializer(guard_profile).data
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def active_assignment(self, request):
        """
        Get guard's current active assignment with full incident details.
        
        GET /api/guards/active_assignment/
        
        Response (if assigned):
        {
            "is_assigned": true,
            "assignment": {
                "id": 123,
                "incident": {...full incident details...},
                "assigned_at": "2026-01-01T10:00:00Z",
                "is_active": true
            }
        }
        
        Response (if not assigned):
        {
            "is_assigned": false,
            "message": "No active assignment"
        }
        """
        from incidents.serializers import IncidentDetailedSerializer
        
        # Validate guard role
        if request.user.role != 'GUARD':
            return Response(
                {'error': 'Only guards can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get guard's profile
        try:
            guard_profile = request.user.guard_profile
        except GuardProfile.DoesNotExist:
            return Response(
                {'error': 'Guard profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Find active assignment
        active_assignment = GuardAssignment.objects.filter(
            guard=request.user,
            is_active=True
        ).select_related('incident', 'incident__beacon').first()
        
        if not active_assignment:
            return Response({
                'is_assigned': False,
                'message': 'No active assignment'
            })
        
        # Return assignment with full incident details
        return Response({
            'is_assigned': True,
            'assignment': {
                'id': active_assignment.id,
                'assigned_at': active_assignment.assigned_at,
                'is_active': active_assignment.is_active,
                'incident': IncidentDetailedSerializer(
                    active_assignment.incident,
                    context={'request': request}
                ).data
            }
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def incident_history(self, request):
        """
        Get guard's incident history.
        
        GET /api/guards/incident_history/
        
        Query Parameters:
        - status: Filter by incident status (CREATED, ASSIGNED, IN_PROGRESS, RESOLVED)
        - limit: Number of incidents to return (default: 20)
        
        Returns incidents where the current guard was:
        - Assigned to the incident
        - Received an alert for the incident
        
        Response:
        {
            "count": 10,
            "incidents": [
                {
                    "id": "uuid",
                    "beacon": {...},
                    "status": "RESOLVED",
                    "priority": 3,
                    "guard_role": "was_assigned",
                    "created_at": "2026-01-01T10:00:00Z",
                    "resolved_at": "2026-01-01T11:30:00Z"
                },
                ...
            ]
        }
        """
        from incidents.models import Incident
        from incidents.serializers import GuardIncidentHistorySerializer
        from django.db.models import Q
        
        guard = request.user
        
        # Guards only - check role
        if guard.role != 'GUARD':
            return Response(
                {'error': 'Only guards can view incident history'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get incidents where guard was involved
        incidents = Incident.objects.filter(
            Q(guard_assignments__guard=guard) |
            Q(guard_alerts__guard=guard)
        ).distinct().order_by('-created_at')
        
        # Apply filters
        incident_status = request.query_params.get('status')
        if incident_status:
            incidents = incidents.filter(status=incident_status)
        
        limit = int(request.query_params.get('limit', 20))
        incidents = incidents[:limit]
        
        serializer = GuardIncidentHistorySerializer(
            incidents, 
            many=True, 
            context={'request': request, 'guard': guard}
        )
        
        return Response({
            'count': len(serializer.data),
            'incidents': serializer.data
        })


class GuardAssignmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Guard Assignments.
    
    GET /api/assignments/ - List assignments
    POST /api/assignments/ - Create assignment (ADMIN only)
    GET /api/assignments/{id}/ - Get assignment details
    PATCH /api/assignments/{id}/ - Update assignment (ADMIN only)
    DELETE /api/assignments/{id}/ - Delete assignment (ADMIN only)
    
    POST /api/assignments/{id}/deactivate/ - Deactivate assignment
    """
    serializer_class = GuardAssignmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Guards see only their own assignments
        if user.role == 'GUARD':
            try:
                return GuardAssignment.objects.filter(guard=user.guard_profile)
            except GuardProfile.DoesNotExist:
                return GuardAssignment.objects.none()
        
        # Admins see all assignments
        return GuardAssignment.objects.all()
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def deactivate(self, request, pk=None):
        """Deactivate a guard assignment."""
        assignment = self.get_object()
        assignment.is_active = False
        assignment.save()
        return Response(GuardAssignmentSerializer(assignment).data)


class GuardAlertViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Guard Alerts (nearest guard notifications).
    
    GET /api/alerts/ - List alerts
    GET /api/alerts/{id}/ - Get alert details
    
    POST /api/alerts/{id}/acknowledge/ - Guard acknowledges alert
    POST /api/alerts/{id}/decline/ - Guard declines alert
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return GuardAlertDetailSerializer
        return GuardAlertSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        # Guards see only alerts sent to them
        if user.role == 'GUARD':
            return GuardAlert.objects.filter(guard=user)
        
        # Admins see all alerts
        return GuardAlert.objects.all()
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def accept(self, request, pk=None):
        """
        Guard accepts the alert (ASSIGNMENT type only).
        Creates GuardAssignment and updates incident status.
        """
        from incidents.services import handle_guard_alert_accepted
        
        alert = self.get_object()
        
        # Only ASSIGNMENT alerts can be accepted
        if alert.alert_type != 'ASSIGNMENT':
            return Response(
                {'error': 'Only ASSIGNMENT alerts can be accepted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        handle_guard_alert_accepted(alert)
        
        from security.serializers import GuardAlertDetailSerializer
        return Response(GuardAlertDetailSerializer(alert).data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def acknowledge(self, request, pk=None):
        """
        DEPRECATED: Use /accept/ instead.
        Guard acknowledges the alert and will respond.
        """
        # Redirect to new accept endpoint behavior
        return self.accept(request, pk)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def decline(self, request, pk=None):
        """Guard declines the alert (busy or unavailable)."""
        from incidents.services import handle_guard_alert_declined
        
        alert = self.get_object()
        handle_guard_alert_declined(alert)
        
        from security.serializers import GuardAlertDetailSerializer
        return Response(GuardAlertDetailSerializer(alert).data)
