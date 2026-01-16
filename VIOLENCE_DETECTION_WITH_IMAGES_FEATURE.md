# Violence Detection with Images Feature - Implementation Guide

## Overview

The violence detection endpoint (`/api/ai/violence-detected/`) has been enhanced to support **optional image attachments**. This allows AI surveillance systems to include evidence photos/videos with violence detection events, which are automatically attached to created incidents.

## Key Features

✅ **Dual Format Support**: Accept both JSON (no images) and multipart form data (with images)
✅ **Smart Deduplication**: Images attached to signals within 5-minute window are added to existing incident
✅ **Cloud Storage**: Images automatically uploaded to Google Cloud Storage (GCS)
✅ **Public URLs**: Generated public URLs for easy access in dashboards/notifications
✅ **Confidence Threshold**: Below-threshold detections still log images for manual review
✅ **Error Handling**: Proper validation and error messages for invalid requests

## Endpoints

### 1. Violence Detection with Images

**Endpoint:** `POST /api/ai/violence-detected/`

**Content-Type:** `multipart/form-data`

**Permission:** `AllowAny` (public)

#### Request (Multipart)

```
POST /api/ai/violence-detected/ HTTP/1.1
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="beacon_id"

ab907856-3412-3412-3412-341278563412
------WebKitFormBoundary
Content-Disposition: form-data; name="confidence_score"

0.95
------WebKitFormBoundary
Content-Disposition: form-data; name="description"

Violent confrontation detected with weapon - immediate response needed
------WebKitFormBoundary
Content-Disposition: form-data; name="device_id"

AI-VISION-SURVEILLANCE-01
------WebKitFormBoundary
Content-Disposition: form-data; name="images"; filename="violence1.jpg"
Content-Type: image/jpeg

[BINARY IMAGE DATA]
------WebKitFormBoundary--
```

#### Form Fields

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| `beacon_id` | string | Yes | Hardware beacon ID | Must exist in database |
| `confidence_score` | float | Yes | Confidence 0.0-1.0 | Must be valid float |
| `description` | string | Yes | Details about detection | Any text |
| `device_id` | string | No | AI device identifier | Optional |
| `images` | file[] | No | Evidence photos/screenshots | Max 3 files |

#### Success Response (201 Created - New Incident)

```json
{
  "status": "incident_created",
  "ai_event_id": 17,
  "incident_id": "72e204c7-3149-4085-bf5a-112fde0333c0",
  "signal_id": 75,
  "confidence_score": 0.95,
  "beacon_location": "Library Entrance",
  "incident_status": "CREATED",
  "incident_priority": "Critical",
  "device_id": "AI-VISION-SURVEILLANCE-01",
  "images": [
    {
      "id": 43,
      "image": "http://storage.googleapis.com/resq-campus-security/incidents/2026/01/16/sample1.jpg",
      "uploaded_at": "2026-01-16T10:01:24.405048Z",
      "description": "AI Detection Image 1 (VIOLENCE)"
    }
  ]
}
```

#### Success Response (200 OK - Added to Existing Incident)

```json
{
  "status": "signal_added_to_existing",
  "ai_event_id": 18,
  "incident_id": "72e204c7-3149-4085-bf5a-112fde0333c0",
  "signal_id": 76,
  "confidence_score": 0.92,
  "beacon_location": "Library Entrance",
  "incident_status": "CREATED",
  "incident_priority": "Critical",
  "images": [
    {
      "id": 44,
      "image": "http://storage.googleapis.com/resq-campus-security/incidents/2026/01/16/additional.jpg",
      "uploaded_at": "2026-01-16T10:02:15.123456Z",
      "description": "AI Detection Image 1 (VIOLENCE)"
    }
  ]
}
```

#### Below Threshold Response (200 OK - Logged Only)

When confidence < 0.75 (75%):

```json
{
  "status": "logged_only",
  "ai_event_id": 19,
  "message": "Confidence 0.65 below threshold 0.75",
  "images_received": 1
}
```

**Note:** Even when below threshold, images are still logged if provided (for manual review).

#### Error Response (400 Bad Request)

```json
{
  "error": "Maximum 3 images allowed"
}
```

Common errors:
- Missing required fields (beacon_id, confidence_score, description)
- Confidence score not between 0.0-1.0
- Beacon not found or inactive
- More than 3 images provided

### 2. Scream Detection with Images

**Endpoint:** `POST /api/ai/scream-detected/`

Same interface as violence detection, but with:
- Confidence threshold: 0.80 (80%)
- Priority escalation: HIGH (instead of CRITICAL)
- Signal type: SCREAM_DETECTED

#### Example Request

```curl
curl -X POST http://localhost:8000/api/ai/scream-detected/ \
  -F "beacon_id=safe:uuid:402:402" \
  -F "confidence_score=0.92" \
  -F "description=Screaming detected in dormitory" \
  -F "device_id=AI-AUDIO-001" \
  -F "images=@screenshot.jpg"
```

## Implementation Details

### Architecture

```
┌─────────────────────────────────┐
│   Multipart POST Request        │
│ (Images + Form Data)            │
└──────────────┬──────────────────┘
               │
               ▼
    ┌──────────────────────────────┐
    │ _process_ai_detection_with_  │
    │      images() Helper         │
    └──────────────┬───────────────┘
               │
    ┌──────────┴────────────────────────────────┐
    │                                           │
    ▼                                           ▼
Validate Fields & Images          Create/Update Incident
    │                                           │
    ├─ beacon_id exists?                       ├─ Dedup check (5 min)
    ├─ confidence_score valid?                 ├─ Create AIEvent
    ├─ description provided?                   ├─ Check threshold
    └─ images ≤ 3?                             └─ Create/Add Signal
                                                   │
                                    ┌──────────────┴──────────────┐
                                    │                             │
                                    ▼                             ▼
                              Process Each Image          Alert Guards
                                    │                    (if new incident)
                  ┌─────────────────┼─────────────────┐
                  │                 │                 │
                  ▼                 ▼                 ▼
             Validate File    Reset File Pointer  Upload to GCS
             Size & Type      (seek to 0)         (Django ORM)
                  │                                    │
                  └────────────────┬───────────────────┘
                                   │
                                   ▼
                            Make Public on GCS
                            (set 'public-read' ACL)
                                   │
                                   ▼
                            Add to Response
                            (with public URLs)
```

### Code Flow

#### Step 1: Request Validation

```python
# Extract form data
beacon_id = request.POST.get('beacon_id')
confidence_score = float(request.POST.get('confidence_score'))
description = request.POST.get('description')
images_list = request.FILES.getlist('images', [])

# Validate required fields
if not beacon_id or not description:
    return Response({'error': 'Field required'}, 400)

# Validate image count
if len(images_list) > 3:
    return Response({'error': 'Maximum 3 images allowed'}, 400)
```

#### Step 2: Create AI Event (Always)

```python
ai_event = AIEvent.objects.create(
    beacon=beacon,
    event_type='VIOLENCE',  # or 'SCREAM'
    confidence_score=0.95,
    details={
        'description': description,
        'device_id': device_id,
        'images_count': len(images_list)
    }
)
```

#### Step 3: Check Confidence Threshold

```python
if confidence_score < 0.75:  # Threshold for violence
    # Log but don't create incident
    return Response({
        'status': 'logged_only',
        'ai_event_id': ai_event.id,
        'message': f'Confidence {confidence_score:.2f} below threshold 0.75',
        'images_received': len(images_list)
    }, 200)
```

#### Step 4: Create or Get Incident (Deduplication)

```python
# Look for existing incident within 5 minutes at same beacon
incident, created, signal = get_or_create_incident_with_signals(
    beacon_id=beacon_id,
    signal_type=IncidentSignal.SignalType.VIOLENCE_DETECTED,
    ai_event_id=ai_event.id,
    description=description,
    details={...}
)
```

**Key behavior:**
- **If new incident:** Status = 201 Created, guards are alerted
- **If existing incident (within 5 min):** Status = 200 OK, no re-alert (dedup)

#### Step 5: Process Images

```python
for idx, image_file in enumerate(images_list[:3]):
    # Reset file pointer
    image_file.seek(0)
    
    # Read to verify completeness
    file_data = image_file.read()
    image_file.seek(0)
    
    # Save to GCS via Django ORM
    incident_image = IncidentImage.objects.create(
        incident=incident,
        image=image_file,
        uploaded_by=None,  # AI detection (no user)
        description=f"AI Detection Image {idx + 1} (VIOLENCE)"
    )
    
    # Verify upload
    if incident_image.image:
        url = incident_image.image.url
        # URL is now: http(s)://storage.googleapis.com/bucket/path
```

#### Step 6: Make Images Public

```python
# In IncidentImage.save() method
storage_backend = self.image.storage
if hasattr(storage_backend, 'bucket'):
    blob = storage_backend.bucket.blob(self.image.name)
    if blob.exists():
        blob.make_public()  # Sets 'public-read' ACL
```

### Image Storage Details

**GCS Bucket Configuration:**
- Bucket: `resq-campus-security`
- Path: `incidents/YYYY/MM/DD/filename.jpg`
- URL Format: `http(s)://storage.googleapis.com/resq-campus-security/incidents/2026/01/16/sample1.jpg`
- ACL: Public-read (viewable without authentication)

**Database Storage:**
```python
class IncidentImage(models.Model):
    incident = ForeignKey(Incident)  # Parent incident
    image = ImageField(upload_to='incidents/%Y/%m/%d/')  # GCS path
    uploaded_by = ForeignKey(User, null=True)  # None for AI detections
    uploaded_at = DateTimeField(auto_now_add=True)
    description = CharField(max_length=255)
```

## Testing

### Test Cases (in test.http)

**0.6a:** Single image with violence detection
**0.6b:** Multiple images (3) with violence detection
**0.6c:** Scream detection with image
**0.6d:** Images below confidence threshold
**0.6e:** Missing required field (should fail)
**0.6f:** Too many images - 4 images (should fail)
**0.6g:** Create new incident with images
**0.6h:** Add images to existing incident (deduplication)
**0.6i:** Compare JSON vs multipart requests

### Running Tests

```bash
# Test script (Python)
python test_violence_with_images.py

# HTTP tests (in test.http)
# Use VS Code REST Client extension
# Click "Send Request" on each test case
```

### Example Test with cURL

```bash
# Single image
curl -X POST http://localhost:8000/api/ai/violence-detected/ \
  -F "beacon_id=ab907856-3412-3412-3412-341278563412" \
  -F "confidence_score=0.95" \
  -F "description=Fight detected with weapon" \
  -F "device_id=AI-VISION-001" \
  -F "images=@evidence.jpg"

# Multiple images
curl -X POST http://localhost:8000/api/ai/violence-detected/ \
  -F "beacon_id=ab907856-3412-3412-3412-341278563412" \
  -F "confidence_score=0.88" \
  -F "description=Multiple suspects involved" \
  -F "images=@photo1.jpg" \
  -F "images=@photo2.jpg" \
  -F "images=@photo3.jpg"
```

## Backward Compatibility

**JSON-only requests still work:**

```json
POST /api/ai/violence-detected/
Content-Type: application/json

{
  "beacon_id": "ab907856-3412-3412-3412-341278563412",
  "confidence_score": 0.92,
  "description": "Fight detected",
  "device_id": "AI-VISION-001"
}
```

The endpoint automatically detects whether multipart form data is being used (checking for `images` in `request.FILES`) and routes to the appropriate handler.

## Integration Points

### 1. Frontend (React Native/Web)

```javascript
const formData = new FormData();
formData.append('beacon_id', 'ab907856-3412-3412-3412-341278563412');
formData.append('confidence_score', '0.95');
formData.append('description', 'Violence detected');
formData.append('device_id', 'AI-VISION-001');

// Add images (as Blob or File objects)
formData.append('images', imageBlob1, 'image1.jpg');
formData.append('images', imageBlob2, 'image2.jpg');

const response = await fetch('/api/ai/violence-detected/', {
  method: 'POST',
  body: formData
});

const result = await response.json();
console.log(result.images); // Array of image objects with URLs
```

### 2. Incident Dashboard

Images are automatically available:
- Display in incident detail view
- Show in guard alert notifications
- Include in incident timeline
- Available for evidence review

### 3. Push Notifications

Incident service includes image URLs in push notifications:

```python
notification_data = {
    "images": [
        "http://storage.googleapis.com/.../incident1.jpg",
        "http://storage.googleapis.com/.../incident2.jpg"
    ]
}
```

## Troubleshooting

### Images Not Uploading

1. **Check GCS bucket credentials:**
   ```bash
   python manage.py shell -c "from django.core.files.storage import default_storage; print(default_storage.bucket)"
   ```

2. **Verify file pointer reset:**
   - Images must have `seek(0)` called before saving
   - Check server logs for "File pointer" messages

3. **Check GCS permissions:**
   - Bucket must have write permissions
   - Service account must have `roles/storage.admin`

### Images Not Public

1. **Verify blob.make_public() is called:**
   ```bash
   # In IncidentImage.save() override
   # Check server logs for "✓ Image X made public"
   ```

2. **Check bucket ACL settings:**
   - Uniform bucket-level access must be DISABLED
   - Object-level ACLs must be ENABLED

### Incident Not Created

1. **Check confidence threshold:**
   - Violence: >= 0.75
   - Scream: >= 0.80

2. **Verify beacon exists:**
   ```bash
   python manage.py shell -c "from incidents.models import Beacon; print(Beacon.objects.filter(is_active=True).values_list('beacon_id', flat=True))"
   ```

3. **Check deduplication window:**
   - Within 5 minutes + same beacon = added to existing
   - After 5 minutes = new incident

## Performance Notes

- Images processed sequentially (not in parallel)
- GCS upload happens via Django ORM (streaming)
- File pointer reset prevents memory issues
- Each image creates separate IncidentImage record

## Security Considerations

- Images are public-read on GCS (viewable by anyone with URL)
- No authentication required for image URLs
- Consider adding URL expiration for sensitive environments
- Images are tied to incidents (audit trail maintained)

## Future Enhancements

- [ ] Image compression before upload
- [ ] Video support (not just images)
- [ ] Image analysis (object detection, face recognition)
- [ ] Automatic image retention/deletion policies
- [ ] Signed URLs with expiration for sensitive content
- [ ] Image encryption at rest on GCS
