# Image Upload Testing - LOCAL SETUP

## Prerequisites
- Django server must be running separately
- Pillow installed (for image support)
- curl available in PATH

## Step 1: Create Test Image
```bash
python gen_image.py
```
This creates `test_image.jpg` in the project root.

## Step 2: Start Django Server (SEPARATE TERMINAL)
```bash
python manage.py runserver 8000
```
Keep this running - DO NOT close this terminal!

## Step 3: Run Tests (NEW TERMINAL)
```bash
# Windows Batch
test_images.bat

# Or use PowerShell
.\test_complete_image_upload.ps1
```

## What Gets Tested
1. ✓ Single image upload
2. ✓ Multiple images (3) upload  
3. ✓ Text-only report (no images)
4. ✓ Location-based report with image

## Verify in Admin Panel
After running tests:
1. Go to: http://localhost:8000/admin/
2. Login with admin credentials
3. Navigate to: Incidents → Incident Images
4. Check that:
   - Images appear in the list
   - Image previews show correctly
   - File paths are valid

## Expected Response Format
```json
{
  "status": "incident_created",
  "incident_id": "uuid",
  "signal_id": 123,
  "report_type": "Safety Concern",
  "images": [
    {
      "id": 1,
      "image": "/media/incidents/2025/12/28/filename.jpg",
      "uploaded_by_email": "student@example.com",
      "uploaded_at": "2025-12-28T16:30:45.123456Z",
      "description": "Image 1"
    }
  ],
  "incident": {...}
}
```

## File Storage
Images are stored in: `./media/incidents/{YYYY}/{MM}/{DD}/`

Example: `./media/incidents/2025/12/28/incident_img_123.jpg`

## Troubleshooting

### "Connection refused" error
→ Django server not running. Start it in separate terminal:
```bash
python manage.py runserver 8000
```

### "400 Bad Request"
→ Check error in response. Common issues:
- `beacon_id` doesn't exist in database
- Missing required field (`type`, `description`)
- File format not supported

### Images not in admin panel
→ Check file permissions on `./media/` directory
→ Verify `MEDIA_ROOT` in settings.py

### Image preview not showing
→ Check media files are served at `/media/` URL
→ Verify `MEDIA_URL` setting in settings.py
→ Check `format_html` is imported in admin.py

## File Locations
- [incidents/views.py](incidents/views.py#L119) - Report endpoint
- [incidents/admin.py](incidents/admin.py#L145) - Admin display with preview
- [incidents/models.py](incidents/models.py#L165) - IncidentImage model
- [campus_security/settings.py](campus_security/settings.py#L133) - Media configuration
