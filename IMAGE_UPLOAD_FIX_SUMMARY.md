# Image Upload Fix - Complete Summary

## Changes Made

### 1. **Django Settings** ([campus_security/settings.py](campus_security/settings.py#L133))
Added file upload size limits:
```python
# File upload settings
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
FILE_UPLOAD_PERMISSIONS = 0o644
```

### 2. **Admin Interface** ([incidents/admin.py](incidents/admin.py#L1-L160))
- Added `format_html` import for safe HTML rendering
- Fixed image preview display with proper HTML formatting
- Updated inline admin to allow adding new images (`extra = 1`)
- Improved IncidentImageAdmin with larger preview (300x200px)

```python
def image_preview(self, obj):
    if obj.image:
        return format_html(
            '<img src="{}" width="300" height="200" style="max-width: 100%; height: auto;" alt="Incident image" />',
            obj.image.url
        )
    return "No image"
```

### 3. **View Handler** ([incidents/views.py](incidents/views.py#L119-L245))
Complete rewrite of the `report()` method to properly handle multipart/form-data:
- Directly extracts form fields from `request.POST` (not request.data)
- Properly retrieves images from `request.FILES.getlist('images')`
- Validates all required fields BEFORE creating incident
- Saves images directly without relying on serializer
- Added error handling for image save failures
- Proper HTTP status codes (201 for creation, 200 for adding signal)

Key changes:
```python
# Extract form data correctly
beacon_id = (request.POST.get('beacon_id', '') or '').strip()
report_type = request.POST.get('type', '').strip()
description = request.POST.get('description', '').strip()
location = (request.POST.get('location', '') or '').strip()

# Get images from request.FILES (not serializer)
images_list = request.FILES.getlist('images', [])

# Save images directly
for idx, image_file in enumerate(images_list[:3]):
    incident_image = IncidentImage.objects.create(
        incident=incident,
        image=image_file,
        uploaded_by=request.user,
        description=f"Image {idx + 1}"
    )
    image_objects.append(incident_image)
```

### 4. **Serializer** ([incidents/serializers.py](incidents/serializers.py#L182-L192))
Reverted IncidentReportSerializer to not include `images` field since we handle files directly in the view.

## Why These Fixes Work

1. **Multipart Form-Data Handling**: Django REST Framework's `request.data` doesn't work well with multipart requests containing both form fields and files. We use `request.POST` for form fields and `request.FILES` for files directly.

2. **Image Storage**: Images are saved directly to the model AFTER the incident is created, ensuring proper file associations.

3. **Admin Display**: Using `format_html()` ensures the HTML is properly escaped and won't cause XSS issues, while still allowing images to display.

4. **Database**: Images are properly stored in the `IncidentImage` model with the correct incident reference and user info.

## Testing

### Local Testing (for you)
1. Start Django server:
   ```bash
   python manage.py runserver 8000
   ```

2. In another terminal, create test image:
   ```bash
   python gen_image.py
   ```

3. Run tests:
   ```bash
   test_images.bat
   ```

4. Check admin panel:
   - Go to http://localhost:8000/admin/
   - Navigate to Incidents → Incident Images
   - Verify images display with previews

### Server Testing (render.com)
The same code will work on the server because:
- Media files are stored in `/media/` directory
- Whitenoise middleware serves media files in production
- File permissions are properly set

## Expected Behavior

**Request:**
```bash
curl -X POST http://localhost:8000/api/incidents/report/ \
  -H "Authorization: Token {token}" \
  -F "beacon_id=safe:uuid:403:403" \
  -F "type=Safety Concern" \
  -F "description=Test" \
  -F "location=Library" \
  -F "images=@test_image.jpg"
```

**Response (201 Created):**
```json
{
  "status": "incident_created",
  "incident_id": "a2b2fb97-xxxx-xxxx-xxxx-xxxxxxxxxx",
  "signal_id": 123,
  "report_type": "Safety Concern",
  "images": [
    {
      "id": 1,
      "image": "/media/incidents/2025/12/28/xyz.jpg",
      "uploaded_by_email": "student@example.com",
      "uploaded_at": "2025-12-28T16:30:45.123456Z",
      "description": "Image 1"
    }
  ],
  "incident": {...}
}
```

## Files Modified
1. ✅ `campus_security/settings.py` - Added upload limits
2. ✅ `incidents/admin.py` - Fixed preview display
3. ✅ `incidents/views.py` - Rewrote report() method
4. ✅ `incidents/serializers.py` - Simplified serializer

## Files Created (Testing)
1. `test_images.bat` - Windows batch test script
2. `test_complete_image_upload.ps1` - PowerShell test script
3. `gen_image.py` - Create test image
4. `IMAGE_UPLOAD_TESTING.md` - Testing guide
5. `test_image_upload.sh` - Linux/Mac test script
6. `create_test_image.py` - Another image generator
