"""Custom Google Cloud Storage backend with signed URLs for image access."""

from storages.backends.gcloud import GoogleCloudStorage
from datetime import timedelta


class PublicGoogleCloudStorage(GoogleCloudStorage):
    """GCS backend that generates signed URLs for image access.
    
    Works with uniform bucket-level access and provides secure, time-limited URLs
    for image preview in admin panel and transfer to guard app.
    """
    
    def url(self, name):
        """Generate a signed URL for the given file that's valid for 7 days."""
        if not name:
            raise ValueError("Missing 'name' argument")
        
        blob = self.bucket.blob(name)
        
        # Generate signed URL valid for 7 days
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(days=7),
            method="GET",
        )
        
        return signed_url
