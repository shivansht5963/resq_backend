# Admin Panel Guide - Violence Detection with Images

## Overview

The Django admin panel has been **fully enhanced** to display and manage all violence detection with images data. You can now:

✅ View all AI detection events (Violence & Scream)
✅ See images attached to each detection
✅ Track incidents created by AI
✅ View image previews and URLs
✅ Monitor confidence scores
✅ Check which signals are AI vs user-generated
✅ Access complete audit trail

---

## How to Access the Admin Panel

1. **Start the server:**
   ```bash
   python manage.py runserver
   ```

2. **Open in browser:**
   ```
   http://localhost:8000/admin/
   ```

3. **Login with admin credentials**

4. **Navigate to the sections below**

---

## 📊 AI Events (Violence & Scream Detection)

### Location: Admin > AI Engine > AI Events

### List View Shows:
- **Beacon** - Location where detection occurred
- **Event Type** - VIOLENCE or SCREAM
- **Confidence Score** - 0.0-1.0 value (color coded)
- **Description** - What triggered the detection
- **📷 Images** - Count and indicator if images attached
- **🚨 Incident** - Link to created incident (if confidence >= threshold)
- **Created At** - Timestamp

### Features:

**Filter by:**
- Event Type (VIOLENCE/SCREAM)
- Date Range (today, this week, etc.)
- Building/Location

**Search for:**
- Location name
- Beacon UUID
- Description text
- Device ID

**Click on any AI Event to see:**

```
┌─────────────────────────────────────────┐
│ AI Event Detail View                    │
├─────────────────────────────────────────┤
│                                         │
│ ▼ AI Detection                          │
│   Beacon: Library 3F Entrance          │
│   Event Type: VIOLENCE                 │
│                                         │
│ ▼ Confidence                            │
│   Score: 95% [████████████████████]    │
│                                         │
│ ▼ Description                           │
│   "Fight detected near library..."     │
│                                         │
│ ▼ Images & Incident                     │
│   📷 3 images                           │
│   🔗 View Incident 72e204c7...         │
│                                         │
│ ▼ Device Info (collapsed)               │
│   Device ID: AI-VISION-001             │
│   AI Type: violence                    │
│   Raw Confidence: 0.95                 │
│                                         │
│ ▼ Details (collapsed)                   │
│   { "device_id": "...", ... }          │
│                                         │
│ ▼ Metadata                              │
│   Created: 2026-01-16 10:01:24         │
│                                         │
└─────────────────────────────────────────┘
```

### Example Data You'll See:

**Violence Detection Example:**
```
Beacon: shivansh home actual beacon
Event Type: VIOLENCE
Confidence Score: 0.92 (92%) ✓
Description: "Fight detected near library entrance"
📷 Images: 3 images attached
🚨 Incident: CRITICAL priority
Device: AI-VISION-001
Detection Time: 2026-01-16 10:01:24
```

---

## 🖼️ Incident Images

### Location: Admin > Incidents > Incident Images

### List View Shows:
- **ID** - Image record ID
- **Incident** - Which incident (clickable link)
- **⚠️ Priority** - Incident priority level
- **Source** - 👤 User or 🤖 AI Detection
- **Uploaded By** - User email or "AI Detection"
- **Uploaded At** - Timestamp
- **Preview** - Thumbnail of image

### Click on Any Image to See:

```
┌──────────────────────────────────────────────┐
│ Incident Image Detail View                   │
├──────────────────────────────────────────────┤
│                                              │
│ ▼ Image Info                                 │
│   Incident: 72e204c7... (click to view)    │
│   [IMAGE PREVIEW - Full Size]               │
│                                              │
│ ▼ Image URL                                  │
│   Public URL:                                │
│   http://storage.googleapis.com/resq-...jpg │
│   📋 Copy URL [Button]                       │
│                                              │
│ ▼ Metadata                                   │
│   Source: 🤖 AI Detection                   │
│   Description: AI Detection Image 1         │
│                                              │
│ ▼ File Details (collapsed)                   │
│   File Name: incident_2026_01_16_001.jpg   │
│   File Size: 2.45 MB                        │
│   Storage: PublicGoogleCloudStorage         │
│   Path: incidents/2026/01/16/...            │
│                                              │
│ ▼ Timestamps                                 │
│   ID: 43                                    │
│   Uploaded: 2026-01-16 10:01:24             │
│                                              │
└──────────────────────────────────────────────┘
```

### Features:
- **Image Preview** - Click to enlarge
- **Copy URL Button** - Copy GCS URL to clipboard
- **File Information** - Size, path, storage type
- **Incident Link** - Jump to related incident
- **Source Indicator** - Shows if from user or AI

---

## 🚨 Incidents (with AI Detection Details)

### Location: Admin > Incidents > Incidents

### List View Now Shows:
- **ID** - Incident UUID
- **Beacon ID** - Hardware beacon identifier
- **Location** - Beacon location name
- **Status** - CREATED, ASSIGNED, IN_PROGRESS, RESOLVED
- **⚠️ Priority** - LOW, MEDIUM, HIGH, CRITICAL (with colors)
- **🤖 AI Detection** - VIOLENCE, SCREAM, or "Manual Report"
- **📷 Images** - Count of attached images
- **📡 Signals** - Number of signals
- **🔔 Buzzer** - Current buzzer status
- **Created At** - Timestamp

### Click on Any Incident to See Complete Details:

```
┌──────────────────────────────────────────────────┐
│ Incident Detail View - ENHANCED                  │
├──────────────────────────────────────────────────┤
│                                                  │
│ ▼ Location                                       │
│   Beacon: Library 3F (click to manage)           │
│   Location: Library 3F Entrance                  │
│                                                  │
│ ▼ Report Info                                    │
│   Type: Safety Concern                           │
│   Description: Fight detected...                │
│                                                  │
│ ▼ Status                                         │
│   Status: CREATED                               │
│   Priority: CRITICAL [Red]                      │
│                                                  │
│ ▼ AI Detection                                   │
│   ┌─────────────────────────────────────────┐  │
│   │ 🤖 AI Event #17                         │  │
│   │ Type: VIOLENCE                          │  │
│   │ Confidence: 92% [Green ✓]               │  │
│   │ Device: AI-VISION-001                   │  │
│   │ Description: Fight detected...          │  │
│   │ Detected: 2026-01-16 10:01:24           │  │
│   └─────────────────────────────────────────┘  │
│                                                  │
│ ▼ Images Summary                                │
│   📷 3 images attached:                         │
│                                                  │
│   [#43] 🤖 AI Detection                        │
│   2026-01-16 10:01:24                          │
│   📥 View Full Image                            │
│                                                  │
│   [#44] 🤖 AI Detection                        │
│   2026-01-16 10:02:15                          │
│   📥 View Full Image                            │
│                                                  │
│   [#45] 👤 user@example.com                     │
│   2026-01-16 10:03:30                          │
│   📥 View Full Image                            │
│                                                  │
│   ... and more                                  │
│                                                  │
│ ▼ Assignment                                     │
│   Guard: John Smith                             │
│   Assigned: 2026-01-16 10:02:00                 │
│                                                  │
│ ▼ Buzzer Control                                │
│   Status: ACTIVE [Red 🔴]                       │
│   Last Updated: 2026-01-16 10:02:00             │
│                                                  │
│ [Signals] [Images] [Events]  (Inline Tabs)      │
│   ┌───────────────────────────────────────┐    │
│   │ Signals:                              │    │
│   │ • VIOLENCE_DETECTED (AI Event #17)   │    │
│   │ • STUDENT_REPORT (Manual)            │    │
│   └───────────────────────────────────────┘    │
│                                                  │
│ [Other Fields...]                               │
│                                                  │
└──────────────────────────────────────────────────┘
```

### Key Sections:

#### 1. **AI Detection** (Collapsed by Default)
- Shows which AI events triggered this incident
- Confidence score with color indicator
- Device information
- Event timestamp

#### 2. **Images Summary** (Always Visible)
- Count of images
- First 5 images displayed
- Source (🤖 AI or 👤 User)
- Direct links to full images
- Count of additional images

#### 3. **Inline Signals Tab**
- Lists all signals that triggered incident
- Shows signal type
- Links to AI events if applicable
- Shows source user/device

#### 4. **Inline Images Tab**
- Thumbnail preview of each image
- Description
- Upload timestamp
- Delete option

---

## 🎯 Quick Reference - What to Check

### To Monitor Violence Detection Activity:

1. **Go to:** Admin > AI Engine > AI Events
2. **Filter by:** Event Type = "VIOLENCE"
3. **Look for:**
   - Recent detections (top of list)
   - High confidence scores (green indicators)
   - Image counts (📷 indicator)
   - Related incidents (🚨 Incident column)

### To Review Detected Images:

1. **Go to:** Admin > Incidents > Incident Images
2. **Filter by:** Source = "AI Detection" (in search)
3. **Look for:**
   - Recent uploads
   - Click to view full image
   - Copy public URL
   - Check file size

### To Check Created Incidents:

1. **Go to:** Admin > Incidents > Incidents
2. **Filter by:** AI Detection = "VIOLENCE" or "SCREAM"
3. **Look for:**
   - Priority level
   - Image count
   - Buzzer status
   - Guard assignment
   - Signal history

### To Track Incident Timeline:

1. **Click on** Incident ID
2. **Scroll to** "Signals" inline section
3. **View all** signals in chronological order
4. **Click on** signal to see details
5. **Jump to** AI Event from signal details
6. **Check** Images inline section for attachment timeline

---

## 💡 Admin Features by Event

### When Violence Detection Happens:

**You'll see:**
```
1. New entry in AI Events list
   - Event Type: VIOLENCE
   - Confidence: (displayed with color)
   - Images count: (if images provided)

2. New entry in Incidents list (if confidence >= 0.75)
   - Status: CREATED
   - Priority: CRITICAL
   - 🤖 AI Detection: VIOLENCE
   - Images: (count)

3. New entries in Incident Images list
   - Source: 🤖 AI Detection
   - Uploaded by: (AI Detection)
   - Full image preview
```

### When Below Threshold:

**You'll see:**
```
1. New entry in AI Events list
   - Confidence: (RED indicator)
   - Status: No incident created
   - But images still attached if provided
```

---

## 🔍 Useful Admin Filters & Searches

### For Violence Detection:

**Filter:**
```
Event Type = VIOLENCE
Date Range = Last 7 days
Building = Main Building
```

**Search:**
```
"fight"
"weapon"
"AI-VISION-001" (device name)
```

### For Images:

**Filter:**
```
Uploaded At = Last 24 hours
Source = AI Detection
```

**Search:**
```
incident UUID
user email
```

### For Incidents:

**Filter:**
```
Status = CREATED
Priority = CRITICAL
AI Detection = VIOLENCE
Buzzer Status = ACTIVE
```

**Search:**
```
beacon location name
incident description
report type
```

---

## 📊 Sample Admin Dashboard View

When you open Admin > AI Engine > AI Events, you'll see:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ AI Events                                           Filter | Search | + │
├─────────────────────────────────────────────────────────────────────────┤
│  Beacon          | Event Type | Confidence | Description | 📷 | 🚨 | At │
├─────────────────────────────────────────────────────────────────────────┤
│ Library 3F       | VIOLENCE   | 0.95 ✓✓✓  | Fight near | 3  | 🔴 | 10:01│
│ Dormitory        | SCREAM     | 0.92 ✓✓✓  | Screaming  | 1  | 🟠 | 09:45│
│ Library 3F       | VIOLENCE   | 0.68       | Uncertain  | 1  | — | 08:30│
│ Science Center   | SCREAM     | 0.85 ✓✓✓  | Loud noise | 2  | 🟡 | 08:15│
│ Library 3F       | VIOLENCE   | 0.92 ✓✓✓  | Fight near | 0  | 🔴 | 08:00│
├─────────────────────────────────────────────────────────────────────────┤
│ Legend: ✓=Above Threshold | 📷=Images | 🚨=Incident | 🔴=Critical      │
└─────────────────────────────────────────────────────────────────────────┘

Click any row to see:
- Full description
- Device information
- All related images
- Full incident details
```

---

## ⚙️ Admin Actions You Can Perform

### On AI Events:
- ✅ View all detection details
- ✅ See attached images
- ✅ Link to related incident
- ✅ View device information
- ❌ Cannot delete (read-only)

### On Images:
- ✅ View preview
- ✅ Copy public URL
- ✅ See file details
- ✅ View GCS storage path
- ✅ Delete if needed
- ✅ Edit description

### On Incidents:
- ✅ View all signals
- ✅ View all images
- ✅ Edit incident status
- ✅ Assign guard
- ✅ Update buzzer status
- ✅ Add resolution notes
- ✅ Resolve incident

### On Incident Signals:
- ✅ View signal details
- ✅ Link to AI event
- ✅ Link to incident
- ✅ View source (user/device/AI)

---

## 🛠️ Troubleshooting Admin View

### Images not showing preview?
- Check image URL is accessible
- Verify GCS bucket permissions
- Check file path in "File Details"

### AI Event not linked to Incident?
- Incident only created if confidence >= threshold
- Check confidence score
- May need to refresh page

### Buzzer status not updating?
- Refresh page to see latest status
- Check incident status changes
- See timestamp in "Buzzer Control" section

### Can't find recent detection?
- Refresh page (F5)
- Check date filters
- Search by beacon location or description
- Check building filter

---

## 📈 Monitoring Dashboard Walkthrough

**Best practice for monitoring violence detection:**

1. **Open Admin > AI Engine > AI Events**
   - Sort by newest first
   - Look for high confidence scores (green)

2. **Filter recent events:**
   - Event Type = VIOLENCE
   - Date = Today

3. **Check each high-confidence event:**
   - Click row to see full details
   - Check image count (📷)
   - Click incident link (🚨)
   - Review images in incident detail

4. **From Incident, check:**
   - Status and priority
   - Buzzer status
   - Guard assignment
   - Image timeline
   - Signal history

5. **Take action if needed:**
   - Edit incident status
   - Change buzzer status
   - Add notes
   - Assign/reassign guard

---

## 🎓 Learning Path for Admin Users

### Level 1: Basic Monitoring
- [ ] Navigate to AI Events list
- [ ] View a violence detection event
- [ ] See image count and type
- [ ] Click to view incident

### Level 2: Detailed Investigation
- [ ] View incident details
- [ ] Review all images inline
- [ ] Check AI detection info
- [ ] See signal history

### Level 3: Full Management
- [ ] Manage incident status
- [ ] Update buzzer control
- [ ] Assign guard
- [ ] Add resolution notes
- [ ] View incident images list

### Level 4: Advanced Analysis
- [ ] Use filters effectively
- [ ] Search by device ID
- [ ] Track AI detection trends
- [ ] Analyze incident patterns

---

## 🚀 You're All Set!

Everything is now in the admin panel for you to:
- ✅ Monitor violence detection in real-time
- ✅ View all images from AI detections
- ✅ Manage incidents and responses
- ✅ Track confidence scores
- ✅ Audit detection history
- ✅ Review evidence images
- ✅ Control IoT buzzers
- ✅ Assign guards

Happy monitoring! 🎉
