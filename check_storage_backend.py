#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campus_security.settings")
django.setup()

from django.core.files.storage import default_storage

print(f"Default storage backend:")
print(f"  Class: {default_storage.__class__.__module__}.{default_storage.__class__.__name__}")
print(f"  Storage object: {default_storage}")

# Check if it's GCS
from storages.backends.gcloud import GoogleCloudStorage
if isinstance(default_storage, GoogleCloudStorage):
    print(f"  ✓ Using GoogleCloudStorage (GCS)")
    print(f"  Bucket: {default_storage.bucket}")
    print(f"  Credentials: {default_storage.credentials}")
else:
    print(f"  ✗ NOT using GoogleCloudStorage")
    print(f"  This is the problem!")
    
# Check settings
from django.conf import settings
print(f"\nSettings check:")
print(f"  DEFAULT_FILE_STORAGE: {settings.DEFAULT_FILE_STORAGE}")
print(f"  MEDIA_ROOT: {getattr(settings, 'MEDIA_ROOT', 'NOT SET')}")
print(f"  MEDIA_URL: {settings.MEDIA_URL}")
print(f"  GS_BUCKET_NAME: {getattr(settings, 'GS_BUCKET_NAME', 'NOT SET')}")
print(f"  GS_PROJECT_ID: {getattr(settings, 'GS_PROJECT_ID', 'NOT SET')}")
