# Netlify Deployment Guide

## Quick Setup for Netlify Deployment

### Step 1: Connect Repository to Netlify
1. Go to [netlify.com](https://netlify.com)
2. Click "New site from Git"
3. Connect your GitHub/GitLab/Bitbucket account
4. Select your repository

### Step 2: Configure Build Settings
Netlify should auto-detect settings from `netlify.toml`. Verify:
- **Build command**: `pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput`
- **Functions directory**: `netlify/functions`
- **Publish directory**: `.`

### Step 3: Environment Variables
In Netlify dashboard, go to Site settings → Build & deploy → Environment:

Add these variables:
```
NETLIFY=true
DJANGO_SETTINGS_MODULE=campus_security.settings
```

### Step 4: Deploy
Simply push to your connected branch. Netlify will automatically build and deploy.

## What Was Changed

1. **netlify.toml** - Configuration file for Netlify builds and redirects
2. **netlify/functions/api.py** - WSGI handler for serverless functions
3. **requirements.txt** - Python dependencies
4. **settings.py** - Updated ALLOWED_HOSTS for Netlify domains, SQLite path for serverless

## Database Notes
- Using SQLite with `/tmp/db.sqlite3` on Netlify (temporary - resets on redeploy)
- For persistent data, you'll need to upgrade to a cloud database later
- For dev/testing, this works fine

## API Endpoints
After deployment, your API will be available at:
```
https://your-site-name.netlify.app/api/accounts/
https://your-site-name.netlify.app/api/incidents/
https://your-site-name.netlify.app/api/security/
https://your-site-name.netlify.app/api/chat/
https://your-site-name.netlify.app/api/ai-engine/
```

## Testing After Deployment
```bash
curl https://your-site-name.netlify.app/api/accounts/
```

## Notes
- Dev mode enabled (DEBUG = True)
- CSRF checks disabled for API endpoints
- Minimal changes - no PostgreSQL migration
- Static files will be served automatically
