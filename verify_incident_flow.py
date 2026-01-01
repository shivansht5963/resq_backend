#!/usr/bin/env python
"""
Incident Tracking Verification Script
Checks if alert system is working properly
"""

# Run: python verify_incident_flow.py

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_security.settings')
django.setup()

from incidents.models import Incident, IncidentSignal
from security.models import GuardAlert, GuardAssignment
from accounts.models import User, Device
from django.utils import timezone
from datetime import timedelta

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def check_incidents():
    """Check incident creation and tracking"""
    print_section("1. INCIDENT VERIFICATION")
    
    incidents = Incident.objects.all().order_by('-created_at')[:5]
    
    if not incidents:
        print("❌ NO INCIDENTS FOUND")
        return False
    
    for incident in incidents:
        print(f"✓ Incident: {str(incident.id)[:8]}")
        print(f"  Status: {incident.status}")
        print(f"  Priority: {incident.priority}")
        print(f"  Location: {incident.location}")
        print(f"  Created: {incident.created_at}")
        print(f"  Signals: {incident.signals.count()}")
        print()
    
    return True

def check_alerts():
    """Check guard alerts creation"""
    print_section("2. GUARD ALERT VERIFICATION")
    
    alerts = GuardAlert.objects.all().order_by('-alert_sent_at')[:10]
    
    if not alerts:
        print("❌ NO ALERTS FOUND")
        return False
    
    for alert in alerts:
        print(f"✓ Alert #{alert.id}")
        print(f"  Incident: {str(alert.incident.id)[:8]} - {alert.incident.location}")
        print(f"  Guard: {alert.guard.full_name} ({alert.guard.email})")
        print(f"  Type: {alert.alert_type}")
        print(f"  Status: {alert.status}")
        print(f"  Distance: {alert.distance_km} km")
        print(f"  Sent: {alert.alert_sent_at}")
        
        if alert.response_deadline:
            time_left = alert.response_deadline - timezone.now()
            print(f"  Response Deadline: {time_left.total_seconds():.0f}s left")
        print()
    
    return True

def check_assignments():
    """Check guard assignments"""
    print_section("3. GUARD ASSIGNMENT VERIFICATION")
    
    assignments = GuardAssignment.objects.filter(is_active=True).order_by('-created_at')[:5]
    
    if not assignments:
        print("⚠️  NO ACTIVE ASSIGNMENTS (This is ok if no alerts accepted yet)")
        return True
    
    for assignment in assignments:
        print(f"✓ Assignment #{assignment.id}")
        print(f"  Incident: {str(assignment.incident.id)[:8]} - {assignment.incident.location}")
        print(f"  Guard: {assignment.guard.full_name}")
        print(f"  Status: {'ACTIVE' if assignment.is_active else 'INACTIVE'}")
        print(f"  Created: {assignment.created_at}")
        print()
    
    return True

def check_device_tokens():
    """Check registered device tokens for guards"""
    print_section("4. DEVICE TOKEN VERIFICATION")
    
    guards = User.objects.filter(role='GUARD', is_active=True)[:5]
    
    if not guards:
        print("⚠️  NO GUARD USERS FOUND")
        return False
    
    found_tokens = False
    for guard in guards:
        devices = Device.objects.filter(user=guard, is_active=True)
        
        if devices:
            found_tokens = True
            print(f"✓ Guard: {guard.full_name}")
            for device in devices:
                token_preview = device.token[:30] + "..." if len(device.token) > 30 else device.token
                print(f"  Token: {token_preview}")
                print(f"  Platform: {device.platform}")
                print(f"  Active: {device.is_active}")
        else:
            print(f"❌ Guard {guard.full_name}: NO DEVICE TOKENS REGISTERED")
    
    if not found_tokens:
        print("\n⚠️  WARNING: No device tokens found for any guards!")
        print("   → Guards won't receive push notifications!")
        print("   → Need to register device tokens via: POST /api/device-tokens/")
    
    print()
    return True

def check_signals():
    """Check incident signals (deduplication)"""
    print_section("5. INCIDENT SIGNAL VERIFICATION")
    
    signals = IncidentSignal.objects.all().order_by('-created_at')[:10]
    
    if not signals:
        print("❌ NO SIGNALS FOUND")
        return False
    
    for signal in signals:
        print(f"✓ Signal #{signal.id}")
        print(f"  Type: {signal.signal_type}")
        print(f"  Incident: {str(signal.incident.id)[:8]} - {signal.incident.location}")
        print(f"  Source: {signal.source_user.full_name if signal.source_user else signal.source_device}")
        print(f"  Created: {signal.created_at}")
        print()
    
    return True

def check_flow_timeline():
    """Show recent activity timeline"""
    print_section("6. RECENT ACTIVITY TIMELINE")
    
    print("Recent incidents (last 10 minutes):\n")
    cutoff = timezone.now() - timedelta(minutes=10)
    recent_incidents = Incident.objects.filter(created_at__gte=cutoff).order_by('-created_at')
    
    if not recent_incidents:
        print("No recent activity in last 10 minutes")
        return True
    
    for incident in recent_incidents:
        elapsed = (timezone.now() - incident.created_at).total_seconds()
        print(f"[{elapsed:.0f}s ago] Incident {str(incident.id)[:8]}")
        print(f"  Location: {incident.location}")
        print(f"  Status: {incident.status}")
        print(f"  Alerts: {incident.guard_alerts.count()}")
        
        # Show alerts for this incident
        for alert in incident.guard_alerts.all():
            print(f"    ├─ Guard {alert.guard.full_name}: {alert.status}")
        
        # Show assignment
        try:
            assignment = incident.guard_assignments.get(is_active=True)
            print(f"  ✓ Assigned to: {assignment.guard.full_name}")
        except:
            pass
        
        print()
    
    return True

def diagnose_push_issues():
    """Diagnose push notification problems"""
    print_section("7. PUSH NOTIFICATION DIAGNOSTICS")
    
    print("Checking for push-related issues:\n")
    
    # Check 1: Device tokens exist
    token_count = Device.objects.filter(is_active=True).count()
    print(f"[{'✓' if token_count > 0 else '❌'}] Active device tokens: {token_count}")
    if token_count == 0:
        print("    → No device tokens registered. Guards can't receive push!")
    
    # Check 2: Guard users exist
    guard_count = User.objects.filter(role='GUARD', is_active=True).count()
    print(f"[{'✓' if guard_count > 0 else '❌'}] Active guards: {guard_count}")
    
    # Check 3: Alerts created
    alert_count = GuardAlert.objects.count()
    print(f"[{'✓' if alert_count > 0 else '❌'}] Total alerts created: {alert_count}")
    
    # Check 4: Recent alerts
    recent_alerts = GuardAlert.objects.filter(
        alert_sent_at__gte=timezone.now() - timedelta(hours=1)
    ).count()
    print(f"[{'✓' if recent_alerts > 0 else '⚠️'}] Alerts in last hour: {recent_alerts}")
    
    # Check 5: Token format
    print("\n[Token Format Validation]")
    invalid_tokens = Device.objects.exclude(token__startswith='ExponentPushToken').count()
    print(f"[{'✓' if invalid_tokens == 0 else '❌'}] Valid Expo token format: {invalid_tokens} invalid")
    
    if invalid_tokens > 0:
        print("    → Some tokens don't start with 'ExponentPushToken['")
        print("    → These won't work with Expo API!")
    
    print()
    return True

def main():
    """Run all checks"""
    print("\n" + "="*60)
    print("  INCIDENT TRACKING & PUSH NOTIFICATION VERIFICATION")
    print("="*60)
    
    results = {
        'Incidents': check_incidents(),
        'Alerts': check_alerts(),
        'Assignments': check_assignments(),
        'Device Tokens': check_device_tokens(),
        'Signals': check_signals(),
        'Timeline': check_flow_timeline(),
        'Push Issues': diagnose_push_issues(),
    }
    
    # Summary
    print_section("SUMMARY")
    
    all_ok = all(results.values())
    
    for check, result in results.items():
        status = "✓" if result else "❌"
        print(f"{status} {check}")
    
    print()
    
    if all_ok:
        print("✅ ALL CHECKS PASSED - System appears to be working correctly!")
    else:
        print("⚠️  SOME CHECKS FAILED - See details above")
        print("\nCommon issues:")
        print("1. No device tokens → Guards won't receive push notifications")
        print("2. No alerts → Check if 'alert_guards_for_incident()' is being called")
        print("3. No assignments → Alerts were declined or expired")
    
    print("\n" + "="*60 + "\n")

if __name__ == '__main__':
    main()
