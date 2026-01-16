"""
Incident deduplication and guard alert service.
Core logic for beacon-centric incident management.
"""
import logging
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from .models import Incident, IncidentSignal, Beacon, IncidentEvent
from security.models import GuardAlert, GuardAssignment
from chat.models import Conversation
from accounts.push_notifications import PushNotificationService

logger = logging.getLogger(__name__)


def log_incident_event(
    incident,
    event_type,
    actor=None,
    target_guard=None,
    previous_status=None,
    new_status=None,
    previous_priority=None,
    new_priority=None,
    details=None
):
    """
    Log an event in the incident's audit trail.
    
    Args:
        incident: Incident instance
        event_type: IncidentEvent.EventType choice
        actor: User who triggered the event (optional)
        target_guard: Guard targeted by the event (for alerts)
        previous_status: Previous incident status
        new_status: New incident status
        previous_priority: Previous priority
        new_priority: New priority
        details: dict with additional context
    
    Returns:
        IncidentEvent: Created event instance
    """
    try:
        event = IncidentEvent.objects.create(
            incident=incident,
            event_type=event_type,
            actor=actor,
            target_guard=target_guard,
            previous_status=previous_status or '',
            new_status=new_status or '',
            previous_priority=previous_priority,
            new_priority=new_priority,
            details=details or {}
        )
        
        logger.info(
            f"[EVENT] {event_type} logged for incident {str(incident.id)[:8]}...",
            extra={'incident_id': str(incident.id), 'event_type': event_type}
        )
        
        return event
    except Exception as e:
        logger.error(f"[EVENT] Failed to log event: {e}")
        return None


# =============================================================================
# STATE MACHINE FOR INCIDENT STATUS TRANSITIONS
# =============================================================================

# Valid status transitions - defines allowed state changes
VALID_TRANSITIONS = {
    Incident.Status.CREATED: [
        Incident.Status.ASSIGNED,
        Incident.Status.RESOLVED,  # Admin can resolve without assignment
    ],
    Incident.Status.ASSIGNED: [
        Incident.Status.IN_PROGRESS,
        Incident.Status.CREATED,   # Can unassign
        Incident.Status.RESOLVED,
    ],
    Incident.Status.IN_PROGRESS: [
        Incident.Status.RESOLVED,
        Incident.Status.ASSIGNED,  # Can reassign
    ],
    Incident.Status.RESOLVED: [],  # Terminal state - no transitions allowed
}


def validate_status_transition(current_status, new_status):
    """
    Check if a status transition is valid.
    
    Args:
        current_status: Current incident status
        new_status: Desired new status
    
    Returns:
        bool: True if transition is allowed
    """
    allowed = VALID_TRANSITIONS.get(current_status, [])
    return new_status in allowed


def transition_incident_status(incident, new_status, actor, notes=""):
    """
    Safely transition incident status with validation and logging.
    
    Args:
        incident: Incident instance
        new_status: Target status
        actor: User triggering the transition
        notes: Optional notes for the event
    
    Returns:
        tuple: (success: bool, error_message: str or None)
    
    Raises:
        ValueError: If transition is not allowed
    """
    current = incident.status
    
    # Validate transition
    if not validate_status_transition(current, new_status):
        error_msg = f"Cannot transition from {current} to {new_status}"
        logger.warning(f"[STATE] Invalid transition: {error_msg}")
        return False, error_msg
    
    # Log the status change event
    log_incident_event(
        incident=incident,
        event_type=IncidentEvent.EventType.STATUS_CHANGED,
        actor=actor,
        previous_status=current,
        new_status=new_status,
        details={"notes": notes} if notes else {}
    )
    
    # Update incident
    incident.status = new_status
    incident.save(update_fields=["status", "updated_at"])
    
    logger.info(
        f"[STATE] Incident {str(incident.id)[:8]} transitioned: {current} -> {new_status}",
        extra={'incident_id': str(incident.id), 'old_status': current, 'new_status': new_status}
    )
    
    return True, None


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
        # Lock beacon to prevent concurrent incident creation
        # This ensures only one process can check/create incident for this beacon at a time
        if not beacon_id.startswith('location:'):
            # For real beacons, lock the beacon row
            Beacon.objects.select_for_update().get(id=beacon.id)
        
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
                old_priority = existing_incident.priority
                existing_incident.priority = new_priority
                existing_incident.save(update_fields=['priority'])
                
                # Send INCIDENT_ESCALATED notification to assigned guard (if any)
                try:
                    assignment = existing_incident.guard_assignments.filter(is_active=True).first()
                    if assignment:
                        guard_user = assignment.guard
                        from accounts.push_notifications import PushNotificationService
                        tokens = PushNotificationService.get_guard_tokens(guard_user)
                        if tokens:
                            priority_display = dict(existing_incident.Priority.choices).get(new_priority, 'UNKNOWN')
                            PushNotificationService.notify_incident_escalated(
                                expo_tokens=tokens,
                                incident_id=str(existing_incident.id),
                                new_priority=priority_display
                            )
                            logger.info(
                                f"[INCIDENT_ESCALATED] Notification sent to guard {guard_user.full_name}",
                                extra={
                                    'incident_id': str(existing_incident.id),
                                    'old_priority': old_priority,
                                    'new_priority': new_priority
                                }
                            )
                except Exception as e:
                    logger.error(
                        f"[INCIDENT_ESCALATED] Failed to send notification: {str(e)}",
                        extra={'incident_id': str(existing_incident.id)}
                    )
            
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
        
        # Log INCIDENT_CREATED event
        from django.contrib.auth import get_user_model
        User = get_user_model()
        actor = None
        if source_user_id:
            try:
                actor = User.objects.get(id=source_user_id)
            except User.DoesNotExist:
                pass
        
        log_incident_event(
            incident=incident,
            event_type=IncidentEvent.EventType.INCIDENT_CREATED,
            actor=actor,
            new_status=Incident.Status.CREATED,
            new_priority=incident.priority,
            details={
                'signal_type': signal_type,
                'beacon_name': beacon.location_name
            }
        )
        
        # Update buzzer status to PENDING (new incident, no guard yet)
        update_buzzer_status_on_incident_created(incident)
        
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
    
    Uses send_with_logging() for:
    - Database logging (PushNotificationLog)
    - Retry logic (3 attempts)
    - GuardAlert tracking field updates
    
    Also logs ALERT_SENT event for each notification.
    Includes incident image URLs in notification data for mobile app to display.
    
    Args:
        incident: Incident instance
        guard_alerts: List of GuardAlert instances
    """
    if not guard_alerts:
        logger.warning(f"No guard alerts to send notifications for incident {incident.id}")
        return
    
    # Get location description
    location = incident.location or incident.beacon.location_name
    priority_name = dict(Incident.Priority.choices).get(incident.priority, 'MEDIUM')
    
    success_count = 0
    fail_count = 0
    
    # Send notifications to each guard
    for alert in guard_alerts:
        guard_user = alert.guard
        
        try:
            # Get all active device tokens for this guard
            tokens = PushNotificationService.get_guard_tokens(guard_user)
            
            if not tokens:
                logger.warning(f"No active tokens for guard {guard_user.email}")
                # Log event even if no tokens
                log_incident_event(
                    incident=incident,
                    event_type=IncidentEvent.EventType.ALERT_FAILED,
                    target_guard=guard_user,
                    details={'error': 'No active push tokens', 'alert_id': alert.id}
                )
                fail_count += 1
                continue
            
            # Get incident images if available
            images = incident.images.all().order_by('uploaded_at')
            image_urls = []
            if images.exists():
                # Get first image to include in push notification
                # Full list of images will be available in the incident details API
                image_urls = [
                    img.image.url for img in images[:3]  # Include first 3 images
                ]
            
            # Send notification with logging and retry
            notification_data = {
                "type": "GUARD_ALERT",
                "incident_id": str(incident.id),
                "alert_id": str(alert.id),
                "priority": priority_name,
                "location": location,
                "image_count": incident.images.count(),
            }
            
            # Add image URLs if available
            if image_urls:
                notification_data["images"] = image_urls
            
            # Send to each token (usually one per device)
            token_success = False
            for token in tokens:
                success = PushNotificationService.send_with_logging(
                    recipient=guard_user,
                    expo_token=token,
                    notification_type='GUARD_ALERT',
                    title="🚨 Incoming Alert",
                    body=f"{priority_name} - {location}",
                    data=notification_data,
                    incident=incident,
                    guard_alert=alert,
                    max_retries=3
                )
                if success:
                    token_success = True
            
            if token_success:
                # Log ALERT_SENT event
                log_incident_event(
                    incident=incident,
                    event_type=IncidentEvent.EventType.ALERT_SENT,
                    target_guard=guard_user,
                    details={
                        'alert_id': alert.id,
                        'priority_rank': alert.priority_rank,
                        'tokens_count': len(tokens),
                        'images_sent': len(image_urls)
                    }
                )
                success_count += 1
                logger.info(f"✅ Sent push to guard {guard_user.email} for incident {str(incident.id)[:8]} with {len(image_urls)} images")
            else:
                # Log failure event
                log_incident_event(
                    incident=incident,
                    event_type=IncidentEvent.EventType.ALERT_FAILED,
                    target_guard=guard_user,
                    details={'error': 'All tokens failed', 'alert_id': alert.id}
                )
                fail_count += 1
                
        except Exception as e:
            logger.error(f"❌ Failed to send notification to guard {guard_user.email}: {e}", exc_info=True)
            fail_count += 1
    
    logger.info(f"[PUSH] Push notification summary: {success_count} success, {fail_count} failed")


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


# =============================================================================
# BUZZER STATUS MANAGEMENT
# =============================================================================

def update_buzzer_status_on_incident_created(incident):
    """
    Update buzzer status when new incident is created.
    Sets status to PENDING (incident exists but no guard assigned yet).
    
    Args:
        incident: Incident instance (just created)
    """
    incident.buzzer_status = Incident.BuzzerStatus.PENDING
    incident.save(update_fields=['buzzer_status', 'buzzer_last_updated'])
    
    logger.info(
        f"[BUZZER] Set status to PENDING for incident {str(incident.id)[:8]}",
        extra={'incident_id': str(incident.id), 'beacon_id': str(incident.beacon.id)}
    )


def update_buzzer_status_on_guard_assignment(incident, guard):
    """
    Update buzzer status when guard is assigned to incident.
    Sets status to ACTIVE (guard assigned and responding).
    
    Args:
        incident: Incident instance
        guard: User instance (guard who was assigned)
    """
    incident.buzzer_status = Incident.BuzzerStatus.ACTIVE
    incident.save(update_fields=['buzzer_status', 'buzzer_last_updated'])
    
    logger.info(
        f"[BUZZER] Set status to ACTIVE for incident {str(incident.id)[:8]} (Guard: {guard.full_name})",
        extra={'incident_id': str(incident.id), 'guard_id': str(guard.id)}
    )


def update_buzzer_status_on_incident_acknowledged(incident):
    """
    Update buzzer status when guard acknowledges incident (en route).
    Sets status to ACKNOWLEDGED (guard confirmed and en route).
    
    Args:
        incident: Incident instance
    """
    incident.buzzer_status = Incident.BuzzerStatus.ACKNOWLEDGED
    incident.save(update_fields=['buzzer_status', 'buzzer_last_updated'])
    
    logger.info(
        f"[BUZZER] Set status to ACKNOWLEDGED for incident {str(incident.id)[:8]}",
        extra={'incident_id': str(incident.id)}
    )


def update_buzzer_status_on_incident_resolved(incident):
    """
    Update buzzer status when incident is marked as RESOLVED.
    Sets status to RESOLVED (incident complete, stop buzzer).
    
    Args:
        incident: Incident instance
    """
    incident.buzzer_status = Incident.BuzzerStatus.RESOLVED
    incident.save(update_fields=['buzzer_status', 'buzzer_last_updated'])
    
    logger.info(
        f"[BUZZER] Set status to RESOLVED for incident {str(incident.id)[:8]}",
        extra={'incident_id': str(incident.id)}
    )
