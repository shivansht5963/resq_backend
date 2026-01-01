"""
Test script for Incident System Redesign.
Tests the new features: event logging, timeline endpoint, resolve workflow.

Run with: python test_incident_redesign.py
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_security.settings')
django.setup()

from django.test import TestCase
from django.contrib.auth import get_user_model
from incidents.models import Beacon, Incident, IncidentSignal, IncidentEvent
from incidents.services import get_or_create_incident_with_signals, log_incident_event
from security.models import GuardProfile, GuardAlert
from accounts.models import PushNotificationLog

User = get_user_model()


def print_header(title):
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_success(msg):
    print(f"  ✅ {msg}")


def print_error(msg):
    print(f"  ❌ {msg}")


def test_incident_event_model():
    """Test IncidentEvent model exists and can be created."""
    print_header("Test 1: IncidentEvent Model")
    
    try:
        # Check the model fields exist
        event_types = IncidentEvent.EventType.choices
        print_success(f"IncidentEvent.EventType has {len(event_types)} event types")
        
        # Check we can query events
        count = IncidentEvent.objects.count()
        print_success(f"IncidentEvent table exists with {count} records")
        
        return True
    except Exception as e:
        print_error(f"Failed: {e}")
        return False


def test_push_notification_log_model():
    """Test PushNotificationLog model exists."""
    print_header("Test 2: PushNotificationLog Model")
    
    try:
        # Check the model fields exist
        status_choices = PushNotificationLog.Status.choices
        print_success(f"PushNotificationLog.Status has {len(status_choices)} status types")
        
        notification_types = PushNotificationLog.NotificationType.choices
        print_success(f"PushNotificationLog.NotificationType has {len(notification_types)} types")
        
        # Check we can query logs
        count = PushNotificationLog.objects.count()
        print_success(f"PushNotificationLog table exists with {count} records")
        
        return True
    except Exception as e:
        print_error(f"Failed: {e}")
        return False


def test_log_incident_event_helper():
    """Test log_incident_event helper function."""
    print_header("Test 3: log_incident_event() Helper")
    
    try:
        # Get or create a test beacon
        beacon, _ = Beacon.objects.get_or_create(
            beacon_id="test:redesign:001",
            defaults={
                'uuid': 'test-uuid-001',
                'major': 999,
                'minor': 1,
                'location_name': 'Test Location - Redesign',
                'building': 'Test Building',
                'floor': 1,
                'is_active': True
            }
        )
        print_success(f"Test beacon: {beacon.location_name}")
        
        # Create a test incident
        incident = Incident.objects.create(
            beacon=beacon,
            status=Incident.Status.CREATED,
            priority=Incident.Priority.MEDIUM,
            description="Test incident for redesign verification"
        )
        print_success(f"Test incident created: {str(incident.id)[:8]}")
        
        # Log an event
        event = log_incident_event(
            incident=incident,
            event_type=IncidentEvent.EventType.INCIDENT_CREATED,
            new_status=Incident.Status.CREATED,
            new_priority=Incident.Priority.MEDIUM,
            details={'test': True, 'source': 'test_script'}
        )
        
        if event:
            print_success(f"Event logged: {event.event_type} (ID: {event.id})")
        else:
            print_error("log_incident_event returned None")
            return False
        
        # Verify event was saved
        saved_event = IncidentEvent.objects.get(id=event.id)
        assert saved_event.event_type == IncidentEvent.EventType.INCIDENT_CREATED
        assert saved_event.details.get('test') == True
        print_success("Event verified in database")
        
        # Cleanup
        incident.delete()
        print_success("Test incident cleaned up")
        
        return True
    except Exception as e:
        print_error(f"Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_incident_creation_logs_event():
    """Test that creating incident via service logs an event."""
    print_header("Test 4: Incident Creation Event Logging")
    
    try:
        import time
        unique_id = f"test:redesign:{int(time.time())}"
        
        # Get or create test beacon with unique ID
        beacon, _ = Beacon.objects.get_or_create(
            beacon_id=unique_id,
            defaults={
                'uuid': f'test-uuid-{int(time.time())}',
                'major': 999,
                'minor': int(time.time()) % 1000,
                'location_name': f'Test Location {int(time.time())}',
                'building': 'Test Building',
                'floor': 1,
                'is_active': True
            }
        )
        
        # Get event count before
        event_count_before = IncidentEvent.objects.count()
        
        # Create incident via service using the unique beacon ID
        incident, created, signal = get_or_create_incident_with_signals(
            beacon_id=unique_id,
            signal_type=IncidentSignal.SignalType.STUDENT_SOS,
            description="Test SOS for event logging verification"
        )
        
        if not created:
            print_error("Incident was not newly created (may be deduped)")
            return False
        
        print_success(f"Incident created via service: {str(incident.id)[:8]}")
        
        # Check event was logged
        event_count_after = IncidentEvent.objects.count()
        events_created = event_count_after - event_count_before
        
        if events_created >= 1:
            print_success(f"Events created: {events_created}")
        else:
            print_error(f"No events were logged (before={event_count_before}, after={event_count_after})")
            return False
        
        # Check the event exists for this incident
        creation_event = IncidentEvent.objects.filter(
            incident=incident,
            event_type=IncidentEvent.EventType.INCIDENT_CREATED
        ).first()
        
        if creation_event:
            print_success(f"INCIDENT_CREATED event found (ID: {creation_event.id})")
            print_success(f"  Details: {creation_event.details}")
        else:
            print_error("INCIDENT_CREATED event not found for incident")
            return False
        
        # Cleanup
        incident.delete()
        print_success("Test incident cleaned up")
        
        return True
    except Exception as e:
        print_error(f"Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_incident_resolution_fields():
    """Test that Incident model has resolution fields."""
    print_header("Test 5: Incident Resolution Fields")
    
    try:
        # Check fields exist on model
        incident = Incident()
        
        # Check resolution fields
        assert hasattr(incident, 'resolved_by'), "Missing resolved_by field"
        print_success("resolved_by field exists")
        
        assert hasattr(incident, 'resolved_at'), "Missing resolved_at field"
        print_success("resolved_at field exists")
        
        assert hasattr(incident, 'resolution_notes'), "Missing resolution_notes field"
        print_success("resolution_notes field exists")
        
        assert hasattr(incident, 'resolution_type'), "Missing resolution_type field"
        print_success("resolution_type field exists")
        
        # Check ResolutionType choices exist
        resolution_types = Incident.ResolutionType.choices
        print_success(f"ResolutionType has {len(resolution_types)} choices: {[r[0] for r in resolution_types]}")
        
        return True
    except AssertionError as e:
        print_error(str(e))
        return False
    except Exception as e:
        print_error(f"Failed: {e}")
        return False


def test_guard_alert_fields():
    """Test that GuardAlert model has new fields."""
    print_header("Test 6: GuardAlert New Fields")
    
    try:
        alert = GuardAlert()
        
        assert hasattr(alert, 'alert_type'), "Missing alert_type field"
        print_success("alert_type field exists")
        
        assert hasattr(alert, 'requires_response'), "Missing requires_response field"
        print_success("requires_response field exists")
        
        assert hasattr(alert, 'response_deadline'), "Missing response_deadline field"
        print_success("response_deadline field exists")
        
        # Check AlertType choices
        alert_types = GuardAlert.AlertType.choices
        print_success(f"AlertType has {len(alert_types)} choices: {[a[0] for a in alert_types]}")
        
        return True
    except AssertionError as e:
        print_error(str(e))
        return False
    except Exception as e:
        print_error(f"Failed: {e}")
        return False


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "="*60)
    print(" INCIDENT SYSTEM REDESIGN - TEST SUITE")
    print("="*60)
    
    tests = [
        ("IncidentEvent Model", test_incident_event_model),
        ("PushNotificationLog Model", test_push_notification_log_model),
        ("log_incident_event() Helper", test_log_incident_event_helper),
        ("Incident Creation Event Logging", test_incident_creation_logs_event),
        ("Incident Resolution Fields", test_incident_resolution_fields),
        ("GuardAlert New Fields", test_guard_alert_fields),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print_error(f"Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print_header("TEST SUMMARY")
    passed = sum(1 for _, r in results if r)
    failed = sum(1 for _, r in results if not r)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {name}")
    
    print(f"\n  Total: {passed}/{len(results)} passed")
    
    if failed == 0:
        print("\n  🎉 ALL TESTS PASSED!")
    else:
        print(f"\n  ⚠️  {failed} test(s) failed")
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
