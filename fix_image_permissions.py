"""
Fix permissions for existing incident images on Google Cloud Storage.

Run this to make all existing incident images publicly readable:
    python manage.py shell < fix_image_permissions.py
"""

from incidents.models import IncidentImage
from django.core.files.storage import default_storage

def fix_image_permissions():
    """Make all existing incident images public on GCS."""
    
    images = IncidentImage.objects.all()
    total = images.count()
    success = 0
    failed = 0
    
    print(f"\nFixing permissions for {total} incident images...\n")
    
    for image in images:
        try:
            if image.image:
                # Get the storage backend
                storage = image.image.storage
                blob = storage.bucket.blob(image.image.name)
                
                # Make blob publicly readable
                blob.make_public()
                
                print(f"✓ Made public: {image.image.name}")
                success += 1
        except Exception as e:
            print(f"✗ Failed: {image.image.name} - {str(e)}")
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Total images: {total}")
    print(f"  Success: {success}")
    print(f"  Failed: {failed}")
    print(f"{'='*60}\n")
    
    return success, failed

if __name__ == "__main__":
    fix_image_permissions()
