"""
URL routing for security app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'security'

router = DefaultRouter()
router.register(r'guards', views.GuardProfileViewSet, basename='guard')
router.register(r'assignments', views.GuardAssignmentViewSet, basename='assignment')
router.register(r'device-tokens', views.DeviceTokenViewSet, basename='device-token')
router.register(r'alerts', views.GuardAlertViewSet, basename='alert')

urlpatterns = [
    path('', include(router.urls)),
]
