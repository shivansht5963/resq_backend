#!/usr/bin/env python
"""
Test script to send a push notification to a specific Expo token.
Usage: python test_push_notification.py
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_security.settings')
django.setup()

from accounts.push_notifications import PushNotificationService
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_push_notification():
    """Send a test push notification."""
    
    # Guard 3's token
    expo_token = "ExponentPushToken[fecDkbJn98xshVVVr2WFFE]"
    
    print("\n" + "="*70)
    print("🚀 PUSH NOTIFICATION TEST")
    print("="*70)
    print(f"Token: {expo_token}")
    print(f"Title: 🚨 Incoming Alert")
    print(f"Body: TEST - Library 3F - Main Hall")
    print("="*70 + "\n")
    
    # Send test notification
    success = PushNotificationService.send_notification(
        expo_token=expo_token,
        title="🚨 Incoming Alert",
        body="TEST - Library 3F - Main Hall",
        data={
            "type": "GUARD_ALERT",
            "incident_id": "test-incident-123",
            "alert_id": "999",
            "priority": "CRITICAL",
            "location": "Library 3F - Main Hall"
        },
        priority="high"
    )
    
    print("\n" + "="*70)
    if success:
        print("✅ PUSH NOTIFICATION SENT SUCCESSFULLY!")
        print("   Check your guard app on your phone 📱")
    else:
        print("❌ FAILED TO SEND PUSH NOTIFICATION")
        print("   Check logs above for details")
    print("="*70 + "\n")
    
    return success

def test_batch_push_notification():
    """Send batch test push notifications."""
    
    tokens = [
        "ExponentPushToken[fecDkbJn98xshVVVr2WFFE]",  # Guard 3
    ]
    
    print("\n" + "="*70)
    print("🚀 BATCH PUSH NOTIFICATION TEST")
    print("="*70)
    print(f"Tokens: {len(tokens)}")
    print("="*70 + "\n")
    
    messages = [
        {
            "to": token,
            "title": "🚨 Batch Test Alert",
            "body": "BATCH TEST - Library 4F",
            "data": {
                "type": "GUARD_ALERT",
                "incident_id": "test-batch-456",
                "alert_id": "888",
                "priority": "HIGH",
                "location": "Library 4F"
            },
            "priority": "high",
            "sound": "default"
        }
        for token in tokens
    ]
    
    results = PushNotificationService.send_batch_notifications(messages)
    
    print("\n" + "="*70)
    print(f"Results: {results}")
    if all(results):
        print("✅ ALL BATCH NOTIFICATIONS SENT SUCCESSFULLY!")
    else:
        print(f"⚠️  {sum(1 for r in results if r)}/{len(results)} notifications sent")
    print("="*70 + "\n")
    
    return results

def test_multiple_notification_types():
    """Test different notification types."""
    
    token = "ExponentPushToken[fecDkbJn98xshVVVr2WFFE]"
    
    print("\n" + "="*70)
    print("🚀 MULTIPLE NOTIFICATION TYPES TEST")
    print("="*70 + "\n")
    
    tests = [
        {
            "name": "GUARD_ALERT",
            "title": "🚨 Incoming Alert",
            "body": "CRITICAL - Hallway 4F",
            "data": {
                "type": "GUARD_ALERT",
                "incident_id": "test-alert-1",
                "alert_id": "1",
                "priority": "CRITICAL",
                "location": "Hallway 4F"
            }
        },
        {
            "name": "ASSIGNMENT_CONFIRMED",
            "title": "✅ Assignment Confirmed",
            "body": "You are assigned to an incident",
            "data": {
                "type": "ASSIGNMENT_CONFIRMED",
                "incident_id": "test-assign-2",
            }
        },
        {
            "name": "NEW_CHAT_MESSAGE",
            "title": "💬 New Message",
            "body": "Student: Help me please, I'm in the library",
            "data": {
                "type": "NEW_CHAT_MESSAGE",
                "incident_id": "test-chat-3",
                "conversation_id": "42",
                "sender": "John Doe (Student)"
            }
        },
        {
            "name": "INCIDENT_ESCALATED",
            "title": "⚠️ Incident Escalated",
            "body": "Priority raised to CRITICAL",
            "data": {
                "type": "INCIDENT_ESCALATED",
                "incident_id": "test-escalate-4",
                "new_priority": "CRITICAL"
            }
        }
    ]
    
    for idx, test in enumerate(tests, 1):
        print(f"{idx}. Testing {test['name']}...")
        success = PushNotificationService.send_notification(
            expo_token=token,
            title=test['title'],
            body=test['body'],
            data=test['data'],
            priority="high"
        )
        status = "✅" if success else "❌"
        print(f"   {status} {test['name']}\n")
    
    print("="*70 + "\n")

if __name__ == "__main__":
    import time
    
    print("\n🔧 CAMPUS SECURITY - PUSH NOTIFICATION TEST SUITE\n")
    
    # Test 1: Single notification
    print("[TEST 1/3] Single notification...")
    test_push_notification()
    time.sleep(2)
    
    # Test 2: Batch notifications
    print("[TEST 2/3] Batch notifications...")
    test_batch_push_notification()
    time.sleep(2)
    
    # Test 3: Multiple notification types
    print("[TEST 3/3] Multiple notification types...")
    test_multiple_notification_types()
    
    print("\n✅ All tests completed!")
    print("📱 Check your guard app on your phone for notifications\n")
