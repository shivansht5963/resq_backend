#!/usr/bin/env python
"""
Verify if uploaded image file actually exists in GCS

Run: python verify_gcs_file.py
"""

import os
from pathlib import Path

# Ensure credentials are set
creds_path = Path(__file__).resolve().parent / 'credentials' / 'gen-lang-client-0117249847-eb5558a80732.json'
if creds_path.exists():
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(creds_path)
    print(f"[GCS] Using credentials from {creds_path}\n")

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_security.settings')
django.setup()

from google.cloud import storage
from incidents.models import IncidentImage
from datetime import datetime, timedelta

print("="*70)
print("GCS FILE VERIFICATION")
print("="*70)

# Get GCS client
client = storage.Client()
bucket = client.bucket('resq-campus-security')

print(f"\nBucket: {bucket.name}")

# Check recent images from database
print(f"\nRecent images in database:")
recent_images = IncidentImage.objects.order_by('-id')[:5]

for img in recent_images:
    print(f"\n  Image ID: {img.id}")
    print(f"  Path: {img.image.name}")
    print(f"  URL: {img.image.url}")
    
    # Check if file exists in GCS
    blob = bucket.blob(img.image.name)
    exists = blob.exists()
    print(f"  Exists in GCS: {'✓ YES' if exists else '✗ NO'}")
    
    if not exists:
        print(f"  ⚠️ FILE MISSING FROM GCS!")
        print(f"     Database has record but file not in bucket")

# Also list what's actually in GCS
print(f"\n\nFiling in GCS (incidents folder, last 10):")
blobs = list(bucket.list_blobs(prefix='incidents/', max_results=10))
blobs.reverse()

if blobs:
    for blob in blobs[:10]:
        size_kb = blob.size / 1024 if blob.size else 0
        print(f"  - {blob.name} ({size_kb:.1f} KB)")
        print(f"    URL: https://storage.googleapis.com/{bucket.name}/{blob.name}")
else:
    print(f"  No files found in incidents/ folder")

print(f"\n" + "="*70 + "\n")
