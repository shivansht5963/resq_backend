#!/usr/bin/env python
import os
import sys
from pathlib import Path
import django

# Set GCS credentials  
creds_path = Path(__file__).resolve().parent / 'credentials' / 'gen-lang-client-0117249847-eb5558a80732.json'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(creds_path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campus_security.settings")
django.setup()

from google.cloud import storage
from incidents.models import IncidentImage

print("=" * 70)
print("FIXING GCS IMAGE PERMISSIONS - Making All Images Public")
print("=" * 70)

# Initialize GCS client
gcs_client = storage.Client(project='gen-lang-client-0117249847')
bucket = gcs_client.bucket('resq-campus-security')

print(f"\nBucket: {bucket.name}")
print(f"Project: {gcs_client.project}")

# Get all images from database
all_images = IncidentImage.objects.all()
print(f"\nProcessing {all_images.count()} images in database...")

success_count = 0
error_count = 0
missing_count = 0

for img in all_images:
    blob_name = img.image.name
    try:
        blob = bucket.blob(blob_name)
        
        if not blob.exists():
            print(f"✗ Missing: {blob_name}")
            missing_count += 1
            continue
        
        # Make public using the standard GCS method
        blob.make_public()
        
        # After make_public, the public_url should work
        public_url = blob.public_url
        print(f"✓ Public: {blob_name}")
        print(f"  URL: {public_url}")
        success_count += 1
            
    except Exception as e:
        print(f"✗ Error processing {blob_name}: {type(e).__name__}: {e}")
        error_count += 1

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"✓ Made public: {success_count}")
print(f"⚠ Missing from GCS: {missing_count}")
print(f"✗ Errors: {error_count}")
print(f"Total processed: {success_count + missing_count + error_count}")

if missing_count > 0:
    print(f"\n⚠ WARNING: {missing_count} images in database but not in GCS bucket!")
    print("These records should be deleted or re-uploaded.")

print("\n" + "=" * 70)
