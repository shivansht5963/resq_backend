import os
import sys
import django
import threading
import time
from concurrent.futures import ThreadPoolExecutor

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_security.settings')
django.setup()

from incidents.models import Beacon, Incident, IncidentSignal
from incidents.services import get_or_create_incident_with_signals, alert_guards_for_incident
from django.contrib.auth import get_user_model
from django.db import transaction, connection

User = get_user_model()

def create_test_data():
    """Create necessary test data."""
    # Create test beacon
    beacon, _ = Beacon.objects.get_or_create(
        beacon_id='race:test:beacon',
        defaults={
            'uuid': 'race:test:beacon',
            'location_name': 'Test Race Beacon',
            'is_active': True,
            'major': 9999,
            'minor': 9999,
            'floor': 1,
            'building': 'Test Building'
        }
    )
    
    # Create test student
    student, _ = User.objects.get_or_create(
        email='racetest@example.com',
        defaults={
            'full_name': 'Race Test Student',
            'role': User.Role.STUDENT,
            'is_active': True
        }
    )
    
    return beacon, student

def simulate_concurrent_requests():
    """Simulate concurrent incident creation requests."""
    beacon, student = create_test_data()
    
    # Clean up existing incidents for this beacon
    Incident.objects.filter(beacon=beacon).delete()
    
    print(f"Starting concurrency test for beacon {beacon.location_name}...")
    
    def worker(thread_id):
        try:
            # Simulate slight timing differences but overlapping transactions
            time.sleep(0.01 * thread_id) 
            
            print(f"Thread {thread_id}: Attempting to create incident...")
            incident, created, signal = get_or_create_incident_with_signals(
                beacon_id=beacon.beacon_id,
                signal_type=IncidentSignal.SignalType.STUDENT_SOS,
                source_user_id=student.id,
                description=f"Thread {thread_id} Report"
            )
            print(f"Thread {thread_id}: Success! Incident ID: {incident.id}, Created: {created}")
            return incident.id
        except Exception as e:
            print(f"Thread {thread_id}: Error: {e}")
            return None

    # Run 5 concurrent threads
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(worker, i) for i in range(5)]
        results = [f.result() for f in futures]
    
    # Verify results
    unique_incidents = set(r for r in results if r)
    incident_count = len(unique_incidents)
    
    print(f"\nTest Complete.")
    print(f"Unique incidents created: {incident_count}")
    print(f"Incident IDs: {unique_incidents}")
    
    if incident_count == 1:
        print("✅ SUCCESS: Only 1 unique incident was created despite concurrent requests.")
        
        # Verify signals
        incident_id = unique_incidents.pop()
        incident = Incident.objects.get(id=incident_id)
        signal_count = incident.signals.count()
        print(f"Signals attached to incident: {signal_count}")
        if signal_count >= 1:
             print(f"✅ SUCCESS: {signal_count} signals were captured and merged.")
             
    else:
        print(f"❌ FAILURE: {incident_count} duplicate incidents were created.")

if __name__ == '__main__':
    try:
        simulate_concurrent_requests()
    except Exception as e:
        print(f"Test failed with error: {e}")
