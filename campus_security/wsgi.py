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

# Add Whitenoise to serve media files in production
from django.conf import settings
if not settings.DEBUG:
    application = WhiteNoise(application, root=settings.MEDIA_ROOT, prefix=settings.MEDIA_URL.lstrip('/'))
