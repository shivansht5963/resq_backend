# AI Model Integration Guide

## Quick Reference for AI Teams

### Endpoint 1: Violence Detection

**URL:** `POST https://resq-server.onrender.com/api/ai/violence-detected/`

**When to call:** Fight detected, weapon, physical assault

**Minimum Request:**
```json
{
  "beacon_id": "safe:uuid:403:403",
  "confidence_score": 0.92,
  "description": "Fight detected"
}
```

**Confidence Threshold:** 0.75 (75%)
- Below 0.75 → Logged but no incident created
- 0.75+ → Incident CRITICAL created + 3 guards alerted

---

### Endpoint 2: Scream Detection

**URL:** `POST https://resq-server.onrender.com/api/ai/scream-detected/`

**When to call:** Loud crying, screaming, distress sounds

**Minimum Request:**
```json
{
  "beacon_id": "safe:uuid:402:402",
  "confidence_score": 0.88,
  "description": "Screaming detected"
}
```

**Confidence Threshold:** 0.80 (80%)
- Below 0.80 → Logged but no incident created
- 0.80+ → Incident HIGH created + 3 guards alerted

---

## Valid Beacon IDs

Get list: `GET https://resq-server.onrender.com/api/beacons/`

**Working Examples:**
```
"safe:uuid:403:403"    (Library 3F)
"safe:uuid:402:402"    (Hallway 4F)
"safe:uuid:401:401"    (Library 4F)
"test:uuid:2:2"        (Hallway 4F)
```

---

## Response Status Guide

| Status | HTTP | Meaning | Next Step |
|--------|------|---------|-----------|
| `incident_created` | 201 | New incident created + guards alerted | Monitor incident_id |
| `signal_added_to_existing` | 200 | Added signal to existing incident | Incident already being handled |
| `logged_only` | 200 | Confidence too low, no incident | No action needed |
| (error) | 400 | Invalid input | Check beacon_id, confidence range |
| (error) | 404 | Beacon not found | Use valid beacon ID from GET /beacons/ |

---

## Example: Complete Integration

### Python
```python
import requests
import json
from datetime import datetime

# Your AI model output
ai_output = {
    'violence_detected': True,
    'confidence': 0.92,
    'beacon': 'safe:uuid:403:403',
    'description': 'Two people fighting near library entrance',
    'timestamp': datetime.now().isoformat()
}

# Call ResQ backend
response = requests.post(
    'https://resq-server.onrender.com/api/ai/violence-detected/',
    json={
        'beacon_id': ai_output['beacon'],
        'confidence_score': ai_output['confidence'],
        'description': ai_output['description']
    }
)

result = response.json()

if response.status_code == 201:
    print(f"✅ New incident created: {result['incident_id']}")
    print(f"   Priority: {result['incident_priority']}")
    print(f"   Location: {result['beacon_location']}")
    print(f"   Guards alerted: 3")
    
elif response.status_code == 200:
    if result['status'] == 'signal_added_to_existing':
        print(f"✅ Signal added to existing incident: {result['incident_id']}")
    elif result['status'] == 'logged_only':
        print(f"⚠️ Low confidence ({ai_output['confidence']}) - logged only, no incident")
        
else:
    print(f"❌ Error: {result['error']}")
```

### Node.js / JavaScript
```javascript
const axios = require('axios');

async function reportViolence(beacon, confidence, description) {
    try {
        const response = await axios.post(
            'https://resq-server.onrender.com/api/ai/violence-detected/',
            {
                beacon_id: beacon,
                confidence_score: confidence,
                description: description
            }
        );
        
        console.log(`✅ Success: ${response.data.status}`);
        console.log(`   Incident: ${response.data.incident_id}`);
        return response.data;
        
    } catch (error) {
        console.error(`❌ Error: ${error.response?.data?.error}`);
    }
}

// Usage
reportViolence(
    'safe:uuid:403:403',
    0.92,
    'Fight detected in library'
);
```

---

## Response Parsing

### When incident_created (201)
```python
# New incident, guards are responding
incident_id = response['incident_id']
guards_count = 3  # Always 3 for new incidents
priority = response['incident_priority']  # CRITICAL or HIGH

# Store incident_id for follow-up tracking
store_incident_tracking(incident_id, response['ai_event_id'])
```

### When signal_added_to_existing (200)
```python
# Incident already being handled
incident_id = response['incident_id']
# Guards already on the way - no action needed
# Your detection confirms existing incident
```

### When logged_only (200)
```python
# Confidence too low
ai_event_id = response['ai_event_id']
# Logged for analytics but didn't trigger emergency response
# Consider re-evaluating model confidence threshold
```

---

## Best Practices

### 1. Confidence Scores
- Use model's actual confidence/probability
- 0.0 = definitely not (violence/scream)
- 1.0 = definitely is
- Range: 0.0-1.0 only

### 2. Descriptions
- Be specific: "Fight between 2 males near north entrance"
- Include details: "Aggressive shouting, physical contact"
- Guards use this to prepare response
- Include timestamp/duration if available

### 3. Beacon ID Validation
- Always use beacon_id from campus database
- Don't make up beacon IDs
- If location unknown, send student SOS via mobile app instead
- Each beacon is tied to physical location for guard routing

### 4. Rate Limiting
- Don't spam same beacon
- Multiple detections within 5 minutes → 1 incident (deduplicated)
- Space out calls if testing (avoid fire drills)

### 5. Error Handling
```python
if response.status_code == 400:
    # Input validation error
    # Check: beacon_id format, confidence range (0-1)
    print(response.json()['error'])
    
elif response.status_code == 404:
    # Beacon not found
    # Get valid beacon IDs from GET /api/beacons/
    print(response.json()['error'])
    
elif response.status_code >= 500:
    # Server error
    # Retry with exponential backoff
    retry()
```

---

## Testing Checklist

- [ ] Get valid beacon IDs: `curl https://resq-server.onrender.com/api/beacons/`
- [ ] Test violence endpoint with 0.92 confidence → should create CRITICAL incident
- [ ] Test scream endpoint with 0.88 confidence → should create HIGH incident
- [ ] Test violence with 0.60 confidence → should return "logged_only"
- [ ] Test with invalid beacon → should return 404
- [ ] Test with confidence > 1.0 → should return 400
- [ ] Verify response includes incident_id
- [ ] Check incident appears in `GET /api/incidents/` within 5s

---

## Troubleshooting

### Q: Getting 404 "Beacon not found"
**A:** Beacon ID must be valid and active. Get list from:
```bash
curl https://resq-server.onrender.com/api/beacons/
```

### Q: Getting "confidence_score must be between 0.0 and 1.0"
**A:** Don't send percentages (0-100). Must be decimals (0-1).
- ❌ Wrong: `"confidence_score": 92`
- ✅ Correct: `"confidence_score": 0.92`

### Q: Signal added to existing, but wanted new incident
**A:** This is correct behavior. If incident exists at same beacon within 5 minutes:
- New signals merge into existing incident
- Guards not re-alerted
- Priority may escalate
- This prevents alert fatigue

### Q: No guards responding to alert
**A:** 
1. Check guards are on duty (`is_active=True`)
2. Verify guards updated location recently
3. Check if incident status is RESOLVED
4. See test.http for guard workflow

### Q: Missing incident_id in response
**A:** Check response status:
- 201 = incident_created (has incident_id)
- 200 = signal_added or logged_only (check 'status' field)

---

## Integration Timeline

### Week 1: Development
- [ ] Integrate endpoints into AI model server
- [ ] Test with dev environment (localhost:8000)
- [ ] Validate confidence thresholds

### Week 2: Testing
- [ ] Test with live beacons
- [ ] Run end-to-end with guard mobile app
- [ ] Monitor false positive rate

### Week 3: Production
- [ ] Deploy to production AI servers
- [ ] Point to production API: `https://resq-server.onrender.com/api/`
- [ ] Monitor incidents daily

---

## Contact & Support

For API issues:
1. Check this guide first
2. Review response error messages
3. See AI_DETECTION_ENDPOINTS.md for detailed docs
4. Test with test.http examples

---

## Model Confidence Guidelines

### Violence Detection (0.75 threshold)
**Model should detect:**
- Punching, kicking, hitting
- Physical contact (fighting)
- Weapon presence
- Aggressive body language + movement

**False positives OK because:**
- Guards will verify
- Better safe than miss real violence
- Lower threshold appropriate for safety

### Scream Detection (0.80 threshold)
**Model should detect:**
- Loud screams/yelling (pain/fear)
- Distressed crying
- Panic sounds

**Higher threshold to avoid:**
- Excited cheering/shouting
- Laughing
- General loud conversation
- Music

---

## API Version Compatibility

**Current Version:** 1.0
- ✅ `/api/ai/violence-detected/`
- ✅ `/api/ai/scream-detected/`
- ✅ `/api/ai-detection/` (legacy, still works)

**Planned:**
- Rate limiting per IP
- Batch endpoint for multiple detections
- Webhook for incident status updates
