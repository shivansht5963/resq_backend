# Cloudinary Integration - Setup Guide

## ✅ Backend Integration Complete

All backend changes done. Now you just need Cloudinary credentials.

## Get Cloudinary Credentials (Free Account)

1. Go to: https://cloudinary.com/users/register/free
2. Sign up (free, no credit card needed)
3. Go to Dashboard
4. Copy these 3 values:

```
Cloud Name: ________________
API Key: ________________
API Secret: ________________
```

## 📝 Add Environment Variables

### Local Development (.env file)

Create `.env` in project root:
```
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

### Render Production

Go to Render Dashboard → Settings → Environment Variables

Add:
```
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

## 🔧 What Changed in Backend

### ✅ requirements.txt
- Added `cloudinary==1.36.0`
- Added `django-cloudinary-storage==0.3.0`

### ✅ settings.py
- Configured Cloudinary connection
- Set `DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'`
- Images now upload to Cloudinary, not disk

### ✅ incidents/models.py
- **NO CHANGES** - Still uses `ImageField`
- Django automatically uses Cloudinary storage

### ✅ incidents/views.py
- **NO CHANGES** - Still uses `request.FILES.getlist()`
- Backend still processes same way

## ❌ Frontend Changes

**ZERO FRONTEND CHANGES NEEDED**

Frontend still:
- ✅ Sends multipart/form-data to `/api/incidents/report/`
- ✅ Sends images same way as before
- ✅ Gets image URLs in response
- ✅ Everything works exactly the same

## 🚀 How It Works Now

1. **Frontend** → Sends image to backend `/api/incidents/report/`
2. **Backend** → Receives image, uploads to Cloudinary
3. **Cloudinary** → Stores image, returns URL
4. **Backend** → Saves URL to database
5. **Frontend** → Gets image URL in response

```
Frontend 
   ↓
Backend (validates, processes)
   ↓
Cloudinary (stores, returns URL)
   ↓
Database (saves URL)
   ↓
Frontend (displays)
```

## ✅ Benefits

✅ Works on Render (no ephemeral filesystem issues)
✅ Automatic backups
✅ CDN included (fast delivery)
✅ No disk space limits
✅ Images persist forever
✅ Mobile-friendly URLs
✅ Auto image optimization available

## 🧪 Test Upload

After adding env variables:

```bash
# Local test
python manage.py runserver

# Upload via API
POST /api/incidents/report/
- beacon_id: test_beacon
- type: theft
- description: test
- images: (select image file)
```

Response will have:
```json
{
  "images": [
    {
      "id": 1,
      "image": "https://res.cloudinary.com/your-cloud/image/upload/v123456/resq-campus-security/incidents/...",
      "uploaded_by_email": "user@example.com",
      "uploaded_at": "2025-12-28T10:30:00Z"
    }
  ]
}
```

## 📋 Summary

| Item | Status |
|------|--------|
| Backend code changes | ✅ Done |
| Frontend code changes | ❌ None needed |
| Requirements updated | ✅ Done |
| Settings configured | ✅ Done |
| Cloudinary account | ⏳ Your turn - create free account |
| Environment variables | ⏳ Your turn - add credentials |

---

**Next Steps:**
1. Create Cloudinary free account (2 min)
2. Get 3 credentials (cloud name, api key, api secret)
3. Add to `.env` or Render environment
4. Test upload
5. Done! ✅

---

**Questions?**
- Cloudinary is completely transparent to frontend
- Backend automatically uploads to Cloudinary
- Images stored in `/resq-campus-security/incidents/` folder on Cloudinary
- All 3 credentials needed - none optional
