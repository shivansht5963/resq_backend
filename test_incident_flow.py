#!/usr/bin/env python
"""
Test script to simulate complete incident flow with push notifications.
Usage: python test_incident_flow.py
"""

import os
import sys
import django
from datetime import datetime

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_security.settings')
django.setup()

from django.contrib.auth import get_user_model
from incidents.models import Incident, Beacon
from security.models import GuardAlert, GuardProfile
from incidents.services import get_or_create_incident_with_signals, alert_guards_for_incident, send_push_notifications_for_alerts
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

User = get_user_model()

def setup_test_data():
    """Create test users and beacons if they don't exist."""
    
    print("\n" + "="*70)
    print("🔧 SETTING UP TEST DATA")
    print("="*70 + "\n")
    
    # Get or create student user
    student, created = User.objects.get_or_create(
        email="test_student@example.com",
        defaults={
            "username": "test_student",
            "full_name": "Test Student",
            "role": "STUDENT"
        }
    )
    if created:
        student.set_password("testpass123")
        student.save()
        print(f"✅ Created student: {student.email}")
    else:
        print(f"ℹ️  Student exists: {student.email}")
    
    # Get or create guard user
    guard, created = User.objects.get_or_create(
        email="gtest3@test.com",
        defaults={
            "username": "gtest3",
            "full_name": "Guard Sarah Smith",
            "role": "GUARD"
        }
    )
    if created:
        guard.set_password("testpass123")
        guard.save()
        print(f"✅ Created guard: {guard.email}")
    else:
        print(f"ℹ️  Guard exists: {guard.email}")
    
    # Create guard profile
    guard_profile, created = GuardProfile.objects.get_or_create(
        user=guard,
        defaults={
            "is_active": True,
            "is_available": True
        }
    )
    if created:
        print(f"✅ Created guard profile")
    else:
        print(f"ℹ️  Guard profile exists")
    
    # Get or create beacon
    beacon, created = Beacon.objects.get_or_create(
        beacon_id="safe:uuid:403:403",
        defaults={
            "uuid": "beacon-uuid-403",
            "major": 3,
            "minor": 403,
            "location_name": "Library 3F - Main Hall",
            "building": "Main Library",
            "floor": 3,
            "is_active": True
        }
    )
    if created:
        print(f"✅ Created beacon: {beacon.location_name}")
    else:
        print(f"ℹ️  Beacon exists: {beacon.location_name}")
    
    # Update guard location to be at the beacon
    guard_profile.current_beacon = beacon
    guard_profile.save()
    print(f"✅ Set guard location to: {beacon.location_name}")
    
    print("\n" + "="*70 + "\n")
    
    return student, guard, beacon, guard_profile

def test_incident_flow():
    """Test complete incident flow."""
    
    student, guard, beacon, guard_profile = setup_test_data()
    
    print("="*70)
    print("🚀 TESTING COMPLETE INCIDENT FLOW")
    print("="*70 + "\n")
    
    # Step 1: Create incident
    print("[STEP 1] Creating incident...")
    try:
        incident, created, signal = get_or_create_incident_with_signals(
            beacon_id=beacon.beacon_id,
            signal_type="STUDENT_SOS",
            source_user_id=student.id,
            description="Test emergency - I need help!"
        )
        print(f"✅ Incident created: {incident.id}")
        print(f"   Status: {incident.status}")
        print(f"   Priority: {incident.priority}")
        print(f"   Beacon: {incident.beacon.location_name}\n")
    except Exception as e:
        logger.error(f"❌ Failed to create incident: {e}", exc_info=True)
        return False
    
    # Step 2: Create alerts
    print("[STEP 2] Creating guard alerts...")
    try:
        alerts = alert_guards_for_incident(incident, max_guards=3)
        print(f"✅ Created {len(alerts)} alerts")
        for alert in alerts:
            print(f"   - Alert {alert.id} sent to {alert.guard.full_name}")
            print(f"     Status: {alert.status}")
            print(f"     Type: {alert.alert_type}")
        print()
    except Exception as e:
        logger.error(f"❌ Failed to create alerts: {e}", exc_info=True)
        return False
    
    # Step 3: Send push notifications
    print("[STEP 3] Sending push notifications...")
    try:
        send_push_notifications_for_alerts(incident, alerts)
        print(f"✅ Push notifications sent to all guards\n")
    except Exception as e:
        logger.error(f"❌ Failed to send push notifications: {e}", exc_info=True)
        return False
    
    # Step 4: Display incident details
    print("[STEP 4] Incident Details:")
    print(f"   ID: {incident.id}")
    print(f"   Beacon: {incident.beacon.location_name}")
    print(f"   Status: {incident.status}")
    print(f"   Priority: {incident.priority}")
    print(f"   Description: {incident.description}")
    print(f"   Created: {incident.created_at}\n")
    
    # Step 5: Display alert details
    print("[STEP 5] Alert Details:")
    for idx, alert in enumerate(alerts, 1):
        print(f"   Alert {idx}:")
        print(f"      ID: {alert.id}")
        print(f"      Guard: {alert.guard.full_name}")
        print(f"      Status: {alert.status}")
        print(f"      Type: {alert.alert_type}")
        print(f"      Deadline: {alert.response_deadline}")
    print()
    
    print("="*70)
    print("✅ INCIDENT FLOW TEST COMPLETED!")
    print("   Check your guard app on your phone for alert notification 📱")
    print("="*70 + "\n")
    
    return True

def test_direct_push():
    """Test direct push to guard 3 token."""
    
    from accounts.push_notifications import PushNotificationService
    
    print("\n" + "="*70)
    print("🚀 DIRECT PUSH TEST TO GUARD 3")
    print("="*70 + "\n")
    
    token = "ExponentPushToken[fecDkbJn98xshVVVr2WFFE]"
    
    print(f"Token: {token}")
    print(f"Title: 🚨 Test Alert - Guard 3")
    print(f"Body: This is a test push notification\n")
    
    success = PushNotificationService.send_notification(
        expo_token=token,
        title="🚨 Test Alert - Guard 3",
        body="This is a test push notification from Django backend",
        data={
            "type": "GUARD_ALERT",
            "incident_id": "test-direct",
            "alert_id": "0",
            "priority": "TEST",
            "location": "Test Location"
        },
        priority="high"
    )
    
    print("="*70)
    if success:
        print("✅ PUSH SENT SUCCESSFULLY!")
    else:
        print("❌ PUSH FAILED - Check logs above")
    print("="*70 + "\n")
    
    return success

if __name__ == "__main__":
    print("\n")
    print("█" * 70)
    print("█ CAMPUS SECURITY - INCIDENT FLOW & PUSH NOTIFICATION TEST")
    print("█" * 70)
    
    # Test 1: Direct push
    print("\n[TEST 1/2] Direct push notification to Guard 3 token...")
    test_direct_push()
    
    # Test 2: Full incident flow
    print("[TEST 2/2] Full incident creation and alert flow...")
    test_incident_flow()
    
    print("\n📱 NEXT STEPS:")
    print("   1. Check your guard app phone for notifications")
    print("   2. If you see notifications, push system is working ✅")
    print("   3. If not, check Django logs for errors\n")
