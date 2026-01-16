from django.urls import path
from . import views

app_name = 'adminEnd'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('incidents/', views.incident_list, name='incident_list'),
    path('incidents/<uuid:incident_id>/', views.incident_detail, name='incident_detail'),

    # Beacons
    path('beacons/', views.beacon_list, name='beacon_list'),
    path('beacons/new/', views.beacon_create, name='beacon_create'),
    path('beacons/<uuid:beacon_id>/', views.beacon_detail, name='beacon_detail'),
    # AJAX endpoints for proximities
    path('beacons/<uuid:beacon_id>/proximities/<int:prox_id>/move/', views.ajax_move_proximity, name='ajax_move_proximity'),
    path('beacons/<uuid:beacon_id>/proximities/<int:prox_id>/update_priority/', views.ajax_update_proximity_priority, name='ajax_update_proximity_priority'),
    path('beacons/<uuid:beacon_id>/proximities/<int:prox_id>/delete/', views.ajax_delete_proximity, name='ajax_delete_proximity'),

    # Guards
    path('guards/', views.guard_list, name='guard_list'),
    path('guards/<int:user_id>/toggle_availability/', views.toggle_guard_availability, name='toggle_guard_availability'),
]
