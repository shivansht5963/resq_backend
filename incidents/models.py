import uuid
from django.db import models
from django.conf import settings


class Beacon(models.Model):
    """Physical beacon for indoor location tracking (iBeacon/Eddystone)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    beacon_id = models.CharField(max_length=100, unique=True, db_index=True, null=True, blank=True, help_text="Hardware beacon ID (UUID:major:minor)")
    uuid = models.CharField(max_length=36, db_index=True, help_text="iBeacon UUID")
    major = models.IntegerField(help_text="iBeacon major value")
    minor = models.IntegerField(help_text="iBeacon minor value")
    
    # Location information (fixed)
    location_name = models.CharField(max_length=255, help_text="e.g., Library Entrance, Hallway 3A")
    building = models.CharField(max_length=255, help_text="e.g., Building A, Science Center")
    floor = models.IntegerField(help_text="Floor number")
    latitude = models.FloatField(null=True, blank=True, help_text="Fixed beacon latitude")
    longitude = models.FloatField(null=True, blank=True, help_text="Fixed beacon longitude")
    
    # Beacon proximity (for expanding-radius guard search)
    nearby_beacons = models.ManyToManyField(
        'self',
        through='BeaconProximity',
        symmetrical=False,
        related_name='nearby_from',
        help_text="Nearby beacons in priority order for guard search expansion"
    )
    
    is_active = models.BooleanField(default=True, db_index=True, help_text="Is beacon operational")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["building", "floor", "location_name"]
        indexes = [
            models.Index(fields=["beacon_id"]),
            models.Index(fields=["uuid", "major", "minor"]),
            models.Index(fields=["building", "floor"]),
            models.Index(fields=["is_active"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["major", "minor"], name="unique_beacon_major_minor")
        ]

    def __str__(self):
        return f"{self.location_name} ({self.building}, Floor {self.floor})"


class BeaconProximity(models.Model):
    """
    Defines proximity relationship between beacons with priority order.
    Used for expanding-radius guard search when no guards found at incident beacon.
    """
    
    from_beacon = models.ForeignKey(
        Beacon,
        on_delete=models.CASCADE,
        related_name='proximity_from'
    )
    to_beacon = models.ForeignKey(
        Beacon,
        on_delete=models.CASCADE,
        related_name='proximity_to'
    )
    priority = models.IntegerField(
        default=1,
        db_index=True,
        help_text="Lower number = higher priority (1 = nearest/same floor, 2 = adjacent floor, 3+ = far zones)"
    )
    
    class Meta:
        ordering = ['priority']
        constraints = [
            models.UniqueConstraint(
                fields=['from_beacon', 'to_beacon'],
                name='unique_beacon_pair'
            )
        ]
        indexes = [
            models.Index(fields=['from_beacon', 'priority']),
        ]
    
    def __str__(self):
        return f"{self.from_beacon.location_name} → {self.to_beacon.location_name} (Priority {self.priority})"


class Incident(models.Model):
    """Unified incident model - beacon-centric emergency."""
    
    class Status(models.TextChoices):
        CREATED = "CREATED", "Created"
        ASSIGNED = "ASSIGNED", "Assigned to Guard"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        RESOLVED = "RESOLVED", "Resolved"

    class Priority(models.IntegerChoices):
        LOW = 1, "Low"
        MEDIUM = 2, "Medium"
        HIGH = 3, "High"
        CRITICAL = 4, "Critical"
    
    class ResolutionType(models.TextChoices):
        RESOLVED_BY_GUARD = "RESOLVED_BY_GUARD", "Resolved by Guard"
        ESCALATED_TO_ADMIN = "ESCALATED_TO_ADMIN", "Escalated to Admin"
    
    class BuzzerStatus(models.TextChoices):
        INACTIVE = "INACTIVE", "Inactive (No Incident)"
        PENDING = "PENDING", "Pending (Incident Created, No Guard Yet)"
        ACTIVE = "ACTIVE", "Active (Incident Assigned to Guard)"
        ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged (Guard En Route)"
        RESOLVED = "RESOLVED", "Resolved (Incident Complete)"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    beacon = models.ForeignKey(
        Beacon,
        on_delete=models.PROTECT,
        related_name="incidents",
        help_text="Location of emergency (mandatory)"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CREATED,
        db_index=True
    )
    priority = models.IntegerField(
        choices=Priority.choices,
        default=Priority.MEDIUM,
        db_index=True
    )
    description = models.TextField(blank=True, help_text="Optional incident description")
    report_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Type of report (e.g., Safety Concern, Suspicious Activity, Infrastructure Issue)"
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        help_text="Location description if different from beacon"
    )
    first_signal_time = models.DateTimeField(null=True, blank=True, db_index=True)
    last_signal_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Resolution tracking
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="resolved_incidents",
        help_text="Guard/Admin who resolved this incident"
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True, help_text="Notes about how incident was resolved")
    resolution_type = models.CharField(
        max_length=30,
        choices=ResolutionType.choices,
        blank=True,
        help_text="How the incident was resolved"
    )
    
    # Assignment tracking (denormalized for quick access)
    current_assigned_guard = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="currently_assigned_incidents",
        help_text="Currently assigned guard"
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    
    # Buzzer Status for IoT devices (ESP32)
    buzzer_status = models.CharField(
        max_length=20,
        choices=BuzzerStatus.choices,
        default=BuzzerStatus.INACTIVE,
        db_index=True,
        help_text="Current buzzer status for ESP32 devices at this beacon"
    )
    buzzer_last_updated = models.DateTimeField(
        auto_now=True,
        help_text="Last time buzzer status was changed"
    )
    
    # Alert stats
    total_alerts_sent = models.PositiveIntegerField(default=0, help_text="Total alerts sent to guards")
    total_alerts_declined = models.PositiveIntegerField(default=0, help_text="Total alerts declined by guards")
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["beacon", "-created_at"]),
            models.Index(fields=["beacon", "status", "-created_at"]),
        ]
        verbose_name = "Incident"
        verbose_name_plural = "Incidents"
    
    def __str__(self):
        return f"Incident {str(self.id)[:8]} at {self.beacon.location_name} - {self.get_status_display()}"


class IncidentImage(models.Model):
    """Images attached to an incident report (max 3 per incident)."""
    
    id = models.AutoField(primary_key=True)
    incident = models.ForeignKey(
        Incident,
        on_delete=models.CASCADE,
        related_name="images",
        help_text="Incident this image belongs to"
    )
    image = models.ImageField(
        upload_to='incidents/%Y/%m/%d/',
        help_text="Incident photo/screenshot"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incident_images",
        help_text="User who uploaded image"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Image caption (optional)"
    )
    
    class Meta:
        ordering = ['uploaded_at']
        verbose_name = "Incident Image"
        verbose_name_plural = "Incident Images"
    
    def save(self, *args, **kwargs):
        """Save image and make it publicly readable on GCS."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Save model to database AND upload file to storage
        super().save(*args, **kwargs)
        
        # After save, try to make the file public (only for GCS)
        if self.image:
            try:
                # Check if using GCS backend
                storage_backend = self.image.storage
                if hasattr(storage_backend, 'bucket'):
                    bucket = storage_backend.bucket
                    blob_name = self.image.name
                    blob = bucket.blob(blob_name)
                    
                    # Try to make public
                    if blob.exists():
                        blob.make_public()
                        logger.info(f"✓ Image {self.id} made public: gs://{bucket.name}/{blob_name}")
                    else:
                        logger.warning(f"⚠ Image {self.id} blob not found immediately after save: {blob_name}")
                        # Try again with a short delay in case of eventual consistency
                        import time
                        time.sleep(0.5)
                        if blob.exists():
                            blob.make_public()
                            logger.info(f"✓ Image {self.id} made public (after retry): gs://{bucket.name}/{blob_name}")
                else:
                    logger.debug(f"Image {self.id} not using GCS backend (local storage)")
            except Exception as e:
                # Log but don't fail - image already saved to storage
                logger.error(f"✗ Could not make image {self.id} public: {type(e).__name__}: {e}")
    
    def __str__(self):
        uploader = self.uploaded_by.email if self.uploaded_by else "Unknown"
        return f"Image for {self.incident.id} uploaded by {uploader}"


class IncidentSignal(models.Model):
    """Source signal that triggered an incident."""
    
    class SignalType(models.TextChoices):
        STUDENT_SOS = "STUDENT_SOS", "Student SOS Report"
        STUDENT_REPORT = "STUDENT_REPORT", "Student General Report"
        VIOLENCE_DETECTED = "VIOLENCE_DETECTED", "Violence Detected"
        SCREAM_DETECTED = "SCREAM_DETECTED", "Scream Detected"
        PANIC_BUTTON = "PANIC_BUTTON", "Panic Button (ESP32)"
    
    id = models.AutoField(primary_key=True)
    incident = models.ForeignKey(
        Incident,
        on_delete=models.CASCADE,
        related_name="signals"
    )
    signal_type = models.CharField(
        max_length=50,
        choices=SignalType.choices,
        db_index=True
    )
    source_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incident_signals",
        help_text="User who triggered signal (SOS)"
    )
    source_device = models.ForeignKey(
        'PhysicalDevice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incident_signals",
        help_text="Physical device that triggered signal"
    )
    ai_event = models.ForeignKey(
        'ai_engine.AIEvent',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incident_signal",
        help_text="AI event that triggered signal"
    )
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["incident", "-created_at"]),
            models.Index(fields=["signal_type", "-created_at"]),
        ]
    
    def __str__(self):
        return f"Signal {self.id} ({self.get_signal_type_display()}) → Incident {str(self.incident.id)[:8]}"


class PhysicalDevice(models.Model):
    """Physical devices (panic buttons, AI detectors) with fixed locations."""

    class DeviceType(models.TextChoices):
        PANIC_BUTTON = "PANIC_BUTTON", "Panic Button"
        AI_VISION = "AI_VISION", "AI Vision Detection"
        AI_AUDIO = "AI_AUDIO", "AI Audio Detection"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device_id = models.CharField(max_length=100, unique=True, db_index=True, help_text="Device identifier (e.g., ESP32-001, AI-VISION-01)")
    device_type = models.CharField(
        max_length=50,
        choices=DeviceType.choices,
        default=DeviceType.PANIC_BUTTON,
        db_index=True,
        help_text="Type of device: Panic button, AI vision, or AI audio"
    )
    beacon = models.ForeignKey(
        Beacon,
        on_delete=models.PROTECT,
        related_name="physical_devices",
        help_text="Location where this device is situated"
    )
    name = models.CharField(max_length=255, blank=True, help_text="Device location name (e.g., Library Entrance)")
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["device_id"]
        indexes = [
            models.Index(fields=["device_id"]),
            models.Index(fields=["device_type"]),
            models.Index(fields=["beacon"]),
            models.Index(fields=["is_active"]),
        ]
    
    def __str__(self):
        return f"{self.device_id} ({self.get_device_type_display()}) - {self.beacon.location_name}"


class IncidentEvent(models.Model):
    """
    Complete audit trail for incident lifecycle.
    Tracks all events from creation to resolution including alerts, assignments, and status changes.
    """
    
    class EventType(models.TextChoices):
        # Incident lifecycle
        INCIDENT_CREATED = "INCIDENT_CREATED", "Incident Created"
        STATUS_CHANGED = "STATUS_CHANGED", "Status Changed"
        PRIORITY_CHANGED = "PRIORITY_CHANGED", "Priority Changed"
        
        # Guard alerts
        ALERT_SENT = "ALERT_SENT", "Alert Sent to Guard"
        ALERT_DELIVERED = "ALERT_DELIVERED", "Push Notification Delivered"
        ALERT_FAILED = "ALERT_FAILED", "Push Notification Failed"
        
        # Guard responses
        ALERT_ACCEPTED = "ALERT_ACCEPTED", "Guard Accepted Alert"
        ALERT_DECLINED = "ALERT_DECLINED", "Guard Declined Alert"
        ALERT_EXPIRED = "ALERT_EXPIRED", "Alert Expired (No Response)"
        
        # Assignment
        GUARD_ASSIGNED = "GUARD_ASSIGNED", "Guard Assigned"
        GUARD_UNASSIGNED = "GUARD_UNASSIGNED", "Guard Unassigned"
        
        # Resolution
        RESOLUTION_STARTED = "RESOLUTION_STARTED", "Resolution Started"
        INCIDENT_RESOLVED = "INCIDENT_RESOLVED", "Incident Resolved"
        
        # Escalation
        ESCALATED_NO_RESPONSE = "ESCALATED_NO_RESPONSE", "Escalated - No Response"
        ALL_GUARDS_EXHAUSTED = "ALL_GUARDS_EXHAUSTED", "All Guards Exhausted"
    
    id = models.AutoField(primary_key=True)
    incident = models.ForeignKey(
        Incident,
        on_delete=models.CASCADE,
        related_name="events"
    )
    event_type = models.CharField(
        max_length=50,
        choices=EventType.choices,
        db_index=True
    )
    
    # Who triggered the event
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="incident_events_triggered",
        help_text="User who triggered this event"
    )
    
    # Target guard (for alert events)
    target_guard = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="incident_events_targeted",
        help_text="Guard targeted by this event (for alerts)"
    )
    
    # State transition tracking
    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, blank=True)
    previous_priority = models.IntegerField(null=True, blank=True)
    new_priority = models.IntegerField(null=True, blank=True)
    
    # Additional context
    details = models.JSONField(default=dict, blank=True, help_text="Flexible metadata for event")
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["incident", "-created_at"]),
            models.Index(fields=["event_type", "-created_at"]),
            models.Index(fields=["actor", "-created_at"]),
            models.Index(fields=["target_guard", "-created_at"]),
        ]
        verbose_name = "Incident Event"
        verbose_name_plural = "Incident Events"
    
    def __str__(self):
        return f"[{self.get_event_type_display()}] Incident {str(self.incident.id)[:8]} at {self.created_at.strftime('%H:%M:%S')}"

