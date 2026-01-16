"""
Guard assignment and location services.
Handles beacon-proximity-aware guard search and alert management.
"""
import logging
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from security.models import GuardProfile, GuardAssignment, GuardAlert
from incidents.models import Incident, BeaconProximity

logger = logging.getLogger(__name__)


def find_available_guards_via_beacon_proximity(incident_beacon, max_guards=3, exclude_guard_ids=None):
    """
    Expanding-radius beacon search: find available guards.
    """
    logger.info(
        f"[SEARCH] 🔍 find_available_guards: beacon={incident_beacon.location_name} "
        f"(id={str(incident_beacon.id)[:8]}...) | max_guards={max_guards}"
    )
    
    if exclude_guard_ids is None:
        exclude_guard_ids = []
    
    found_guards = []
    visited_beacons = set()
    search_queue = [(incident_beacon, 0)]  # (beacon, priority_level)
    
    while search_queue and len(found_guards) < max_guards:
        current_beacon, priority_level = search_queue.pop(0)
        
        # Skip if already searched
        if current_beacon.id in visited_beacons:
            continue
        visited_beacons.add(current_beacon.id)
        
        # Find guards at current beacon
        guard_profiles = GuardProfile.objects.filter(
            current_beacon=current_beacon,
            is_active=True,
            is_available=True,
            user__is_active=True
        ).exclude(
            user_id__in=exclude_guard_ids
        ).select_related('user')
        
        # Log what we're finding
        all_guards_at_beacon = GuardProfile.objects.filter(current_beacon=current_beacon)
        logger.info(
            f"[SEARCH] Beacon '{current_beacon.location_name}': "
            f"total_guards={all_guards_at_beacon.count()}, "
            f"eligible={guard_profiles.count()}"
        )
        
        for guard_profile in guard_profiles:
            # Check if guard is already assigned to another active incident
            existing_assignment = GuardAssignment.objects.filter(
                guard=guard_profile.user,
                is_active=True
            ).exists()
            
            if existing_assignment:
                logger.info(
                    f"[SEARCH] ⚠️ SKIP: Guard {guard_profile.user.full_name} already has active assignment"
                )
                continue
            
            found_guards.append((guard_profile.user, current_beacon, priority_level))
            logger.info(
                f"[SEARCH] ✅ FOUND: Guard {guard_profile.user.full_name} at {current_beacon.location_name}"
            )
            
            if len(found_guards) >= max_guards:
                break
        
        # If not enough guards found, add nearby beacons to search queue
        if len(found_guards) < max_guards:
            nearby_beacons = BeaconProximity.objects.filter(
                from_beacon=current_beacon
            ).select_related('to_beacon').order_by('priority')
            
            for proximity in nearby_beacons:
                if proximity.to_beacon.id not in visited_beacons:
                    search_queue.append((proximity.to_beacon, proximity.priority))
    
    logger.info(
        f"[SEARCH] 📊 Result: found {len(found_guards)} guards for beacon {incident_beacon.location_name}"
    )
    
    if len(found_guards) == 0:
        # Debug: show all guard profiles to help diagnose
        all_guards = GuardProfile.objects.select_related('user', 'current_beacon').all()
        logger.warning(f"[SEARCH] ⚠️ NO GUARDS FOUND! Debugging all guards:")
        for gp in all_guards:
            beacon_match = gp.current_beacon and gp.current_beacon.id == incident_beacon.id
            logger.warning(
                f"[SEARCH]   - {gp.user.full_name}: "
                f"is_active={gp.is_active}, is_available={gp.is_available}, "
                f"user.is_active={gp.user.is_active}, "
                f"beacon={'MATCH' if beacon_match else gp.current_beacon.location_name if gp.current_beacon else 'NULL'}"
            )
    
    return found_guards[:max_guards]


def alert_guards_via_beacon_proximity(incident, max_guards=3, alert_type='ASSIGNMENT', requires_response=True):
    """
    Send alerts to available guards using beacon-proximity search.
    
    CRITICAL:
    - Only alerts if incident has NO active GuardAssignment
    - Creates alerts only once per (incident, guard) pair
    - Supports ASSIGNMENT and BROADCAST alert types
    - ASSIGNMENT: Guards must accept/reject (response_deadline set for auto-escalation)
    - BROADCAST: Read-only, no response required
    
    Args:
        incident: Incident instance
        max_guards: Max number of guards to alert (default 3)
        alert_type: 'ASSIGNMENT' or 'BROADCAST'
        requires_response: True/False (for compatibility)
    
    Returns:
        list: GuardAlert instances created
    """
    from datetime import timedelta
    
    # 1. Check if incident already has active assignment
    # Use select_for_update() to lock the incident and prevent concurrent alert generation
    incident = Incident.objects.select_for_update().get(id=incident.id)
    
    active_assignment = GuardAssignment.objects.filter(
        incident=incident,
        is_active=True
    ).exists()
    
    if active_assignment:
        logger.info(
            f"[ALERT] Incident {incident.id} already has active assignment. Skipping alerts.",
            extra={'incident_id': str(incident.id)}
        )
        return []
    
    # 2. Get already-alerted guard IDs to avoid re-alerting (only for ASSIGNMENT type)
    already_alerted_guard_ids = []
    if alert_type == 'ASSIGNMENT':
        already_alerted_guard_ids = list(
            GuardAlert.objects.filter(
                incident=incident,
                status__in=[GuardAlert.AlertStatus.SENT, GuardAlert.AlertStatus.ACCEPTED]
            ).values_list('guard_id', flat=True)
        )
    # For BROADCAST, we want to alert all active guards regardless of prior alerts
    
    # 3. Find available guards via beacon proximity
    available_guards = find_available_guards_via_beacon_proximity(
        incident_beacon=incident.beacon,
        max_guards=max_guards,
        exclude_guard_ids=already_alerted_guard_ids
    )
    
    if not available_guards:
        logger.warning(
            f"[ALERT] No available guards found for incident {incident.id}",
            extra={'incident_id': str(incident.id)}
        )
        return []
    
    # 4. Create alerts for found guards with appropriate type and deadline
    created_alerts = []
    response_deadline = None
    
    if alert_type == 'ASSIGNMENT':
        # Set 45-second timeout for auto-escalation
        response_deadline = timezone.now() + timedelta(seconds=45)
    
    for rank, (guard_user, beacon, priority_level) in enumerate(available_guards, 1):
        try:
            alert = GuardAlert.objects.create(
                incident=incident,
                guard=guard_user,
                status=GuardAlert.AlertStatus.SENT,
                alert_type=alert_type,
                requires_response=requires_response,
                distance_km=0.0,  # Beacon-based, not GPS distance
                priority_rank=rank,
                response_deadline=response_deadline
            )
            created_alerts.append(alert)
            
            logger.info(
                f"[ALERT] Sent {alert_type} alert to guard {guard_user.full_name} for incident {incident.id} (rank #{rank})",
                extra={
                    'incident_id': str(incident.id),
                    'guard_id': str(guard_user.id),
                    'alert_type': alert_type,
                    'beacon_id': str(beacon.id),
                    'beacon_name': beacon.location_name,
                    'proximity_level': priority_level
                }
            )
        except Exception as e:
            logger.error(
                f"[ALERT] Failed to create alert for guard {guard_user.full_name}: {str(e)}",
                extra={'incident_id': str(incident.id), 'guard_id': str(guard_user.id)}
            )
    
    return created_alerts


def broadcast_alert_all_guards(incident, requires_response=False):
    """
    Send BROADCAST alerts to all active guards (awareness only, no assignment).
    
    Used for system-wide events (fire, evacuation, etc.)
    Guards receive read-only notification without accept/reject buttons.
    
    Args:
        incident: Incident instance
        requires_response: Always False for broadcasts
    
    Returns:
        list: GuardAlert instances created
    """
    from security.models import GuardProfile
    
    # Get all active guards
    active_guards = GuardProfile.objects.filter(
        is_active=True,
        user__is_active=True
    ).select_related('user')
    
    created_alerts = []
    
    for rank, guard_profile in enumerate(active_guards, 1):
        try:
            # Check if alert already exists for this guard-incident pair
            existing_alert = GuardAlert.objects.filter(
                incident=incident,
                guard=guard_profile.user,
                alert_type='BROADCAST'
            ).exists()
            
            if existing_alert:
                logger.debug(
                    f"[BROADCAST] Alert already exists for guard {guard_profile.user.full_name}",
                    extra={'guard_id': str(guard_profile.user.id)}
                )
                continue
            
            alert = GuardAlert.objects.create(
                incident=incident,
                guard=guard_profile.user,
                status=GuardAlert.AlertStatus.SENT,
                alert_type='BROADCAST',
                requires_response=False,  # Read-only, no response required
                priority_rank=rank
            )
            created_alerts.append(alert)
            
            logger.info(
                f"[BROADCAST] Alert sent to guard {guard_profile.user.full_name}",
                extra={'incident_id': str(incident.id), 'guard_id': str(guard_profile.user.id)}
            )
        except Exception as e:
            logger.error(
                f"[BROADCAST] Failed to create alert: {str(e)}",
                extra={'incident_id': str(incident.id)}
            )
    
    logger.info(
        f"[BROADCAST] Sent {len(created_alerts)} broadcast alerts for incident {incident.id}",
        extra={'incident_id': str(incident.id), 'alerts_sent': len(created_alerts)}
    )
    
    return created_alerts


def handle_guard_alert_accepted_via_proximity(alert):
    """
    Guard accepted alert via beacon-proximity search.
    Creates assignment and updates incident status.
    
    Called when ASSIGNMENT-type alert is accepted.
    Creates formal GuardAssignment link.

    Args:
        alert: GuardAlert instance
    """
    from incidents.models import Incident
    from accounts.push_notifications import PushNotificationService
    
    with transaction.atomic():
        # 1. Only allow ACCEPTED for ASSIGNMENT alerts
        if alert.alert_type != 'ASSIGNMENT':
            logger.warning(
                f"[ACCEPT] Cannot accept non-ASSIGNMENT alert {alert.id}",
                extra={'alert_id': alert.id, 'alert_type': alert.alert_type}
            )
            return
        
        # 2. Update alert status to ACCEPTED
        alert.status = GuardAlert.AlertStatus.ACCEPTED
        alert.save(update_fields=['status', 'updated_at'])
        
        # 3. Create assignment (enforce one-per-incident via unique constraint)
        try:
            assignment, created = GuardAssignment.objects.update_or_create(
                incident=alert.incident,
                defaults={'guard': alert.guard, 'is_active': True}
            )
        except Exception as e:
            logger.error(
                f"[ACCEPT] Failed to create assignment: {str(e)}",
                extra={'incident_id': str(alert.incident.id), 'guard_id': str(alert.guard.id)}
            )
            raise
        
        # 4. Link alert to assignment
        alert.assignment = assignment
        alert.save(update_fields=['assignment'])
        
        # 5. Update incident status
        incident = alert.incident
        if incident.status == Incident.Status.CREATED:
            incident.status = Incident.Status.ASSIGNED
            incident.save(update_fields=['status'])
            
            # Update buzzer status to ACTIVE (guard assigned)
            from incidents.services import update_buzzer_status_on_guard_assignment
            update_buzzer_status_on_guard_assignment(incident, alert.guard)
        
        # 6. Mark other ASSIGNMENT alerts as expired (guard is now assigned)
        GuardAlert.objects.filter(
            incident=incident,
            alert_type='ASSIGNMENT',
            status__in=[GuardAlert.AlertStatus.SENT]
        ).exclude(id=alert.id).update(status=GuardAlert.AlertStatus.EXPIRED)
        
        # 7. Send ASSIGNMENT_CONFIRMED notification to guard
        try:
            guard_user = alert.guard
            tokens = PushNotificationService.get_guard_tokens(guard_user)
            if tokens:
                PushNotificationService.notify_assignment_confirmed(
                    expo_tokens=tokens,
                    incident_id=str(incident.id)
                )
                logger.info(
                    f"[ASSIGNMENT_CONFIRMED] Notification sent to guard {guard_user.full_name}",
                    extra={'incident_id': str(incident.id), 'guard_id': str(guard_user.id)}
                )
        except Exception as e:
            logger.error(
                f"[ASSIGNMENT_CONFIRMED] Failed to send notification: {str(e)}",
                extra={'incident_id': str(incident.id), 'guard_id': str(alert.guard.id)}
            )
        
        logger.info(
            f"[ACCEPT] Guard {alert.guard.full_name} accepted incident {incident.id}",
            extra={'incident_id': str(incident.id), 'guard_id': str(alert.guard.id)}
        )


def handle_guard_alert_declined_via_proximity(alert):
    """
    Guard declined alert. Try next guard from beacon-proximity search.
    
    Does NOT restart search from beginning. Continues expanding radius.
    
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
        
        # 2. Get already-alerted/declined guard IDs
        alerted_guard_ids = list(
            GuardAlert.objects.filter(
                incident=alert.incident
            ).values_list('guard_id', flat=True)
        )
        
        # 3. Continue search for next available guard
        next_guards = find_available_guards_via_beacon_proximity(
            incident_beacon=alert.incident.beacon,
            max_guards=1,
            exclude_guard_ids=alerted_guard_ids
        )
        
        if next_guards:
            next_guard_user, next_beacon, next_priority = next_guards[0]
            
            # Create alert for next guard
            new_alert = GuardAlert.objects.create(
                incident=alert.incident,
                guard=next_guard_user,
                status=GuardAlert.AlertStatus.SENT,
                distance_km=0.0,
                priority_rank=(alert.priority_rank or 1) + 1
            )
            
            logger.info(
                f"[NEXT_GUARD] Alerted next guard {next_guard_user.full_name} for incident {alert.incident.id}",
                extra={
                    'incident_id': str(alert.incident.id),
                    'guard_id': str(next_guard_user.id),
                    'beacon_name': next_beacon.location_name
                }
            )
        else:
            # No more guards available
            logger.warning(
                f"[NO_GUARDS] All available guards exhausted/declined for incident {alert.incident.id}",
                extra={'incident_id': str(alert.incident.id)}
            )


def auto_escalate_expired_alerts():
    """
    Scheduled task: Auto-escalate ASSIGNMENT alerts that have exceeded response_deadline.
    
    Called by periodic task (e.g., every 10 seconds):
    - Find all SENT ASSIGNMENT alerts past response_deadline
    - Mark as EXPIRED
    - Auto-alert next available guard
    
    This prevents "silent failures" where guards don't respond.
    
    Returns:
        dict: {'escalated': count, 'failed': count}
    """
    from django.utils import timezone
    
    now = timezone.now()
    escalated_count = 0
    failed_count = 0
    
    # Find expired ASSIGNMENT alerts
    expired_alerts = GuardAlert.objects.filter(
        alert_type='ASSIGNMENT',
        status=GuardAlert.AlertStatus.SENT,
        response_deadline__isnull=False,
        response_deadline__lt=now
    ).select_related('incident', 'guard')
    
    logger.info(
        f"[AUTO-ESCALATE] Found {expired_alerts.count()} expired alerts for auto-escalation",
        extra={'count': expired_alerts.count()}
    )
    
    for alert in expired_alerts:
        try:
            # Mark alert as EXPIRED
            alert.status = GuardAlert.AlertStatus.EXPIRED
            alert.save(update_fields=['status', 'updated_at'])
            
            logger.info(
                f"[AUTO-ESCALATE] Alert {alert.id} expired. Searching for next guard.",
                extra={'incident_id': str(alert.incident.id), 'guard_id': str(alert.guard.id)}
            )
            
            # Try to find and alert next guard (same logic as decline)
            alerted_guard_ids = list(
                GuardAlert.objects.filter(
                    incident=alert.incident
                ).values_list('guard_id', flat=True)
            )
            
            next_guards = find_available_guards_via_beacon_proximity(
                incident_beacon=alert.incident.beacon,
                max_guards=1,
                exclude_guard_ids=alerted_guard_ids
            )
            
            if next_guards:
                next_guard_user, next_beacon, next_priority = next_guards[0]
                
                # Create alert for next guard with same deadline
                new_alert = GuardAlert.objects.create(
                    incident=alert.incident,
                    guard=next_guard_user,
                    status=GuardAlert.AlertStatus.SENT,
                    alert_type='ASSIGNMENT',
                    requires_response=True,
                    distance_km=0.0,
                    priority_rank=(alert.priority_rank or 1) + 1,
                    response_deadline=timezone.now() + timedelta(seconds=45)
                )
                
                logger.info(
                    f"[AUTO-ESCALATE] Auto-alerted guard {next_guard_user.full_name} for incident {alert.incident.id}",
                    extra={
                        'incident_id': str(alert.incident.id),
                        'guard_id': str(next_guard_user.id),
                        'trigger': 'response_timeout'
                    }
                )
                escalated_count += 1
            else:
                logger.warning(
                    f"[AUTO-ESCALATE] No guards available for incident {alert.incident.id}",
                    extra={'incident_id': str(alert.incident.id)}
                )
                failed_count += 1
        
        except Exception as e:
            logger.error(
                f"[AUTO-ESCALATE] Failed to escalate alert {alert.id}: {str(e)}",
                extra={'alert_id': alert.id}
            )
            failed_count += 1
    
    result = {'escalated': escalated_count, 'failed': failed_count}
    logger.info(
        f"[AUTO-ESCALATE] Complete - Escalated {escalated_count}, Failed {failed_count}",
        extra=result
    )
    
    return result
