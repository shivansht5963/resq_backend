# Image Upload Guide for Report Incident Feature

## API Endpoint
```
POST /api/incidents/report/
```

## Authentication
```
Headers: Authorization: Token {user_token}
```

## Request Format
**Content-Type: `multipart/form-data`** (NOT JSON)

## Required Fields

| Field | Type | Required | Details |
|-------|------|----------|---------|
| `type` | string | ✅ | Incident type (e.g., "theft", "injury", "suspicious") |
| `description` | string | ✅ | Detailed incident description |
| `beacon_id` | string | ⚠️ | Beacon ID (if location not provided) |
| `location` | string | ⚠️ | Free text location (if beacon_id not provided) |
| `images` | file[] | ❌ | Image files (optional, max 3 images) |

**Note:** Either `beacon_id` OR `location` must be provided.

## Image Constraints
- **Max images:** 3 per incident
- **Supported formats:** JPG, PNG, GIF, WebP
- **Max file size:** 10MB per file (50MB total)
- **Max upload size:** 10MB in memory

## JavaScript/Fetch Example

```javascript
const formData = new FormData();
formData.append('type', 'theft');
formData.append('description', 'Laptop stolen from library');
formData.append('beacon_id', 'BEACON_123');

// Add images
const imageInput = document.querySelector('input[type="file"]');
for (let file of imageInput.files) {
  formData.append('images', file);
}

const response = await fetch('/api/incidents/report/', {
  method: 'POST',
  headers: {
    'Authorization': `Token ${userToken}`,
  },
  body: formData
});

const data = await response.json();
console.log(data); // Returns 201 with incident data including image URLs
```

## React/Axios Example

```javascript
const handleImageUpload = async (formData) => {
  try {
    const response = await axios.post('/api/incidents/report/', formData, {
      headers: {
        'Authorization': `Token ${userToken}`,
        'Content-Type': 'multipart/form-data'
      }
    });
    return response.data; // Full incident object with image URLs
  } catch (error) {
    console.error('Upload failed:', error.response.data);
  }
};
```

## Success Response (201 Created)
```json
{
  "id": "incident-uuid",
  "type": "theft",
  "description": "Laptop stolen from library",
  "status": "open",
  "beacon_id": "BEACON_123",
  "images": [
    {
      "id": 1,
      "image": "/media/incidents/2025/12/28/photo1.jpg",
      "uploaded_by_email": "student@university.edu",
      "uploaded_at": "2025-12-28T10:30:00Z",
      "description": "Image 1"
    },
    {
      "id": 2,
      "image": "/media/incidents/2025/12/28/photo2.jpg",
      "uploaded_by_email": "student@university.edu",
      "uploaded_at": "2025-12-28T10:30:01Z",
      "description": "Image 2"
    }
  ]
}
```

## Common Issues & Fixes

### ❌ Image not opening when downloaded
**Cause:** Corrupted image file or invalid format
**Fix:** 
- Ensure file is a valid JPG/PNG/GIF/WebP image before upload
- Test image locally before uploading
- Try uploading from different device/camera
- Compress image using image tool first

### ❌ Image shows broken link in admin preview
**Cause:** Media files not being served or image URL is wrong
**Fix:**
- Verify `/media/` URLs in response are absolute (not relative)
- Check that Django is serving media files (WhiteNoise in production)
- On Render: Ensure disk volume is mounted (`render.yaml` disks section)
- Check file permissions on server

### ❌ Using JSON Content-Type
**Wrong:**
```javascript
headers: { 'Content-Type': 'application/json' }
```
**Fix:** Use `FormData` or set `Content-Type: multipart/form-data`

### ❌ Sending images in JSON body
**Wrong:**
```javascript
const data = { description: "...", images: imageBlob }
```
**Fix:** Use FormData and append files to it

### ❌ Missing beacon_id OR location
**Error:** 400 Bad Request - "Either beacon_id or location required"
**Fix:** Provide at least one location identifier

### ❌ More than 3 images
**Error:** 400 Bad Request - "Max 3 images allowed"
**Fix:** Limit file input to 3 files max

### ❌ File too large
**Error:** 413 Payload Too Large
**Fix:** Compress images before upload (aim for <2MB each)

## Image Compression Tip (JavaScript)
```javascript
async function compressImage(file) {
  const canvas = await html2canvas(file);
  return new Promise(resolve => {
    canvas.toBlob(resolve, 'image/jpeg', 0.7);
  });
}
```

## Testing with cURL
```bash
curl -X POST http://localhost:8000/api/incidents/report/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -F "type=theft" \
  -F "description=Stolen item" \
  -F "beacon_id=BEACON_123" \
  -F "images=@photo1.jpg" \
  -F "images=@photo2.jpg"
```

## Summary
1. Use **multipart/form-data** (FormData in JS)
2. Include **required fields** (type, description, beacon_id/location)
3. Append **max 3 images**
4. Send **Authorization header** with token
5. Expect **201 response** with image URLs ready to display

---
**Status:** Images are now **saved to persistent storage on Render** and **served via API**. Frontend can display image URLs directly from response.
