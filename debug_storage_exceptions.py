#!/usr/bin/env python
import os
import sys
from pathlib import Path

# Set GCS credentials BEFORE Django setup
creds_path = Path(__file__).resolve().parent / 'credentials' / 'gen-lang-client-0117249847-eb5558a80732.json'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(creds_path)

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campus_security.settings")

# Patch the storage handler to catch exceptions
from django.core.files.storage.handler import StorageHandler

original_getitem = StorageHandler.__getitem__

def patched_getitem(self, alias):
    print(f"\n[PATCH] StorageHandler.__getitem__('{alias}') called")
    print(f"  Current _storages: {self._storages}")
    
    try:
        result = original_getitem(self, alias)
        print(f"  Result: {result}")
        return result
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise

StorageHandler.__getitem__ = patched_getitem

# Now setup Django
print("Setting up Django...")
django.setup()
print("Django setup complete\n")

from django.conf import settings
from django.core.files.storage import storages, default_storage

print("=" * 60)
print("Accessing default_storage...")
print("=" * 60)

try:
    print(f"default_storage = {default_storage}")
    print(f"Type: {type(default_storage).__name__}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
