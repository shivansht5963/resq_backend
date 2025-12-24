from rest_framework import serializers
from .models import Beacon, ReportedIncident, BeaconIncident, PanicButtonIncident, ESP32Device


class BeaconSerializer(serializers.ModelSerializer):
    """Serializer for Beacon model."""

    class Meta:
        model = Beacon
        fields = ('id', 'uuid', 'major', 'minor', 'location_name', 'building', 'floor', 'created_at')
        read_only_fields = ('id', 'created_at')


class ReportedIncidentSerializer(serializers.ModelSerializer):
    """Serializer for ReportedIncident - student manually reported incidents."""

    student = serializers.StringRelatedField(read_only=True)
    beacon = BeaconSerializer(read_only=True)
    beacon_id = serializers.PrimaryKeyRelatedField(
        queryset=Beacon.objects.all(),
        source='beacon',
        write_only=True,
        required=False,
        allow_null=True,
        help_text="Optional: Beacon location where incident occurred"
    )

    class Meta:
        model = ReportedIncident
        fields = (
            'id', 'student', 'beacon', 'beacon_id',
            'status', 'priority', 'description',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class BeaconIncidentSerializer(serializers.ModelSerializer):
    """Serializer for BeaconIncident - automatic beacon detection."""

    student = serializers.StringRelatedField(read_only=True)
    beacon = BeaconSerializer(read_only=True)
    beacon_id = serializers.PrimaryKeyRelatedField(
        queryset=Beacon.objects.all(),
        source='beacon',
        write_only=True,
        required=True
    )

    class Meta:
        model = BeaconIncident
        fields = (
            'id', 'student', 'beacon', 'beacon_id',
            'status', 'priority', 'description',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'student', 'created_at', 'updated_at')


class PanicButtonIncidentSerializer(serializers.ModelSerializer):
    """Serializer for PanicButtonIncident - ESP32 panic button alerts."""

    esp32_device = serializers.StringRelatedField(read_only=True)
    student = serializers.StringRelatedField(read_only=True)
    esp32_device_id = serializers.PrimaryKeyRelatedField(
        queryset=ESP32Device.objects.all(),
        source='esp32_device',
        write_only=True,
        required=True
    )

    class Meta:
        model = PanicButtonIncident
        fields = (
            'id', 'esp32_device', 'esp32_device_id', 'student',
            'status', 'priority', 'description',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'student', 'created_at', 'updated_at')
