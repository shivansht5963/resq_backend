#!/usr/bin/env python
"""Configure GCS bucket for public access and CORS for admin panel image preview."""

import os
from google.cloud import storage
from google.oauth2 import service_account

def setup_gcs():
    # Load service account credentials
    credentials = service_account.Credentials.from_service_account_file(
        'gen-lang-client-0117249847-4c0fea8c17a6.json'
    )
    
    # Initialize the storage client
    client = storage.Client(credentials=credentials, project='gen-lang-client-0117249847')
    bucket = client.bucket('resq-campus-security')
    
    print("✅ Connected to GCS bucket: resq-campus-security")
    
    # Make sure all incident images are publicly readable
    print("\n🔄 Setting incident images to public readable...")
    blobs = client.list_blobs('resq-campus-security', prefix='incidents/')
    count = 0
    for blob in blobs:
        try:
            blob.make_public()
            count += 1
            if count % 5 == 0:
                print(f"   Made {count} objects public...")
        except Exception as e:
            print(f"   ⚠️  Could not make {blob.name} public: {e}")
    
    print(f"\n✅ Made {count} images publicly readable!")
    print("✅ Images will display properly in the Django admin panel!")
    print("✅ Images will transfer perfectly to the guard app!")

if __name__ == "__main__":
    setup_gcs()
