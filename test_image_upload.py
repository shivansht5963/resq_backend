"""
Image Upload Diagnostic Script
Helps identify exactly where the image upload is failing
"""

import os
import sys
import django
from io import BytesIO
from PIL import Image as PILImage

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_security.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.conf import settings
from incidents.models import Beacon, Incident, IncidentImage

User = get_user_model()

print("=" * 80)
print("IMAGE UPLOAD DIAGNOSTIC TOOL")
print("=" * 80)

# 1. Check media directory
print("\n[1] Checking Media Directory...")
media_root = settings.MEDIA_ROOT
print(f"   MEDIA_ROOT: {media_root}")
print(f"   MEDIA_URL: {settings.MEDIA_URL}")

if os.path.exists(media_root):
    print(f"   ✅ Media directory exists")
    print(f"   Writable: {os.access(media_root, os.W_OK)}")
else:
    print(f"   ❌ Media directory does NOT exist")
    print(f"   Creating directory...")
    os.makedirs(media_root, exist_ok=True)
    print(f"   ✅ Created")

# 2. Check if Pillow is installed
print("\n[2] Checking Pillow Installation...")
try:
    from PIL import Image
    print(f"   ✅ Pillow is installed: {PILImage.__version__}")
except ImportError:
    print(f"   ❌ Pillow is NOT installed")

# 3. Create test image in memory
print("\n[3] Creating Test Image...")
try:
    img = PILImage.new('RGB', (100, 100), color='red')
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    print(f"   ✅ Test image created (size: {img_bytes.getbuffer().nbytes} bytes)")
except Exception as e:
    print(f"   ❌ Failed to create test image: {e}")
    sys.exit(1)

# 4. Check if test user exists
print("\n[4] Checking Test User...")
try:
    user = User.objects.filter(email='test@example.com').first()
    if user:
        print(f"   ✅ Test user exists: {user.email}")
    else:
        print(f"   ❌ Test user does not exist")
        print(f"   Creating test user...")
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            full_name='Test User'
        )
        print(f"   ✅ Test user created")
except Exception as e:
    print(f"   ❌ Error with test user: {e}")
    sys.exit(1)

# 5. Check if test beacon exists
print("\n[5] Checking Test Beacon...")
try:
    beacon = Beacon.objects.filter(beacon_id='TEST_BEACON').first()
    if beacon:
        print(f"   ✅ Test beacon exists: {beacon.beacon_id}")
    else:
        print(f"   ❌ Test beacon does not exist")
        print(f"   Creating test beacon...")
        beacon = Beacon.objects.create(
            beacon_id='TEST_BEACON',
            uuid='f7826da6-4fa2-4e98-8024-bc5b71e0893e',
            major=1,
            minor=1,
            location_name='Test Location',
            building='Test Building',
            floor=1
        )
        print(f"   ✅ Test beacon created")
except Exception as e:
    print(f"   ❌ Error with test beacon: {e}")
    sys.exit(1)

# 6. Test direct IncidentImage model save
print("\n[6] Testing Direct Model Save...")
try:
    from incidents.models import IncidentSignal
    
    # Create incident via service
    from incidents.services import get_or_create_incident_with_signals
    
    incident, created, signal = get_or_create_incident_with_signals(
        beacon_id='TEST_BEACON',
        signal_type=IncidentSignal.SignalType.STUDENT_REPORT,
        source_user_id=user.id,
        description='Test incident for image upload'
    )
    print(f"   ✅ Incident created: {incident.id}")
    
    # Try to save image directly
    img_bytes.seek(0)
    img_file = type('ImageFile', (), {
        'read': lambda: img_bytes.getvalue(),
        'name': 'test.jpg',
        'size': img_bytes.getbuffer().nbytes,
        'seek': img_bytes.seek,
        'tell': img_bytes.tell
    })()
    
    from django.core.files.uploadedfile import SimpleUploadedFile
    uploaded_file = SimpleUploadedFile(
        name='test_image.jpg',
        content=img_bytes.getvalue(),
        content_type='image/jpeg'
    )
    
    incident_image = IncidentImage.objects.create(
        incident=incident,
        image=uploaded_file,
        uploaded_by=user,
        description='Test image'
    )
    print(f"   ✅ IncidentImage saved: ID {incident_image.id}")
    print(f"   Image path: {incident_image.image.name}")
    print(f"   Image URL: {incident_image.image.url}")
    
    # Check if file was actually saved
    full_path = incident_image.image.path
    print(f"   Full path: {full_path}")
    if os.path.exists(full_path):
        print(f"   ✅ File exists on disk")
        print(f"   File size: {os.path.getsize(full_path)} bytes")
    else:
        print(f"   ❌ File does NOT exist on disk")
        
except Exception as e:
    print(f"   ❌ Error saving image: {e}")
    import traceback
    traceback.print_exc()

# 7. Test API endpoint with test client
print("\n[7] Testing API Endpoint...")
try:
    client = Client()
    
    # Login using the correct endpoint
    login_response = client.post('/api/auth/login/', {
        'email': 'test@example.com',
        'password': 'testpass123'
    }, content_type='application/json')
    
    if login_response.status_code == 200:
        print(f"   ✅ Login successful")
        data = login_response.json()
        token = data.get('token') or data.get('auth_token')
        print(f"   Token: {token[:20]}..." if token else "   Token: None")
    else:
        print(f"   ❌ Login failed: {login_response.status_code}")
        print(f"   Response: {login_response.content[:200]}")
        token = None
    
    if token:
        # Prepare multipart form data
        img_bytes.seek(0)
        
        from django.core.files.uploadedfile import SimpleUploadedFile
        test_file = SimpleUploadedFile(
            name='test_api.jpg',
            content=img_bytes.getvalue(),
            content_type='image/jpeg'
        )
        
        # Test report endpoint
        report_response = client.post(
            '/api/incidents/report/',
            {
                'type': 'theft',
                'description': 'Test incident with image',
                'beacon_id': 'TEST_BEACON',
                'images': test_file
            },
            HTTP_AUTHORIZATION=f'Token {token}'
        )
        
        print(f"   API Response Status: {report_response.status_code}")
        if report_response.status_code in [201, 200]:
            print(f"   ✅ Upload successful via API")
            response_data = report_response.json()
            if 'images' in response_data and response_data['images']:
                print(f"   Images in response: {len(response_data['images'])}")
                for img in response_data['images']:
                    print(f"      - Image URL: {img.get('image', 'N/A')}")
            else:
                print(f"   Response: {response_data}")
        else:
            print(f"   ❌ Upload failed")
            try:
                print(f"   Response: {report_response.json()}")
            except:
                print(f"   Response: {report_response.content[:200]}")
    else:
        print(f"   ⚠️  Skipping API test - no token")
            
except Exception as e:
    print(f"   ❌ Error testing API: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)
