# Quick Reference Guide - Violence Detection with Images

## 🚀 Quick Start

### API Endpoint
```
POST /api/ai/violence-detected/
POST /api/ai/scream-detected/
```

### Basic Request (with image)
```bash
curl -X POST http://localhost:8000/api/ai/violence-detected/ \
  -F "beacon_id=ab907856-3412-3412-3412-341278563412" \
  -F "confidence_score=0.95" \
  -F "description=Fight with weapon detected" \
  -F "images=@photo.jpg"
```

### Response (Success)
```json
{
  "status": "incident_created",
  "incident_id": "72e204c7-3149...",
  "images": [
    {
      "image": "http://storage.googleapis.com/...image.jpg",
      "uploaded_at": "2026-01-16T10:01:24Z"
    }
  ]
}
```

---

## 📋 Form Fields Reference

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `beacon_id` | string | ✅ Yes | Must exist in database |
| `confidence_score` | float | ✅ Yes | 0.0-1.0 range |
| `description` | string | ✅ Yes | Details about detection |
| `device_id` | string | ❌ No | AI device identifier |
| `images` | file[] | ❌ No | Max 3 images |

---

## 🎯 Confidence Thresholds

| Detection | Threshold | Priority | Alert Count |
|-----------|-----------|----------|-------------|
| **Violence** | 75% | CRITICAL | 5 guards |
| **Scream** | 80% | HIGH | 3 guards |

**Below threshold:** Logged only, no incident created (unless images provided)

---

## 📸 Image Constraints

- **Maximum:** 3 images per request
- **Format:** JPG, PNG, GIF
- **Size:** Up to 10MB total (configurable)
- **Storage:** Google Cloud Storage (public URLs)

---

## 🔄 Deduplication Logic

**Same beacon + Within 5 minutes?**
- ✅ YES → Add to existing incident (Status 200)
- ❌ NO → Create new incident (Status 201)

**Guard alerts sent only on NEW incidents** (not on dedup)

---

## ✅ Valid Request Examples

### Single Image
```bash
curl -X POST http://localhost:8000/api/ai/violence-detected/ \
  -F "beacon_id=ab907856-3412-3412-3412-341278563412" \
  -F "confidence_score=0.95" \
  -F "description=Violent confrontation detected" \
  -F "device_id=AI-VISION-001" \
  -F "images=@evidence.jpg"
```

### Multiple Images
```bash
curl -X POST http://localhost:8000/api/ai/violence-detected/ \
  -F "beacon_id=ab907856-3412-3412-3412-341278563412" \
  -F "confidence_score=0.88" \
  -F "description=Multiple suspects involved" \
  -F "images=@photo1.jpg" \
  -F "images=@photo2.jpg" \
  -F "images=@photo3.jpg"
```

### JSON (Original - No Images)
```bash
curl -X POST http://localhost:8000/api/ai/violence-detected/ \
  -H "Content-Type: application/json" \
  -d '{
    "beacon_id": "ab907856-3412-3412-3412-341278563412",
    "confidence_score": 0.92,
    "description": "Fight detected",
    "device_id": "AI-VISION-001"
  }'
```

### Below Threshold
```bash
curl -X POST http://localhost:8000/api/ai/violence-detected/ \
  -F "beacon_id=ab907856-3412-3412-3412-341278563412" \
  -F "confidence_score=0.65" \
  -F "description=Uncertain violence detection" \
  -F "images=@review.jpg"
```

---

## ❌ Error Cases

### Missing Required Field
```json
{
  "error": "beacon_id is required"
}
```
Status: 400 Bad Request

### Invalid Beacon
```json
{
  "error": "Beacon ab907856... not found or inactive"
}
```
Status: 404 Not Found

### Too Many Images
```json
{
  "error": "Maximum 3 images allowed"
}
```
Status: 400 Bad Request

### Invalid Confidence Score
```json
{
  "error": "confidence_score must be between 0.0 and 1.0"
}
```
Status: 400 Bad Request

---

## 📍 Response Status Codes

| Code | Status | Meaning |
|------|--------|---------|
| **201** | Created | New incident created |
| **200** | OK | Added to existing incident (dedup) |
| **200** | OK | Logged only (below threshold) |
| **400** | Bad Request | Invalid input |
| **404** | Not Found | Beacon not found |

---

## 🔗 Integration Checklist

- [ ] Get valid beacon IDs from `/api/beacons/`
- [ ] Set correct confidence scores (0.0-1.0)
- [ ] Include description (required)
- [ ] Prepare up to 3 images
- [ ] Test with cURL or REST Client
- [ ] Parse image URLs from response
- [ ] Display images in incident view
- [ ] Include image URLs in notifications

---

## 🧪 Testing

### Option 1: Python Script
```bash
python test_violence_with_images.py
```

### Option 2: REST Client (VS Code)
Open `test.http` → Tests 0.6a-0.6i

### Option 3: cURL
```bash
curl -X POST http://localhost:8000/api/ai/violence-detected/ \
  -F "beacon_id=YOUR_BEACON_ID" \
  -F "confidence_score=0.95" \
  -F "description=Test" \
  -F "images=@test_images/sample1.jpg"
```

---

## 🐛 Troubleshooting

**Q: Images not uploading?**
A: Check GCS bucket credentials and `GOOGLE_APPLICATION_CREDENTIALS`

**Q: Incident created but images missing?**
A: Check file pointer reset in code (seek(0) calls)

**Q: Getting 404 for beacon?**
A: Run `python manage.py shell` and check valid beacon IDs:
```python
from incidents.models import Beacon
print(Beacon.objects.filter(is_active=True).values_list('beacon_id'))
```

**Q: Images not public?**
A: Check GCS bucket ACL settings and logs for "made public" messages

---

## 📚 Full Documentation

- **Implementation Guide:** `VIOLENCE_DETECTION_WITH_IMAGES_FEATURE.md`
- **Study Document:** `VIOLENCE_DETECTION_AND_IMAGE_UPLOAD_STUDY.md`
- **Feature Summary:** `FEATURE_IMPLEMENTATION_SUMMARY.md`
- **Code:** `ai_engine/views.py` (violence_detected, scream_detected)
- **Tests:** `test.http` (0.6a-0.6i), `test_violence_with_images.py`

---

## 🎓 How It Works (Simplified)

```
1. Send POST request with images
         ↓
2. Validate all fields
         ↓
3. Create AIEvent (for analytics)
         ↓
4. Check confidence threshold
         ↓
   Below? → Return "logged_only" ✓
   Above? → Continue to step 5 ↓
         ↓
5. Check for existing incident (within 5 min)
         ↓
   Found? → Add signal & images ✓ (Status 200)
   Not found? → Create new ✓ (Status 201)
         ↓
6. Upload images to GCS
         ↓
7. Alert guards (if new incident)
         ↓
8. Return response with image URLs
```

---

## 💡 Pro Tips

1. **Always check response image URLs** - Verify they're accessible
2. **Use device_id** - Helps identify which AI system detected violence
3. **Reuse incident_id** - Query `/api/incidents/{id}/` for full details
4. **Include both JSON and multipart** - Support both in your integrations
5. **Test with test_images/** - Use provided sample images first
6. **Monitor GCS bucket** - Watch for storage quota issues
7. **Check dedup window** - 5 minutes is the timeframe for same beacon

---

## 🚀 Go Live Checklist

- [ ] GCS bucket configured and credentials set
- [ ] Beacons created in database
- [ ] Test images work with endpoint
- [ ] Image URLs are publicly accessible
- [ ] Incidents appear in dashboard
- [ ] Guard alerts sent correctly
- [ ] Images display in incident view
- [ ] Test on staging before production
- [ ] Monitor logs for errors
- [ ] Set up GCS monitoring/alerts

---

**Last Updated:** January 16, 2026
**Status:** ✅ Ready for Production
