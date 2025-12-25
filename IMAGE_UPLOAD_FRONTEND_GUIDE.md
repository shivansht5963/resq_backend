# Image Upload & Incident Reporting - Frontend Integration Guide

## Overview
Students can now report incidents with up to 3 images attached. The API handles:
- Beacon-based reports (with BLE detection)
- Location-based reports (manual location entry)
- Multiple image uploads (max 3 images per report)
- Automatic deduplication (combines reports at same location within 5 minutes)
- Guard alerting on new incident creation

---

## Endpoint: POST /api/incidents/report/

### Content-Type
**`multipart/form-data`** (for file uploads)

### Request Format

#### Form Data (NOT JSON):
```
POST /api/incidents/report/ HTTP/1.1
Host: resq-server.onrender.com
Authorization: Token {student_token}
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="beacon_id"

safe:uuid:403:403
------WebKitFormBoundary
Content-Disposition: form-data; name="type"

Safety Concern
------WebKitFormBoundary
Content-Disposition: form-data; name="description"

Broken glass near library entrance on third floor
------WebKitFormBoundary
Content-Disposition: form-data; name="location"

Library 3F, Main Entrance
------WebKitFormBoundary
Content-Disposition: form-data; name="images"; filename="broken_glass_1.jpg"
Content-Type: image/jpeg

[Binary image data...]
------WebKitFormBoundary
Content-Disposition: form-data; name="images"; filename="broken_glass_2.jpg"
Content-Type: image/jpeg

[Binary image data...]
------WebKitFormBoundary--
```

### Form Fields

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `beacon_id` | string | Conditional* | Hardware beacon ID (from BLE scan) | `"safe:uuid:403:403"` |
| `type` | string | ✅ Yes | Report category | `"Safety Concern"` |
| `description` | string | ✅ Yes | Detailed description (max 1000 chars) | `"Broken glass hazard"` |
| `location` | string | Conditional* | Location description if no beacon | `"Library 3F, Room 201"` |
| `images` | file[] | ❌ No | Image files (max 3, JPEG/PNG) | File upload |

**Conditional: Either `beacon_id` OR `location` must be provided (at least one required)**

### Request Examples

#### JavaScript/React Native (with axios):
```javascript
// Multi-image report with beacon
const formData = new FormData();
formData.append('beacon_id', 'safe:uuid:403:403');
formData.append('type', 'Safety Concern');
formData.append('description', 'Broken glass near entrance');
formData.append('location', 'Library 3F');

// Add images
selectedImages.forEach(imageUri => {
  const imageName = imageUri.split('/').pop();
  const imageType = 'image/jpeg';
  formData.append('images', {
    uri: imageUri,
    type: imageType,
    name: imageName,
  });
});

const response = await axios.post(
  'https://resq-server.onrender.com/api/incidents/report/',
  formData,
  {
    headers: {
      'Authorization': `Token ${studentToken}`,
      'Content-Type': 'multipart/form-data',
    },
  }
);
```

#### cURL:
```bash
curl -X POST \
  https://resq-server.onrender.com/api/incidents/report/ \
  -H "Authorization: Token abc123token" \
  -F "beacon_id=safe:uuid:403:403" \
  -F "type=Safety Concern" \
  -F "description=Broken glass hazard at entrance" \
  -F "location=Library 3F" \
  -F "images=@/path/to/image1.jpg" \
  -F "images=@/path/to/image2.jpg"
```

---

## Response Format

### Success Response: 201 Created (New Incident)
```json
{
  "status": "incident_created",
  "incident_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "signal_id": 42,
  "report_type": "Safety Concern",
  "images": [
    {
      "id": 1,
      "image": "https://resq-server.onrender.com/media/incidents/2025/12/26/broken_glass_1.jpg",
      "uploaded_by_email": "student@example.com",
      "uploaded_at": "2025-12-26T10:30:45Z",
      "description": "Image 1"
    },
    {
      "id": 2,
      "image": "https://resq-server.onrender.com/media/incidents/2025/12/26/broken_glass_2.jpg",
      "uploaded_by_email": "student@example.com",
      "uploaded_at": "2025-12-26T10:30:46Z",
      "description": "Image 2"
    }
  ],
  "incident": {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "beacon": {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "beacon_id": "safe:uuid:403:403",
      "uuid": "uuid-403",
      "location_name": "Library 3F",
      "building": "Main Library",
      "floor": 3,
      "latitude": 40.7128,
      "longitude": -74.0060,
      "is_active": true,
      "created_at": "2025-01-15T08:00:00Z"
    },
    "status": "CREATED",
    "priority": 2,
    "description": "[Safety Concern] Broken glass near entrance",
    "first_signal_time": "2025-12-26T10:30:45Z",
    "last_signal_time": "2025-12-26T10:30:45Z",
    "signals": [
      {
        "id": 42,
        "signal_type": "STUDENT_REPORT",
        "source_user": {
          "id": 5,
          "email": "student@example.com",
          "full_name": "John Doe"
        },
        "timestamp": "2025-12-26T10:30:45Z"
      }
    ],
    "guard_assignment": null,
    "guard_alerts": [],
    "conversation": null,
    "created_at": "2025-12-26T10:30:45Z",
    "updated_at": "2025-12-26T10:30:45Z"
  }
}
```

### Success Response: 200 OK (Signal Added to Existing Incident)
```json
{
  "status": "signal_added_to_existing",
  "incident_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "signal_id": 43,
  "report_type": "Safety Concern",
  "images": [
    {
      "id": 3,
      "image": "https://resq-server.onrender.com/media/incidents/2025/12/26/broken_glass_3.jpg",
      "uploaded_by_email": "student2@example.com",
      "uploaded_at": "2025-12-26T10:31:15Z",
      "description": "Image 1"
    }
  ],
  "incident": {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "status": "CREATED",
    "signals": [
      {
        "id": 42,
        "signal_type": "STUDENT_REPORT",
        "source_user": { ... }
      },
      {
        "id": 43,
        "signal_type": "STUDENT_REPORT",
        "source_user": { ... }
      }
    ],
    ...
  }
}
```

---

## Error Responses

### 400 Bad Request - Missing Required Fields
```json
{
  "type": ["This field is required."],
  "description": ["This field is required."]
}
```

### 400 Bad Request - No Beacon or Location
```json
{
  "error": "Either beacon_id or location must be provided"
}
```

### 400 Bad Request - Too Many Images
```json
{
  "error": "Maximum 3 images allowed per report"
}
```

### 400 Bad Request - Invalid Beacon
```json
{
  "error": "Invalid or inactive beacon: safe:uuid:999:999"
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden - Non-Student User
```json
{
  "error": "Only students can report incidents"
}
```

---

## Image Specifications

### Accepted Formats
- **JPEG** (.jpg, .jpeg)
- **PNG** (.png)

### Size Limits
- **Max per image**: 10 MB
- **Total per report**: 30 MB (3 × 10 MB)

### Storage
- **Path**: `/media/incidents/{YYYY}/{MM}/{DD}/`
- **Lifetime**: Permanent (until incident deleted)
- **Access**: Public URL (included in response)

---

## Frontend Integration Example

### Complete React Native Implementation

```javascript
import * as ImagePicker from 'expo-image-picker';
import axios from 'axios';

const reportIncident = async (reportData) => {
  const {
    beaconId,
    type,
    description,
    location,
    selectedImages,
    studentToken,
  } = reportData;

  // Validate inputs
  if (!type || !description) {
    throw new Error('Type and description are required');
  }
  
  if (!beaconId && !location) {
    throw new Error('Either beacon_id or location must be provided');
  }
  
  if (selectedImages.length > 3) {
    throw new Error('Maximum 3 images allowed');
  }

  // Build form data
  const formData = new FormData();
  
  if (beaconId) {
    formData.append('beacon_id', beaconId);
  }
  
  formData.append('type', type);
  formData.append('description', description);
  
  if (location) {
    formData.append('location', location);
  }

  // Add images
  selectedImages.forEach((imageUri, index) => {
    const fileName = imageUri.split('/').pop();
    formData.append('images', {
      uri: imageUri,
      type: 'image/jpeg',
      name: fileName || `image_${index}.jpg`,
    });
  });

  try {
    const response = await axios.post(
      'https://resq-server.onrender.com/api/incidents/report/',
      formData,
      {
        headers: {
          'Authorization': `Token ${studentToken}`,
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return {
      success: true,
      incidentId: response.data.incident_id,
      status: response.data.status,
      images: response.data.images,
      incident: response.data.incident,
    };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.error || error.message,
    };
  }
};

// Usage
const handleReportIncident = async () => {
  const result = await reportIncident({
    beaconId: 'safe:uuid:403:403',
    type: 'Safety Concern',
    description: 'Broken glass at entrance',
    location: 'Library 3F',
    selectedImages: [
      'file:///storage/emulated/0/DCIM/image1.jpg',
      'file:///storage/emulated/0/DCIM/image2.jpg',
    ],
    studentToken: userToken,
  });

  if (result.success) {
    console.log('Incident reported:', result.incidentId);
    // Navigate to incident detail screen
    navigation.navigate('IncidentDetail', {
      incidentId: result.incidentId,
    });
  } else {
    Alert.alert('Error', result.error);
  }
};
```

---

## Image Picker Integration

### Using expo-image-picker
```javascript
import * as ImagePicker from 'expo-image-picker';

const pickImages = async () => {
  // Request permission
  const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
  if (status !== 'granted') {
    Alert.alert('Permission required', 'Camera roll permission needed');
    return;
  }

  // Pick images
  const result = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ImagePicker.MediaTypeOptions.Images,
    allowsMultiple: true,
    aspect: [4, 3],
    quality: 0.8,
  });

  if (!result.canceled) {
    // Max 3 images
    const selectedUris = result.assets
      .slice(0, 3)
      .map((asset) => asset.uri);
    setSelectedImages(selectedUris);
  }
};
```

---

## Response Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| `201` | New incident created | Show success, navigate to incident |
| `200` | Signal added to existing | Show "Added to existing incident" |
| `400` | Validation error | Show error message to user |
| `401` | Unauthorized | Redirect to login |
| `403` | Only students can report | Show error |
| `500` | Server error | Show generic error, retry option |

---

## Deduplication Logic (Backend)

When student submits a report:
1. Check if incident exists at **same beacon/location**
2. Within **last 5 minutes**
3. With status **CREATED, ASSIGNED, or IN_PROGRESS**

**If match found:**
- Add new `IncidentSignal` (STUDENT_REPORT type)
- Attach images to existing incident
- Return `200 OK` with incident details

**If no match:**
- Create new `Incident`
- Create `IncidentSignal`
- Attach images
- Alert all guards
- Return `201 CREATED`

---

## Best Practices for Frontend

1. **Validate Before Upload**
   ```javascript
   if (!formData.beacon_id && !formData.location) {
     showError('Provide either beacon or location');
     return;
   }
   ```

2. **Show Upload Progress**
   ```javascript
   axios.post(url, formData, {
     onUploadProgress: (progressEvent) => {
       const progress = progressEvent.loaded / progressEvent.total;
       setUploadProgress(progress);
     },
   });
   ```

3. **Compress Images Before Upload**
   ```javascript
   const manipResult = await ImageManipulator.manipulateAsync(
     imageUri,
     [{ resize: { width: 1200, height: 1200 } }],
     { compress: 0.7, format: SaveFormat.JPEG }
   );
   ```

4. **Handle Network Errors**
   ```javascript
   try {
     // upload
   } catch (error) {
     if (error.code === 'ECONNABORTED') {
       showError('Upload timeout. Try again.');
     } else if (error.response?.status === 413) {
       showError('Image too large');
     }
   }
   ```

5. **Show Preview Before Submit**
   - Display selected images in list
   - Allow remove/reorder
   - Show total file size

---

## Chat Integration with Images

When incident is created, guards can view all images in conversation:

```javascript
// In chat view
const getIncidentImages = async (incidentId) => {
  const response = await axios.get(
    `https://resq-server.onrender.com/api/incidents/${incidentId}/`,
    { headers: { 'Authorization': `Token ${token}` } }
  );
  
  return response.data.images; // Array of image objects with URLs
};

// Display in chat
incident.images.map((image) => (
  <Image 
    source={{ uri: image.image }}
    style={{ width: 200, height: 200 }}
  />
))
```

---

## Testing Checklist for Frontend

- [ ] Form accepts beacon_id OR location
- [ ] Shows error if neither provided
- [ ] Image picker limits to 3 images
- [ ] Shows file size validation
- [ ] Displays upload progress
- [ ] Handles network errors gracefully
- [ ] Shows image previews before submit
- [ ] Submits with correct headers
- [ ] Parses response correctly
- [ ] Displays success message
- [ ] Links to incident detail page
- [ ] Shows images in incident detail
- [ ] Works offline (queue for later)

