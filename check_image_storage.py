"""
Diagnose image upload issues - check database vs GCS storage.

Run this to verify images are where they should be:
    python manage.py shell < check_image_storage.py
"""

from incidents.models import IncidentImage
from django.core.files.storage import default_storage
from google.cloud import storage as gcs_storage

def check_images():
    """Verify images in database match files in GCS."""
    
    print("\n" + "="*70)
    print("IMAGE STORAGE DIAGNOSIS")
    print("="*70 + "\n")
    
    # Get all incident images
    images = IncidentImage.objects.all().order_by('-uploaded_at')
    total = images.count()
    
    print(f"Total images in database: {total}\n")
    
    if total == 0:
        print("No images found in database.")
        return
    
    # Get GCS bucket info
    try:
        storage = default_storage
        bucket_name = storage.bucket.name
        print(f"GCS Bucket: {bucket_name}\n")
        print(f"{'ID':<5} {'DB Path':<50} {'GCS Exists':<12} {'URL Status':<10}")
        print("-" * 77)
        
        gcs_client = gcs_storage.Client()
        bucket = gcs_client.bucket(bucket_name)
        
        exist_count = 0
        missing_count = 0
        
        for image in images:
            db_path = image.image.name if image.image else "NO_FILE"
            image_id = str(image.id)[:4]  # Show first 4 chars of ID
            
            # Check if blob exists in GCS
            if image.image:
                blob = bucket.blob(image.image.name)
                exists = blob.exists()
                exist_count += 1 if exists else 0
                missing_count += 0 if exists else 1
                
                exists_str = "✓ YES" if exists else "✗ NO"
                
                # Try to get URL
                try:
                    url = image.image.url
                    url_status = "✓ OK"
                except Exception as e:
                    url_status = f"✗ ERR: {str(e)[:20]}"
                
                print(f"{image_id:<5} {db_path:<50} {exists_str:<12} {url_status:<10}")
            else:
                print(f"{image_id:<5} {'NO_FILE':<50} {'N/A':<12} {'EMPTY':<10}")
        
        print("-" * 77)
        print(f"\nSummary:")
        print(f"  Total in DB: {total}")
        print(f"  Exist in GCS: {exist_count}")
        print(f"  Missing in GCS: {missing_count}")
        print()
        
        if missing_count > 0:
            print("⚠️  WARNING: Some images are in database but missing from GCS!")
            print("   Possible causes:")
            print("   1. Upload failed but object created in database")
            print("   2. File was deleted from GCS after creation")
            print("   3. GCS path doesn't match what storage backend expects")
            print()
            
            # Show missing ones
            print("Missing images:")
            for image in images:
                if image.image:
                    blob = bucket.blob(image.image.name)
                    if not blob.exists():
                        print(f"  - {image.id}: {image.image.name}")
    
    except Exception as e:
        print(f"Error checking GCS: {e}")
        print("\nTrying to show image URLs anyway:")
        for idx, image in enumerate(images[:5], 1):
            print(f"{idx}. Image {image.id}: {image.image.url if image.image else 'NO_FILE'}")
    
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    check_images()
