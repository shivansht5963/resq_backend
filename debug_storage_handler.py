#!/usr/bin/env python
import os
import sys
import logging
from pathlib import Path

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

# Set GCS credentials
creds_path = Path(__file__).resolve().parent / 'credentials' / 'gen-lang-client-0117249847-eb5558a80732.json'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(creds_path)

# Monkey patch django's storage handler to log what's happening
original_handler_init = None

def patch_storage_handler():
    from django.core.files.storage.handler import StorageHandler
    global original_handler_init
    original_handler_init = StorageHandler.__init__
    
    def new_init(self, *args, **kwargs):
        print(f"[PATCH] StorageHandler.__init__ called")
        result = original_handler_init(self, *args, **kwargs)
        print(f"[PATCH] StorageHandler initialized, _storages: {self._storages if hasattr(self, '_storages') else 'N/A'}")
        return result
    
    StorageHandler.__init__ = new_init

patch_storage_handler()

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campus_security.settings")

print("\n[DJANGO SETUP] Starting Django setup...")
django.setup()
print("[DJANGO SETUP] Django setup complete\n")

from django.conf import settings
from django.core.files.storage import storages, default_storage

print("=" * 60)
print("STORAGE CONFIGURATION STATUS")
print("=" * 60)
print(f"DEFAULT_FILE_STORAGE setting: {settings.DEFAULT_FILE_STORAGE}")
print(f"default_storage returned: {default_storage}")
print(f"default_storage class: {default_storage.__class__.__name__}")

# Try to get the actual storage
print("\n[DEBUG] Trying to get 'default' storage from handler...")
try:
    # This is what's causing the problem - let's catch the error
    default_from_handler = storages['default']
    print(f"Got storage: {default_from_handler}")
except Exception as e:
    print(f"Error getting storage: {e}")
    import traceback
    traceback.print_exc()

# Check if there's an error silently being caught
print("\n[DEBUG] Checking StorageHandler internals...")
try:
    print(f"storages object: {storages}")
    print(f"storages._storages: {storages._storages if hasattr(storages, '_storages') else 'N/A'}")
except Exception as e:
    print(f"Error: {e}")
