from rest_framework import serializers
from .models import Beacon, Incident, IncidentSignal, ESP32Device, IncidentImage
from security.models import GuardAssignment, GuardAlert
from chat.models import Conversation, Message


class IncidentImageSerializer(serializers.ModelSerializer):
    """Serializer for incident images."""
    
    uploaded_by_email = serializers.CharField(source='uploaded_by.email', read_only=True)
    
    class Meta:
        model = IncidentImage
        fields = ('id', 'image', 'uploaded_by_email', 'uploaded_at', 'description')
        read_only_fields = ('id', 'uploaded_at', 'uploaded_by_email')


class BeaconSerializer(serializers.ModelSerializer):
    """Serializer for Beacon model."""

    class Meta:
        model = Beacon
        fields = ('id', 'beacon_id', 'uuid', 'major', 'minor', 'location_name', 'building', 'floor', 'latitude', 'longitude', 'is_active', 'created_at')
        read_only_fields = ('id', 'created_at')


class ESP32DeviceSerializer(serializers.ModelSerializer):
    """Serializer for ESP32Device."""

    beacon = BeaconSerializer(read_only=True)

    class Meta:
        model = ESP32Device
        fields = ('id', 'device_id', 'beacon', 'name', 'is_active')
        read_only_fields = ('id',)


class IncidentSignalSerializer(serializers.ModelSerializer):
    """Serializer for IncidentSignal - individual triggers."""

    source_user = serializers.SerializerMethodField()
    source_device = ESP32DeviceSerializer(read_only=True)
    
    class Meta:
        model = IncidentSignal
        fields = ('id', 'signal_type', 'source_user', 'source_device', 'ai_event', 'details', 'created_at')
        read_only_fields = ('id', 'created_at')
    
    def get_source_user(self, obj):
        if obj.source_user:
            return {
                'id': str(obj.source_user.id),
                'full_name': obj.source_user.full_name,
                'email': obj.source_user.email
            }
        return None


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message."""

    sender = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ('id', 'sender', 'message_text', 'created_at')
        read_only_fields = ('id', 'sender', 'created_at')
    
    def get_sender(self, obj):
        return {
            'id': str(obj.sender.id),
            'full_name': obj.sender.full_name,
            'email': obj.sender.email
        }


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for Conversation."""

    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ('id', 'created_at', 'updated_at', 'messages')
        read_only_fields = ('id', 'created_at', 'updated_at')


class GuardAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for GuardAssignment."""

    guard = serializers.SerializerMethodField()

    class Meta:
        model = GuardAssignment
        fields = ('id', 'guard', 'assigned_at', 'is_active')
        read_only_fields = ('id', 'assigned_at')
    
    def get_guard(self, obj):
        return {
            'id': str(obj.guard.id),
            'full_name': obj.guard.full_name,
            'email': obj.guard.email
        }


class IncidentDetailedSerializer(serializers.ModelSerializer):
    """Full incident serializer with all related data."""

    beacon = BeaconSerializer(read_only=True)
    signals = IncidentSignalSerializer(many=True, read_only=True)
    images = IncidentImageSerializer(many=True, read_only=True)
    guard_assignment = serializers.SerializerMethodField()
    conversation = ConversationSerializer(read_only=True)
    guard_alerts = serializers.SerializerMethodField()

    class Meta:
        model = Incident
        fields = (
            'id', 'beacon', 'status', 'priority', 'description', 'report_type', 'location',
            'first_signal_time', 'last_signal_time',
            'signals', 'images', 'guard_assignment', 'guard_alerts', 'conversation',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'first_signal_time', 'last_signal_time')
    
    def get_guard_assignment(self, obj):
        try:
            assignment = obj.guard_assignments.get(is_active=True)
            return GuardAssignmentSerializer(assignment).data
        except GuardAssignment.DoesNotExist:
            return None
    
    def get_guard_alerts(self, obj):
        alerts = obj.guard_alerts.all().order_by('priority_rank')
        return [
            {
                'id': alert.id,
                'guard': {
                    'id': str(alert.guard.id),
                    'full_name': alert.guard.full_name
                },
                'status': alert.status,
                'distance_km': alert.distance_km,
                'priority_rank': alert.priority_rank,
                'alert_sent_at': alert.alert_sent_at
            }
            for alert in alerts
        ]


class IncidentListSerializer(serializers.ModelSerializer):
    """Lightweight incident serializer for list views."""

    beacon = BeaconSerializer(read_only=True)
    signal_count = serializers.SerializerMethodField()
    guard_assignment = serializers.SerializerMethodField()

    class Meta:
        model = Incident
        fields = (
            'id', 'beacon', 'status', 'priority', 'description', 'report_type', 'location',
            'signal_count', 'guard_assignment',
            'first_signal_time', 'last_signal_time',
            'created_at'
        )
        read_only_fields = ('id', 'created_at', 'first_signal_time', 'last_signal_time')
    
    def get_signal_count(self, obj):
        return obj.signals.count()
    
    def get_guard_assignment(self, obj):
        try:
            assignment = obj.guard_assignments.get(is_active=True)
            return {
                'guard_name': assignment.guard.full_name,
                'assigned_at': assignment.assigned_at
            }
        except GuardAssignment.DoesNotExist:
            return None


class IncidentCreateSerializer(serializers.Serializer):
    """Serializer for creating incidents via SOS report."""

    beacon_id = serializers.CharField(required=True, max_length=100, help_text="Hardware beacon ID (e.g., safe:uuid:403:403)")
    description = serializers.CharField(required=False, allow_blank=True, max_length=1000)

    class Meta:
        fields = ('beacon_id', 'description')


class IncidentReportSerializer(serializers.Serializer):
    """Serializer for creating non-emergency incidents via student report."""

    beacon_id = serializers.CharField(required=False, allow_blank=True, max_length=100, help_text="Hardware beacon ID (optional)")
    type = serializers.CharField(required=True, max_length=100, help_text="Report type (e.g., Safety Concern, Suspicious Activity, Infrastructure Issue)")
    description = serializers.CharField(required=True, max_length=1000, help_text="Detailed description of the incident")
    location = serializers.CharField(required=False, allow_blank=True, max_length=255, help_text="Location description if no beacon available")

    class Meta:
        fields = ('beacon_id', 'type', 'description', 'location')
