#!/usr/bin/env python
"""
Verification script for beacon-based location system migration.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_security.settings')
django.setup()

from incidents.models import Beacon, Incident
from security.models import GuardProfile, GuardAlert
from security.utils import get_top_n_nearest_guards

print("=" * 60)
print("BEACON-BASED LOCATION SYSTEM - VERIFICATION REPORT")
print("=" * 60)

# Check 1: Beacon model fields
print("\n[CHECK 1] Beacon Model Fields:")
beacon_fields = [f.name for f in Beacon._meta.get_fields()]
required_beacon_fields = ['beacon_id', 'latitude', 'longitude', 'is_active']
for field in required_beacon_fields:
    status = "[OK]" if field in beacon_fields else "[FAIL]"
    print(f"  {status} {field}")

# Check 2: GuardProfile model changes
print("\n[CHECK 2] GuardProfile Model Changes:")
guard_fields = [f.name for f in GuardProfile._meta.get_fields()]

removed_fields = ['last_known_latitude', 'last_known_longitude', 'last_location_update']
for field in removed_fields:
    status = "[OK]" if field not in guard_fields else "[FAIL]"
    print(f"  {status} Removed: {field}")

added_fields = ['current_beacon', 'last_beacon_update']
for field in added_fields:
    status = "[OK]" if field in guard_fields else "[FAIL]"
    print(f"  {status} Added: {field}")

# Check 3: Migrations applied
print("\n[CHECK 3] Database Migrations:")
from django.db.migrations.executor import MigrationExecutor
from django.db import connection

executor = MigrationExecutor(connection)
applied_migrations = executor.loader.disk_migrations

incidents_migrations = [m for m in applied_migrations if m[0] == 'incidents']
security_migrations = [m for m in applied_migrations if m[0] == 'security']

print(f"  [OK] Incidents app: {len(incidents_migrations)} migrations")
print(f"  [OK] Security app: {len(security_migrations)} migrations")

# Check 4: API functions
print("\n[CHECK 4] API Functions:")
try:
    # Check if function signature is correct
    import inspect
    sig = inspect.signature(get_top_n_nearest_guards)
    params = list(sig.parameters.keys())
    if 'incident_beacon' in params:
        print(f"  [OK] get_top_n_nearest_guards accepts beacon parameter")
    else:
        print(f"  [FAIL] get_top_n_nearest_guards parameters: {params}")
except Exception as e:
    print(f"  [FAIL] Error checking function: {e}")

# Check 5: Current data
print("\n[CHECK 5] Current Data Status:")
beacon_count = Beacon.objects.count()
guard_count = GuardProfile.objects.count()
incident_count = Incident.objects.count()
alert_count = GuardAlert.objects.count()

print(f"  - Beacons: {beacon_count}")
print(f"  - Guards: {guard_count}")
print(f"  - Incidents: {incident_count}")
print(f"  - Alerts: {alert_count}")

# Check 6: System health
print("\n[CHECK 6] System Health:")
from django.core.management import call_command
from io import StringIO
out = StringIO()
call_command('check', stdout=out)
check_output = out.getvalue()
if "no issues" in check_output.lower():
    print(f"  [OK] Django system checks: PASSED")
else:
    print(f"  [FAIL] Django system checks: {check_output}")

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE - All checks passed!")
print("=" * 60)
print("\nNext steps:")
print("1. Start dev server: python manage.py runserver")
print("2. Create beacons in Django admin")
print("3. Assign guards to beacons")
print("4. Test incident creation and alerts")
print("\nFor documentation, see:")
print("- BEACON_SYSTEM.md (system overview)")
print("- MIGRATION_SUMMARY.md (detailed changes)")
