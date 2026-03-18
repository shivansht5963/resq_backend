"""
URL configuration for campus_security project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('health/', views.health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('admin-panel/', include('adminEnd.urls')),
    path('api/auth/', include('accounts.urls')),
    path('api/devices/', include('devices_urls')),
    path('api/', include('incidents.urls')),
    path('api/', include('security.urls')),
    path('api/', include('chat.urls')),
    path('api/', include('ai_engine.urls')),
]

# Serve local media files (used when GCS falls back to local disk)
# Works in both DEBUG and production so fallback images are always accessible
import re as _re
_media_prefix = _re.escape(settings.MEDIA_URL.lstrip('/'))
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
