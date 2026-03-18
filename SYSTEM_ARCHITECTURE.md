# ResQ — Full System Architecture

> **ResQ** is a campus safety and emergency response system. This document describes the complete system architecture including all actors, hardware components, APIs, data flows, and infrastructure integrations.

---

## Architecture Diagram

![ResQ Full System Architecture](C:\Users\Shivansh\.gemini\antigravity\brain\071bdac3-fc64-4ffb-a538-f9cc386aed67\resq_system_architecture_v2_1773721848583.png)

---

## System Components

### 1. 📱 Student Mobile App
- **Role**: Primary interface for students to report incidents and receive emergency alerts
- **Interactions with ResQ System**:
  - `POST /api/auth/signup/` — Register a new account
  - `POST /api/auth/login/` — Authenticate (JWT token)
  - `POST /api/panic/` — Trigger SOS / panic alert
  - `GET/POST /api/incidents/` — View and report incidents
  - `GET/POST /api/conversations/` & `/api/messages/` — In-app chat with guards
  - **Receives**: Push notifications for incident updates and SOS acknowledgements

---

### 2. 🤖 AI CCTV Camera
- **Role**: Edge AI device monitoring campus for violence and audio threats
- **Interactions with ResQ System**:
  - `POST /api/violence-detected/` — Sends detection event + captured image
  - `POST /api/scream-detected/` — Sends scream/audio threat alert
  - `POST /api/ai-detection/` — Legacy unified detection endpoint
- **Output**: Creates an `AIEvent` and auto-escalates to an `Incident` in the system

---

### 3. 🔴 ESP32 Beacon + Buzzer
- **Role**: Dual-purpose IoT device — BLE beacon for indoor location tracking + physical buzzer/panic button
- **As a BLE Beacon**:
  - Broadcasts BLE signals picked up by student/guard mobile apps
  - Mobile app scans nearby beacons and reports proximity to the backend
  - Backend uses beacon proximity data to identify **location of incident**
  - Beacon records stored via `GET/POST /api/beacons/`
- **As a Buzzer/Panic Button**:
  - `POST /api/panic/` — Physical button press triggers a panic incident
  - `GET /api/incidents/buzzer-status/` — Device polls for buzzer trigger commands
  - **Receives**: Buzzer activation command from backend when an incident is confirmed nearby

---

### 4. 🛡️ Guard Mobile App
- **Role**: Security guard interface for receiving assignments and managing incidents
- **Interactions with ResQ System**:
  - `POST /api/auth/login/` — Authenticate as guard
  - `GET/POST /api/guards/` — View and update guard profile
  - `GET/POST /api/assignments/` — View and accept incident assignments
  - `GET/POST /api/alerts/` — Receive and acknowledge alerts
  - `GET/POST /api/conversations/` & `/api/messages/` — Chat with students
  - **Receives**: Push notifications for new incidents and assignments

---

### 5. 🖥️ Admin Web Dashboard
- **Role**: Web-based control panel for system administrators
- **URL Base**: `/admin-panel/`
- **Capabilities**:
  - Manage the full incident lifecycle (Open → In Progress → Resolved)
  - Manage users (Students, Guards, Admins)
  - Configure and view ESP32 Beacons: `GET/POST /api/beacons/`
  - View AI detection event logs: `GET /api/ai-events/`
  - View push notification delivery logs
  - Assign guards to incidents manually

---

### 6. ☁️ Google Cloud Storage (GCS)
- **Role**: Cloud storage for all media files uploaded during incidents
- **Interactions**:
  - Incident images (from AI camera) are stored directly in GCS buckets
  - Media URLs are returned alongside incident data
  - Configurable via `GOOGLE_APPLICATION_CREDENTIALS` and bucket name in settings
  - Falls back to local file storage in development mode

---

### 7. 🗄️ SQLite / PostgreSQL Database
- **Role**: Persistent storage for all application state
- **Key Tables**:

| Table | Description |
|-------|-------------|
| `auth_user` | Users — Student, Guard, Admin roles |
| `accounts_device` | Mobile devices registered for push notifications |
| `accounts_push_notification_log` | Full log of all push notification deliveries |
| `incidents_incident` | All reported incidents with status tracking |
| `incidents_beacon` | Registered ESP32 BLE beacons with location metadata |
| `security_guardprofile` | Guard profiles linked to users |
| `security_guardalert` | Alerts dispatched to guards |
| `security_guardassignment` | Guard ↔ Incident assignment records |
| `ai_engine_aievent` | AI camera detection event log |
| `chat_conversation` | Chat conversations between users |
| `chat_message` | Individual chat messages |

---

## API Endpoint Reference

| Module | Endpoint | Method | Description |
|--------|----------|--------|-------------|
| **Auth** | `/api/auth/signup/` | POST | User registration |
| **Auth** | `/api/auth/login/` | POST | Login (JWT) |
| **Auth** | `/api/auth/logout/` | POST | Logout |
| **Devices** | `/api/devices/register/` | POST | Register device for push notifications |
| **Incidents** | `/api/incidents/` | GET/POST | List / create incidents |
| **Incidents** | `/api/incidents/{id}/` | GET/PATCH | Incident detail / update status |
| **Incidents** | `/api/incidents/buzzer-status/` | GET | ESP32 polls for buzzer trigger |
| **Incidents** | `/api/panic/` | POST | Panic button / SOS press |
| **Beacons** | `/api/beacons/` | GET/POST | BLE beacon management |
| **Security** | `/api/guards/` | GET/POST | Guard profiles |
| **Security** | `/api/assignments/` | GET/POST | Guard-incident assignments |
| **Security** | `/api/alerts/` | GET/POST | Guard alerts |
| **Chat** | `/api/conversations/` | GET/POST | Conversations |
| **Chat** | `/api/messages/` | GET/POST | Messages |
| **AI Engine** | `/api/violence-detected/` | POST | Violence detection event |
| **AI Engine** | `/api/scream-detected/` | POST | Scream/audio detection event |
| **AI Engine** | `/api/ai-detection/` | POST | Legacy detection endpoint |
| **AI Engine** | `/api/ai-events/` | GET | View AI detection event log |
| **Admin** | `/admin-panel/` | — | Admin dashboard (web UI) |

---

## Data Flow: Incident Lifecycle

```
[AI Camera] detects violence on campus
        ↓
POST /api/violence-detected/  (+ image attached)
        ↓
ResQ Backend creates Incident record
Image uploaded → Google Cloud Storage
        ↓
Nearby ESP32 Beacon identifies incident location
        ↓
Nearest Guard identified by beacon proximity
GuardAlert created → GuardAssignment created
        ↓
Push Notification → Guard mobile app alerted
ESP32 Buzzer triggered → Physical alert at location
        ↓
Guard acknowledges → Assignment: IN_PROGRESS
        ↓
Guard resolves → Incident: RESOLVED
        ↓
Push Notification → Student / Reporter notified
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend Framework | Django 4.x + Django REST Framework |
| Authentication | JWT (Token-based) |
| Database | SQLite (dev) / PostgreSQL-compatible (prod) |
| Media Storage | Google Cloud Storage (GCS) |
| Push Notifications | Expo Push Notification API (internal service) |
| IoT Hardware | ESP32 — BLE Beacon + Buzzer via HTTP polling |
| AI Integration | External AI camera via REST webhooks |
| Real-time | Django Channels (ASGI via `asgi.py`) |
| Deployment | Render.com (`Procfile` + `render.yaml`) |
| Admin UI | Django Admin + custom `adminEnd` app |

---

*Generated: 2026-03-17 | ResQ System v1.0*
