from rest_framework import serializers
from .models import AIEvent


class AIEventSerializer(serializers.ModelSerializer):
    """Serializer for AIEvent model - list view."""

    beacon = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = AIEvent
        fields = ('id', 'beacon', 'event_type', 'confidence_score', 'details', 'created_at')
        read_only_fields = ('id', 'created_at')


class AIEventDetailSerializer(serializers.ModelSerializer):
    """Detailed AIEvent serializer with beacon info."""

    beacon = serializers.SerializerMethodField()

    class Meta:
        model = AIEvent
        fields = ('id', 'beacon', 'event_type', 'confidence_score', 'details', 'created_at')
        read_only_fields = ('id', 'created_at')

    def get_beacon(self, obj):
        if obj.beacon:
            from incidents.serializers import BeaconSerializer
            return BeaconSerializer(obj.beacon).data
        return None

    def get_reported_incident(self, obj):
        if obj.reported_incident:
            return {
                'id': str(obj.reported_incident.id),
                'student': obj.reported_incident.student.full_name,
                'status': obj.reported_incident.status,
                'priority': obj.reported_incident.priority
            }
        return None

    def get_beacon_incident(self, obj):
        if obj.beacon_incident:
            return {
                'id': str(obj.beacon_incident.id),
                'student': obj.beacon_incident.student.full_name,
                'status': obj.beacon_incident.status,
                'priority': obj.beacon_incident.priority,
                'beacon': obj.beacon_incident.beacon.location_name
            }
        return None

    def get_panic_incident(self, obj):
        if obj.panic_incident:
            return {
                'id': str(obj.panic_incident.id),
                'device': obj.panic_incident.esp32_device.device_id,
                'status': obj.panic_incident.status,
                'priority': obj.panic_incident.priority
            }
        return None
