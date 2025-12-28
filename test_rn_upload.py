"""
Debug script to test image uploads like React Native would
"""

import os
import sys
import django
from io import BytesIO

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_security.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image as PILImage
from incidents.models import IncidentImage, Incident

User = get_user_model()

print("=" * 80)
print("REACT NATIVE IMAGE UPLOAD TEST")
print("=" * 80)

# Get or create test user
user, _ = User.objects.get_or_create(
    email='rn-test@example.com',
    defaults={'full_name': 'RN Tester', 'password': 'test123'}
)
if _:
    user.set_password('test123')
    user.save()
print(f"\n✅ Test user: {user.email}")

# Create test image (simulate React Native upload)
print("\n[1] Creating test image (like React Native camera)...")
img = PILImage.new('RGB', (800, 600), color='blue')
img_bytes = BytesIO()
img.save(img_bytes, format='JPEG')
img_bytes.seek(0)
print(f"✅ Image created: {img_bytes.getbuffer().nbytes} bytes")

# Test with Django test client (simulates what React Native does)
print("\n[2] Testing API endpoint...")
client = Client()

# Login
login_response = client.post('/api/auth/login/', {
    'email': 'rn-test@example.com',
    'password': 'test123'
}, content_type='application/json')

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.status_code}")
    print(login_response.json())
    sys.exit(1)

token = login_response.json().get('auth_token')
if not token:
    print(f"❌ No token in response: {login_response.json()}")
    sys.exit(1)
print(f"✅ Logged in, token: {token[:20]}...")

# Prepare image like React Native would
img_bytes.seek(0)
test_file = SimpleUploadedFile(
    name='react-native-photo.jpg',
    content=img_bytes.getvalue(),
    content_type='image/jpeg'
)

print("\n[3] Uploading image via POST /api/incidents/report/...")
report_response = client.post(
    '/api/incidents/report/',
    {
        'type': 'accident',
        'description': 'Test from React Native',
        'location': 'Test Location',
        'images': test_file
    },
    HTTP_AUTHORIZATION=f'Token {token}'
)

print(f"Response Status: {report_response.status_code}")

if report_response.status_code not in [200, 201]:
    print(f"❌ Upload failed!")
    print(report_response.json())
else:
    print(f"✅ Upload successful!")
    response = report_response.json()
    
    print(f"\nResponse Data:")
    print(f"  Status: {response.get('status')}")
    print(f"  Incident ID: {response.get('incident_id')}")
    print(f"  Report Type: {response.get('report_type')}")
    
    # Check images in response
    images = response.get('images', [])
    print(f"\n  Images in response: {len(images)}")
    if images:
        for i, img_data in enumerate(images):
            print(f"    Image {i+1}:")
            print(f"      - ID: {img_data.get('id')}")
            print(f"      - URL: {img_data.get('image')}")
            print(f"      - Uploaded by: {img_data.get('uploaded_by_email')}")
    else:
        print(f"    ⚠️  NO IMAGES IN RESPONSE!")
    
    # Check images in incident data
    incident_data = response.get('incident', {})
    incident_images = incident_data.get('images', [])
    print(f"\n  Images in incident detail: {len(incident_images)}")
    if incident_images:
        for i, img_data in enumerate(incident_images):
            print(f"    Image {i+1}: {img_data.get('image')}")
    else:
        print(f"    ⚠️  NO IMAGES IN INCIDENT DETAIL!")
    
    # Check database directly
    incident_id = response.get('incident_id')
    incident = Incident.objects.get(id=incident_id)
    db_images = incident.images.all()
    print(f"\n[4] Database check for incident {incident_id}:")
    print(f"  Total images in DB: {db_images.count()}")
    
    for db_img in db_images:
        print(f"    - Image ID: {db_img.id}")
        print(f"      File: {db_img.image.name}")
        print(f"      URL: {db_img.image.url}")
        try:
            # Try to access the file
            if db_img.image:
                print(f"      ✅ File accessible")
            else:
                print(f"      ❌ File not accessible")
        except Exception as e:
            print(f"      ❌ Error: {e}")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
