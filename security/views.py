"""
ViewSets for security app.
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.utils import timezone
from .models import GuardProfile, GuardAssignment, DeviceToken, GuardAlert
from .serializers import GuardProfileSerializer, GuardAssignmentSerializer, DeviceTokenSerializer, GuardAlertSerializer, GuardAlertDetailSerializer, GuardLocationUpdateSerializer
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


class DeviceTokenViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Device Tokens (FCM for push notifications).
    
    GET /api/device-tokens/ - List device tokens
    POST /api/device-tokens/ - Register new device token
    GET /api/device-tokens/{id}/ - Get token details
    DELETE /api/device-tokens/{id}/ - Delete token (logout device)
    """
    serializer_class = DeviceTokenSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # Users can only see their own device tokens
        return DeviceToken.objects.filter(user=user)
    
    def perform_create(self, serializer):
        """Register device token for current user."""
        serializer.save(user=self.request.user)


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
    def acknowledge(self, request, pk=None):
        """Guard acknowledges the alert and will respond."""
        from incidents.services import handle_guard_alert_acknowledged
        
        alert = self.get_object()
        handle_guard_alert_acknowledged(alert)
        
        from security.serializers import GuardAlertDetailSerializer
        return Response(GuardAlertDetailSerializer(alert).data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def decline(self, request, pk=None):
        """Guard declines the alert (busy or unavailable)."""
        from incidents.services import handle_guard_alert_declined
        
        alert = self.get_object()
        handle_guard_alert_declined(alert)
        
        from security.serializers import GuardAlertDetailSerializer
        return Response(GuardAlertDetailSerializer(alert).data)
