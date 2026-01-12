"""
Fix missing images - delete orphaned database records or re-upload.

Run to find and fix missing images:
    python manage.py shell < fix_missing_images.py
"""

from incidents.models import IncidentImage
from google.cloud import storage as gcs_storage
from django.core.files.storage import default_storage

def fix_missing_images():
    """Remove database records for images that don't exist in GCS."""
    
    print("\n" + "="*70)
    print("IMAGE CLEANUP - REMOVE ORPHANED DATABASE RECORDS")
    print("="*70 + "\n")
    
    images = IncidentImage.objects.all()
    
    if not images.exists():
        print("No images in database to check.")
        return
    
    try:
        storage = default_storage
        bucket = storage.bucket
        
        print(f"Checking {images.count()} images...\n")
        
        orphaned = []
        valid = []
        
        for image in images:
            if image.image:
                blob = bucket.blob(image.image.name)
                if blob.exists():
                    valid.append(image)
                else:
                    orphaned.append(image)
        
        print(f"Found:")
        print(f"  Valid images in GCS: {len(valid)}")
        print(f"  Orphaned (DB only): {len(orphaned)}\n")
        
        if orphaned:
            print("Orphaned images (will be deleted from database):")
            for image in orphaned:
                incident_id = image.incident.id if image.incident else "UNKNOWN"
                print(f"  - ID {image.id}: {image.image.name} (incident: {incident_id})")
            
            print("\nDeleting orphaned records...")
            for image in orphaned:
                image_id = image.id
                image.delete()
                print(f"  ✓ Deleted image {image_id}")
            
            print(f"\n✅ Deleted {len(orphaned)} orphaned image records")
        else:
            print("✅ All images in database have corresponding files in GCS")
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure GCS credentials are properly configured")
        print("2. Check GOOGLE_CLOUD_PROJECT setting")
        print("3. Verify service account has storage.objects.get permission")
    
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    fix_missing_images()
