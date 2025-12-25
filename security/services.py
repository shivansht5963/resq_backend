"""
Guard assignment and location services.
Handles beacon-proximity-aware guard search and alert management.
"""
import logging
from django.db import transaction
from security.models import GuardProfile, GuardAssignment, GuardAlert
from incidents.models import Incident, BeaconProximity

logger = logging.getLogger(__name__)


def find_available_guards_via_beacon_proximity(incident_beacon, max_guards=3, exclude_guard_ids=None):
    """
    Expanding-radius beacon search: find available guards.
    
    Search order:
    1. Incident beacon itself
    2. Nearby beacons (by priority order from BeaconProximity)
    3. Continue expanding until max_guards found or all beacons exhausted
    
    Args:
        incident_beacon: Beacon instance where incident occurred
        max_guards: Max number of guards to return (default 3)
        exclude_guard_ids: List of guard user IDs to skip (already alerted or busy)
    
    Returns:
        list: [(guard_user, beacon, priority_level), ...] ordered by beacon search order
    
    Notes:
        - Guards must be is_active=True and is_available=True
        - Guards already assigned to another incident are skipped
        - Returns in beacon search order (not by guard availability)
    """
    
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
        
        for guard_profile in guard_profiles:
            # Check if guard is already assigned to another active incident
            existing_assignment = GuardAssignment.objects.filter(
                guard=guard_profile.user,
                is_active=True
            ).exists()
            
            if existing_assignment:
                logger.debug(
                    f"[SKIP] Guard {guard_profile.user.full_name} already assigned to another incident",
                    extra={'guard_id': str(guard_profile.user.id)}
                )
                continue
            
            found_guards.append((guard_profile.user, current_beacon, priority_level))
            
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
        f"[SEARCH] Found {len(found_guards)} guards for beacon {incident_beacon.location_name}",
        extra={
            'beacon_id': str(incident_beacon.id),
            'guards_found': len(found_guards),
            'max_guards': max_guards
        }
    )
    
    return found_guards[:max_guards]


def alert_guards_via_beacon_proximity(incident, max_guards=3):
    """
    Send alerts to available guards using beacon-proximity search.
    
    CRITICAL:
    - Only alerts if incident has NO active GuardAssignment
    - Creates alerts only once per (incident, guard) pair
    - Logs all operations for debugging
    
    Args:
        incident: Incident instance
        max_guards: Max number of guards to alert (default 3)
    
    Returns:
        list: GuardAlert instances created
    """
    
    # 1. Check if incident already has active assignment
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
    
    # 2. Get already-alerted guard IDs to avoid re-alerting
    already_alerted_guard_ids = list(
        GuardAlert.objects.filter(
            incident=incident,
            status__in=[GuardAlert.AlertStatus.SENT, GuardAlert.AlertStatus.ACKNOWLEDGED]
        ).values_list('guard_id', flat=True)
    )
    
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
    
    # 4. Create alerts for found guards
    created_alerts = []
    for rank, (guard_user, beacon, priority_level) in enumerate(available_guards, 1):
        try:
            alert = GuardAlert.objects.create(
                incident=incident,
                guard=guard_user,
                status=GuardAlert.AlertStatus.SENT,
                distance_km=0.0,  # Beacon-based, not GPS distance
                priority_rank=rank
            )
            created_alerts.append(alert)
            
            logger.info(
                f"[ALERT] Sent alert to guard {guard_user.full_name} for incident {incident.id} (rank #{rank})",
                extra={
                    'incident_id': str(incident.id),
                    'guard_id': str(guard_user.id),
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


def handle_guard_alert_acknowledged_via_proximity(alert):
    """
    Guard acknowledged alert via beacon-proximity search.
    Creates assignment and updates incident status.
    
    Args:
        alert: GuardAlert instance
    """
    
    with transaction.atomic():
        # 1. Update alert status
        alert.status = GuardAlert.AlertStatus.ACKNOWLEDGED
        alert.save(update_fields=['status', 'updated_at'])
        
        # 2. Create assignment (enforce one-per-incident via unique constraint)
        try:
            assignment, created = GuardAssignment.objects.update_or_create(
                incident=alert.incident,
                defaults={'guard': alert.guard, 'is_active': True}
            )
        except Exception as e:
            logger.error(
                f"[ASSIGNMENT] Failed to create assignment: {str(e)}",
                extra={'incident_id': str(alert.incident.id), 'guard_id': str(alert.guard.id)}
            )
            raise
        
        # 3. Link alert to assignment
        alert.assignment = assignment
        alert.save(update_fields=['assignment'])
        
        # 4. Update incident status
        incident = alert.incident
        if incident.status == Incident.Status.CREATED:
            incident.status = Incident.Status.ASSIGNED
            incident.save(update_fields=['status'])
        
        # 5. Mark other alerts as expired (guard is now assigned)
        GuardAlert.objects.filter(
            incident=incident,
            status__in=[GuardAlert.AlertStatus.SENT]
        ).exclude(id=alert.id).update(status=GuardAlert.AlertStatus.EXPIRED)
        
        logger.info(
            f"[ASSIGNMENT] Guard {alert.guard.full_name} assigned to incident {incident.id}",
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
