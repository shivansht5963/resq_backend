from rest_framework import serializers
from .models import Beacon, Incident, IncidentSignal, PhysicalDevice, IncidentImage, IncidentEvent
from security.models import GuardAssignment, GuardAlert
from chat.models import Conversation, Message


class IncidentImageSerializer(serializers.ModelSerializer):
    """Serializer for incident images."""
    
    uploaded_by_email = serializers.CharField(source='uploaded_by.email', read_only=True)
    image = serializers.SerializerMethodField()
    
    class Meta:
        model = IncidentImage
        fields = ('id', 'image', 'uploaded_by_email', 'uploaded_at', 'description')
        read_only_fields = ('id', 'uploaded_at', 'uploaded_by_email')
    
    def get_image(self, obj):
        """Return absolute URL for image."""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class BeaconSerializer(serializers.ModelSerializer):
    """Serializer for Beacon model."""

    class Meta:
        model = Beacon
        fields = ('id', 'beacon_id', 'uuid', 'major', 'minor', 'location_name', 'building', 'floor', 'latitude', 'longitude', 'is_active', 'created_at')
        read_only_fields = ('id', 'created_at')


class PhysicalDeviceSerializer(serializers.ModelSerializer):
    """Serializer for PhysicalDevice."""

    beacon = BeaconSerializer(read_only=True)

    class Meta:
        model = PhysicalDevice
        fields = ('id', 'device_id', 'device_type', 'beacon', 'name', 'is_active')
        read_only_fields = ('id',)


class IncidentSignalSerializer(serializers.ModelSerializer):
    """Serializer for IncidentSignal - individual triggers."""

    source_user = serializers.SerializerMethodField()
    source_device = PhysicalDeviceSerializer(read_only=True)
    
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


class IncidentStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for student polling incident status.
    
    Shows:
    - Incident details
    - Guard assignment status (waiting/assigned)
    - Guard information (when assigned)
    - Alert status details
    - Timeline of updates
    """
    
    beacon = BeaconSerializer(read_only=True)
    signal_count = serializers.SerializerMethodField()
    guard_status = serializers.SerializerMethodField()
    guard_assignment = serializers.SerializerMethodField()
    alert_status_summary = serializers.SerializerMethodField()
    pending_alerts = serializers.SerializerMethodField()
    
    class Meta:
        model = Incident
        fields = (
            'id', 'beacon', 'status', 'priority', 'description', 'report_type', 'location',
            'signal_count',
            'guard_status',  # NEW: "WAITING_FOR_GUARD" or "GUARD_ASSIGNED"
            'guard_assignment',  # NEW: Guard details when assigned
            'alert_status_summary',  # NEW: Summary of alert statuses
            'pending_alerts',  # NEW: Pending alerts to guards
            'first_signal_time', 'last_signal_time',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'first_signal_time', 'last_signal_time')
    
    def get_signal_count(self, obj):
        """Count of signals for this incident."""
        return obj.signals.count()
    
    def get_guard_status(self, obj):
        """
        Return guard assignment status.
        
        Returns:
        - "WAITING_FOR_GUARD" if incident has SENT/DECLINED alerts
        - "GUARD_ASSIGNED" if active assignment exists
        - "NO_ASSIGNMENT" if all alerts expired/declined
        """
        # Check if has active assignment
        try:
            assignment = obj.guard_assignments.get(is_active=True)
            return {
                'status': 'GUARD_ASSIGNED',
                'message': 'Guard has been assigned to your incident',
                'assigned_at': assignment.assigned_at
            }
        except GuardAssignment.DoesNotExist:
            pass
        
        # Check if alerts are still pending
        pending_alerts = obj.guard_alerts.filter(
            status__in=['SENT', 'ACCEPTED']
        ).count()
        
        if pending_alerts > 0:
            return {
                'status': 'WAITING_FOR_GUARD',
                'message': f'Searching for available guard... ({pending_alerts} being contacted)',
                'pending_alerts': pending_alerts
            }
        
        return {
            'status': 'NO_ASSIGNMENT',
            'message': 'No guard available at this time. Admin has been notified.',
            'pending_alerts': 0
        }
    
    def get_guard_assignment(self, obj):
        """Get active guard assignment details."""
        try:
            assignment = obj.guard_assignments.get(is_active=True)
            return {
                'id': assignment.id,
                'guard': {
                    'id': str(assignment.guard.id),
                    'full_name': assignment.guard.full_name,
                    'email': assignment.guard.email
                },
                'assigned_at': assignment.assigned_at,
                'status': 'ACTIVE'
            }
        except GuardAssignment.DoesNotExist:
            return None
    
    def get_alert_status_summary(self, obj):
        """Summary of alert statuses."""
        alerts = obj.guard_alerts.all()
        return {
            'total_alerts': alerts.count(),
            'sent': alerts.filter(status='SENT').count(),
            'accepted': alerts.filter(status='ACCEPTED').count(),
            'declined': alerts.filter(status='DECLINED').count(),
            'expired': alerts.filter(status='EXPIRED').count()
        }
    
    def get_pending_alerts(self, obj):
        """List of pending (SENT) alerts with guard info."""
        pending = obj.guard_alerts.filter(status='SENT').order_by('priority_rank')
        return [
            {
                'id': alert.id,
                'guard': {
                    'id': str(alert.guard.id),
                    'full_name': alert.guard.full_name
                },
                'priority_rank': alert.priority_rank,
                'alert_type': alert.alert_type,
                'requires_response': alert.requires_response,
                'alert_sent_at': alert.alert_sent_at,
                'response_deadline': alert.response_deadline
            }
            for alert in pending
        ]


class IncidentReportSerializer(serializers.Serializer):
    """Serializer for creating non-emergency incidents via student report."""

    beacon_id = serializers.CharField(required=False, allow_blank=True, max_length=100, help_text="Hardware beacon ID (optional)")
    type = serializers.CharField(required=True, max_length=100, help_text="Report type (e.g., Safety Concern, Suspicious Activity, Infrastructure Issue)")
    description = serializers.CharField(required=True, max_length=1000, help_text="Detailed description of the incident")
    location = serializers.CharField(required=False, allow_blank=True, max_length=255, help_text="Location description if no beacon available")

    class Meta:
        fields = ('beacon_id', 'type', 'description', 'location')


class IncidentEventSerializer(serializers.ModelSerializer):
    """
    Serializer for IncidentEvent - audit trail entries.
    
    Used for the incident timeline/history endpoints.
    """
    
    actor = serializers.SerializerMethodField()
    target_guard = serializers.SerializerMethodField()
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    
    class Meta:
        model = IncidentEvent
        fields = (
            'id', 'event_type', 'event_type_display',
            'actor', 'target_guard',
            'previous_status', 'new_status',
            'previous_priority', 'new_priority',
            'details', 'created_at'
        )
        read_only_fields = ('id', 'created_at')
    
    def get_actor(self, obj):
        """Return actor user info."""
        if obj.actor:
            return {
                'id': str(obj.actor.id),
                'full_name': obj.actor.full_name,
                'email': obj.actor.email,
                'role': obj.actor.role
            }
        return None
    
    def get_target_guard(self, obj):
        """Return target guard info (for alert events)."""
        if obj.target_guard:
            return {
                'id': str(obj.target_guard.id),
                'full_name': obj.target_guard.full_name,
                'email': obj.target_guard.email
            }
        return None


class IncidentTimelineSerializer(serializers.ModelSerializer):
    """
    Serializer for incident timeline view.
    
    Returns incident with full event history for audit trail.
    Used by guards and admins to view complete incident history.
    """
    
    beacon = BeaconSerializer(read_only=True)
    events = IncidentEventSerializer(many=True, read_only=True)
    current_assignment = serializers.SerializerMethodField()
    resolution_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Incident
        fields = (
            'id', 'beacon', 'status', 'priority', 'description',
            'report_type', 'location',
            'current_assignment', 'resolution_info',
            'events',  # Full event timeline
            'created_at', 'updated_at', 'resolved_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'resolved_at')
    
    def get_current_assignment(self, obj):
        """Get active guard assignment info."""
        try:
            assignment = obj.guard_assignments.get(is_active=True)
            return {
                'guard': {
                    'id': str(assignment.guard.id),
                    'full_name': assignment.guard.full_name,
                    'email': assignment.guard.email
                },
                'assigned_at': assignment.assigned_at
            }
        except GuardAssignment.DoesNotExist:
            return None
    
    def get_resolution_info(self, obj):
        """Get resolution details if incident is resolved."""
        if obj.status != Incident.Status.RESOLVED:
            return None
        
        return {
            'resolved_by': {
                'id': str(obj.resolved_by.id),
                'full_name': obj.resolved_by.full_name
            } if obj.resolved_by else None,
            'resolved_at': obj.resolved_at,
            'resolution_type': obj.resolution_type,
            'resolution_notes': obj.resolution_notes
        }


class GuardIncidentHistorySerializer(serializers.ModelSerializer):
    """
    Serializer for guard's incident history view.
    
    Shows incidents the guard was involved with (assigned, alerted, etc.)
    Lighter weight than full timeline for list views.
    """
    
    beacon = BeaconSerializer(read_only=True)
    guard_role = serializers.SerializerMethodField()
    
    class Meta:
        model = Incident
        fields = (
            'id', 'beacon', 'status', 'priority', 'description',
            'report_type', 'location',
            'guard_role',  # What role the guard played
            'created_at', 'resolved_at'
        )
        read_only_fields = fields
    
    def get_guard_role(self, obj):
        """
        Determine what role the current guard played in this incident.
        
        Returns: 'assigned', 'accepted', 'declined', 'alerted', etc.
        """
        guard = self.context.get('guard')
        if not guard:
            return None
        
        # Check if guard was assigned
        try:
            assignment = obj.guard_assignments.get(guard=guard)
            if assignment.is_active:
                return 'currently_assigned'
            return 'was_assigned'
        except GuardAssignment.DoesNotExist:
            pass
        
        # Check guard's alert status
        alerts = obj.guard_alerts.filter(guard=guard)
        if alerts.exists():
            alert = alerts.first()
            return f'alert_{alert.status.lower()}'
        
        return None

