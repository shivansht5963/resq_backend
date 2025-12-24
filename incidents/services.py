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
        beacon_id: UUID of beacon location
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
    
    # 1. Validate beacon
    try:
        beacon = Beacon.objects.get(id=beacon_id, is_active=True)
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
    - AI_AUDIO → at least HIGH
    - AI_VISION → at least MEDIUM
    - STUDENT_SOS → MEDIUM
    """
    
    priority_map = {
        IncidentSignal.SignalType.PANIC_BUTTON: Incident.Priority.CRITICAL,
        IncidentSignal.SignalType.AI_AUDIO: Incident.Priority.HIGH,
        IncidentSignal.SignalType.AI_VISION: Incident.Priority.MEDIUM,
        IncidentSignal.SignalType.STUDENT_SOS: Incident.Priority.MEDIUM
    }
    
    new_priority = priority_map.get(new_signal_type, Incident.Priority.MEDIUM)
    return max(current, new_priority)


def get_initial_priority(signal_type):
    """Get initial priority based on first signal type."""
    
    priority_map = {
        IncidentSignal.SignalType.PANIC_BUTTON: Incident.Priority.CRITICAL,
        IncidentSignal.SignalType.AI_AUDIO: Incident.Priority.HIGH,
        IncidentSignal.SignalType.AI_VISION: Incident.Priority.MEDIUM,
        IncidentSignal.SignalType.STUDENT_SOS: Incident.Priority.MEDIUM
    }
    
    return priority_map.get(signal_type, Incident.Priority.MEDIUM)


def alert_guards_for_incident(incident, max_guards=3):
    """
    Send alerts to nearest guards.
    
    CRITICAL: Only sends alerts if incident has NO active GuardAssignment.
    This prevents re-alerting when new signals arrive on existing incident.
    
    Args:
        incident: Incident model instance
        max_guards: Max number of guards to alert (default 3)
    """
    
    # 1. Check if incident already has active assignment
    active_assignment = GuardAssignment.objects.filter(
        incident=incident,
        is_active=True
    ).exists()
    
    if active_assignment:
        logger.info(
            f"[ALERT] Incident {incident.id} already has active assignment. Skipping guard alerts.",
            extra={'incident_id': str(incident.id)}
        )
        return
    
    # 2. Find nearest guards
    nearest_guards = find_top_n_nearest_guards(
        beacon=incident.beacon,
        n=max_guards,
        exclude_current_beacon=True
    )
    
    # 3. Create alerts
    for rank, (guard_user, distance_km) in enumerate(nearest_guards, 1):
        # Check if guard already has pending alert for this incident
        existing_alert = GuardAlert.objects.filter(
            incident=incident,
            guard=guard_user,
            status__in=[GuardAlert.AlertStatus.SENT, GuardAlert.AlertStatus.ACKNOWLEDGED]
        ).exists()
        
        if existing_alert:
            logger.info(
                f"[ALERT] Guard {guard_user.full_name} already has alert for incident {incident.id}. Skipping.",
                extra={'incident_id': str(incident.id), 'guard_id': str(guard_user.id)}
            )
            continue
        
        # Create alert
        alert = GuardAlert.objects.create(
            incident=incident,
            guard=guard_user,
            status=GuardAlert.AlertStatus.SENT,
            distance_km=distance_km,
            priority_rank=rank
        )
        
        logger.info(
            f"[ALERT] Sent alert to guard {guard_user.full_name} for incident {incident.id} (rank #{rank})",
            extra={
                'incident_id': str(incident.id),
                'guard_id': str(guard_user.id),
                'distance_km': distance_km,
                'alert_id': alert.id
            }
        )


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


def handle_guard_alert_acknowledged(alert):
    """
    Guard acknowledged the alert. Create assignment and update incident status.
    
    Args:
        alert: GuardAlert instance
    """
    
    with transaction.atomic():
        # 1. Update alert status
        alert.status = GuardAlert.AlertStatus.ACKNOWLEDGED
        alert.save(update_fields=['status', 'updated_at'])
        
        # 2. Create or update assignment
        assignment, created = GuardAssignment.objects.update_or_create(
            incident=alert.incident,
            defaults={'guard': alert.guard, 'is_active': True}
        )
        
        # 3. Link alert to assignment
        alert.assignment = assignment
        alert.save(update_fields=['assignment'])
        
        # 4. Update incident status
        incident = alert.incident
        if incident.status == Incident.Status.CREATED:
            incident.status = Incident.Status.ASSIGNED
            incident.save(update_fields=['status'])
        
        logger.info(
            f"[ASSIGNMENT] Guard {alert.guard.full_name} assigned to incident {incident.id}",
            extra={'incident_id': str(incident.id), 'guard_id': str(alert.guard.id)}
        )


def handle_guard_alert_declined(alert):
    """
    Guard declined alert. Try next guard.
    
    Args:
        alert: GuardAlert instance
    """
    
    with transaction.atomic():
        # 1. Update alert status
        alert.status = GuardAlert.AlertStatus.DECLINED
        alert.save(update_fields=['status', 'updated_at'])
        
        logger.info(
            f"[DECLINED] Guard {alert.guard.full_name} declined incident {alert.incident.id}",
            extra={'incident_id': str(alert.incident.id), 'guard_id': str(alert.guard.id)}
        )
        
        # 2. Find next guard
        alerted_guard_ids = GuardAlert.objects.filter(
            incident=alert.incident
        ).values_list('guard_id', flat=True)
        
        next_guards = find_top_n_nearest_guards(
            beacon=alert.incident.beacon,
            n=1,
            available_only=True
        )
        
        if next_guards:
            next_guard_user, next_distance = next_guards[0]
            
            # Check if already alerted
            existing_alert = GuardAlert.objects.filter(
                incident=alert.incident,
                guard=next_guard_user
            ).exists()
            
            if not existing_alert:
                new_alert = GuardAlert.objects.create(
                    incident=alert.incident,
                    guard=next_guard_user,
                    status=GuardAlert.AlertStatus.SENT,
                    distance_km=next_distance,
                    priority_rank=alert.priority_rank + 1 if alert.priority_rank else 2
                )
                
                logger.info(
                    f"[NEXT_GUARD] Alerted next guard {next_guard_user.full_name}",
                    extra={'incident_id': str(alert.incident.id)}
                )
        else:
            # All guards exhausted
            logger.warning(
                f"[NO_GUARDS] All guards exhausted for incident {alert.incident.id}",
                extra={'incident_id': str(alert.incident.id)}
            )
