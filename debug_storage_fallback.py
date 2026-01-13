#!/usr/bin/env python
import os
import sys
from pathlib import Path

# Set GCS credentials
creds_path = Path(__file__).resolve().parent / 'credentials' / 'gen-lang-client-0117249847-eb5558a80732.json'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(creds_path)

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campus_security.settings")
django.setup()

from django.conf import settings
from django.utils.module_loading import import_string

print("Attempting to instantiate GCS storage with proper error handling...")
print("=" * 60)

try:
    storage_class = import_string(settings.DEFAULT_FILE_STORAGE)
    print(f"Class loaded: {storage_class}")
    
    # Try to instantiate with detailed error reporting
    storage = storage_class()
    print(f"✓ Successfully created storage: {storage}")
except Exception as e:
    print(f"✗ ERROR INSTANTIATING STORAGE:")
    print(f"  Type: {type(e).__name__}")
    print(f"  Message: {e}")
    import traceback
    traceback.print_exc()
    
# Check if there's a fallback mechanism
print("\n" + "=" * 60)
print("Checking Django's storage initialization...")

from django.core.files import storage as storage_module
print(f"Storage module path: {storage_module.__file__}")

# Check if there's a DEFAULT_FILE_STORAGE fallback
print(f"\nDjango's default storage backend (if none specified):")
from django.core.files.storage import FileSystemStorage
print(f"  FileSystemStorage: {FileSystemStorage}")

#Check if there's an error during storage setup
print("\n" + "=" * 60)
print("Checking for exceptions in storage initialization...")

# Manually do what Django's storage handler does
print("\nManual storage initialization (what Django does):")
try:
    from django.core.files.storage import storages
    # Access the storage handler
    handler = storages._wrapped
    print(f"Storage handler: {handler}")
    print(f"Handler type: {type(handler)}")
    
    # Check if default storage is set
    if hasattr(handler, '_storages'):
        print(f"Handler._storages: {handler._storages}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

# Try accessing through the property
print("\nAccessing via storages['default']...")
try:
    from django.core.files.storage import storages
    default = storages['default']
    print(f"Type: {type(default)}")
    print(f"Value: {default}")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
