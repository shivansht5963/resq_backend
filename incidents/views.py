"""
ViewSets for unified incident management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.http import JsonResponse
from django.db import transaction
from .models import Beacon, Incident, IncidentSignal, PhysicalDevice, IncidentImage
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
            ).distinct().prefetch_related('signals', 'images', 'guard_assignments', 'guard_alerts', 'conversation__messages')
        
        # Guards see all incidents (for their location/nearby)
        if user.role == 'GUARD':
            return Incident.objects.all().prefetch_related('signals', 'images', 'guard_assignments', 'guard_alerts', 'conversation__messages')
        
        # Admins see all
        return Incident.objects.all().prefetch_related('signals', 'images', 'guard_assignments', 'guard_alerts', 'conversation__messages')
    
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
                
                # IMPORTANT: Reset file pointer to beginning before saving
                # This ensures the entire file is available for GCS upload
                image_file.seek(0)
                print(f"  ✅ File pointer reset to position 0")
                
                # Read file into memory to ensure it's complete
                file_data = image_file.read()
                print(f"  ✅ Read {len(file_data)} bytes from file")
                
                # Reset pointer again after reading
                image_file.seek(0)
                print(f"  File pointer reset again to position 0")
                
                # Save to GCS via Django's storage system
                print(f"  [→] Uploading to Google Cloud Storage...")
                print(f"      Storage backend: {IncidentImage._meta.get_field('image').storage.__class__.__name__}")
                
                # Use create_incident_image helper to handle upload properly
                incident_image = IncidentImage.objects.create(
                    incident=incident,
                    image=image_file,
                    uploaded_by=request.user,
                    description=f"Image {idx + 1}"
                )
                
                # Verify file was actually saved to GCS
                if incident_image.image:
                    try:
                        stored_url = incident_image.image.url
                        print(f"  ✅ Image {idx + 1} uploaded successfully!")
                        print(f"     ID: {incident_image.id}")
                        print(f"     File path: {incident_image.image.name}")
                        print(f"     GCS URL: {stored_url}")
                        image_objects.append(incident_image)
                    except Exception as url_error:
                        print(f"  ⚠️  Image saved but URL generation failed: {url_error}")
                        print(f"     File path: {incident_image.image.name}")
                        image_objects.append(incident_image)
                else:
                    print(f"  ❌ Image {idx + 1}: No image file after save")
                
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
        Mark incident as RESOLVED with full audit trail.
        
        POST /api/incidents/{id}/resolve/
        
        Request Body:
        {
            "resolution_notes": "Description of resolution (REQUIRED)",
            "resolution_type": "RESOLVED_BY_GUARD" | "ESCALATED_TO_ADMIN"
        }
        
        Requirements:
        - Incident must NOT be already resolved
        - Non-admins: Must have an active assignment to this incident
        - Admins: Can resolve any incident without assignment
        - resolution_notes is REQUIRED
        
        Side Effects:
        - Updates incident status to RESOLVED
        - Sets resolved_by, resolved_at, resolution_notes, resolution_type
        - Deactivates any active guard assignment
        - Logs INCIDENT_RESOLVED event to audit trail
        """
        from django.utils import timezone
        from .services import log_incident_event, validate_status_transition
        from .models import IncidentEvent
        from security.models import GuardAssignment
        
        incident = self.get_object()
        
        # 1. State validation using state machine
        if not validate_status_transition(incident.status, Incident.Status.RESOLVED):
            return Response(
                {'error': f'Cannot resolve incident in {incident.status} status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 2. Check for active assignment (non-admins need assignment)
        active_assignment = GuardAssignment.objects.filter(
            incident=incident,
            is_active=True
        ).first()
        
        is_admin = request.user.role == 'ADMIN'
        is_assigned_guard = active_assignment and active_assignment.guard == request.user
        
        if not is_admin and not is_assigned_guard:
            return Response(
                {'error': 'Only assigned guard or admin can resolve this incident'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 3. Validate resolution notes (REQUIRED)
        resolution_notes = request.data.get('resolution_notes', '').strip()
        if not resolution_notes:
            return Response(
                {'error': 'resolution_notes is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 4. Get and validate resolution type
        resolution_type = request.data.get('resolution_type', Incident.ResolutionType.RESOLVED_BY_GUARD)
        valid_types = [choice[0] for choice in Incident.ResolutionType.choices]
        if resolution_type not in valid_types:
            resolution_type = Incident.ResolutionType.RESOLVED_BY_GUARD
        
        # Store previous status for event logging
        previous_status = incident.status
        
        # Update incident
        incident.status = Incident.Status.RESOLVED
        incident.resolved_by = request.user
        incident.resolved_at = timezone.now()
        incident.resolution_notes = resolution_notes
        incident.resolution_type = resolution_type
        incident.save()
        
        # Update buzzer status to RESOLVED (incident complete, stop buzzer)
        from .services import update_buzzer_status_on_incident_resolved
        update_buzzer_status_on_incident_resolved(incident)
        
        # Deactivate any active assignment
        deactivated = GuardAssignment.objects.filter(
            incident=incident,
            is_active=True
        ).update(is_active=False)
        
        # Log event to audit trail
        log_incident_event(
            incident=incident,
            event_type=IncidentEvent.EventType.INCIDENT_RESOLVED,
            actor=request.user,
            previous_status=previous_status,
            new_status=Incident.Status.RESOLVED,
            details={
                'resolution_type': resolution_type,
                'resolution_notes': resolution_notes[:200],
                'assignments_deactivated': deactivated,
                'resolved_by_role': request.user.role
            }
        )
        
        return Response(IncidentDetailedSerializer(incident, context={'request': request}).data)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def status_poll(self, request, pk=None):
        """
        Student polls for incident status updates (guard assignment status).
        
        Shows:
        - Guard assignment status (WAITING_FOR_GUARD / GUARD_ASSIGNED / NO_ASSIGNMENT)
        - Pending alerts to guards
        - Guard details (when assigned)
        - Timeline of status changes
        
        GET /api/incidents/{id}/status_poll/
        
        Response:
        {
            "id": "uuid",
            "status": "CREATED/ASSIGNED/IN_PROGRESS/RESOLVED",
            "priority": 4,
            "guard_status": {
                "status": "WAITING_FOR_GUARD",
                "message": "Searching for available guard... (2 being contacted)",
                "pending_alerts": 2
            },
            "guard_assignment": null,
            "alert_status_summary": {
                "total_alerts": 3,
                "sent": 2,
                "accepted": 0,
                "declined": 1,
                "expired": 0
            },
            "pending_alerts": [
                {
                    "id": 1,
                    "guard": {"id": "uuid", "full_name": "John"},
                    "priority_rank": 1,
                    "alert_type": "ASSIGNMENT",
                    "alert_sent_at": "2025-12-30T10:00:00Z",
                    "response_deadline": "2025-12-30T10:00:45Z"
                }
            ]
        }
        """
        from incidents.serializers import IncidentStatusUpdateSerializer
        
        incident = self.get_object()
        
        # Only allow student who reported it or admin to poll
        is_student_reporter = incident.signals.filter(source_user=request.user).exists()
        is_admin = request.user.role == 'ADMIN'
        
        if not (is_student_reporter or is_admin):
            return Response(
                {'error': 'You do not have permission to poll this incident'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = IncidentStatusUpdateSerializer(incident, context={'request': request})
        return Response(serializer.data)
    
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
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def timeline(self, request, pk=None):
        """
        Get full incident timeline with all events.
        
        GET /api/incidents/{id}/timeline/
        
        Returns incident details with complete event history (audit trail).
        Guards and admins can view timelines for any incident.
        Students can only view timeline for incidents they reported.
        
        Response:
        {
            "id": "uuid",
            "beacon": {...},
            "status": "ASSIGNED",
            "priority": 3,
            "events": [
                {
                    "id": 1,
                    "event_type": "INCIDENT_CREATED",
                    "event_type_display": "Incident Created",
                    "actor": {"id": "uuid", "full_name": "...", "role": "STUDENT"},
                    "target_guard": null,
                    "previous_status": "",
                    "new_status": "CREATED",
                    "details": {"signal_type": "STUDENT_SOS"},
                    "created_at": "2026-01-01T10:00:00Z"
                },
                ...
            ],
            "current_assignment": {...},
            "resolution_info": null
        }
        """
        from .serializers import IncidentTimelineSerializer
        
        incident = self.get_object()
        
        # Permission check: guards/admins can view any, students only their own
        is_student_reporter = incident.signals.filter(source_user=request.user).exists()
        is_guard_or_admin = request.user.role in ['GUARD', 'ADMIN']
        
        if not (is_student_reporter or is_guard_or_admin):
            return Response(
                {'error': 'You do not have permission to view this timeline'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = IncidentTimelineSerializer(incident, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def events(self, request, pk=None):
        """
        Get event history for an incident (flat list).
        
        GET /api/incidents/{id}/events/
        
        Query Parameters:
        - event_type: Filter by event type (e.g., ALERT_SENT, STATUS_CHANGED)
        - limit: Number of events to return (default: 50)
        
        Response:
        {
            "count": 5,
            "events": [
                {
                    "id": 1,
                    "event_type": "INCIDENT_CREATED",
                    "event_type_display": "Incident Created",
                    ...
                },
                ...
            ]
        }
        """
        from .serializers import IncidentEventSerializer
        
        incident = self.get_object()
        
        # Permission check
        is_student_reporter = incident.signals.filter(source_user=request.user).exists()
        is_guard_or_admin = request.user.role in ['GUARD', 'ADMIN']
        
        if not (is_student_reporter or is_guard_or_admin):
            return Response(
                {'error': 'You do not have permission to view these events'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get events with optional filters
        events = incident.events.all().order_by('-created_at')
        
        event_type = request.query_params.get('event_type')
        if event_type:
            events = events.filter(event_type=event_type)
        
        limit = int(request.query_params.get('limit', 50))
        events = events[:limit]
        
        serializer = IncidentEventSerializer(events, many=True)
        return Response({
            'count': len(serializer.data),
            'events': serializer.data
        })


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
        esp_device = PhysicalDevice.objects.get(device_id=device_id, is_active=True)
    except PhysicalDevice.DoesNotExist:
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
            details={
                'device_id': device_id,
                'device_type': esp_device.get_device_type_display()
            }
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


@api_view(['GET'])
@permission_classes([AllowAny])
def buzzer_status_endpoint(request):
    """
    Public ESP32 Buzzer Status Polling Endpoint - NO AUTHENTICATION REQUIRED
    
    GET /api/incidents/buzzer-status/?beacon_id=<beacon_id>
    
    Query Parameters:
    - beacon_id: Hardware beacon ID (REQUIRED)
    
    Response (200 OK):
    {
        "incident_active": true   # or false
    }
    """
    beacon_id = request.query_params.get('beacon_id', '').strip()
    
    if not beacon_id:
        return JsonResponse({'incident_active': False}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        beacon = Beacon.objects.get(beacon_id=beacon_id, is_active=True)
    except Beacon.DoesNotExist:
        return JsonResponse({'incident_active': False}, status=status.HTTP_404_NOT_FOUND)
    
    # Get all ACTIVE incidents for this beacon (not resolved)
    active_incidents = Incident.objects.filter(
        beacon=beacon,
        status__in=[Incident.Status.CREATED, Incident.Status.ASSIGNED, Incident.Status.IN_PROGRESS]
    ).order_by('-created_at')
    
    # If no active incidents, buzzer is inactive
    if not active_incidents.exists():
        return JsonResponse({'incident_active': False})
    
    # Get the most recent incident
    incident = active_incidents.first()
    
    # Determine if buzzer should be active
    should_buzz = incident.buzzer_status in [
        Incident.BuzzerStatus.PENDING,
        Incident.BuzzerStatus.ACTIVE
    ]
    
    return JsonResponse({'incident_active': should_buzz})
