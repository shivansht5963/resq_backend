"""
URL routing for incidents app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'incidents'

router = DefaultRouter()
router.register(r'beacons', views.BeaconViewSet, basename='beacon')
router.register(r'incidents', views.IncidentViewSet, basename='incident')

urlpatterns = [
    # Public endpoints (no auth required) - must come BEFORE router
    path('incidents/buzzer-status/', views.buzzer_status_endpoint, name='buzzer-status'),
    path('panic/', views.panic_button_endpoint, name='panic-button'),
    
    # Router endpoints (may require auth)
    path('', include(router.urls)),
]
