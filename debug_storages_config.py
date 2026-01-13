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
from django.core.files.storage import storages

print("=" * 60)
print("STORAGE CONFIGURATION")
print("=" * 60)

print(f"\nDjango settings.DEFAULT_FILE_STORAGE: {settings.DEFAULT_FILE_STORAGE}")
print(f"\nDjango settings.STORAGES: {settings.STORAGES}")

print(f"\nStorageHandler.backends: {storages.backends}")

print("\nAttempting to create storage for 'default'...")
try:
    params = storages.backends['default']
    print(f"Backend params for 'default': {params}")
    
    storage = storages.create_storage(params)
    print(f"Created storage: {storage}")
    print(f"  Type: {type(storage)}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
