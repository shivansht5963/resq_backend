"""
URL routing for incidents app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'incidents'

router = DefaultRouter()
router.register(r'beacons', views.BeaconViewSet, basename='beacon')
router.register(r'reported-incidents', views.ReportedIncidentViewSet, basename='reported-incident')
router.register(r'beacon-incidents', views.BeaconIncidentViewSet, basename='beacon-incident')
router.register(r'panic-incidents', views.PanicButtonIncidentViewSet, basename='panic-incident')

urlpatterns = [
    path('', include(router.urls)),
    path('panic/', views.panic_button_endpoint, name='panic-button'),
]
