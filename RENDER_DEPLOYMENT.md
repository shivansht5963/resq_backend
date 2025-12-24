# Render Deployment Guide

## Quick Setup for Render Deployment

### Step 1: Push to GitHub
```bash
git add .
git commit -m "Setup Render deployment"
git push
```

### Step 2: Connect to Render
1. Go to [render.com](https://render.com)
2. Sign up/Login with GitHub
3. Click **New +** → **Web Service**
4. Connect your GitHub repository
5. Select your repository

### Step 3: Configure Deploy Settings
Fill in the form:
- **Name**: `resq-backend` (or your choice)
- **Environment**: Python 3
- **Build Command**: Leave empty (will auto-use render.yaml)
- **Start Command**: Leave empty (will auto-use render.yaml)
- **Plan**: Free (for testing)

### Step 4: Environment Variables (Optional)
Add in Render dashboard → Environment:
```
DEBUG=True
DJANGO_SETTINGS_MODULE=campus_security.settings
```

### Step 5: Deploy
Click **Create Web Service**. Render will:
1. Install dependencies from requirements.txt
2. Run migrations automatically
3. Collect static files
4. Start the server with Gunicorn

## What Was Changed

1. **Procfile** - Startup command for Render
2. **render.yaml** - Complete Render configuration
3. **requirements.txt** - Added Gunicorn (WSGI server)
4. **settings.py** - Updated ALLOWED_HOSTS for Render domains

## Database
- Using SQLite (included in repo)
- Data persists between deployments on Render
- No PostgreSQL needed for testing

## API Endpoints
After deployment, your API will be available at:
```
https://resq-backend.onrender.com/api/accounts/
https://resq-backend.onrender.com/api/incidents/
https://resq-backend.onrender.com/api/security/
https://resq-backend.onrender.com/api/chat/
https://resq-backend.onrender.com/api/ai-engine/
```
*(Replace resq-backend with your actual service name)*

## Testing After Deployment
```bash
curl https://resq-backend.onrender.com/api/accounts/
```

## Logs & Debugging
View logs in Render dashboard → Logs tab. Check for:
- Migration issues
- Database errors
- Import errors

## Notes
- Dev mode enabled (DEBUG = True)
- SQLite database persists on Render
- Free tier has limitations (sleeps after 15 min inactivity)
- Paid tier recommended for production
