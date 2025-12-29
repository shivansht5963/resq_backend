"""Django management command to make all incident images publicly readable in GCS."""

from django.core.management.base import BaseCommand
from django.conf import settings
from incidents.models import IncidentImage
from google.cloud import storage
from google.oauth2 import service_account


class Command(BaseCommand):
    help = 'Make all incident images publicly readable in Google Cloud Storage'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Making incident images public...'))
        
        try:
            # Initialize GCS client with service account credentials
            credentials = service_account.Credentials.from_service_account_file(
                'gen-lang-client-0117249847-4c0fea8c17a6.json'
            )
            client = storage.Client(credentials=credentials, project='gen-lang-client-0117249847')
            bucket = client.bucket(settings.GS_BUCKET_NAME)
            
            # Get all incident images
            images = IncidentImage.objects.all()
            count = 0
            
            for image in images:
                if image.image.name:
                    try:
                        blob = bucket.blob(image.image.name)
                        blob.make_public()
                        count += 1
                        self.stdout.write(f"  ✅ {image.image.name}")
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"  ⚠️  {image.image.name}: {e}"))
            
            self.stdout.write(self.style.SUCCESS(f'\n✅ Made {count} images publicly readable!'))
            self.stdout.write(self.style.SUCCESS('Images should now display in admin panel and transfer to guard app!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))
