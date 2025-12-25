## ADMIN SETUP QUICK GUIDE

### 1. Access Django Admin
```
http://localhost:8000/admin/
Login with admin credentials
```

---

## 2. Setting Up Beacon Proximities

### Via Beacon Edit (Recommended - Visual)
1. Go to **Incidents → Beacons**
2. Click on a beacon (e.g., "Library 4F")
3. Scroll down to **"Beacon Proximities"** inline table
4. Click **"Add another Beacon Proximity"**
5. Select nearby beacon from dropdown
6. Set priority (1=nearest, 2=adjacent floor, 3+=far)
7. Save

### Via BeaconProximity Admin (Direct)
1. Go to **Incidents → Beacon Proximities**
2. Click **"Add Beacon Proximity"**
3. Fill in:
   - **From Beacon:** Library 4F
   - **To Beacon:** Hallway 4F
   - **Priority:** 1
4. Save

---

## 3. Example Setup for 4-Floor Building

```
=== Building A ===

Library 4F (From Beacon)
├─ Priority 1: Hallway 4F
├─ Priority 1: Stairwell 4F
├─ Priority 2: Library 3F
├─ Priority 2: Library 5F
└─ Priority 3: Main Entrance

Library 3F (From Beacon)
├─ Priority 1: Hallway 3F
├─ Priority 2: Library 4F
├─ Priority 2: Library 2F
└─ Priority 3: Main Entrance

... (repeat for each beacon)
```

---

## 4. Monitoring Guard Activity

### Guard Profiles
- **URL:** `/admin/security/guardprofile/`
- **View:** Current location, availability, last activity
- **Filter:** By active, available, building
- **Update:** Click guard → edit current_beacon

### Guard Alerts
- **URL:** `/admin/security/guardalert/`
- **View:** Real-time incident alerts
- **Status:** SENT (pending), ACKNOWLEDGED (accepted), DECLINED (rejected), EXPIRED (replaced)
- **Filter:** By status, priority, date
- **Action:** Click to see full incident details and assignment

### Guard Assignments
- **URL:** `/admin/security/guardassignment/`
- **View:** Active guard-to-incident assignments
- **Filter:** By active status and date
- **Verify:** One-per-incident constraint enforced

---

## 5. Monitoring Incidents

### Incidents
- **URL:** `/admin/incidents/incident/`
- **View:** Status (CREATED → ASSIGNED → RESOLVED)
- **Filter:** By status, priority, location
- **Related:** Click incident → see guard assignment, alerts, conversation

### Beacon Proximities
- **URL:** `/admin/incidents/beaconproximity/`
- **View:** Confirm all relationships exist
- **Search:** Find by beacon name
- **Check:** Priorities are logical

---

## 6. Common Admin Tasks

### Check Guard Location
1. Go to **Security → Guard Profiles**
2. Find guard by name/email
3. View **Current Beacon** field
4. See **Last Beacon Update** timestamp

### See Who's Assigned to an Incident
1. Go to **Incidents → Incidents**
2. Click incident ID
3. Scroll to **Guard Assignments** section
4. Click guard name to view profile

### View All Alerts for an Incident
1. Go to **Incidents → Incidents**
2. Click incident ID
3. Scroll to **Guard Alerts** section
4. Filter by status (SENT, ACKNOWLEDGED, etc.)

### Debug: Check Beacon Search Path
1. Go to **Incidents → Beacon Proximities**
2. Search by from_beacon (e.g., "Library 4F")
3. Review all nearby beacons in priority order
4. Verify relationships are correct

---

## 7. Testing in Admin

### Test Alert Generation
1. Create new incident via **Incidents → Incidents**
2. Fill in beacon, priority, description
3. Save
4. Go to **Security → Guard Alerts**
5. Filter by status=SENT
6. Verify alerts created for nearby guards

### Test Guard Acknowledgment
1. Click on a SENT alert
2. Change status to ACKNOWLEDGED
3. Save
4. Go to **Security → Guard Assignments**
5. Verify assignment created for that guard/incident

### Test Decline Flow
1. Create second alert for same incident
2. Change status to DECLINED
3. Save
4. Go back to **Security → Guard Alerts**
5. Check if next guard has SENT alert

---

## 8. Database Constraints (Auto-Enforced)

### One Active Assignment Per Incident
```
UNIQUE(incident, is_active=True)
```
**Effect:** Only one guard can be active on incident at a time

### One Alert Per Guard-Incident Pair
```
UNIQUE(incident, guard)
```
**Effect:** Same guard won't receive 2 alerts for same incident

### Unique Beacon Identifiers
```
UNIQUE(uuid, major, minor)
UNIQUE(beacon_id)
```
**Effect:** No duplicate beacons in system

### Unique Beacon Pair
```
UNIQUE(from_beacon, to_beacon)
```
**Effect:** No duplicate proximity relationships

---

## 9. Search Tips

### Find Guards by Location
1. Go to **Security → Guard Profiles**
2. Search: "Hallway 4F"
3. All guards at that beacon appear

### Find Incidents by Location
1. Go to **Incidents → Incidents**
2. Filter: building="Main", floor="4"
3. All 4F incidents appear

### Find Declines
1. Go to **Security → Guard Alerts**
2. Filter: status="DECLINED"
3. See who declined and when

### Find Unassigned Incidents
1. Go to **Incidents → Incidents**
2. Filter: status="CREATED"
3. Incidents still waiting for guard

---

## 10. Performance Notes

### Slow Admin Pages?
- Beacon list with many proximity relationships can be slow
- Use search/filter to narrow results
- BeaconProximity admin is lightweight

### Checking Alert Volume
- Guard Alerts table grows with incidents
- Filter by date to see recent activity
- Can be archived/cleared periodically

### Location Update Frequency
- Guards update every 10-15 seconds
- GuardProfile.current_beacon updated (lightweight)
- last_beacon_update indexed for quick lookup

---

## 11. Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Can't create proximity relationship | Check from_beacon and to_beacon aren't the same |
| Missing beacon in dropdown | Beacon must be is_active=True |
| Guard alert not created | No guards available at/near incident beacon |
| Assignment won't create | is_active assignment already exists |
| Can't delete beacon | Deactivate instead (is_active=False) |

---

**Last Updated:** December 25, 2025  
**Status:** Ready for Deployment ✅
