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
    first_signal_time = models.DateTimeField(null=True, blank=True, db_index=True)
    last_signal_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
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


class IncidentSignal(models.Model):
    """Source signal that triggered an incident."""
    
    class SignalType(models.TextChoices):
        STUDENT_SOS = "STUDENT_SOS", "Student SOS Report"
        AI_VISION = "AI_VISION", "AI Vision Detection"
        AI_AUDIO = "AI_AUDIO", "AI Audio Detection"
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
        'ESP32Device',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incident_signals",
        help_text="ESP32 device that triggered signal"
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


class ESP32Device(models.Model):
    """ESP32 panic button devices with fixed locations."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device_id = models.CharField(max_length=100, unique=True, db_index=True, help_text="ESP32 device identifier")
    beacon = models.ForeignKey(
        Beacon,
        on_delete=models.PROTECT,
        related_name="esp32_devices",
        help_text="Location of this panic button"
    )
    name = models.CharField(max_length=255, blank=True, help_text="Device location name (e.g., Library Entrance)")
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["device_id"]
        indexes = [
            models.Index(fields=["device_id"]),
            models.Index(fields=["beacon"]),
            models.Index(fields=["is_active"]),
        ]
    
    def __str__(self):
        return f"{self.device_id} ({self.beacon.location_name})"
