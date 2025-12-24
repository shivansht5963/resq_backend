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


class BaseIncident(models.Model):
    """Abstract base class for all incident types."""

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
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ReportedIncident(BaseIncident):
    """Student manually reported incident (beacon is optional)."""

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reported_incidents"
    )
    beacon = models.ForeignKey(
        Beacon,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reported_incidents",
        help_text="Optional: Beacon location where incident occurred"
    )
    description = models.TextField(help_text="Incident description")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["student", "-created_at"]),
        ]
        verbose_name = "Reported Incident"
        verbose_name_plural = "Reported Incidents"

    def __str__(self):
        return f"Report {str(self.id)[:8]} by {self.student.full_name} - {self.get_status_display()}"


class BeaconIncident(BaseIncident):
    """Automatic incident detected via BLE beacon (required beacon)."""

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="beacon_incidents"
    )
    beacon = models.ForeignKey(
        Beacon,
        on_delete=models.PROTECT,
        related_name="beacon_incidents",
        help_text="Required: Beacon that triggered this incident"
    )
    description = models.TextField(blank=True, null=True, help_text="Optional: Incident details")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["beacon", "-created_at"]),
        ]
        verbose_name = "Beacon Incident"
        verbose_name_plural = "Beacon Incidents"

    def __str__(self):
        return f"Beacon Alert {str(self.id)[:8]} at {self.beacon.location_name} - {self.get_status_display()}"


class PanicButtonIncident(BaseIncident):
    """Panic button (ESP32) alert incident."""

    esp32_device = models.ForeignKey(
        'ESP32Device',
        on_delete=models.PROTECT,
        related_name="panic_incidents",
        help_text="ESP32 panic button that was pressed"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="panic_incidents",
        help_text="Student who pressed the button (if known)"
    )
    description = models.TextField(blank=True, null=True, help_text="Optional: Additional context")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["esp32_device", "-created_at"]),
        ]
        verbose_name = "Panic Button Incident"
        verbose_name_plural = "Panic Button Incidents"

    def __str__(self):
        device_name = self.esp32_device.name or self.esp32_device.device_id
        return f"Panic Alert {str(self.id)[:8]} at {device_name} - {self.get_status_display()}"


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
