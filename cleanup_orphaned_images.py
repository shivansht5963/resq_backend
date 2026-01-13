#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campus_security.settings")
django.setup()

from incidents.models import IncidentImage
from google.cloud import storage

# Get GCS client
gcs_client = storage.Client(project='gen-lang-client-0117249847')
bucket = gcs_client.bucket('resq-campus-security')

print("=" * 60)
print("CLEANING UP ORPHANED DATABASE RECORDS")
print("=" * 60)

orphaned_ids = []

# Check each image in database
for img in IncidentImage.objects.all().order_by('-id'):
    try:
        blob = bucket.blob(img.image.name)
        exists = blob.exists()
        
        if not exists:
            print(f"✗ Orphaned: ID {img.id}, Path: {img.image.name}")
            orphaned_ids.append(img.id)
        else:
            print(f"✓ Valid: ID {img.id}, Path: {img.image.name}")
    except Exception as e:
        print(f"? Error checking ID {img.id}: {e}")

print(f"\nFound {len(orphaned_ids)} orphaned records: {orphaned_ids}")

if orphaned_ids:
    print(f"\nDeleting orphaned records...")
    deleted_count, _ = IncidentImage.objects.filter(id__in=orphaned_ids).delete()
    print(f"✓ Deleted {deleted_count} records")
else:
    print("No orphaned records to delete")

print("\n" + "=" * 60)
print("CLEANUP COMPLETE")
print("=" * 60)
