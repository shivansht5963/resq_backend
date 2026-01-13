#!/usr/bin/env python
"""
Simple runner for debug scripts in Django shell.
Works cross-platform (Windows, Mac, Linux).

Usage:
    python run_debug.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_security.settings')
django.setup()

# Now run the debug script
import io
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from incidents.models import Incident, IncidentImage, Beacon
from django.core.files.storage import default_storage
from PIL import Image as PILImage
from io import BytesIO

User = get_user_model()

print("\n" + "="*70)
print("DEBUG IMAGE UPLOAD - CHECKING FILE STORAGE")
print("="*70)

# Get or create test user
user, created = User.objects.get_or_create(
    email="debug@test.com",
    defaults={
        'password': 'debug123',
        'full_name': 'Debug User',
        'role': 'STUDENT'
    }
)
print(f"\n[USER] {user.email} {'(created)' if created else '(existing)'}")

# Get or create test beacon
beacon, _ = Beacon.objects.get_or_create(
    beacon_id="debug_beacon",
    defaults={
        'uuid': 'f7826da6-4fa2-4e98-8024-bc5b71e0893e',
        'major': 10001,
        'minor': 10001,
        'location_name': 'Debug Location',
        'building': 'Building A',
        'floor': 1,
        'latitude': 40.7128,
        'longitude': -74.0060
    }
)
print(f"[BEACON] {beacon.location_name}")

# Get or create test incident
incident, _ = Incident.objects.get_or_create(
    beacon=beacon,
    description="Debug test",
    defaults={
        'status': 'CREATED',
        'priority': 3,
        'location': 'Debug Location'
    }
)
print(f"[INCIDENT] {incident.id}")

# Create test image file
print("\n[IMAGE CREATION]")
image = PILImage.new('RGB', (640, 480), color='red')
image_io = BytesIO()
image.save(image_io, format='JPEG', quality=85)
image_io.seek(0)
image_io.name = 'debug_test.jpg'
print(f"  Created: {image_io.name}")
print(f"  Size: {image_io.getbuffer().nbytes} bytes")
print(f"  Position: {image_io.tell()}")

# Check storage backend
print("\n[STORAGE BACKEND]")
storage = default_storage
print(f"  Class: {storage.__class__.__name__}")
print(f"  Module: {storage.__class__.__module__}")

if hasattr(storage, 'bucket'):
    print(f"  Bucket: {storage.bucket.name}")
    print(f"  Has bucket attribute: ✓")
else:
    print(f"  Has bucket attribute: ✗")

# Try uploading directly with storage
print("\n[DIRECT STORAGE TEST]")
try:
    image_io.seek(0)
    filename = f"debug_test_{user.id}.jpg"
    path = storage.save(f'test/{filename}', image_io)
    print(f"  ✓ Direct save succeeded")
    print(f"    Path: {path}")
    
    try:
        url = storage.url(path)
        print(f"    URL: {url}")
    except Exception as e:
        print(f"    URL error: {e}")
except Exception as e:
    print(f"  ✗ Direct save failed: {e}")
    import traceback
    traceback.print_exc()

# Now try creating IncidentImage model
print("\n[MODEL SAVE TEST]")
image_io.seek(0)

try:
    # Convert BytesIO to Django File object
    from django.core.files.base import File
    
    django_file = File(image_io, name='debug_test.jpg')
    
    incident_image = IncidentImage(
        incident=incident,
        image=django_file,
        uploaded_by=user,
        description="Debug test image"
    )
    
    print(f"  Created IncidentImage object with Django File (not saved yet)")
    print(f"    Image field: {incident_image.image}")
    print(f"    Image name: {incident_image.image.name}")
    
    # Now save
    print(f"\n  Calling save()...")
    incident_image.save()
    
    print(f"  ✓ Save succeeded")
    print(f"    ID: {incident_image.id}")
    print(f"    Image name: {incident_image.image.name}")
    print(f"    Image path: {incident_image.image.name}")
    
    # Try to get URL
    try:
        url = incident_image.image.url
        print(f"    Image URL: {url}")
        
        # Check if file exists in GCS
        if hasattr(storage, 'bucket'):
            blob = storage.bucket.blob(incident_image.image.name)
            exists = blob.exists()
            print(f"    Exists in GCS: {'✓ YES' if exists else '✗ NO'}")
            
            if not exists:
                print(f"\n    ⚠️  FILE NOT IN GCS!")
                print(f"       Database has record: {incident_image.image.name}")
                print(f"       But GCS doesn't have the file")
                print(f"       This is the problem!")
    except Exception as e:
        print(f"    Error getting URL: {e}")
    
except Exception as e:
    print(f"  ✗ Save failed: {e}")
    import traceback
    traceback.print_exc()

# Query back from database
print("\n[DATABASE QUERY]")
try:
    saved_image = IncidentImage.objects.filter(uploaded_by=user).last()
    if saved_image:
        print(f"  ✓ Found image in database")
        print(f"    ID: {saved_image.id}")
        print(f"    Name: {saved_image.image.name}")
        
        try:
            print(f"    URL: {saved_image.image.url}")
        except Exception as e:
            print(f"    URL error: {e}")
    else:
        print(f"  ✗ No images found for user")
except Exception as e:
    print(f"  ✗ Query failed: {e}")

print("\n" + "="*70)
print("\nDEBUG TEST COMPLETE")
print("\nInterpret the output above to determine where the upload fails.")
print("="*70 + "\n")
