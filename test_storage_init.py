#!/usr/bin/env python
"""
Test if PublicGoogleCloudStorage can be instantiated

Run: python test_storage_init.py
"""

import os
from pathlib import Path

# Set credentials
creds_path = Path(__file__).resolve().parent / 'credentials' / 'gen-lang-client-0117249847-eb5558a80732.json'
if creds_path.exists():
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(creds_path)

print("Testing Storage Backend Initialization")
print("="*70)

# Test 1: Import
print("\n[1] Importing PublicGoogleCloudStorage...")
try:
    from campus_security.storage import PublicGoogleCloudStorage
    print("  ✓ Import successful")
except Exception as e:
    print(f"  ✗ Import failed: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Try to instantiate directly
print("\n[2] Instantiating PublicGoogleCloudStorage()...")
try:
    storage = PublicGoogleCloudStorage()
    print(f"  ✓ Instantiation successful")
    print(f"    Class: {storage.__class__.__name__}")
    print(f"    Bucket: {storage.bucket.name if hasattr(storage, 'bucket') else 'NO BUCKET'}")
except Exception as e:
    print(f"  ✗ Instantiation failed: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Check Django's default_storage
print("\n[3] Checking Django default_storage...")
try:
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_security.settings')
    django.setup()
    
    from django.core.files.storage import default_storage
    print(f"  default_storage class: {default_storage.__class__.__name__}")
    print(f"  Module: {default_storage.__class__.__module__}")
    
    if hasattr(default_storage, 'bucket'):
        print(f"  Bucket: {default_storage.bucket.name}")
    else:
        print(f"  ✗ No bucket attribute (FileSystem storage?)")
        
    # Try to save a test file
    print(f"\n[4] Testing file save with default_storage...")
    from io import BytesIO
    test_file = BytesIO(b'test content')
    test_file.name = 'test.txt'
    
    try:
        path = default_storage.save('test/storage_test.txt', test_file)
        print(f"  ✓ Save succeeded: {path}")
        
        try:
            url = default_storage.url(path)
            print(f"    URL: {url}")
        except Exception as e:
            print(f"    URL error: {e}")
    except Exception as e:
        print(f"  ✗ Save failed: {e}")
        
except Exception as e:
    print(f"  ✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
