#!/usr/bin/env python
"""
Diagnose GCS Upload Issues - Check Credentials and Permissions

Run: python diagnose_gcs.py
"""

import os
import sys
import json

print("\n" + "="*70)
print("GCS CREDENTIALS & PERMISSIONS DIAGNOSTIC")
print("="*70)

# Check 1: GOOGLE_APPLICATION_CREDENTIALS
print("\n[1] GOOGLE_APPLICATION_CREDENTIALS")
cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
print(f"  Path: {cred_path}")

if cred_path:
    if os.path.exists(cred_path):
        print(f"  ✓ File exists")
        try:
            with open(cred_path, 'r') as f:
                creds = json.load(f)
            print(f"  ✓ File is valid JSON")
            print(f"  Service account: {creds.get('client_email', 'UNKNOWN')}")
            print(f"  Project ID: {creds.get('project_id', 'UNKNOWN')}")
        except json.JSONDecodeError:
            print(f"  ✗ File is NOT valid JSON")
    else:
        print(f"  ✗ File does NOT exist at that path")
else:
    print(f"  ✗ Environment variable not set")

# Check 2: Try to load Google credentials
print("\n[2] LOADING GOOGLE CREDENTIALS")
try:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    
    if cred_path and os.path.exists(cred_path):
        credentials = service_account.Credentials.from_service_account_file(
            cred_path,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        print(f"  ✓ Credentials loaded successfully")
        print(f"  Service account email: {credentials.service_account_email}")
        print(f"  Project ID: {credentials.project_id}")
        
        # Refresh to check if they're valid
        print(f"  Testing credentials validity...")
        credentials.refresh(Request())
        print(f"  ✓ Credentials are valid and can authenticate")
    else:
        print(f"  ✗ Cannot load - credentials file not found")
except Exception as e:
    print(f"  ✗ Error loading credentials: {e}")

# Check 3: Django configuration
print("\n[3] DJANGO CONFIGURATION")
try:
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_security.settings')
    django.setup()
    
    from django.conf import settings
    print(f"  DEFAULT_FILE_STORAGE: {settings.DEFAULT_FILE_STORAGE}")
    print(f"  GS_BUCKET_NAME: {settings.GS_BUCKET_NAME}")
    print(f"  GS_PROJECT_ID: {settings.GS_PROJECT_ID}")
    print(f"  GS_QUERYSTRING_AUTH: {settings.GS_QUERYSTRING_AUTH}")
    print(f"  MEDIA_URL: {settings.MEDIA_URL}")
except Exception as e:
    print(f"  ✗ Error loading Django settings: {e}")

# Check 4: Test direct GCS upload
print("\n[4] TEST DIRECT GCS UPLOAD")
try:
    from google.cloud import storage
    from io import BytesIO
    
    # Use default credentials from environment
    client = storage.Client()
    bucket = client.bucket('resq-campus-security')
    
    print(f"  ✓ GCS client initialized")
    print(f"  Bucket: {bucket.name}")
    
    # Try to upload test file
    test_blob = bucket.blob('test_direct_upload_$(date +%s).txt')
    test_content = b'Test upload to verify permissions'
    
    try:
        test_blob.upload_from_string(test_content, content_type='text/plain')
        print(f"  ✓ Successfully uploaded test file to GCS")
        print(f"    Path: {test_blob.name}")
        
        # Try to access it
        if test_blob.exists():
            print(f"  ✓ File exists in GCS (can be verified)")
        else:
            print(f"  ✗ File uploaded but doesn't exist check")
    except Exception as e:
        print(f"  ✗ Upload failed: {e}")
        print(f"     This indicates permission issue")
        
except Exception as e:
    print(f"  ✗ Cannot test GCS: {e}")
    print(f"     Make sure google-cloud-storage is installed:")
    print(f"     pip install google-cloud-storage")

# Check 5: Test django-storages
print("\n[5] TEST DJANGO-STORAGES UPLOAD")
try:
    from django.core.files.base import File
    from django.core.files.storage import default_storage
    from io import BytesIO
    
    print(f"  Storage backend: {default_storage.__class__.__name__}")
    
    # Create test file
    test_file = BytesIO(b'Django storages test file')
    test_file.name = 'django_test.txt'
    
    # Try to save
    try:
        path = default_storage.save('test/django_upload_test.txt', test_file)
        print(f"  ✓ Django-storages save succeeded")
        print(f"    Path: {path}")
        
        # Try to get URL
        try:
            url = default_storage.url(path)
            print(f"    URL: {url}")
        except Exception as e:
            print(f"    URL error: {e}")
            
        # Check if file exists in GCS
        if hasattr(default_storage, 'bucket'):
            blob = default_storage.bucket.blob(path)
            if blob.exists():
                print(f"  ✓ File confirmed in GCS")
            else:
                print(f"  ✗ File NOT in GCS (save failed silently)")
    except Exception as e:
        print(f"  ✗ Django-storages save failed: {e}")
        
except Exception as e:
    print(f"  ✗ Cannot test django-storages: {e}")

print("\n" + "="*70)
print("\nDIAGNOSTIC COMPLETE")
print("="*70 + "\n")
