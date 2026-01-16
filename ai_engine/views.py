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


def _process_ai_detection_with_images(request, event_type, signal_type, confidence_threshold):
    """
    Internal helper for AI detection with multipart image uploads.
    
    Handles image attachment to new/existing incidents from AI detection.
    
    Args:
        request: HTTP request with multipart form data
        event_type: "VIOLENCE" or "SCREAM"
        signal_type: IncidentSignal.SignalType enum
        confidence_threshold: Min confidence (0-1)
    
    Returns:
        Response with incident details and image URLs
    """
    from incidents.models import Beacon, IncidentSignal, PhysicalDevice, IncidentImage
    from incidents.services import get_or_create_incident_with_signals, alert_guards_for_incident
    
    # Extract form data (multipart)
    beacon_id = (request.POST.get('beacon_id', '') or '').strip()
    confidence_score = request.POST.get('confidence_score')
    description = request.POST.get('description', '').strip()
    device_id = (request.POST.get('device_id', '') or '').strip()
    images_list = request.FILES.getlist('images', [])
    
    # Validate required fields
    if not beacon_id:
        return Response(
            {'error': 'beacon_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if confidence_score is None:
        return Response(
            {'error': 'confidence_score is required (0.0-1.0)'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not description:
        return Response(
            {'error': 'description is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate confidence score range
    try:
        confidence_score = float(confidence_score)
        if not (0.0 <= confidence_score <= 1.0):
            return Response(
                {'error': 'confidence_score must be between 0.0 and 1.0'},
                status=status.HTTP_400_BAD_REQUEST
            )
    except (ValueError, TypeError):
        return Response(
            {'error': 'confidence_score must be a valid number'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate image count
    if len(images_list) > 3:
        return Response(
            {'error': 'Maximum 3 images allowed'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate beacon exists
    try:
        beacon = Beacon.objects.get(beacon_id=beacon_id, is_active=True)
    except Beacon.DoesNotExist:
        return Response(
            {'error': f'Beacon {beacon_id} not found or inactive'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Look up device if provided
    source_device = None
    if device_id:
        try:
            source_device = PhysicalDevice.objects.get(device_id=device_id, is_active=True)
        except PhysicalDevice.DoesNotExist:
            source_device = None
    
    # Step 1: Always log the AI event
    ai_event = AIEvent.objects.create(
        beacon=beacon,
        event_type=event_type,
        confidence_score=confidence_score,
        details={
            'description': description,
            'raw_confidence': confidence_score,
            'device_id': device_id if device_id else None,
            'images_count': len(images_list)
        }
    )
    
    # Step 2: Check confidence threshold
    if confidence_score < confidence_threshold:
        return Response({
            'status': 'logged_only',
            'ai_event_id': ai_event.id,
            'message': f'Confidence {confidence_score:.2f} below threshold {confidence_threshold}',
            'images_received': len(images_list)
        }, status=status.HTTP_200_OK)
    
    # Step 3: Create incident signal
    try:
        incident, created, signal = get_or_create_incident_with_signals(
            beacon_id=beacon_id,
            signal_type=signal_type,
            ai_event_id=ai_event.id,
            source_device_id=source_device.id if source_device else None,
            description=description,
            details={
                'description': description,
                'ai_confidence': confidence_score,
                'ai_type': event_type.lower(),
                'device_id': device_id if device_id else None,
                'images_count': len(images_list)
            }
        )
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    # Step 4: Process and attach images
    image_objects = []
    print(f"\n{'='*60}")
    print(f"[AI DETECTION IMAGE UPLOAD] Processing {len(images_list)} images for incident {incident.id}")
    print(f"{'='*60}")
    
    for idx, image_file in enumerate(images_list[:3]):
        try:
            print(f"\n[Image {idx + 1}] Starting upload...")
            print(f"  File name: {image_file.name}")
            print(f"  Content type: {image_file.content_type}")
            print(f"  File size: {image_file.size} bytes")
            
            # Reset file pointer and read to verify
            image_file.seek(0)
            file_data = image_file.read()
            image_file.seek(0)
            print(f"  ✅ File read: {len(file_data)} bytes")
            
            # Save image to GCS
            incident_image = IncidentImage.objects.create(
                incident=incident,
                image=image_file,
                uploaded_by=None,  # AI detection (no user)
                description=f"AI Detection Image {idx + 1} ({event_type})"
            )
            
            if incident_image.image:
                stored_url = incident_image.image.url
                print(f"  ✅ Image {idx + 1} uploaded successfully!")
                print(f"     GCS URL: {stored_url}")
                image_objects.append(incident_image)
        except Exception as e:
            print(f"  ❌ ERROR saving image {idx + 1}: {str(e)}")
            continue
    
    print(f"\n[AI DETECTION IMAGE UPLOAD] Summary: {len(image_objects)} images uploaded")
    print(f"{'='*60}\n")
    
    # Step 5: Alert guards only if incident was newly created
    if created:
        alert_guards_for_incident(incident)
    
    # Prepare response
    response_data = {
        'status': 'incident_created' if created else 'signal_added_to_existing',
        'ai_event_id': ai_event.id,
        'incident_id': str(incident.id),
        'signal_id': signal.id,
        'confidence_score': confidence_score,
        'beacon_location': beacon.location_name,
        'incident_status': incident.status,
        'incident_priority': incident.get_priority_display(),
        'images': [
            {
                'id': img.id,
                'image': img.image.url,
                'uploaded_at': img.uploaded_at.isoformat(),
                'description': img.description
            }
            for img in image_objects
        ]
    }
    
    if device_id:
        response_data['device_id'] = device_id
    
    return Response(response_data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


def _process_ai_detection(request, event_type, signal_type, confidence_threshold, description_required=True):
    """
    Internal helper for AI detection endpoints.
    
    Args:
        request: HTTP request
        event_type: "VIOLENCE" or "SCREAM"
        signal_type: IncidentSignal.SignalType enum
        confidence_threshold: Min confidence (0-1)
        description_required: Whether description is mandatory
    
    Returns:
        Response with incident details or error
    """
    from incidents.models import Beacon, IncidentSignal, PhysicalDevice
    from incidents.services import get_or_create_incident_with_signals, alert_guards_for_incident
    
    beacon_id = request.data.get('beacon_id', '').strip()
    confidence_score = request.data.get('confidence_score')
    description = request.data.get('description', '').strip()
    device_id = request.data.get('device_id', '').strip()
    
    # Validate required fields
    if not beacon_id:
        return Response(
            {'error': 'beacon_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if confidence_score is None:
        return Response(
            {'error': 'confidence_score is required (0.0-1.0)'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if description_required and not description:
        return Response(
            {'error': 'description is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate confidence score range
    try:
        confidence_score = float(confidence_score)
        if not (0.0 <= confidence_score <= 1.0):
            return Response(
                {'error': 'confidence_score must be between 0.0 and 1.0'},
                status=status.HTTP_400_BAD_REQUEST
            )
    except (ValueError, TypeError):
        return Response(
            {'error': 'confidence_score must be a valid number'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate beacon exists
    try:
        beacon = Beacon.objects.get(beacon_id=beacon_id, is_active=True)
    except Beacon.DoesNotExist:
        return Response(
            {'error': f'Beacon {beacon_id} not found or inactive'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Look up device if provided
    source_device = None
    if device_id:
        try:
            source_device = PhysicalDevice.objects.get(device_id=device_id, is_active=True)
        except PhysicalDevice.DoesNotExist:
            # Device not found but continue (optional field)
            source_device = None
    
    # Step 1: Always log the AI event (for analytics/audit)
    ai_event = AIEvent.objects.create(
        beacon=beacon,
        event_type=event_type,
        confidence_score=confidence_score,
        details={
            'description': description,
            'raw_confidence': confidence_score,
            'device_id': device_id if device_id else None
        }
    )
    
    # Step 2: Check confidence threshold
    if confidence_score < confidence_threshold:
        return Response({
            'status': 'logged_only',
            'ai_event_id': ai_event.id,
            'message': f'Confidence {confidence_score:.2f} below threshold {confidence_threshold}'
        }, status=status.HTTP_200_OK)
    
    # Step 3: Create incident signal with description
    try:
        incident, created, signal = get_or_create_incident_with_signals(
            beacon_id=beacon_id,
            signal_type=signal_type,
            ai_event_id=ai_event.id,
            source_device_id=source_device.id if source_device else None,
            description=description,
            details={
                'description': description,
                'ai_confidence': confidence_score,
                'ai_type': event_type.lower(),
                'device_id': device_id if device_id else None
            }
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
        'confidence_score': confidence_score,
        'beacon_location': beacon.location_name,
        'incident_status': incident.status,
        'incident_priority': incident.get_priority_display()
    }
    
    if device_id:
        response_data['device_id'] = device_id
    
    return Response(response_data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def violence_detected(request):
    """
    Violence Detection Endpoint (with optional image attachments).
    
    Logs violence detection and creates/merges incident if confidence is high.
    Confidence threshold: 0.75 (75%)
    
    POST /api/ai/violence-detected/
    
    Request (JSON):
    {
        "beacon_id": "safe:uuid:403:403",
        "confidence_score": 0.92,
        "description": "Fight detected near library entrance",
        "device_id": "AI-MODEL-VIOLENCE-01"  // Optional
    }
    
    Request (Multipart with images):
    Form Data:
    - beacon_id: string
    - confidence_score: float
    - description: string
    - device_id: string (optional)
    - images: file[] (optional, max 3 images)
    
    Response (201 if new incident):
    {
        "status": "incident_created",
        "ai_event_id": 123,
        "incident_id": "75ca3932-0b7c-475b-834b-0573dfe037dc",
        "signal_id": 456,
        "confidence_score": 0.92,
        "beacon_location": "Library 3F Entrance",
        "incident_status": "CREATED",
        "incident_priority": "Critical",
        "device_id": "AI-MODEL-VIOLENCE-01",
        "images": [
            {
                "id": 1,
                "image": "https://storage.googleapis.com/...",
                "uploaded_at": "2025-12-26T...",
                "description": "Violence Detection Image 1"
            }
        ]
    }
    
    Response (200 if added to existing incident):
    {
        "status": "signal_added_to_existing",
        "incident_id": "...",
        "images": [...]
    }
    
    Response (200 if below threshold):
    {
        "status": "logged_only",
        "ai_event_id": 123,
        "message": "Confidence 0.65 below threshold 0.75"
    }
    """
    from incidents.models import IncidentSignal, IncidentImage
    
    # Check if multipart form data (has images) or JSON
    has_images = 'images' in request.FILES
    
    if has_images:
        # Handle multipart form data with images
        return _process_ai_detection_with_images(
            request,
            event_type=AIEvent.EventType.VIOLENCE,
            signal_type=IncidentSignal.SignalType.VIOLENCE_DETECTED,
            confidence_threshold=0.75
        )
    else:
        # Handle JSON request without images
        return _process_ai_detection(
            request,
            event_type=AIEvent.EventType.VIOLENCE,
            signal_type=IncidentSignal.SignalType.VIOLENCE_DETECTED,
            confidence_threshold=0.75,
            description_required=True
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def scream_detected(request):
    """
    Scream Detection Endpoint (with optional image attachments).
    
    Logs scream/cry detection and creates/merges incident if confidence is high.
    Confidence threshold: 0.80 (80%)
    
    POST /api/ai/scream-detected/
    
    Request (JSON):
    {
        "beacon_id": "safe:uuid:403:403",
        "confidence_score": 0.88,
        "description": "Loud screaming heard in hallway",
        "device_id": "AI-MODEL-AUDIO-01"  // Optional
    }
    
    Request (Multipart with images):
    Form Data:
    - beacon_id: string
    - confidence_score: float
    - description: string
    - device_id: string (optional)
    - images: file[] (optional, max 3 images)
    
    Response (201 if new incident):
    {
        "status": "incident_created",
        "ai_event_id": 124,
        "incident_id": "75ca3932-0b7c-475b-834b-0573dfe037dd",
        "signal_id": 457,
        "confidence_score": 0.88,
        "beacon_location": "Library 3F",
        "incident_status": "CREATED",
        "incident_priority": "High",
        "device_id": "AI-MODEL-AUDIO-01",
        "images": [...]
    }
    
    Response (200 if added to existing incident):
    {
        "status": "signal_added_to_existing",
        "incident_id": "...",
        "images": [...]
    }
    
    Response (200 if below threshold):
    {
        "status": "logged_only",
        "ai_event_id": 124,
        "message": "Confidence 0.72 below threshold 0.80"
    }
    """
    from incidents.models import IncidentSignal
    
    # Check if multipart form data (has images) or JSON
    has_images = 'images' in request.FILES
    
    if has_images:
        # Handle multipart form data with images
        return _process_ai_detection_with_images(
            request,
            event_type=AIEvent.EventType.SCREAM,
            signal_type=IncidentSignal.SignalType.SCREAM_DETECTED,
            confidence_threshold=0.80
        )
    else:
        # Handle JSON request without images
        return _process_ai_detection(
            request,
            event_type=AIEvent.EventType.SCREAM,
            signal_type=IncidentSignal.SignalType.SCREAM_DETECTED,
            confidence_threshold=0.80,
            description_required=True
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def ai_detection_endpoint(request):
    """
    LEGACY AI Detection Endpoint (kept for backward compatibility).
    
    POST /api/ai-detection/
    
    Request:
    {
        "beacon_id": "uuid",
        "event_type": "VIOLENCE" | "SCREAM",
        "confidence_score": 0.92,
        "description": "Optional description",
        "device_id": "AI-MODEL-01",  // Optional
        "details": {
            "additional_info": "..."
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
    from incidents.models import Beacon, IncidentSignal, PhysicalDevice
    from incidents.services import get_or_create_incident_with_signals, alert_guards_for_incident
    
    beacon_id = request.data.get('beacon_id', '').strip()
    event_type = request.data.get('event_type', '').strip().upper()
    confidence_score = request.data.get('confidence_score')
    description = request.data.get('description', '').strip()
    device_id = request.data.get('device_id', '').strip()
    details = request.data.get('details', {})
    
    if not all([beacon_id, event_type, confidence_score is not None]):
        return Response(
            {'error': 'beacon_id, event_type, and confidence_score are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Map types
    type_mapping = {
        'VIOLENCE': (AIEvent.EventType.VIOLENCE, IncidentSignal.SignalType.VIOLENCE_DETECTED, 0.75),
        'SCREAM': (AIEvent.EventType.SCREAM, IncidentSignal.SignalType.SCREAM_DETECTED, 0.80),
    }
    
    if event_type not in type_mapping:
        return Response(
            {'error': f'Invalid event_type: {event_type}. Must be: VIOLENCE or SCREAM'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate beacon
    try:
        beacon = Beacon.objects.get(beacon_id=beacon_id, is_active=True)
    except Beacon.DoesNotExist:
        return Response(
            {'error': f'Beacon {beacon_id} not found or inactive'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Look up device if provided
    source_device = None
    if device_id:
        try:
            source_device = PhysicalDevice.objects.get(device_id=device_id, is_active=True)
        except PhysicalDevice.DoesNotExist:
            source_device = None
    
    # Step 1: Always log the AI event (for analytics/audit)
    mapped_event_type, signal_type, threshold = type_mapping[event_type]
    
    ai_event = AIEvent.objects.create(
        beacon=beacon,
        event_type=mapped_event_type,
        confidence_score=confidence_score,
        details={
            'description': description,
            'raw_confidence': confidence_score,
            'device_id': device_id if device_id else None,
            **details
        }
    )
    
    # Step 2: Check confidence threshold
    if confidence_score < threshold:
        return Response({
            'status': 'logged_only',
            'ai_event_id': ai_event.id,
            'message': f'Confidence {confidence_score:.2f} below threshold {threshold}'
        }, status=status.HTTP_200_OK)
    
    # Step 3: Create incident signal
    try:
        incident, created, signal = get_or_create_incident_with_signals(
            beacon_id=beacon_id,
            signal_type=signal_type,
            ai_event_id=ai_event.id,
            source_device_id=source_device.id if source_device else None,
            description=description,
            details={
                'description': description,
                'ai_confidence': confidence_score,
                'ai_type': mapped_event_type.lower(),
                'device_id': device_id if device_id else None,
                **details
            }
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
    
    if device_id:
        response_data['device_id'] = device_id
    
    return Response(response_data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
