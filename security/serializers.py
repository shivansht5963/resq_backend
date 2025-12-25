from rest_framework import serializers
from .models import GuardProfile, GuardAssignment, DeviceToken, GuardAlert


class GuardProfileSerializer(serializers.ModelSerializer):
    """Serializer for GuardProfile model."""

    user = serializers.StringRelatedField(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=__import__('accounts.models', fromlist=['User']).User.objects.filter(role='GUARD'),
        source='user',
        write_only=True
    )
    # Beacon info (read-only, includes location details)
    current_beacon = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = GuardProfile
        fields = ('id', 'user', 'user_id', 'is_active', 'is_available', 'current_beacon', 'last_beacon_update', 'last_active_at', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at', 'last_beacon_update', 'current_beacon')
    
    def get_current_beacon(self, obj):
        """Return beacon details if guard is assigned to one."""
        if obj.current_beacon:
            return {
                'id': obj.current_beacon.id,
                'beacon_id': obj.current_beacon.beacon_id,
                'location_name': obj.current_beacon.location_name,
                'building': obj.current_beacon.building,
                'floor': obj.current_beacon.floor,
                'latitude': obj.current_beacon.latitude,
                'longitude': obj.current_beacon.longitude
            }
        return None


class GuardAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for GuardAssignment model."""

    guard = serializers.StringRelatedField(read_only=True)
    incident = serializers.StringRelatedField(read_only=True)
    guard_id = serializers.PrimaryKeyRelatedField(
        queryset=__import__('accounts.models', fromlist=['User']).User.objects.filter(role='GUARD'),
        source='guard',
        write_only=True
    )
    incident_id = serializers.PrimaryKeyRelatedField(
        queryset=__import__('incidents.models', fromlist=['Incident']).Incident.objects.all(),
        source='incident',
        write_only=True,
        required=True
    )

    class Meta:
        model = GuardAssignment
        fields = ('id', 'guard', 'guard_id', 'incident', 'incident_id', 'is_active', 'assigned_at', 'updated_at')
        read_only_fields = ('id', 'assigned_at', 'updated_at')


class DeviceTokenSerializer(serializers.ModelSerializer):
    """Serializer for DeviceToken model."""

    user = serializers.StringRelatedField(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=__import__('accounts.models', fromlist=['User']).User.objects.all(),
        source='user',
        write_only=True
    )

    class Meta:
        model = DeviceToken
        fields = ('id', 'user', 'user_id', 'token', 'platform', 'is_active', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class GuardAlertSerializer(serializers.ModelSerializer):
    """Serializer for GuardAlert model."""
    
    incident_id = serializers.PrimaryKeyRelatedField(
        source='incident',
        read_only=True
    )
    guard_name = serializers.CharField(source='guard.full_name', read_only=True)
    guard_id = serializers.PrimaryKeyRelatedField(
        source='guard',
        read_only=True
    )
    
    class Meta:
        model = GuardAlert
        fields = ('id', 'incident_id', 'guard_id', 'guard_name', 'distance_km', 'status', 'priority_rank', 'alert_sent_at', 'updated_at')
        read_only_fields = ('id', 'alert_sent_at', 'updated_at')


class GuardAlertDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for GuardAlert with full incident info."""
    
    incident = serializers.SerializerMethodField()
    guard = serializers.SerializerMethodField()
    
    class Meta:
        model = GuardAlert
        fields = ('id', 'incident', 'guard', 'distance_km', 'status', 'priority_rank', 'alert_sent_at', 'updated_at')
        read_only_fields = ('id', 'alert_sent_at', 'updated_at')
    
    def get_incident(self, obj):
        from incidents.serializers import IncidentDetailedSerializer
        return IncidentDetailedSerializer(obj.incident).data
    
    def get_guard(self, obj):
        return {
            'id': obj.guard.id,
            'name': obj.guard.full_name,
            'email': obj.guard.email
        }


class GuardLocationUpdateSerializer(serializers.Serializer):
    """Serializer for guard location update endpoint."""
    
    nearest_beacon_id = serializers.UUIDField(
        required=True,
        help_text="UUID of the nearest beacon (from mobile detection)"
    )
    timestamp = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Client-side timestamp (optional, server uses current time)"
    )
    
    def validate_nearest_beacon_id(self, value):
        """Validate that beacon exists and is active."""
        from incidents.models import Beacon
        try:
            beacon = Beacon.objects.get(id=value, is_active=True)
            return beacon
        except Beacon.DoesNotExist:
            raise serializers.ValidationError(f"Beacon {value} not found or inactive")
