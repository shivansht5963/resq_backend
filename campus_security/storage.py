"""Custom Google Cloud Storage backend for public image access."""

from storages.backends.gcloud import GoogleCloudStorage


class PublicGoogleCloudStorage(GoogleCloudStorage):
    """GCS backend that returns direct public URLs for image access.
    
    Requires bucket to be configured with:
    1. Uniform bucket-level access DISABLED (use object-level ACLs)
    2. All incident image objects set with 'public-read' ACL
    3. Bucket policy allowing public read access (if needed for admin)
    
    This enables direct HTTPS URLs that work with:
    - Frontend React/React Native apps
    - Push notifications with image preview
    - Admin panel image display
    """
    
    def url(self, name):
        """Return direct public HTTPS URL for the given file.
        
        For incident images: Returns public URL like:
        https://storage.googleapis.com/bucket-name/path/to/image.jpg
        
        Images must have 'public-read' ACL for this to work.
        """
        if not name:
            raise ValueError("Missing 'name' argument")
        
        # Return direct public URL (no signing needed)
        blob = self.bucket.blob(name)
        # Make blob public-read during generation
        blob.make_public()
        
        # Return direct HTTPS URL
        return f"https://storage.googleapis.com/{self.bucket.name}/{blob.name}"
