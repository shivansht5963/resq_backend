"""
WSGI config for campus_security project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_security.settings')

application = get_wsgi_application()

# Always use WhiteNoise to serve both static and media files
from django.conf import settings
application = WhiteNoise(
    application,
    root=str(settings.BASE_DIR),  # Serve from project root
    index_file=False,  # Don't serve index files
    mimetypes={'.js': 'application/javascript'},
)

# Add media directory to WhiteNoise
application.add_files(str(settings.MEDIA_ROOT), prefix=settings.MEDIA_URL.lstrip('/'))
