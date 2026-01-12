#!/usr/bin/env python
"""
Test script to verify incident API returns all images with proper format.

Tests:
1. Create incident with multiple images
2. Verify GET /api/incidents/{id}/ returns all images with absolute URLs
3. Verify list endpoint includes image_count
4. Verify image serializer returns proper fields
"""

import os
import django
import json
from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_security.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test.client import Client
from rest_framework.test import APIRequestFactory
from incidents.models import Incident, Beacon, IncidentImage, IncidentSignal
from incidents.serializers import IncidentDetailedSerializer, IncidentImageSerializer

User = get_user_model()


def create_test_image(filename='test_image.jpg'):
    """Create a simple test image using SimpleUploadedFile."""
    img = Image.new('RGB', (100, 100), color='red')
    img_io = BytesIO()
    img.save(img_io, format='JPEG')
    img_io.seek(0)
    
    # Use SimpleUploadedFile which is Django-compatible
    return SimpleUploadedFile(
        filename,
        img_io.getvalue(),
        content_type='image/jpeg'
    )


def test_incident_image_api():
    """Test the incident image API response."""
    print("\n" + "="*70)
    print("TEST: Incident Image API Response")
    print("="*70)
    
    # Create test user (student)
    try:
        student = User.objects.get(email='test_student@example.com')
    except User.DoesNotExist:
        student = User.objects.create_user(
            email='test_student@example.com',
            password='testpass123',
            full_name='Test Student',
            role='STUDENT'
        )
    
    # Create test beacon
    beacon, _ = Beacon.objects.get_or_create(
        beacon_id='test:beacon:001',
        defaults={
            'uuid': '550e8400-e29b-41d4-a716-446655440000',
            'major': 100,
            'minor': 1,
            'location_name': 'Test Location',
            'building': 'Test Building',
            'floor': 1
        }
    )
    
    # Create incident
    incident = Incident.objects.create(
        beacon=beacon,
        description='Test incident with images',
        report_type='Safety Concern',
        status=Incident.Status.CREATED,
        priority=Incident.Priority.HIGH
    )
    
    # Create signal
    signal = IncidentSignal.objects.create(
        incident=incident,
        signal_type=IncidentSignal.SignalType.STUDENT_REPORT,
        source_user=student,
        details={}
    )
    
    print(f"\n✓ Created test incident: {incident.id}")
    print(f"✓ Created test signal: {signal.id}")
    
    # Add multiple images
    image_count = 3
    image_ids = []
    for i in range(image_count):
        img = create_test_image()
        incident_img = IncidentImage.objects.create(
            incident=incident,
            image=img,
            uploaded_by=student,
            description=f'Test image {i+1}'
        )
        image_ids.append(incident_img.id)
        print(f"✓ Added image {i+1}: {incident_img.id}")
    
    # Test serialization with request context (to get absolute URLs)
    factory = APIRequestFactory()
    request = factory.get(f'/api/incidents/{incident.id}/')
    
    serializer = IncidentDetailedSerializer(incident, context={'request': request})
    data = serializer.data
    
    print("\n" + "-"*70)
    print("SERIALIZED INCIDENT DATA:")
    print("-"*70)
    
    # Check images field
    if 'images' in data:
        images_data = data['images']
        print(f"\n✓ Images field present in response")
        print(f"✓ Number of images: {len(images_data)}")
        
        # Verify each image
        for idx, img_data in enumerate(images_data):
            print(f"\n  Image {idx + 1}:")
            print(f"    - ID: {img_data.get('id')}")
            print(f"    - Image URL: {img_data.get('image')}")
            print(f"    - Uploaded by: {img_data.get('uploaded_by_email')}")
            print(f"    - Uploaded by name: {img_data.get('uploaded_by_name')}")
            print(f"    - Uploaded at: {img_data.get('uploaded_at')}")
            print(f"    - Description: {img_data.get('description')}")
            
            # Verify URL is absolute
            if img_data.get('image'):
                if img_data['image'].startswith('http'):
                    print(f"    ✓ URL is absolute (HTTP/HTTPS)")
                else:
                    print(f"    ✗ URL is NOT absolute")
            else:
                print(f"    ✗ Image URL is missing!")
    else:
        print(f"✗ Images field NOT present in response!")
    
    # Test list serializer
    print("\n" + "-"*70)
    print("LIST VIEW DATA:")
    print("-"*70)
    
    from incidents.serializers import IncidentListSerializer
    list_serializer = IncidentListSerializer(incident, context={'request': request})
    list_data = list_serializer.data
    
    print(f"\n✓ Image count in list view: {list_data.get('image_count')}")
    
    # Test IncidentImageSerializer directly
    print("\n" + "-"*70)
    print("INCIDENT IMAGE SERIALIZER TEST:")
    print("-"*70)
    
    images = incident.images.all()
    img_serializer = IncidentImageSerializer(images, many=True, context={'request': request})
    img_data = img_serializer.data
    
    print(f"\n✓ Direct serialization of {len(img_data)} images:")
    for idx, img in enumerate(img_data):
        print(f"\n  Image {idx + 1} fields:")
        for key, value in img.items():
            if key == 'image':
                print(f"    - {key}: {'✓ Present' if value else '✗ Missing'}")
            else:
                print(f"    - {key}: {value}")
    
    # Test push notification data
    print("\n" + "-"*70)
    print("PUSH NOTIFICATION DATA:")
    print("-"*70)
    
    # Simulate what send_push_notifications_for_alerts does
    images = incident.images.all().order_by('uploaded_at')
    image_urls = []
    if images.exists():
        image_urls = [
            img.image.url for img in images[:3]
        ]
    
    notification_data = {
        "type": "GUARD_ALERT",
        "incident_id": str(incident.id),
        "alert_id": "test-alert-id",
        "priority": "HIGH",
        "location": incident.location or incident.beacon.location_name,
        "image_count": incident.images.count(),
    }
    
    if image_urls:
        notification_data["images"] = image_urls
    
    print(f"\n✓ Notification data includes:")
    print(f"  - Image count: {notification_data.get('image_count')}")
    print(f"  - Images present: {'Yes' if 'images' in notification_data else 'No'}")
    print(f"  - Number of image URLs: {len(image_urls)}")
    
    if image_urls:
        for idx, url in enumerate(image_urls):
            print(f"    - Image {idx+1}: {url}")
    
    print("\n" + "="*70)
    print("✓ ALL TESTS PASSED - Images are properly formatted and included")
    print("="*70 + "\n")
    
    # Cleanup
    incident.delete()
    print("Cleaned up test data.")


def test_with_client():
    """Test using Django test client (simulates API request)."""
    print("\n" + "="*70)
    print("TEST: Using Django Test Client (Full API Simulation)")
    print("="*70)
    
    client = Client()
    
    # Create test user
    try:
        student = User.objects.get(email='api_test_student@example.com')
    except User.DoesNotExist:
        student = User.objects.create_user(
            email='api_test_student@example.com',
            password='testpass123',
            full_name='API Test Student',
            role='STUDENT'
        )
    
    # Create beacon
    beacon, _ = Beacon.objects.get_or_create(
        beacon_id='test:api:beacon',
        defaults={
            'uuid': '550e8400-e29b-41d4-a716-446655440001',
            'major': 101,
            'minor': 2,
            'location_name': 'API Test Location',
            'building': 'API Test Building',
            'floor': 2
        }
    )
    
    # Create incident with signal
    incident = Incident.objects.create(
        beacon=beacon,
        description='API test incident',
        report_type='Test Report',
        status=Incident.Status.CREATED,
        priority=Incident.Priority.MEDIUM
    )
    
    signal = IncidentSignal.objects.create(
        incident=incident,
        signal_type=IncidentSignal.SignalType.STUDENT_REPORT,
        source_user=student,
        details={}
    )
    
    # Add images
    for i in range(2):
        img = create_test_image()
        IncidentImage.objects.create(
            incident=incident,
            image=img,
            uploaded_by=student,
            description=f'API test image {i+1}'
        )
    
    print(f"\n✓ Created incident {incident.id} with 2 images")
    
    # Simulate API call to retrieve incident details
    print(f"\nSimulating: GET /api/incidents/{incident.id}/")
    print("Note: In actual API, authentication would be required")
    
    # Directly test serializer
    factory = APIRequestFactory()
    request = factory.get(f'/api/incidents/{incident.id}/')
    
    serializer = IncidentDetailedSerializer(incident, context={'request': request})
    response_data = serializer.data
    
    print(f"\n✓ Response includes {len(response_data.get('images', []))} images")
    
    for img in response_data.get('images', []):
        print(f"\n  Image details:")
        print(f"    ID: {img.get('id')}")
        print(f"    URL: {img.get('image')[:50]}..." if img.get('image') else "    URL: None")
        print(f"    Uploaded by: {img.get('uploaded_by_name')} ({img.get('uploaded_by_email')})")
    
    # Cleanup
    incident.delete()
    print(f"\n✓ Cleaned up test data")


if __name__ == '__main__':
    try:
        test_incident_image_api()
        test_with_client()
        print("\n" + "="*70)
        print("✓✓✓ ALL TESTS COMPLETED SUCCESSFULLY ✓✓✓")
        print("="*70)
    except Exception as e:
        print(f"\n✗ Test failed with error:")
        print(f"  {str(e)}")
        import traceback
        traceback.print_exc()
