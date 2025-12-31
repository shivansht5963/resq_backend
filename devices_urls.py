"""
Device management URLs.
Exposed at /api/devices/ for push notification device registration.
"""
from django.urls import path
from accounts import views

urlpatterns = [
    path('register/', views.register_device, name='register-device'),
    path('unregister/', views.unregister_device, name='unregister-device'),
    path('', views.list_devices, name='list-devices'),
]
