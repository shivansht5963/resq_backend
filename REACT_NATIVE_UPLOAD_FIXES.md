# React Native Image Upload - 5 Key Fixes

## 1️⃣ Remove Content-Type Header

**Problem:** Setting `Content-Type: multipart/form-data` manually breaks the request.

**Fix:**
```javascript
// ❌ WRONG
const response = await fetch(url, {
  method: 'POST',
  headers: {
    'Content-Type': 'multipart/form-data',  // Remove!
    'Authorization': `Token ${token}`
  },
  body: formData
});

// ✅ CORRECT
const response = await fetch(url, {
  method: 'POST',
  headers: {
    'Authorization': `Token ${token}`
    // FormData auto-sets correct Content-Type
  },
  body: formData
});
```

**Why:** FormData automatically sets the correct `Content-Type` with boundary. If you override it, the boundary is missing and backend can't parse it.

---

## 2️⃣ Add Filename to Blob

**Problem:** Images uploaded without filename/extension.

**Fix:**
```javascript
// ❌ WRONG
formData.append('images', blob);

// ✅ CORRECT
formData.append('images', blob, 'incident-photo.jpg');
//                              ↑ filename + extension
```

**Why:** Backend needs filename to determine file type and save with proper extension.

---

## 3️⃣ Handle React Native File URIs

**Problem:** React Native gives file URIs like `file:///storage/...`, not Blobs.

**Fix:**
```javascript
// Convert file URI to Blob
async function fileUriToBlob(fileUri) {
  try {
    const response = await fetch(fileUri);
    const blob = await response.blob();
    return blob;
  } catch (error) {
    console.error('Failed to convert file:', error);
    return null;
  }
}

// Use in upload
for (let uri of imageUris) {
  const blob = await fileUriToBlob(uri);
  if (blob) {
    formData.append('images', blob, `image-${Date.now()}.jpg`);
  }
}
```

**Why:** React Native returns file paths, not actual file objects. Must fetch and convert to Blob first.

---

## 4️⃣ Add Timeout Handling

**Problem:** Image uploads can be slow and fail silently.

**Fix:**
```javascript
async function uploadWithTimeout(url, options, timeoutMs = 30000) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new Error('Upload timeout - network too slow');
    }
    throw error;
  }
}

// Use:
const response = await uploadWithTimeout(
  '/api/incidents/report/',
  { method: 'POST', headers, body: formData },
  30000 // 30 second timeout
);
```

**Why:** Prevents hanging requests. Shows user "Upload timeout" instead of silent failure.

---

## 5️⃣ Validate Before Upload

**Problem:** Upload fails if missing required data - bad UX.

**Fix:**
```javascript
function validateIncidentReport(data) {
  const { type, description, imageUris, beaconId, location } = data;

  // Check required fields
  if (!type?.trim()) {
    throw new Error('Incident type required');
  }
  if (!description?.trim()) {
    throw new Error('Description required');
  }

  // Check location
  if (!beaconId && !location) {
    throw new Error('Beacon ID or location required');
  }

  // Check images
  if (imageUris.length === 0) {
    throw new Error('Select at least 1 image');
  }
  if (imageUris.length > 3) {
    throw new Error('Max 3 images allowed');
  }

  return true;
}

// Use:
try {
  validateIncidentReport(formData);
  // Proceed with upload
} catch (error) {
  Alert.alert('Validation Error', error.message);
}
```

**Why:** Catch errors before uploading. Better UX and saves bandwidth.

---

## Complete Upload Function

```javascript
async function reportIncident(incidentData) {
  try {
    // 1. Validate
    validateIncidentReport(incidentData);

    // 2. Build FormData
    const formData = new FormData();
    formData.append('type', incidentData.type);
    formData.append('description', incidentData.description);
    if (incidentData.beaconId) {
      formData.append('beacon_id', incidentData.beaconId);
    }
    if (incidentData.location) {
      formData.append('location', incidentData.location);
    }

    // 3. Convert images to Blobs
    for (let i = 0; i < incidentData.imageUris.length; i++) {
      const blob = await fileUriToBlob(incidentData.imageUris[i]);
      if (blob) {
        formData.append('images', blob, `image-${i}.jpg`);
      }
    }

    // 4. Upload with timeout
    const response = await uploadWithTimeout(
      '/api/incidents/report/',
      {
        method: 'POST',
        headers: {
          'Authorization': `Token ${token}`
          // NO Content-Type header!
        },
        body: formData
      },
      30000
    );

    // 5. Check response
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Upload failed');
    }

    const result = await response.json();
    return result; // Has incident ID + image URLs

  } catch (error) {
    console.error('Incident report failed:', error);
    throw error;
  }
}
```

---

## Testing Checklist

- [ ] FormData doesn't set Content-Type header manually
- [ ] All images have filenames with extensions
- [ ] File URIs converted to Blobs before upload
- [ ] Timeout set to 30 seconds
- [ ] Validation runs before sending
- [ ] Error handling shows user-friendly messages
- [ ] Token is valid and in Authorization header
- [ ] Max 3 images enforced
- [ ] beacon_id OR location provided

✅ All checks pass → Upload will work!
