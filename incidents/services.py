"""
Incident deduplication and guard alert service.
Core logic for beacon-centric incident management.
"""
import logging
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from .models import Incident, IncidentSignal, Beacon
from security.models import GuardAlert, GuardAssignment
from chat.models import Conversation
from accounts.push_notifications import PushNotificationService

logger = logging.getLogger(__name__)

# Configurable deduplication window (minutes)
DEDUP_WINDOW_MINUTES = getattr(
    __import__('django.conf', fromlist=['settings']).settings,
    'INCIDENT_DEDUP_WINDOW_MINUTES',
    5
)

# Confidence thresholds for AI detection
AI_VISION_CONFIDENCE_THRESHOLD = 0.75
AI_AUDIO_CONFIDENCE_THRESHOLD = 0.80


def get_or_create_incident_with_signals(
    beacon_id,
    signal_type,
    source_user_id=None,
    source_device_id=None,
    ai_event_id=None,
    details=None,
    description=None
):
    """
    Atomic operation: get existing active incident or create new.
    
    Args:
        beacon_id: Hardware beacon ID (e.g., "safe:uuid:403:403")
        signal_type: IncidentSignal.SignalType choice (STUDENT_SOS, AI_VISION, AI_AUDIO, PANIC_BUTTON)
        source_user_id: User who triggered signal (for STUDENT_SOS)
        source_device_id: ESP32Device that triggered signal (for PANIC_BUTTON)
        ai_event_id: AIEvent that triggered signal (for AI_**)
        details: JSONField dict with signal-specific data
        description: Optional incident description
    
    Returns:
        tuple: (incident, created: bool, signal: IncidentSignal)
    
    Raises:
        ValueError: if beacon is invalid or inactive
    """
    
    # 1. Validate beacon (lookup by beacon_id hardware identifier)
    # Allow virtual beacon_ids (location:*) for non-beacon-based reports
    if beacon_id.startswith('location:'):
        # Virtual beacon for location-based reports
        # Create or get virtual beacon placeholder
        beacon, _ = Beacon.objects.get_or_create(
            beacon_id=beacon_id,
            defaults={
                'uuid': beacon_id,
                'major': 0,
                'minor': 0,
                'location_name': beacon_id.replace('location:', '').replace('_', ' ').title(),
                'building': 'Virtual Location',
                'floor': 0,
                'is_active': True
            }
        )
    else:
        # Real hardware beacon
        try:
            beacon = Beacon.objects.get(beacon_id=beacon_id, is_active=True)
        except Beacon.DoesNotExist:
            raise ValueError(f"Invalid or inactive beacon: {beacon_id}")
    
    # 2. Try to find existing active incident within dedup window
    dedup_cutoff = timezone.now() - timedelta(minutes=DEDUP_WINDOW_MINUTES)
    
    with transaction.atomic():
        # Lock for atomic operation
        existing_incident = Incident.objects.select_for_update().filter(
            beacon=beacon,
            status__in=[
                Incident.Status.CREATED,
                Incident.Status.ASSIGNED,
                Incident.Status.IN_PROGRESS
            ],
            created_at__gte=dedup_cutoff
        ).order_by('-created_at').first()
        
        if existing_incident:
            # Attach new signal to existing incident
            signal = IncidentSignal.objects.create(
                incident=existing_incident,
                signal_type=signal_type,
                source_user_id=source_user_id,
                source_device_id=source_device_id,
                ai_event_id=ai_event_id,
                details=details or {}
            )
            
            # Escalate priority if needed
            new_priority = escalate_priority(
                current=existing_incident.priority,
                new_signal_type=signal_type
            )
            
            if new_priority > existing_incident.priority:
                existing_incident.priority = new_priority
                existing_incident.save(update_fields=['priority'])
            
            # Update last signal time
            existing_incident.last_signal_time = timezone.now()
            existing_incident.save(update_fields=['last_signal_time'])
            
            logger.info(
                f"[DEDUP] Added signal {signal_type} to existing incident {existing_incident.id}",
                extra={'beacon_id': str(beacon.id), 'incident_id': str(existing_incident.id)}
            )
            
            return existing_incident, False, signal
        
        # 3. No existing incident, create new
        incident = Incident.objects.create(
            beacon=beacon,
            status=Incident.Status.CREATED,
            priority=get_initial_priority(signal_type),
            description=description or ""
        )
        
        signal = IncidentSignal.objects.create(
            incident=incident,
            signal_type=signal_type,
            source_user_id=source_user_id,
            source_device_id=source_device_id,
            ai_event_id=ai_event_id,
            details=details or {}
        )
        
        # Create conversation for new incident
        Conversation.objects.create(incident=incident)
        
        logger.info(
            f"[NEW] Created incident {incident.id} with signal {signal_type}",
            extra={'beacon_id': str(beacon.id), 'incident_id': str(incident.id)}
        )
        
        return incident, True, signal


def escalate_priority(current, new_signal_type):
    """
    Escalate priority based on signal type.
    
    Rules:
    - PANIC_BUTTON → always CRITICAL
    - VIOLENCE_DETECTED → CRITICAL
    - SCREAM_DETECTED → HIGH
    - STUDENT_SOS → MEDIUM
    - STUDENT_REPORT → MEDIUM
    """
    
    priority_map = {
        IncidentSignal.SignalType.PANIC_BUTTON: Incident.Priority.CRITICAL,
        IncidentSignal.SignalType.VIOLENCE_DETECTED: Incident.Priority.CRITICAL,
        IncidentSignal.SignalType.SCREAM_DETECTED: Incident.Priority.HIGH,
        IncidentSignal.SignalType.STUDENT_SOS: Incident.Priority.MEDIUM,
        IncidentSignal.SignalType.STUDENT_REPORT: Incident.Priority.MEDIUM
    }
    
    new_priority = priority_map.get(new_signal_type, Incident.Priority.MEDIUM)
    return max(current, new_priority)


def get_initial_priority(signal_type):
    """Get initial priority based on first signal type."""
    
    priority_map = {
        IncidentSignal.SignalType.PANIC_BUTTON: Incident.Priority.CRITICAL,
        IncidentSignal.SignalType.VIOLENCE_DETECTED: Incident.Priority.CRITICAL,
        IncidentSignal.SignalType.SCREAM_DETECTED: Incident.Priority.HIGH,
        IncidentSignal.SignalType.STUDENT_SOS: Incident.Priority.MEDIUM,
        IncidentSignal.SignalType.STUDENT_REPORT: Incident.Priority.MEDIUM
    }
    
    return priority_map.get(signal_type, Incident.Priority.MEDIUM)


def alert_guards_for_incident(incident, max_guards=None):
    """
    Send alerts to nearest guards based on incident priority.
    
    Uses ASSIGNMENT or BROADCAST alert type based on incident severity.
    Sends push notifications to registered guard devices.
    
    CRITICAL: Only sends alerts if incident has NO active GuardAssignment.
    This prevents re-alerting when new signals arrive on existing incident.
    
    Args:
        incident: Incident instance
        max_guards: Override number of guards to alert (if None, use priority rules)
    
    Returns:
        list: GuardAlert instances created
    """
    from security.services import (
        alert_guards_via_beacon_proximity,
        broadcast_alert_all_guards
    )
    
    # Determine alert fanout rules based on incident priority
    fanout_rules = get_alert_fanout_rules(incident)
    alert_type = fanout_rules['alert_type']
    requires_response = fanout_rules['requires_response']
    if max_guards is None:
        max_guards = fanout_rules['max_guards']
    
    logger.info(
        f"[ALERT] Sending {alert_type} alerts for incident {incident.id}",
        extra={
            'incident_id': str(incident.id),
            'priority': incident.priority,
            'alert_type': alert_type,
            'max_guards': max_guards
        }
    )
    
    # BROADCAST alerts go to all active guards (read-only)
    if alert_type == 'BROADCAST':
        alerts = broadcast_alert_all_guards(incident, requires_response=False)
    else:
        # ASSIGNMENT alerts use beacon-proximity search
        alerts = alert_guards_via_beacon_proximity(
            incident,
            max_guards=max_guards,
            alert_type=alert_type,
            requires_response=requires_response
        )
    
    # Send push notifications to all alerted guards
    try:
        send_push_notifications_for_alerts(incident, alerts)
    except Exception as e:
        logger.error(f"Failed to send push notifications for incident {incident.id}: {e}")
    
    return alerts


def send_push_notifications_for_alerts(incident, guard_alerts):
    """
    Send push notifications to guards who received alerts.
    
    Args:
        incident: Incident instance
        guard_alerts: List of GuardAlert instances
    """
    if not guard_alerts:
        return
    
    # Get location description
    location = incident.location or incident.beacon.location_name
    priority_name = dict(Incident.Priority.choices).get(incident.priority, 'MEDIUM')
    
    # Get unique guard users from alerts
    guard_users = set(alert.recipient for alert in guard_alerts)
    
    for guard_user in guard_users:
        try:
            # Get all active device tokens for this guard
            tokens = PushNotificationService.get_guard_tokens(guard_user)
            
            if tokens:
                # Send GUARD_ALERT notification
                PushNotificationService.notify_guard_alert(
                    expo_tokens=tokens,
                    incident_id=str(incident.id),
                    alert_id=guard_alerts[0].id,  # Use first alert ID
                    priority=priority_name,
                    location=location
                )
                logger.info(f"Sent push notification to guard {guard_user.email} for incident {incident.id}")
        except Exception as e:
            logger.error(f"Failed to send notification to guard {guard_user.email}: {e}")


def find_top_n_nearest_guards(beacon, n=3, exclude_current_beacon=True, available_only=True):
    """
    Find top N nearest guards to a beacon.
    
    Returns:
        list: [(guard_user, distance_km), ...]
    
    TODO: Implement actual beacon distance calculation.
    For now, returns random guards. Needs proper implementation.
    """
    from django.contrib.auth import get_user_model
    from security.models import GuardProfile
    
    User = get_user_model()
    
    # Build query
    query = GuardProfile.objects.filter(is_active=True)
    
    if available_only:
        query = query.filter(is_available=True)
    
    if exclude_current_beacon:
        query = query.exclude(current_beacon=beacon)
    
    # Sort by creation (TODO: replace with actual distance calculation)
    guards = list(query[:n])
    
    # Return list of (guard_user, distance_km) tuples
    result = [(g.user, g.current_beacon.latitude if g.current_beacon else 0.0) for g in guards]
    return result[:n]


def handle_guard_alert_accepted(alert):
    """
    Guard accepted ASSIGNMENT alert.
    Creates assignment and updates incident status.
    
    Wrapper around security.services function.
    
    Args:
        alert: GuardAlert instance
    """
    from security.services import handle_guard_alert_accepted_via_proximity
    
    return handle_guard_alert_accepted_via_proximity(alert)


def handle_guard_alert_acknowledged(alert):
    """
    DEPRECATED: Use handle_guard_alert_accepted instead.
    Kept for backward compatibility.
    """
    return handle_guard_alert_accepted(alert)


def handle_guard_alert_declined(alert):
    """
    Guard declined alert. Try next guard via beacon-proximity search.
    
    Now uses beacon-proximity logic - continues expanding radius.
    Does NOT restart from beginning.
    
    Args:
        alert: GuardAlert instance
    """
    from security.services import handle_guard_alert_declined_via_proximity
    
    return handle_guard_alert_declined_via_proximity(alert)


def get_alert_fanout_rules(incident):
    """
    Determine alert type and number of guards based on incident priority & signal types.
    
    Fanout Rules (Hackathon-Optimized):
    
    CRITICAL Priority → ASSIGNMENT alert to 5 guards
      (Panic button, violence, etc.)
    
    HIGH Priority → ASSIGNMENT alert to 3 guards
      (Screaming, severe threats)
    
    MEDIUM Priority → ASSIGNMENT alert to 2 guards
      (Student SOS, general reports)
    
    SYSTEM-WIDE Events → BROADCAST alert to ALL guards
      (Fire, evacuation, system emergency)
    
    Args:
        incident: Incident instance
    
    Returns:
        dict: {
            'alert_type': 'ASSIGNMENT' or 'BROADCAST',
            'requires_response': True/False,
            'max_guards': int (number to alert)
        }
    """
    from security.models import GuardAlert
    
    priority = incident.priority
    
    # Check if this is a system-wide broadcast (e.g., fire, evacuation)
    is_system_broadcast = False
    if incident.signals.exists():
        signal_types = set(incident.signals.values_list('signal_type', flat=True))
        # Future: Add FIRE_DETECTED, EVACUATION_ALERT, etc. to signal types
        # For now, only explicit system broadcasts
        is_system_broadcast = False
    
    if is_system_broadcast:
        return {
            'alert_type': GuardAlert.AlertType.BROADCAST,
            'requires_response': False,
            'max_guards': 999,  # All active guards
        }
    
    # Assignment-based alerts with fanout based on priority
    if priority == incident.Priority.CRITICAL:
        return {
            'alert_type': GuardAlert.AlertType.ASSIGNMENT,
            'requires_response': True,
            'max_guards': 5,
        }
    elif priority == incident.Priority.HIGH:
        return {
            'alert_type': GuardAlert.AlertType.ASSIGNMENT,
            'requires_response': True,
            'max_guards': 3,
        }
    else:  # MEDIUM, LOW
        return {
            'alert_type': GuardAlert.AlertType.ASSIGNMENT,
            'requires_response': True,
            'max_guards': 2,
        }
