"""Custom Google Cloud Storage backend for public image access."""

from storages.backends.gcloud import GoogleCloudStorage
from django.conf import settings


class PublicGoogleCloudStorage(GoogleCloudStorage):
    """GCS backend that returns direct public URLs for image access.
    
    Requires bucket to be configured with:
    1. Uniform bucket-level access DISABLED (use object-level ACLs)
    2. All incident image objects set with 'public-read' ACL
    
    This enables direct HTTPS URLs that work with:
    - Frontend React/React Native apps (always HTTPS)
    - Push notifications with image preview
    - Admin panel image display (HTTP for local dev, HTTPS for prod)
    """
    
    def url(self, name):
        """Return direct public URL for the given file.
        
        Local development: Returns HTTP URL to avoid mixed content blocking
        Production (Render): Returns HTTPS URL for security
        
        Returns URL like:
        - http://storage.googleapis.com/bucket-name/path/image.jpg  (localhost)
        - https://storage.googleapis.com/bucket-name/path/image.jpg  (production)
        
        Images must have 'public-read' ACL for this to work.
        """
        if not name:
            raise ValueError("Missing 'name' argument")
        
        # Use HTTP for local development (to avoid mixed content blocking in admin)
        # Use HTTPS for production (Render)
        protocol = "http" if settings.DEBUG else "https"
        
        return f"{protocol}://storage.googleapis.com/{self.bucket.name}/{name}"
