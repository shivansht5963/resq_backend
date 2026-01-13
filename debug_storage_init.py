#!/usr/bin/env python
import os
import sys
from pathlib import Path

# Set GCS credentials
creds_path = Path(__file__).resolve().parent / 'credentials' / 'gen-lang-client-0117249847-eb5558a80732.json'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(creds_path)

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campus_security.settings")

# Try importing directly
print("=" * 60)
print("DIRECT IMPORT TEST")
print("=" * 60)

try:
    from storages.backends.gcloud import GoogleCloudStorage
    print("✓ Successfully imported GoogleCloudStorage from storages")
    
    # Try to instantiate it
    storage = GoogleCloudStorage()
    print(f"✓ Successfully instantiated GoogleCloudStorage")
    print(f"  Bucket: {storage.bucket}")
    print(f"  Client: {storage.client}")
except Exception as e:
    print(f"✗ Failed to instantiate GoogleCloudStorage: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("DJANGO SETUP TEST")
print("=" * 60)

django.setup()

from django.conf import settings
from django.core.files.storage import default_storage

print(f"Settings DEFAULT_FILE_STORAGE: {settings.DEFAULT_FILE_STORAGE}")
print(f"Actual default_storage class: {default_storage.__class__.__module__}.{default_storage.__class__.__name__}")

# Check for initialization errors
print(f"\nChecking settings imports:")
print(f"  INSTALLED_APPS has 'storages': {'storages' in settings.INSTALLED_APPS}")

# Try manually loading the class
print("\n" + "=" * 60)
print("MANUAL CLASS LOAD TEST")
print("=" * 60)

try:
    # Dynamically load the class specified in DEFAULT_FILE_STORAGE
    from django.utils.module_loading import import_string
    storage_class = import_string(settings.DEFAULT_FILE_STORAGE)
    print(f"✓ Loaded class: {storage_class}")
    print(f"  Base classes: {storage_class.__bases__}")
    
    # Try to instantiate it
    manual_storage = storage_class()
    print(f"✓ Instantiated: {manual_storage}")
    print(f"  Type: {type(manual_storage)}")
except Exception as e:
    print(f"✗ Failed: {e}")
    import traceback
    traceback.print_exc()

# Check if there's an initialization error being silently caught
print("\n" + "=" * 60)
print("STORAGE HANDLER DEBUG")
print("=" * 60)

from django.core.files.storage import storages as storage_handler

try:
    # Try to access the storage handler's internal __getitem__
    default = storage_handler['default']
    print(f"Storage handler['default']: {default}")
    print(f"  Class: {default.__class__}")
except Exception as e:
    print(f"✗ Error accessing storage: {e}")
    import traceback
    traceback.print_exc()
    
print("\n" + "=" * 60)
print("CHECKING FOR INITIALIZATION ISSUES")
print("=" * 60)

# Check GCS credentials
print(f"GOOGLE_APPLICATION_CREDENTIALS: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'NOT SET')}")
print(f"GS_BUCKET_NAME: {settings.GS_BUCKET_NAME}")
print(f"GS_PROJECT_ID: {settings.GS_PROJECT_ID}")
print(f"GS_QUERYSTRING_AUTH: {settings.GS_QUERYSTRING_AUTH}")
