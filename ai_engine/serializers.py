from rest_framework import serializers
from .models import AIEvent


class AIEventSerializer(serializers.ModelSerializer):
    """Serializer for AIEvent model - list view."""

    reported_incident_id = serializers.PrimaryKeyRelatedField(
        queryset=__import__('incidents.models', fromlist=['ReportedIncident']).ReportedIncident.objects.all(),
        source='reported_incident',
        write_only=True,
        required=False
    )
    beacon_incident_id = serializers.PrimaryKeyRelatedField(
        queryset=__import__('incidents.models', fromlist=['BeaconIncident']).BeaconIncident.objects.all(),
        source='beacon_incident',
        write_only=True,
        required=False
    )
    panic_incident_id = serializers.PrimaryKeyRelatedField(
        queryset=__import__('incidents.models', fromlist=['PanicButtonIncident']).PanicButtonIncident.objects.all(),
        source='panic_incident',
        write_only=True,
        required=False
    )

    class Meta:
        model = AIEvent
        fields = (
            'id', 'reported_incident_id', 'beacon_incident_id', 'panic_incident_id',
            'event_type', 'confidence_score', 'details', 'created_at'
        )
        read_only_fields = ('id', 'created_at')


class AIEventDetailSerializer(serializers.ModelSerializer):
    """Detailed AIEvent serializer with incident info."""

    reported_incident = serializers.SerializerMethodField()
    beacon_incident = serializers.SerializerMethodField()
    panic_incident = serializers.SerializerMethodField()

    class Meta:
        model = AIEvent
        fields = (
            'id', 'reported_incident', 'beacon_incident', 'panic_incident',
            'event_type', 'confidence_score', 'details', 'created_at'
        )
        read_only_fields = ('id', 'created_at')

    def get_reported_incident(self, obj):
        if obj.reported_incident:
            from incidents.serializers import ReportedIncidentSerializer
            return ReportedIncidentSerializer(obj.reported_incident).data
        return None

    def get_beacon_incident(self, obj):
        if obj.beacon_incident:
            from incidents.serializers import BeaconIncidentSerializer
            return BeaconIncidentSerializer(obj.beacon_incident).data
        return None

    def get_panic_incident(self, obj):
        if obj.panic_incident:
            from incidents.serializers import PanicButtonIncidentSerializer
            return PanicButtonIncidentSerializer(obj.panic_incident).data
        return None


class AIEventDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for AIEvent with incident info."""

    reported_incident = serializers.SerializerMethodField()
    beacon_incident = serializers.SerializerMethodField()
    panic_incident = serializers.SerializerMethodField()

    class Meta:
        model = AIEvent
        fields = ('id', 'reported_incident', 'beacon_incident', 'panic_incident', 'event_type', 'confidence_score', 'details', 'created_at')
        read_only_fields = ('id', 'created_at')

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
