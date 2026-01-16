from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Count
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models.functions import TruncDate
from datetime import timedelta
import json


from django.db import transaction
from django.db.models import F

from incidents.models import Incident, IncidentEvent, Beacon, BeaconProximity
from security.models import GuardAlert, GuardAssignment, GuardProfile

try:
    from google.auth.exceptions import DefaultCredentialsError
except Exception:
    class DefaultCredentialsError(Exception):
        pass

from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden
from functools import wraps


def read_only(view_func):

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if getattr(settings, 'ADMINEND_VIEW_ONLY', True) and request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
 
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('Accept','').startswith('application/json'):
                return JsonResponse({'error': 'AdminEnd is view-only; write operations are disabled.'}, status=403)
            else:
                from django.contrib import messages
                messages.error(request, 'Admin panel is currently view-only; write operations are disabled.')
                return HttpResponseForbidden('AdminEnd is view-only.')
        return view_func(request, *args, **kwargs)
    return _wrapped


def admin_required(view_func):
    """Decorator: allow only logged-in ADMIN users."""
    return user_passes_test(lambda u: u.is_authenticated and getattr(u, 'role', None) == 'ADMIN', login_url='home')(view_func)


@admin_required
def dashboard(request):
    """Show summary KPIs, recent incidents and simple charts."""
    incidents_total = Incident.objects.all().count()
    incidents_open = Incident.objects.exclude(status=Incident.Status.RESOLVED).count()
    incidents_by_status_qs = Incident.objects.values('status').annotate(count=Count('id'))
    incidents_by_status = {item['status']: item['count'] for item in incidents_by_status_qs}

    active_alerts = GuardAlert.objects.filter(status=GuardAlert.AlertStatus.SENT).count()
    active_assignments = GuardAssignment.objects.filter(is_active=True).count()
    guards_on_duty = GuardProfile.objects.filter(is_active=True).count()
    recent_incidents = Incident.objects.order_by('-created_at')[:5]

    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=6)
    daily_qs = Incident.objects.filter(created_at__date__gte=start_date).annotate(date=TruncDate('created_at')).values('date').annotate(count=Count('id')).order_by('date')

    counts_by_day = {}
    for i in range(7):
        d = (start_date + timedelta(days=i))
        counts_by_day[d.isoformat()] = 0
    for item in daily_qs:
        counts_by_day[item['date'].isoformat()] = item['count']

   
    chart_labels = list(counts_by_day.keys())
    chart_data = list(counts_by_day.values())

    context = {
        'incidents_total': incidents_total,
        'incidents_open': incidents_open,
        'incidents_by_status': incidents_by_status,
        'active_alerts': active_alerts,
        'active_assignments': active_assignments,
        'guards_on_duty': guards_on_duty,
        'recent_incidents': recent_incidents,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
        'status_counts_json': json.dumps(incidents_by_status),
    }
    return render(request, 'adminEnd/dashboard.html', context)


@admin_required
def incident_list(request):
    """List incidents with basic filtering, search and pagination."""
    qs = Incident.objects.select_related('beacon').order_by('-created_at')

    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status')
    priority_filter = request.GET.get('priority')

    if q:
        qs = qs.filter(beacon__location_name__icontains=q) | qs.filter(id__icontains=q)
    if status_filter:
        qs = qs.filter(status=status_filter)
    if priority_filter:
        qs = qs.filter(priority=priority_filter)

    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'adminEnd/incidents_list.html', {'page_obj': page_obj, 'q': q, 'status_filter': status_filter, 'priority_filter': priority_filter})


@admin_required
@read_only
def incident_detail(request, incident_id):
    """Show incident detail and allow admin resolution, assign/unassign guards."""
    incident = get_object_or_404(Incident, id=incident_id)

    from django.contrib.auth import get_user_model
    from django.db import IntegrityError, transaction
    User = get_user_model()

    if request.method == 'POST':
        # Handle resolve action
        if 'resolve' in request.POST:
            resolution_notes = request.POST.get('resolution_notes', '').strip()
            resolution_type = request.POST.get('resolution_type', Incident.ResolutionType.RESOLVED_BY_GUARD)

            if not resolution_notes:
                messages.error(request, 'Resolution notes are required to resolve an incident.')
            else:
                from incidents.services import validate_status_transition, log_incident_event
                from security.models import GuardAssignment
                from django.utils import timezone

                if not validate_status_transition(incident.status, Incident.Status.RESOLVED):
                    messages.error(request, f'Cannot resolve incident in {incident.status} status')
                else:
                    previous_status = incident.status
                    incident.status = Incident.Status.RESOLVED
                    incident.resolved_by = request.user
                    incident.resolved_at = timezone.now()
                    incident.resolution_notes = resolution_notes
                    incident.resolution_type = resolution_type
                    incident.save()

                    # Deactivate any active assignment
                    GuardAssignment.objects.filter(incident=incident, is_active=True).update(is_active=False)

                    log_incident_event(
                        incident=incident,
                        event_type=Incident.EventType.INCIDENT_RESOLVED if hasattr(Incident, 'EventType') else 'INCIDENT_RESOLVED',
                        actor=request.user,
                        previous_status=previous_status,
                        new_status=Incident.Status.RESOLVED,
                        details={'resolution_type': resolution_type, 'resolution_notes': resolution_notes[:200]}
                    )

                    messages.success(request, 'Incident marked as RESOLVED')
                    return redirect('adminEnd:incident_detail', incident_id=incident.id)

        # Handle assign action
        if 'assign' in request.POST:
            guard_id = request.POST.get('guard_id')
            if not guard_id:
                messages.error(request, 'Please select a guard to assign')
            else:
                try:
                    guard_user = User.objects.get(id=guard_id, role=User.Role.GUARD)
                except User.DoesNotExist:
                    messages.error(request, 'Selected guard not found or not a guard')
                else:
                    try:
                        with transaction.atomic():
                            prev_status = incident.status
                            assignment = GuardAssignment.objects.create(incident=incident, guard=guard_user)
                            incident.current_assigned_guard = guard_user
                            incident.assigned_at = timezone.now()
                            incident.status = Incident.Status.ASSIGNED
                            incident.save(update_fields=['current_assigned_guard', 'assigned_at', 'status'])

                            from incidents.services import log_incident_event
                            log_incident_event(
                                incident=incident,
                                event_type=IncidentEvent.EventType.GUARD_ASSIGNED,
                                actor=request.user,
                                target_guard=guard_user,
                                previous_status=prev_status,
                                new_status=Incident.Status.ASSIGNED,
                                details={'assignment_id': assignment.id}
                            )

                            messages.success(request, f'Guard {guard_user.full_name} assigned to incident')
                            return redirect('adminEnd:incident_detail', incident_id=incident.id)
                    except IntegrityError:
                        messages.error(request, 'Could not assign guard — guard may already have an active assignment or incident already assigned')

        # Handle unassign action
        if 'unassign' in request.POST:
            active_assign = GuardAssignment.objects.filter(incident=incident, is_active=True).first()
            if not active_assign:
                messages.error(request, 'No active assignment to unassign')
            else:
                active_assign.is_active = False
                active_assign.save()

                incident.current_assigned_guard = None
                incident.assigned_at = None
                incident.status = Incident.Status.CREATED
                incident.save(update_fields=['current_assigned_guard', 'assigned_at', 'status'])

                from incidents.services import log_incident_event
                log_incident_event(
                    incident=incident,
                    event_type=IncidentEvent.EventType.GUARD_UNASSIGNED if hasattr(IncidentEvent, 'EventType') else 'GUARD_UNASSIGNED',
                    actor=request.user,
                    details={'assignment_id': active_assign.id}
                )

                messages.success(request, 'Assignment removed')
                return redirect('adminEnd:incident_detail', incident_id=incident.id)

    # Gather related objects
    images_qs = incident.images.all()

    # Resolve image URLs safely — accessing `.image.url` can trigger GCS auth.
    images_info = []
    gcs_credentials_missing = False
    for img in images_qs:
        try:
            url = img.image.url
        except DefaultCredentialsError:
            url = None
            gcs_credentials_missing = True
        except Exception:
            # Some other storage-related error — treat as unavailable
            url = None
        images_info.append({'url': url, 'description': img.description})

    signals = incident.signals.all().order_by('-created_at')[:20]
    events = incident.events.all().order_by('-created_at')[:50]

    # Available guards for assignment
    available_guards = User.objects.filter(role=User.Role.GUARD, guard_profile__is_active=True, guard_profile__is_available=True)

    context = {
        'incident': incident,
        'images_info': images_info,
        'gcs_credentials_missing': gcs_credentials_missing,
        'signals': signals,
        'events': events,
        'available_guards': available_guards,
        'adminend_view_only': settings.ADMINEND_VIEW_ONLY,
    }
    return render(request, 'adminEnd/incident_detail.html', context)


@admin_required
def beacon_list(request):
    from .forms import BeaconForm
    qs = Beacon.objects.order_by('building', 'floor', 'location_name')
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(location_name__icontains=q) | qs.filter(beacon_id__icontains=q)

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'adminEnd/beacons_list.html', {'page_obj': page_obj, 'q': q, 'adminend_view_only': settings.ADMINEND_VIEW_ONLY})


@admin_required
@read_only
def beacon_create(request):
    from .forms import BeaconForm
    if request.method == 'POST':
        form = BeaconForm(request.POST)
        if form.is_valid():
            beacon = form.save()
            messages.success(request, 'Beacon created')
            return redirect('adminEnd:beacon_detail', beacon_id=beacon.id)
    else:
        form = BeaconForm()
    return render(request, 'adminEnd/beacon_form.html', {'form': form, 'creating': True, 'adminend_view_only': settings.ADMINEND_VIEW_ONLY})


@admin_required
@read_only
def beacon_detail(request, beacon_id):
    from .forms import BeaconForm
    beacon = get_object_or_404(Beacon, id=beacon_id)
    if request.method == 'POST':
        from django.db.models import F
        from django.db import transaction

        if 'toggle_active' in request.POST:
            beacon.is_active = not beacon.is_active
            beacon.save(update_fields=['is_active'])
            messages.success(request, f'Beacon active set to {beacon.is_active}')
            return redirect('adminEnd:beacon_detail', beacon_id=beacon.id)

        # Handle add proximity with shifting
        if 'add_proximity' in request.POST:
            from .forms import BeaconProximityForm
            formp = BeaconProximityForm(request.POST, from_beacon=beacon)
            if formp.is_valid():
                to_beacon = formp.cleaned_data['to_beacon']
                priority = formp.cleaned_data['priority']
                # Prevent self reference explicitly
                if to_beacon.id == beacon.id:
                    formp.add_error('to_beacon', 'Cannot point proximity to the same beacon')
                elif BeaconProximity.objects.filter(from_beacon=beacon, to_beacon=to_beacon).exists():
                    formp.add_error(None, 'Proximity relation already exists')
                else:
                    try:
                        with transaction.atomic():
                            # Shift existing priorities >= priority up by 1
                            BeaconProximity.objects.filter(from_beacon=beacon, priority__gte=priority).update(priority=F('priority') + 1)
                            prox = BeaconProximity.objects.create(from_beacon=beacon, to_beacon=to_beacon, priority=priority)
                        messages.success(request, 'Proximity relation added')
                        return redirect('adminEnd:beacon_detail', beacon_id=beacon.id)
                    except Exception as e:
                        messages.error(request, f'Could not add proximity: {e}')
            # fall through to render form with errors
            form = BeaconForm(instance=beacon)
            proximities = BeaconProximity.objects.filter(from_beacon=beacon).select_related('to_beacon').order_by('priority')
            return render(request, 'adminEnd/beacon_form.html', {'form': form, 'beacon': beacon, 'proximity_form': formp, 'proximities': proximities})

        # Handle edit proximity priority with reordering
        if 'edit_proximity' in request.POST:
            prox_id = request.POST.get('proximity_id')
            new_prio = request.POST.get('priority')
            try:
                prox = BeaconProximity.objects.get(id=prox_id, from_beacon=beacon)
                new_prio_int = int(new_prio)
                if new_prio_int < 1:
                    raise ValueError('Priority must be >= 1')

                old_prio = prox.priority
                if new_prio_int == old_prio:
                    messages.info(request, 'No change in priority')
                    return redirect('adminEnd:beacon_detail', beacon_id=beacon.id)

                with transaction.atomic():
                    if new_prio_int < old_prio:
                        # Shift items in [new_prio, old_prio-1] up by 1
                        BeaconProximity.objects.filter(from_beacon=beacon, priority__gte=new_prio_int, priority__lt=old_prio).update(priority=F('priority') + 1)
                    else:
                        # Shift items in (old_prio, new_prio] down by 1
                        BeaconProximity.objects.filter(from_beacon=beacon, priority__gt=old_prio, priority__lte=new_prio_int).update(priority=F('priority') - 1)
                    prox.priority = new_prio_int
                    prox.save()
                messages.success(request, 'Proximity updated')
                return redirect('adminEnd:beacon_detail', beacon_id=beacon.id)
            except Exception as e:
                messages.error(request, f'Could not update proximity: {e}')

        # Handle move up/down actions
        if 'move_up' in request.POST or 'move_down' in request.POST:
            prox_id = request.POST.get('proximity_id')
            direction = 'up' if 'move_up' in request.POST else 'down'
            try:
                with transaction.atomic():
                    prox = BeaconProximity.objects.select_for_update().get(id=prox_id, from_beacon=beacon)
                    if direction == 'up' and prox.priority > 1:
                        target_prio = prox.priority - 1
                        other = BeaconProximity.objects.select_for_update().filter(from_beacon=beacon, priority=target_prio).first()
                        if other:
                            # swap priorities
                            other.priority = -1
                            other.save()
                            prox.priority = target_prio
                            prox.save()
                            other.priority = target_prio + 1
                            other.save()
                        else:
                            prox.priority = target_prio
                            prox.save()
                    elif direction == 'down':
                        target_prio = prox.priority + 1
                        other = BeaconProximity.objects.select_for_update().filter(from_beacon=beacon, priority=target_prio).first()
                        if other:
                            other.priority = -1
                            other.save()
                            prox.priority = target_prio
                            prox.save()
                            other.priority = target_prio - 1
                            other.save()
                        else:
                            prox.priority = target_prio
                            prox.save()
                messages.success(request, 'Proximity moved')
                return redirect('adminEnd:beacon_detail', beacon_id=beacon.id)
            except Exception as e:
                messages.error(request, f'Could not move proximity: {e}')

        # Handle delete proximity and collapse priorities
        if 'delete_proximity' in request.POST:
            prox_id = request.POST.get('proximity_id')
            try:
                with transaction.atomic():
                    prox = BeaconProximity.objects.get(id=prox_id, from_beacon=beacon)
                    old_prio = prox.priority
                    prox.delete()
                    # Collapse larger priorities down by 1
                    BeaconProximity.objects.filter(from_beacon=beacon, priority__gt=old_prio).update(priority=F('priority') - 1)
                messages.success(request, 'Proximity removed')
                return redirect('adminEnd:beacon_detail', beacon_id=beacon.id)
            except BeaconProximity.DoesNotExist:
                messages.error(request, 'Proximity not found')

        form = BeaconForm(request.POST, instance=beacon)
        if form.is_valid():
            form.save()
            messages.success(request, 'Beacon updated')
            return redirect('adminEnd:beacon_detail', beacon_id=beacon.id)
    else:
        form = BeaconForm(instance=beacon)

    proximities = BeaconProximity.objects.filter(from_beacon=beacon).select_related('to_beacon').order_by('priority')
    proximity_form = __import__('adminEnd.forms', fromlist=['BeaconProximityForm']).BeaconProximityForm(from_beacon=beacon)

    return render(request, 'adminEnd/beacon_form.html', {'form': form, 'beacon': beacon, 'proximity_form': proximity_form, 'proximities': proximities, 'adminend_view_only': settings.ADMINEND_VIEW_ONLY})


@admin_required
@read_only
def ajax_move_proximity(request, beacon_id, prox_id):

    from django.http import JsonResponse
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    beacon = get_object_or_404(Beacon, id=beacon_id)
    direction = request.POST.get('direction')

    try:
        with transaction.atomic():
            prox = BeaconProximity.objects.select_for_update().get(id=prox_id, from_beacon=beacon)
            if direction == 'up' and prox.priority > 1:
                target_prio = prox.priority - 1
                other = BeaconProximity.objects.select_for_update().filter(from_beacon=beacon, priority=target_prio).first()
                if other:
                    other.priority = -1
                    other.save()
                    prox.priority = target_prio
                    prox.save()
                    other.priority = target_prio + 1
                    other.save()
                else:
                    prox.priority = target_prio
                    prox.save()
            elif direction == 'down':
                target_prio = prox.priority + 1
                other = BeaconProximity.objects.select_for_update().filter(from_beacon=beacon, priority=target_prio).first()
                if other:
                    other.priority = -1
                    other.save()
                    prox.priority = target_prio
                    prox.save()
                    other.priority = target_prio - 1
                    other.save()
                else:
                    prox.priority = target_prio
                    prox.save()
            else:
                return JsonResponse({'error': 'Invalid direction or no-op'}, status=400)
    except BeaconProximity.DoesNotExist:
        return JsonResponse({'error': 'Proximity not found'}, status=404)

    # Return updated list
    proximities = list(BeaconProximity.objects.filter(from_beacon=beacon).order_by('priority').values('id', 'to_beacon_id', 'priority'))
    return JsonResponse({'success': True, 'proximities': proximities})


@admin_required
@read_only
def ajax_update_proximity_priority(request, beacon_id, prox_id):
    
    from django.http import JsonResponse
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    beacon = get_object_or_404(Beacon, id=beacon_id)
    new_prio = request.POST.get('priority')
    try:
        new_prio_int = int(new_prio)
        if new_prio_int < 1:
            return JsonResponse({'error': 'Priority must be >= 1'}, status=400)
    except Exception:
        return JsonResponse({'error': 'Invalid priority'}, status=400)

    try:
        with transaction.atomic():
            prox = BeaconProximity.objects.select_for_update().get(id=prox_id, from_beacon=beacon)
            old_prio = prox.priority
            if new_prio_int == old_prio:
                pass
            else:
                if new_prio_int < old_prio:
                    BeaconProximity.objects.filter(from_beacon=beacon, priority__gte=new_prio_int, priority__lt=old_prio).update(priority=F('priority') + 1)
                else:
                    BeaconProximity.objects.filter(from_beacon=beacon, priority__gt=old_prio, priority__lte=new_prio_int).update(priority=F('priority') - 1)
                prox.priority = new_prio_int
                prox.save()
    except BeaconProximity.DoesNotExist:
        return JsonResponse({'error': 'Proximity not found'}, status=404)

    proximities = list(BeaconProximity.objects.filter(from_beacon=beacon).order_by('priority').values('id', 'to_beacon_id', 'priority'))
    return JsonResponse({'success': True, 'proximities': proximities})


@admin_required
@read_only
def ajax_delete_proximity(request, beacon_id, prox_id):
    """AJAX: delete proximity and collapse priorities."""
    from django.http import JsonResponse
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    beacon = get_object_or_404(Beacon, id=beacon_id)
    try:
        with transaction.atomic():
            prox = BeaconProximity.objects.get(id=prox_id, from_beacon=beacon)
            old_prio = prox.priority
            prox.delete()
            BeaconProximity.objects.filter(from_beacon=beacon, priority__gt=old_prio).update(priority=F('priority') - 1)
    except BeaconProximity.DoesNotExist:
        return JsonResponse({'error': 'Proximity not found'}, status=404)

    proximities = list(BeaconProximity.objects.filter(from_beacon=beacon).order_by('priority').values('id', 'to_beacon_id', 'priority'))
    return JsonResponse({'success': True, 'proximities': proximities})


@admin_required
def guard_list(request):
    User = __import__('django.contrib.auth', fromlist=['get_user_model']).get_user_model()
    guards = User.objects.filter(role=User.Role.GUARD).select_related('guard_profile').order_by('-id')
    return render(request, 'adminEnd/guards_list.html', {'guards': guards, 'adminend_view_only': settings.ADMINEND_VIEW_ONLY})


@admin_required
@read_only
def toggle_guard_availability(request, user_id):
    User = __import__('django.contrib.auth', fromlist=['get_user_model']).get_user_model()
    user = get_object_or_404(User, id=user_id, role=User.Role.GUARD)
    try:
        profile = user.guard_profile
    except Exception:
        messages.error(request, 'Guard profile not found')
        return redirect('adminEnd:guard_list')

    profile.is_available = not profile.is_available
    profile.save(update_fields=['is_available'])
    messages.success(request, f"Guard availability set to {profile.is_available}")
    return redirect('adminEnd:guard_list')
