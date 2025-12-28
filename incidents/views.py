"""
ViewSets for unified incident management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db import transaction
from .models import Beacon, Incident, IncidentSignal, ESP32Device, IncidentImage
from .serializers import (
    BeaconSerializer,
    IncidentDetailedSerializer,
    IncidentListSerializer,
    IncidentCreateSerializer,
    IncidentReportSerializer,
    IncidentImageSerializer
)
from .services import (
    get_or_create_incident_with_signals,
    alert_guards_for_incident
)
from accounts.permissions import IsStudent, IsGuard


class BeaconViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Beacon locations.
    
    GET /api/beacons/ - List all beacons
    GET /api/beacons/{id}/ - Get beacon details
    """
    queryset = Beacon.objects.all()
    serializer_class = BeaconSerializer
    permission_classes = [IsAuthenticated]


class IncidentViewSet(viewsets.ModelViewSet):
    """
    Unified ViewSet for all incidents.
    
    GET    /api/incidents/              - List incidents (filtered by role)
    POST   /api/incidents/              - Create incident (admin only)
    GET    /api/incidents/{id}/         - Get incident details + all signals
    PATCH  /api/incidents/{id}/         - Update incident status/priority
    POST   /api/incidents/{id}/resolve/ - Mark as RESOLVED
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Students see only incidents they were involved in
        if user.role == 'STUDENT':
            return Incident.objects.filter(
                signals__source_user=user
            ).distinct().prefetch_related('signals', 'guard_assignments', 'conversation__messages')
        
        # Guards see all incidents (for their location/nearby)
        if user.role == 'GUARD':
            return Incident.objects.all().prefetch_related('signals', 'guard_assignments', 'conversation__messages')
        
        # Admins see all
        return Incident.objects.all().prefetch_related('signals', 'guard_assignments', 'conversation__messages')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return IncidentDetailedSerializer
        if self.action == 'list':
            return IncidentListSerializer
        return IncidentDetailedSerializer
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def report_sos(self, request):
        """
        Student reports emergency via SOS.
        
        POST /api/incidents/report-sos/
        
        Request:
        {
            "beacon_id": "uuid",
            "description": "Optional description"
        }
        """
        serializer = IncidentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        if request.user.role != 'STUDENT':
            return Response(
                {'error': 'Only students can report SOS'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            incident, created, signal = get_or_create_incident_with_signals(
                beacon_id=serializer.validated_data['beacon_id'],
                signal_type=IncidentSignal.SignalType.STUDENT_SOS,
                source_user_id=request.user.id,
                description=serializer.validated_data.get('description', '')
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        # Only alert guards if incident was newly created
        if created:
            alert_guards_for_incident(incident)
        
        response_data = {
            'status': 'incident_created' if created else 'signal_added_to_existing',
            'incident_id': str(incident.id),
            'signal_id': signal.id,
            'incident': IncidentDetailedSerializer(incident, context={'request': request}).data
        }
        
        return Response(response_data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def report(self, request):
        """
        Student reports non-emergency incident with optional images.
        
        POST /api/incidents/report/ (multipart/form-data)
        
        Form Data:
        - beacon_id: string (optional, e.g., "safe:uuid:403:403")
        - type: string (required, e.g., "Safety Concern")
        - description: string (required)
        - location: string (optional, required if no beacon_id)
        - images: file[] (optional, max 3 images)
        
        Response: 201/200 OK
        {
            "status": "incident_created",
            "incident_id": "uuid",
            "signal_id": 123,
            "report_type": "Safety Concern",
            "images": [
                {
                    "id": 1,
                    "image": "https://...",
                    "uploaded_by_email": "student@example.com",
                    "uploaded_at": "2025-12-26T...",
                    "description": ""
                }
            ],
            "incident": {...}
        }
        """
        # DEBUG: Check storage configuration at START
        from django.conf import settings
        print(f"\n{'='*60}")
        print(f"[STORAGE CONFIG CHECK]")
        print(f"{'='*60}")
        print(f"  DEFAULT_FILE_STORAGE: {settings.DEFAULT_FILE_STORAGE}")
        print(f"  MEDIA_ROOT: {settings.MEDIA_ROOT}")
        print(f"  MEDIA_URL: {settings.MEDIA_URL}")
        print(f"{'='*60}\n")
        
        # Check user role first
        if request.user.role != 'STUDENT':
            return Response(
                {'error': 'Only students can report incidents'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Extract form data from request.POST (not request.data for multipart)
        beacon_id = (request.POST.get('beacon_id', '') or '').strip()
        report_type = request.POST.get('type', '').strip()
        description = request.POST.get('description', '').strip()
        location = (request.POST.get('location', '') or '').strip()
        
        # Get images from request.FILES
        images_list = request.FILES.getlist('images', [])
        
        # Log request info
        print(f"\n{'='*60}")
        print(f"[INCIDENT REPORT] New report from {request.user.email}")
        print(f"{'='*60}")
        print(f"  Type: {report_type}")
        print(f"  Description: {description[:50]}...")
        print(f"  Beacon ID: {beacon_id}")
        print(f"  Location: {location}")
        print(f"  Images received: {len(images_list)}")
        if images_list:
            for i, f in enumerate(images_list):
                print(f"    [{i+1}] {f.name} ({f.content_type}, {f.size} bytes)")
        print(f"{'='*60}\n")
        
        # Validate required fields
        if not report_type:
            return Response({'error': 'type field is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not description:
            return Response({'error': 'description field is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not beacon_id and not location:
            return Response(
                {'error': 'Either beacon_id or location must be provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate image count (max 3)
        if len(images_list) > 3:
            return Response(
                {'error': 'Maximum 3 images allowed per report'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Create or get incident based on beacon or location
            if beacon_id:
                # Use actual beacon if provided
                incident, created, signal = get_or_create_incident_with_signals(
                    beacon_id=beacon_id,
                    signal_type=IncidentSignal.SignalType.STUDENT_REPORT,
                    source_user_id=request.user.id,
                    description=description
                )
            else:
                # For location-only reports, use location as beacon_id
                virtual_beacon_id = f"location:{location.lower().replace(' ', '_')}"
                incident, created, signal = get_or_create_incident_with_signals(
                    beacon_id=virtual_beacon_id,
                    signal_type=IncidentSignal.SignalType.STUDENT_REPORT,
                    source_user_id=request.user.id,
                    description=description
                )
            
            # Always update report_type and location fields
            incident.report_type = report_type
            incident.location = location if location else incident.beacon.location_name
            incident.save()
            
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        # Store images directly from request.FILES
        image_objects = []
        print(f"\n{'='*60}")
        print(f"[IMAGE UPLOAD] Processing {len(images_list)} images for incident {incident.id}")
        print(f"{'='*60}")
        
        for idx, image_file in enumerate(images_list[:3]):
            try:
                print(f"\n[Image {idx + 1}] Starting upload...")
                print(f"  File name: {image_file.name}")
                print(f"  Content type: {image_file.content_type}")
                print(f"  File size: {image_file.size} bytes")
                
                # Reset file pointer to beginning
                image_file.seek(0)
                print(f"  ✅ File pointer reset to position 0")
                
                # Save directly to Cloudinary
                print(f"  [→] Uploading to Cloudinary...")
                print(f"      Storage backend: {IncidentImage._meta.get_field('image').storage.__class__.__name__}")
                
                incident_image = IncidentImage.objects.create(
                    incident=incident,
                    image=image_file,
                    uploaded_by=request.user,
                    description=f"Image {idx + 1}"
                )
                image_objects.append(incident_image)
                print(f"  ✅ Image {idx + 1} uploaded successfully to Cloudinary!")
                print(f"     ID: {incident_image.id}")
                print(f"     File path: {incident_image.image.name}")
                print(f"     Cloudinary URL: {incident_image.image.url}")
                
            except Exception as e:
                print(f"\n  ❌ ERROR saving image {idx + 1}:")
                print(f"     Error: {str(e)}")
                import traceback
                print(f"     Traceback:")
                for line in traceback.format_exc().split('\n'):
                    if line:
                        print(f"     {line}")
                print(f"  ⚠️  Skipping this image and continuing...")
                continue
        
        print(f"\n[IMAGE UPLOAD] Summary:")
        print(f"  Total images uploaded: {len(image_objects)}")
        print(f"{'='*60}\n")
        
        # Only alert guards if incident was newly created
        if created:
            alert_guards_for_incident(incident)
        
        # Refresh incident from database to get all images
        incident.refresh_from_db()
        
        print(f"Incident {incident.id} has {incident.images.count()} images")
        
        response_data = {
            'status': 'incident_created' if created else 'signal_added_to_existing',
            'incident_id': str(incident.id),
            'signal_id': signal.id,
            'report_type': report_type,
            'images': IncidentImageSerializer(image_objects, many=True, context={'request': request}).data,
            'incident': IncidentDetailedSerializer(incident, context={'request': request}).data
        }
        
        return Response(response_data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """
        Mark incident as RESOLVED.
        
        POST /api/incidents/{id}/resolve/
        """
        incident = self.get_object()
        
        incident.status = Incident.Status.RESOLVED
        incident.save()
        
        # Deactivate any active assignment
        from security.models import GuardAssignment
        GuardAssignment.objects.filter(
            incident=incident,
            is_active=True
        ).update(is_active=False)
        
        return Response(
            IncidentDetailedSerializer(incident, context={'request': request}).data,
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['get'])
    def signals(self, request, pk=None):
        """
        Get all signals for an incident.
        
        GET /api/incidents/{id}/signals/
        """
        incident = self.get_object()
        signals = incident.signals.all().order_by('-created_at')
        
        from .serializers import IncidentSignalSerializer
        serializer = IncidentSignalSerializer(signals, many=True)
        
        return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def panic_button_endpoint(request):
    """
    ESP32 Panic Button API - Trigger emergency incident.
    
    POST /api/panic/
    
    Request:
    {
        "device_id": "ESP32-001"
    }
    
    Response (201 Created):
    {
        "status": "incident_created" | "signal_added_to_existing",
        "incident_id": "...",
        "alerts_sent": 3
    }
    """
    device_id = request.data.get('device_id')
    
    if not device_id:
        return Response(
            {'error': 'device_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        esp_device = ESP32Device.objects.get(device_id=device_id, is_active=True)
    except ESP32Device.DoesNotExist:
        return Response(
            {'error': f'Device {device_id} not found or inactive'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if not esp_device.beacon.is_active:
        return Response(
            {'error': 'Device beacon is inactive'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        incident, created, signal = get_or_create_incident_with_signals(
            beacon_id=esp_device.beacon.id,
            signal_type=IncidentSignal.SignalType.PANIC_BUTTON,
            source_device_id=esp_device.id,
            details={'device_id': device_id}
        )
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    # Count alerts sent only if incident was newly created
    alerts_sent = 0
    if created:
        alert_guards_for_incident(incident)
        alerts_sent = incident.guard_alerts.count()
    
    response_data = {
        'status': 'incident_created' if created else 'signal_added_to_existing',
        'incident_id': str(incident.id),
        'alerts_sent': alerts_sent,
        'location': esp_device.beacon.location_name
    }
    
    return Response(response_data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
