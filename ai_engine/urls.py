"""
URL routing for ai_engine app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'ai_engine'

router = DefaultRouter()
router.register(r'ai-events', views.AIEventViewSet, basename='ai-event')

urlpatterns = [
    path('', include(router.urls)),
    # New endpoints (recommended)
    path('violence-detected/', views.violence_detected, name='violence-detected'),
    path('scream-detected/', views.scream_detected, name='scream-detected'),
    # Legacy endpoint (backward compatible)
    path('ai-detection/', views.ai_detection_endpoint, name='ai-detection'),
]
