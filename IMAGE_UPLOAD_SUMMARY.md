# Image Upload Implementation Summary

## ✅ Complete Implementation

### What Was Added

**1. Backend Model** (`incidents/models.py`)
- New `IncidentImage` model
- Fields: id, incident (FK), image, uploaded_by (FK), uploaded_at, description
- Auto path: `/incidents/{YYYY}/{MM}/{DD}/`
- Supports JPEG, PNG images up to 10MB each
- Max 3 images per incident

**2. Serializers** (`incidents/serializers.py`)
- `IncidentImageSerializer`: Handles image serialization
- Returns: image URL, uploader email, upload timestamp, description
- Integrated into `IncidentDetailedSerializer`

**3. Endpoint** (`incidents/views.py`)
- Updated `report()` action to handle multipart/form-data
- Accepts up to 3 images via `images` field
- Automatically stores images under incident
- Returns image details in response

**4. Database Migration Needed**
```bash
python manage.py makemigrations incidents
python manage.py migrate
```

---

## Request/Response Formats (Ready for Frontend)

### POST /api/incidents/report/ (multipart/form-data)

**Request:**
```
Content-Type: multipart/form-data

form-data:
  beacon_id: "safe:uuid:403:403"        (optional)
  type: "Safety Concern"                (required)
  description: "Description here"       (required)
  location: "Library 3F"                (optional, required if no beacon)
  images: [File, File, File]           (optional, max 3)
```

**Response (201 Created):**
```json
{
  "status": "incident_created",
  "incident_id": "uuid",
  "signal_id": 123,
  "report_type": "Safety Concern",
  "images": [
    {
      "id": 1,
      "image": "https://resq-server.onrender.com/media/incidents/2025/12/26/photo.jpg",
      "uploaded_by_email": "student@example.com",
      "uploaded_at": "2025-12-26T10:30:45Z",
      "description": "Image 1"
    }
  ],
  "incident": {
    "id": "uuid",
    "status": "CREATED",
    "signals": [...],
    "images": [...]
  }
}
```

---

## Frontend Integration Code Examples

### React Native (Expo)
```javascript
const reportWithImages = async (formData) => {
  const data = new FormData();
  
  data.append('beacon_id', formData.beaconId);
  data.append('type', formData.type);
  data.append('description', formData.description);
  
  formData.images.forEach((img, i) => {
    data.append('images', {
      uri: img,
      type: 'image/jpeg',
      name: `image_${i}.jpg`
    });
  });

  const response = await fetch(
    'https://resq-server.onrender.com/api/incidents/report/',
    {
      method: 'POST',
      headers: {
        'Authorization': `Token ${token}`,
      },
      body: data,
    }
  );
  
  return response.json();
};
```

### JavaScript/Web
```javascript
const formElement = document.getElementById('reportForm');
const formData = new FormData(formElement);

// formElement HTML:
// <input name="beacon_id">
// <input name="type">
// <textarea name="description">
// <input type="file" name="images" multiple accept="image/*">

const response = await fetch(
  'https://resq-server.onrender.com/api/incidents/report/',
  {
    method: 'POST',
    headers: {
      'Authorization': `Token ${token}`,
    },
    body: formData,
  }
);
```

---

## Files Changed

### Backend Code:
1. **incidents/models.py**
   - Added `IncidentImage` model with image storage
   
2. **incidents/serializers.py**
   - Added `IncidentImageSerializer`
   - Updated `IncidentDetailedSerializer` to include `images` field
   
3. **incidents/views.py**
   - Updated `report()` action to handle `images` field
   - Added validation: max 3 images per report
   - Auto-associate images with incident
   - Return images in response

### Documentation:
1. **IMAGE_UPLOAD_FRONTEND_GUIDE.md**
   - Complete frontend integration guide
   - Request/response formats
   - Code examples (JS, React Native, cURL)
   - Error handling
   - Best practices
   - Testing checklist

### Testing:
1. **test.http**
   - 2.1g: Image upload with beacon
   - 2.1h: Location-based report without beacon
   - 2.1i: Image validation (max 3 images)

---

## Validation Rules

| Field | Required | Max Length | Format |
|-------|----------|-----------|--------|
| beacon_id | Conditional | 100 | string |
| type | Yes | 100 | string |
| description | Yes | 1000 | string |
| location | Conditional | 255 | string |
| images | No | 3 files | JPEG/PNG, 10MB each |
| **Total images** | - | **3 max** | - |

**Note:** Either `beacon_id` OR `location` must be provided (at least one)

---

## How It Works

```
Frontend submits report with images
        ↓
Server validates fields
        ↓
Check if images ≤ 3
        ↓
Create/Get incident (deduplication logic)
        ↓
Create IncidentSignal (type: STUDENT_REPORT)
        ↓
Save each image to /media/incidents/{YYYY}/{MM}/{DD}/
        ↓
Create IncidentImage records linked to incident
        ↓
Return 201/200 with image URLs and incident details
        ↓
Guards see images in incident detail + chat
```

---

## Guard View of Images

Guards can see all images when viewing incident:

**GET /api/incidents/{incident_id}/**
```json
{
  "id": "uuid",
  "images": [
    {
      "id": 1,
      "image": "https://resq-server.onrender.com/media/incidents/...",
      "uploaded_by_email": "student@example.com",
      "uploaded_at": "2025-12-26T10:30:45Z",
      "description": "Image 1"
    }
  ]
}
```

Guards can also click images to view full size in incident detail screen.

---

## Testing Checklist

### Backend:
- [ ] Run migrations: `python manage.py migrate`
- [ ] Test 2.1g: Upload with beacon + images
- [ ] Test 2.1h: Upload without beacon, location only
- [ ] Test 2.1i: Validate max 3 images error
- [ ] Test with 1 image, 2 images, 3 images
- [ ] Test missing beacon_id AND location (should fail)
- [ ] Test missing type or description (should fail)
- [ ] Verify images stored in correct path
- [ ] Verify image URLs returned correctly
- [ ] Verify incident deduplication still works

### Frontend Integration:
- [ ] Form accepts file input (max 3)
- [ ] Image picker integration
- [ ] Image preview before upload
- [ ] Upload progress indicator
- [ ] Error handling (network, file size, etc.)
- [ ] Success message + navigation
- [ ] Display images in incident detail
- [ ] Display images in chat view

---

## Next Steps for Frontend Team

1. **Read** `IMAGE_UPLOAD_FRONTEND_GUIDE.md` for complete specifications
2. **Implement** image picker (use `expo-image-picker` for React Native)
3. **Test** with test requests in `test.http` (2.1g, 2.1h, 2.1i)
4. **Verify** images display correctly in incident detail
5. **Add** image compression before upload (recommended)
6. **Test** offline scenarios and error cases

---

## Production Considerations

1. **Image Storage:**
   - Currently uses local Django storage
   - For cloud deployment, configure S3/Cloud Storage in settings

2. **Performance:**
   - Consider image resizing on backend
   - Add CDN for image delivery

3. **Security:**
   - Validate image MIME types (done)
   - Scan for malware (implement if needed)
   - Rate limit image uploads per student

4. **Storage Limits:**
   - Monitor disk usage
   - Archive old incidents
   - Set cleanup policies

