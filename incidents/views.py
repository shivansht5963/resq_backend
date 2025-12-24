"""
ViewSets for incidents app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from .models import Beacon, ReportedIncident, BeaconIncident, PanicButtonIncident, ESP32Device
from .serializers import (
    BeaconSerializer, 
    ReportedIncidentSerializer, BeaconIncidentSerializer, PanicButtonIncidentSerializer
)
from accounts.permissions import IsStudent, IsGuard, IsStudentOwner


class BeaconViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Beacon locations.
    
    GET /api/beacons/ - List all beacons
    GET /api/beacons/{id}/ - Get beacon details
    """
    queryset = Beacon.objects.all()
    serializer_class = BeaconSerializer
    permission_classes = [IsAuthenticated]


class ReportedIncidentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Student Reported Incidents (beacon is optional).
    
    GET /api/reported-incidents/ - List incidents (filtered by role)
    POST /api/reported-incidents/ - Create new incident (STUDENT only)
    GET /api/reported-incidents/{id}/ - Get incident details
    PATCH /api/reported-incidents/{id}/ - Update incident (ADMIN only)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ReportedIncidentSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        # Students see only their own incidents
        if user.role == 'STUDENT':
            return ReportedIncident.objects.filter(student=user)
        
        # Guards see all reported incidents
        if user.role == 'GUARD':
            return ReportedIncident.objects.all()
        
        # Admins see all incidents
        return ReportedIncident.objects.all()
    
    def perform_create(self, serializer):
        """Create incident with current user as student."""
        if self.request.user.role != 'STUDENT':
            raise PermissionError("Only students can create incidents")
        
        incident = serializer.save(student=self.request.user)
        
        # Auto-alert nearest guards if beacon is provided
        if incident.beacon:
            from security.utils import get_top_n_nearest_guards
            from security.models import GuardAlert
            
            nearest_guards = get_top_n_nearest_guards(
                incident.beacon,
                n=3,
                max_distance_km=1.0
            )
            
            for rank, (guard_profile, distance_km) in enumerate(nearest_guards, 1):
                GuardAlert.objects.create(
                    reported_incident=incident,
                    guard=guard_profile,
                    distance_km=distance_km,
                    priority_rank=rank,
                    status='SENT'
                )


class BeaconIncidentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Automatic Beacon Incidents (beacon detection).
    
    GET /api/beacon-incidents/ - List beacon incidents
    GET /api/beacon-incidents/{id}/ - Get incident details
    """
    permission_classes = [IsAuthenticated]
    serializer_class = BeaconIncidentSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        # Students see only their own incidents
        if user.role == 'STUDENT':
            return BeaconIncident.objects.filter(student=user)
        
        # Guards and Admins see all
        return BeaconIncident.objects.all()


class PanicButtonIncidentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Panic Button Incidents.
    
    GET /api/panic-incidents/ - List panic incidents
    GET /api/panic-incidents/{id}/ - Get incident details
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PanicButtonIncidentSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        # Students see only their own incidents
        if user.role == 'STUDENT':
            return PanicButtonIncident.objects.filter(student=user)
        
        # Guards and Admins see all
        return PanicButtonIncident.objects.all()


# ESP32 Panic Button API (No Authentication Required)
@api_view(['POST'])
@permission_classes([AllowAny])
def panic_button_endpoint(request):
    """
    ESP32 Panic Button API - Trigger emergency incident from panic button.
    
    POST /api/panic/
    
    Request:
    {
        "device_id": "ESP32-001"
    }
    
    Response (201 Created):
    {
        "incident_id": "...",
        "alerts_created": 3,
        "message": "Emergency alert triggered - 3 guards notified"
    }
    """
    device_id = request.data.get('device_id')
    
    if not device_id:
        return Response(
            {'error': 'device_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Find ESP32 device
    try:
        esp_device = ESP32Device.objects.get(device_id=device_id)
    except ESP32Device.DoesNotExist:
        return Response(
            {'error': f'Device {device_id} not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if not esp_device.is_active:
        return Response(
            {'error': f'Device {device_id} is inactive'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get beacon from device
    beacon = esp_device.beacon
    if not beacon.is_active:
        return Response(
            {'error': 'Device beacon is inactive'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create panic button incident
    incident = PanicButtonIncident.objects.create(
        esp32_device=esp_device,
        student=None,  # Student unknown for panic button
        status=PanicButtonIncident.Status.CREATED,
        priority=PanicButtonIncident.Priority.CRITICAL,
        description=f"Panic button: {device_id}"
    )
    
    # Auto-alert nearest guards
    from security.utils import get_top_n_nearest_guards
    from security.models import GuardAlert
    
    nearest_guards = get_top_n_nearest_guards(beacon, n=3, max_distance_km=1.0)
    
    alerts_created = 0
    for rank, (guard_profile, distance_km) in enumerate(nearest_guards, 1):
        GuardAlert.objects.create(
            panic_incident=incident,
            guard=guard_profile,
            distance_km=distance_km,
            priority_rank=rank,
            status='SENT'
        )
        alerts_created += 1
    
    return Response({
        'incident_id': str(incident.id),
        'alerts_created': alerts_created,
        'message': f'Emergency alert triggered - {alerts_created} guards notified',
        'location': beacon.location_name,
        'status': 'success'
    }, status=status.HTTP_201_CREATED)
