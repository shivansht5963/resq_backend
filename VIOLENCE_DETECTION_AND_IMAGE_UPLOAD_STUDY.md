# Violence Detection & Image Upload Flow - Comprehensive Study

## Table of Contents
1. [Violence Detection Flow](#violence-detection-flow)
2. [Image Upload Flow](#image-upload-flow)
3. [Data Format & API Specifications](#data-format--api-specifications)
4. [Backend Processing](#backend-processing)
5. [Cloud Storage Integration](#cloud-storage-integration)

---

## Violence Detection Flow

### 1. API Endpoint

**Endpoint:** `POST /api/ai/violence-detected/`

**Permission:** `AllowAny` (Public endpoint - no authentication required)

**Location:** [ai_engine/views.py](ai_engine/views.py#L177)

### 2. Request Format (JSON)

```json
{
    "beacon_id": "safe:uuid:403:403",
    "confidence_score": 0.92,
    "description": "Fight detected near library entrance",
    "device_id": "AI-MODEL-VIOLENCE-01"
}
```

**Required Fields:**
- `beacon_id` (string): Hardware beacon ID identifying the location
- `confidence_score` (float): 0.0-1.0, confidence of violence detection
- `description` (string): Details about the violence detected

**Optional Fields:**
- `device_id` (string): Identifier of the AI detection device/model

### 3. Confidence Threshold

Violence detection uses a **0.75 (75%) confidence threshold**

```python
# From ai_engine/views.py:177
return _process_ai_detection(
    request,
    event_type=AIEvent.EventType.VIOLENCE,
    signal_type=IncidentSignal.SignalType.VIOLENCE_DETECTED,
    confidence_threshold=0.75,  # ← Threshold
    description_required=True
)
```

### 4. Backend Processing Flow

The `_process_ai_detection()` helper function (lines 29-168 in ai_engine/views.py) handles the complete flow:

#### Step 1: Input Validation
```python
# Extract and validate request data
beacon_id = request.data.get('beacon_id', '').strip()
confidence_score = float(request.data.get('confidence_score'))
description = request.data.get('description', '').strip()
device_id = request.data.get('device_id', '').strip()

# Validate ranges
if not (0.0 <= confidence_score <= 1.0):
    return Response({'error': 'confidence_score must be between 0.0 and 1.0'}, ...)

# Validate beacon exists and is active
try:
    beacon = Beacon.objects.get(beacon_id=beacon_id, is_active=True)
except Beacon.DoesNotExist:
    return Response({'error': f'Beacon {beacon_id} not found or inactive'}, ...)
```

#### Step 2: AI Event Logging
Regardless of confidence threshold, an `AIEvent` record is always created for analytics/audit:

```python
ai_event = AIEvent.objects.create(
    beacon=beacon,
    event_type="VIOLENCE",
    confidence_score=0.92,
    details={
        'description': description,
        'raw_confidence': 0.92,
        'device_id': device_id
    }
)
```

**AIEvent Model** (ai_engine/models.py):
```python
class AIEvent(models.Model):
    id = AutoField
    beacon = ForeignKey(Beacon)
    event_type = CharField("VIOLENCE" | "SCREAM")
    confidence_score = FloatField  # 0.0-1.0
    details = JSONField  # Additional metadata
    created_at = DateTimeField  # Auto timestamp
```

#### Step 3: Confidence Threshold Check
```python
if confidence_score < 0.75:  # Below threshold
    return Response({
        'status': 'logged_only',
        'ai_event_id': ai_event.id,
        'message': f'Confidence 0.65 below threshold 0.75'
    }, status=HTTP_200_OK)
```

**Response when below threshold:**
- AI event is logged for analytics
- **NO incident is created**
- Response status: 200 OK (not an error)

#### Step 4: Incident Creation/Merging
When confidence ≥ 0.75, an incident is created or signal is added to existing:

```python
incident, created, signal = get_or_create_incident_with_signals(
    beacon_id=beacon_id,
    signal_type=IncidentSignal.SignalType.VIOLENCE_DETECTED,
    ai_event_id=ai_event.id,
    source_device_id=source_device.id if source_device else None,
    description=description,
    details={
        'description': description,
        'ai_confidence': 0.92,
        'ai_type': 'violence',
        'device_id': device_id
    }
)
```

### 5. Deduplication Logic

**Location:** incidents/services.py - `get_or_create_incident_with_signals()` function

The backend automatically **deduplicates** violence detections within a 5-minute window:

```python
DEDUP_WINDOW_MINUTES = 5  # Configurable in settings

# Look for existing incident at same beacon within 5 minutes
dedup_cutoff = timezone.now() - timedelta(minutes=5)

existing_incident = Incident.objects.select_for_update().filter(
    beacon=beacon,
    status__in=[
        Incident.Status.CREATED,
        Incident.Status.ASSIGNED,
        Incident.Status.IN_PROGRESS
    ],
    created_at__gte=dedup_cutoff
).order_by('-created_at').first()
```

**If existing incident found:**
- ✅ New signal (IncidentSignal) is added to the existing incident
- Priority may be escalated based on signal type
- **No new incident created**
- **Existing guards are NOT re-alerted** (prevents spam)

**If no existing incident:**
- ✅ New Incident is created
- ✅ New IncidentSignal is created
- ✅ Conversation thread is created for incident
- ✅ Buzzer status set to PENDING
- ✅ Guards are alerted

### 6. Priority Assignment

Violence detection signals set incident priority to **CRITICAL**:

```python
def get_initial_priority(signal_type):
    priority_map = {
        IncidentSignal.SignalType.VIOLENCE_DETECTED: Incident.Priority.CRITICAL,
        # ...
    }
    return priority_map.get(signal_type, Priority.MEDIUM)
```

**Incident Priority Levels:**
```python
class Priority(IntegerChoices):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4  # ← Violence goes here
```

### 7. Guard Alerting

Once incident is created (not on dedup signals), guards are alerted:

```python
if created:  # Only alert on new incident creation
    alert_guards_for_incident(incident)
```

**Alert Fanout Rules** (incidents/services.py - `get_alert_fanout_rules()`):
- **CRITICAL incidents** (violence) → Alert to **5 guards** via ASSIGNMENT
- Requires response: **True** (guards must accept/decline)
- Uses beacon-proximity search to find nearest guards

### 8. Response Format

**Response (201 Created - new incident):**
```json
{
    "status": "incident_created",
    "ai_event_id": 123,
    "incident_id": "75ca3932-0b7c-475b-834b-0573dfe037dc",
    "signal_id": 456,
    "confidence_score": 0.92,
    "beacon_location": "Library 3F Entrance",
    "incident_status": "CREATED",
    "incident_priority": "Critical",
    "device_id": "AI-MODEL-VIOLENCE-01"
}
```

**Response (200 OK - added to existing):**
```json
{
    "status": "signal_added_to_existing",
    "ai_event_id": 123,
    "incident_id": "75ca3932-0b7c-475b-834b-0573dfe037dc",
    "signal_id": 457,
    "confidence_score": 0.92,
    "beacon_location": "Library 3F Entrance",
    "incident_status": "CREATED",
    "incident_priority": "Critical"
}
```

---

## Image Upload Flow

### 1. API Endpoint

**Endpoint:** `POST /api/incidents/report/`

**Permission:** `IsAuthenticated` (Students only)

**Content-Type:** `multipart/form-data`

**Location:** [incidents/views.py](incidents/views.py#L111-L300)

### 2. Multipart Form Data Format

**Request:**
```
POST /api/incidents/report/ HTTP/1.1
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="beacon_id"

safe:uuid:403:403
------WebKitFormBoundary
Content-Disposition: form-data; name="type"

Safety Concern
------WebKitFormBoundary
Content-Disposition: form-data; name="description"

Suspicious activity in hallway
------WebKitFormBoundary
Content-Disposition: form-data; name="location"

Hallway 3A
------WebKitFormBoundary
Content-Disposition: form-data; name="images"; filename="photo1.jpg"
Content-Type: image/jpeg

[BINARY IMAGE DATA]
------WebKitFormBoundary
Content-Disposition: form-data; name="images"; filename="photo2.jpg"
Content-Type: image/jpeg

[BINARY IMAGE DATA]
------WebKitFormBoundary--
```

**Form Fields:**
- `beacon_id` (optional): UUID of beacon location
- `type` (required): Report type (e.g., "Safety Concern", "Suspicious Activity")
- `description` (required): Detailed description of incident
- `location` (optional): Location description if no beacon_id
- `images` (optional): File array, max 3 images

**Constraints:**
- Maximum 3 images per report
- Either beacon_id OR location must be provided

### 3. Backend Processing Flow

#### Step 1: Extract Multipart Data
```python
# Django's request.FILES handles multipart parsing automatically
images_list = request.FILES.getlist('images', [])

# Form fields come from request.POST (not request.data for multipart)
beacon_id = request.POST.get('beacon_id', '').strip()
report_type = request.POST.get('type', '').strip()
description = request.POST.get('description', '').strip()
location = request.POST.get('location', '').strip()

print(f"Images received: {len(images_list)}")
for i, f in enumerate(images_list):
    print(f"  [{i+1}] {f.name} ({f.content_type}, {f.size} bytes)")
```

#### Step 2: Validation
```python
# Validate required fields
if not report_type:
    return Response({'error': 'type field is required'}, ...)
if not description:
    return Response({'error': 'description field is required'}, ...)
if not beacon_id and not location:
    return Response({'error': 'Either beacon_id or location must be provided'}, ...)

# Validate image count
if len(images_list) > 3:
    return Response({'error': 'Maximum 3 images allowed per report'}, ...)
```

#### Step 3: Incident Creation/Deduplication
Same as violence detection - uses `get_or_create_incident_with_signals()`:

```python
incident, created, signal = get_or_create_incident_with_signals(
    beacon_id=beacon_id,
    signal_type=IncidentSignal.SignalType.STUDENT_REPORT,
    source_user_id=request.user.id,
    description=description
)

# Update report metadata
incident.report_type = report_type
incident.location = location if location else incident.beacon.location_name
incident.save()
```

#### Step 4: Image Processing & Upload

**Critical Steps:**

```python
for idx, image_file in enumerate(images_list[:3]):  # Max 3
    # IMPORTANT: Reset file pointer to beginning
    image_file.seek(0)
    print(f"✅ File pointer reset to position 0")
    
    # Read file into memory to ensure it's complete
    file_data = image_file.read()
    print(f"✅ Read {len(file_data)} bytes from file")
    
    # Reset pointer again after reading
    image_file.seek(0)
    
    # Save to GCS via Django's storage system
    incident_image = IncidentImage.objects.create(
        incident=incident,
        image=image_file,
        uploaded_by=request.user,
        description=f"Image {idx + 1}"
    )
    
    # Verify file was actually saved
    if incident_image.image:
        stored_url = incident_image.image.url
        print(f"✅ Image uploaded successfully!")
        print(f"   GCS URL: {stored_url}")
```

**Key Implementation Details:**
- ✅ File pointer (`seek(0)`) is reset BEFORE and AFTER reading
- ✅ File data is read into memory to ensure completeness
- ✅ Django's ORM handles actual GCS upload via storage backend
- ✅ Image URL is generated automatically after save

#### Step 5: Image Model & Database

**IncidentImage Model** (incidents/models.py):
```python
class IncidentImage(models.Model):
    id = AutoField
    incident = ForeignKey(Incident)  # Which incident
    image = ImageField(upload_to='incidents/%Y/%m/%d/')  # GCS path
    uploaded_by = ForeignKey(User)  # Who uploaded
    uploaded_at = DateTimeField(auto_now_add=True)
    description = CharField(max_length=255)
    
    def save(self, *args, **kwargs):
        """Save image and make it publicly readable on GCS."""
        super().save(*args, **kwargs)  # Upload to GCS
        
        # Make file public on GCS
        if self.image:
            storage_backend = self.image.storage
            if hasattr(storage_backend, 'bucket'):
                blob_name = self.image.name
                blob = storage_backend.bucket.blob(blob_name)
                
                if blob.exists():
                    blob.make_public()  # Set 'public-read' ACL
                    logger.info(f"✓ Image {self.id} made public")
```

**Database Fields:**
- `incident`: Foreign key to parent incident
- `image`: ImageField (stored on GCS)
- `uploaded_by`: User who uploaded
- `uploaded_at`: Auto-generated timestamp
- `description`: Optional image caption

---

## Data Format & API Specifications

### Violence Detection Request/Response

**Request:**
```bash
curl -X POST http://localhost:8000/api/ai/violence-detected/ \
  -H "Content-Type: application/json" \
  -d '{
    "beacon_id": "safe:uuid:403:403",
    "confidence_score": 0.92,
    "description": "Fight detected near library entrance",
    "device_id": "AI-MODEL-VIOLENCE-01"
  }'
```

**Success Response (201):**
```json
{
    "status": "incident_created",
    "ai_event_id": 123,
    "incident_id": "75ca3932-0b7c-475b-834b-0573dfe037dc",
    "signal_id": 456,
    "confidence_score": 0.92,
    "beacon_location": "Library 3F Entrance",
    "incident_status": "CREATED",
    "incident_priority": "Critical",
    "device_id": "AI-MODEL-VIOLENCE-01"
}
```

**Error Response (400):**
```json
{
    "error": "Beacon safe:uuid:403:403 not found or inactive"
}
```

**Below Threshold Response (200):**
```json
{
    "status": "logged_only",
    "ai_event_id": 123,
    "message": "Confidence 0.65 below threshold 0.75"
}
```

### Image Upload Request/Response

**Request (cURL):**
```bash
curl -X POST http://localhost:8000/api/incidents/report/ \
  -H "Authorization: Bearer {token}" \
  -F "beacon_id=safe:uuid:403:403" \
  -F "type=Safety Concern" \
  -F "description=Suspicious activity in hallway" \
  -F "images=@photo1.jpg" \
  -F "images=@photo2.jpg"
```

**Success Response (201):**
```json
{
    "status": "incident_created",
    "incident_id": "75ca3932-0b7c-475b-834b-0573dfe037dd",
    "signal_id": 458,
    "report_type": "Safety Concern",
    "images": [
        {
            "id": 1,
            "image": "http://storage.googleapis.com/bucket/incidents/2025/12/26/image1.jpg",
            "uploaded_by_email": "student@example.com",
            "uploaded_at": "2025-12-26T10:30:45Z",
            "description": "Image 1"
        },
        {
            "id": 2,
            "image": "http://storage.googleapis.com/bucket/incidents/2025/12/26/image2.jpg",
            "uploaded_by_email": "student@example.com",
            "uploaded_at": "2025-12-26T10:30:46Z",
            "description": "Image 2"
        }
    ],
    "incident": {
        "id": "75ca3932-0b7c-475b-834b-0573dfe037dd",
        "status": "CREATED",
        "priority": "MEDIUM",
        "description": "Suspicious activity in hallway",
        "beacon_location": "Hallway 3A",
        "created_at": "2025-12-26T10:30:45Z",
        "signals": [...]
    }
}
```

---

## Backend Processing

### Request Flow Diagram

```
┌─────────────────────────────────┐
│   API Request (POST)            │
│ - Violence: /api/ai/violence... │
│ - Upload: /api/incidents/report │
└──────────────┬──────────────────┘
               │
               ▼
    ┌──────────────────────┐
    │  Input Validation    │
    │  - Beacon exists?    │
    │  - Fields required?  │
    │  - Images ≤ 3?       │
    └──────────┬───────────┘
               │
               ▼
    ┌──────────────────────┐
    │  Create AIEvent      │ (Always, even if confidence < threshold)
    │  (For analytics)     │
    └──────────┬───────────┘
               │
               ▼
    ┌──────────────────────┐
    │  Check Threshold     │
    │  Confidence ≥ 0.75?  │
    └─┬────────────────┬──┘
      │ NO             │ YES
      │                │
      ▼                ▼
 ┌────────┐     ┌─────────────────────┐
 │Logged  │     │ Deduplication       │
 │Only    │     │ Search (5 min)      │
 │        │     │ existing incident   │
 └────────┘     └──────┬───────┬──────┘
                       │       │
                   YES │       │ NO
                       │       │
              ┌────────▼┐   ┌──▼──────────┐
              │Add to   │   │Create New   │
              │existing │   │Incident     │
              │incident │   │             │
              │         │   │Set status:  │
              │(dedup)  │   │CREATED      │
              └────────┬┘   └──┬──────────┘
                       │       │
                       └───┬───┘
                           │
                           ▼
              ┌────────────────────────┐
              │ Alert Guards?          │
              │ Only on NEW incident!  │
              │ (5 guards for CRITICAL)│
              └────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │ Send Push Notifications│
              │ to Alerted Guards      │
              └────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │ Return Response        │
              │ (201 Created / 200 OK) │
              └────────────────────────┘
```

### Atomic Transactions

Both operations use database transactions for consistency:

```python
with transaction.atomic():
    # Lock beacon to prevent concurrent creation
    Beacon.objects.select_for_update().get(id=beacon.id)
    
    # Check for existing incident (with row lock)
    existing_incident = Incident.objects.select_for_update().filter(...)
    
    if existing_incident:
        # Add signal (no re-alert)
        signal = IncidentSignal.objects.create(...)
    else:
        # Create incident, signal, conversation atomically
        incident = Incident.objects.create(...)
        signal = IncidentSignal.objects.create(...)
        conversation = Conversation.objects.create(...)
```

**Prevents:**
- Race conditions (concurrent incident creation)
- Duplicate incidents (pessimistic locking)
- Orphaned data (atomic all-or-nothing)

---

## Cloud Storage Integration

### Storage Configuration

**Settings** (campus_security/settings.py):
```python
GS_BUCKET_NAME = config('GCS_BUCKET_NAME', default='resq-images-prod')
GS_PROJECT_ID = config('GS_PROJECT_ID', default='gen-lang-client-0117249847')
GS_CREDENTIALS = None  # Uses GOOGLE_APPLICATION_CREDENTIALS env var
GS_QUERYSTRING_AUTH = False  # Use public URLs (not signed)

STORAGES = {
    'default': {
        'BACKEND': 'campus_security.storage.PublicGoogleCloudStorage',
        'OPTIONS': {
            'bucket_name': GS_BUCKET_NAME,
            'project_id': GS_PROJECT_ID,
        },
    },
}

DEFAULT_FILE_STORAGE = 'campus_security.storage.PublicGoogleCloudStorage'
MEDIA_URL = 'https://storage.googleapis.com/{}/'.format(GS_BUCKET_NAME)
```

### Custom Storage Backend

**Location:** campus_security/storage.py

```python
class PublicGoogleCloudStorage(GoogleCloudStorage):
    """GCS backend that returns direct public URLs."""
    
    def url(self, name):
        """Return public HTTPS URL for the file."""
        if not name:
            raise ValueError("Missing 'name' argument")
        
        # HTTP for local dev, HTTPS for production
        protocol = "http" if settings.DEBUG else "https"
        
        return f"{protocol}://storage.googleapis.com/{self.bucket.name}/{name}"
```

### Image Upload to GCS

**Flow:**
1. Form multipart data received by Django
2. Django creates TemporaryUploadedFile in memory
3. `IncidentImage.objects.create(image=image_file)` called
4. Django ORM:
   - Calls `storage.save()` (PublicGoogleCloudStorage)
   - Uploads file to GCS bucket: `gs://resq-images-prod/incidents/2025/12/26/image1.jpg`
   - Returns storage path: `incidents/2025/12/26/image1.jpg`
   - Saves database record with path
5. `IncidentImage.save()` override:
   - Gets GCS blob object
   - Calls `blob.make_public()` to set 'public-read' ACL
6. Frontend retrieves via public URL: `https://storage.googleapis.com/resq-images-prod/incidents/2025/12/26/image1.jpg`

### File Pointer Management

**Critical for multipart uploads:**

```python
# File arrives as UploadedFile from Django's multipart parser
image_file = request.FILES['images']

# Step 1: Reset to start
image_file.seek(0)  # Pointer at byte 0

# Step 2: Read entire file to verify
file_data = image_file.read()  # Reads all bytes, pointer moves to EOF

# Step 3: Reset again before saving
image_file.seek(0)  # Pointer back to byte 0

# Step 4: Save (reads from pointer position 0 to EOF)
incident_image.image = image_file
incident_image.save()  # Storage backend reads entire file
```

**Why this matters:**
- After Django's multipart parser, file pointer might not be at position 0
- If not reset, storage backend might read from middle of file (corrupted upload)
- Verify complete file is available before saving

---

## Summary

### Violence Detection
- **Endpoint:** POST /api/ai/violence-detected/
- **Auth:** Public (AllowAny)
- **Threshold:** 75% confidence
- **Always:** Creates AIEvent for logging
- **If above threshold:** Creates Incident or adds signal to existing
- **Deduplication:** 5-minute window per beacon
- **Guards alerted:** 5 guards, CRITICAL priority
- **No re-alert:** When signal added to existing incident

### Image Upload
- **Endpoint:** POST /api/incidents/report/
- **Auth:** Students only (IsAuthenticated)
- **Format:** multipart/form-data
- **Max images:** 3 per report
- **Storage:** Google Cloud Storage
- **Privacy:** Public URLs (no authentication needed to view)
- **File handling:** Pointer reset before/after reading
- **ACL:** Set to public-read after upload
- **Path:** `incidents/YYYY/MM/DD/filename.ext`

### Shared Components
- **Incident deduplication:** 5-minute window
- **Priority escalation:** Based on signal type
- **Atomic transactions:** Prevents race conditions
- **Guard alerts:** Only on new incident creation
- **Database logging:** All events recorded in IncidentEvent
