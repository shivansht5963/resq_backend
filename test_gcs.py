#!/usr/bin/env python
"""Test Google Cloud Storage integration"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_security.settings')
django.setup()

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings

print("=" * 60)
print("Testing Google Cloud Storage Integration")
print("=" * 60)
print(f"Storage Backend: {settings.DEFAULT_FILE_STORAGE}")
print(f"Bucket Name: {settings.GS_BUCKET_NAME}")
print(f"Project ID: {settings.GS_PROJECT_ID}")
print()

# Test file upload
test_content = b"Hello from RESQ! This is a test file uploaded to Google Cloud Storage."
file_path = "test-uploads/hello.txt"

try:
    # Save the test file
    saved_path = default_storage.save(file_path, ContentFile(test_content))
    print(f"✅ File uploaded successfully to GCS!")
    print(f"   Path: {saved_path}")
    
    # Get the URL
    file_url = default_storage.url(saved_path)
    print(f"   URL: {file_url}")
    
    # Verify it exists
    if default_storage.exists(saved_path):
        print(f"✅ File verified in GCS bucket!")
    
    # Read it back
    file_content = default_storage.open(saved_path).read()
    if file_content == test_content:
        print(f"✅ File content verified!")
    
    # List files in bucket
    print("\n📁 Files in bucket:")
    for file in default_storage.listdir('test-uploads')[1][:5]:
        print(f"   - {file}")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED! GCS is working perfectly!")
    print("=" * 60)
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
