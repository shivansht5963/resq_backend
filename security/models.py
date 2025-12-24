from django.db import models
from django.conf import settings
from django.utils import timezone


class GuardProfile(models.Model):
    """Guard-specific profile and beacon-based location tracking."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="guard_profile"
    )
    is_active = models.BooleanField(default=True, db_index=True, help_text="Guard is on duty")
    is_available = models.BooleanField(default=True, db_index=True, help_text="Guard is available for incidents")
    
    # Beacon-based location (replaces GPS)
    current_beacon = models.ForeignKey(
        "incidents.Beacon",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guards_present",
        help_text="Which beacon the guard is near (indoor location)"
    )
    last_beacon_update = models.DateTimeField(null=True, blank=True, help_text="When guard's beacon was last updated")
    
    last_active_at = models.DateTimeField(default=timezone.now, help_text="Last activity timestamp")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_active_at"]
        indexes = [
            models.Index(fields=["is_available"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["current_beacon"]),
        ]

    def __str__(self):
        return f"GuardProfile: {self.user.full_name}"


class GuardAssignment(models.Model):
    """Assignment of guards to incidents."""

    id = models.AutoField(primary_key=True)
    guard = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assignments"
    )
    # Support all three incident types
    reported_incident = models.ForeignKey(
        "incidents.ReportedIncident",
        on_delete=models.CASCADE,
        related_name="guard_assignments",
        null=True,
        blank=True
    )
    beacon_incident = models.ForeignKey(
        "incidents.BeaconIncident",
        on_delete=models.CASCADE,
        related_name="guard_assignments",
        null=True,
        blank=True
    )
    panic_incident = models.ForeignKey(
        "incidents.PanicButtonIncident",
        on_delete=models.CASCADE,
        related_name="guard_assignments",
        null=True,
        blank=True
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-assigned_at"]
        indexes = [
            models.Index(fields=["is_active", "-assigned_at"]),
            models.Index(fields=["reported_incident", "-assigned_at"]),
            models.Index(fields=["beacon_incident", "-assigned_at"]),
            models.Index(fields=["panic_incident", "-assigned_at"]),
        ]

    def __str__(self):
        incident_id = self.reported_incident.id or self.beacon_incident.id or self.panic_incident.id
        return f"{self.guard.full_name} → Incident {str(incident_id)[:8]}"


class DeviceToken(models.Model):
    """FCM device tokens for push notifications."""

    class Platform(models.TextChoices):
        ANDROID = "ANDROID", "Android"
        IOS = "IOS", "iOS"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="device_tokens"
    )
    token = models.TextField(unique=True, db_index=True)
    platform = models.CharField(max_length=20, choices=Platform.choices)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["platform"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.platform}"


class GuardAlert(models.Model):
    """Alert sent to nearest guards when incident is created."""
    
    class AlertStatus(models.TextChoices):
        SENT = "SENT", "Sent"
        ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged"
        DECLINED = "DECLINED", "Declined"
        EXPIRED = "EXPIRED", "Expired"
    
    # Support all three incident types
    reported_incident = models.ForeignKey(
        "incidents.ReportedIncident",
        on_delete=models.CASCADE,
        related_name="guard_alerts",
        null=True,
        blank=True
    )
    beacon_incident = models.ForeignKey(
        "incidents.BeaconIncident",
        on_delete=models.CASCADE,
        related_name="guard_alerts",
        null=True,
        blank=True
    )
    panic_incident = models.ForeignKey(
        "incidents.PanicButtonIncident",
        on_delete=models.CASCADE,
        related_name="guard_alerts",
        null=True,
        blank=True
    )
    guard = models.ForeignKey(
        GuardProfile,
        on_delete=models.CASCADE,
        related_name="alerts"
    )
    distance_km = models.FloatField(help_text="Distance from guard to incident in kilometers")
    status = models.CharField(
        max_length=20,
        choices=AlertStatus.choices,
        default=AlertStatus.SENT,
        db_index=True
    )
    priority_rank = models.IntegerField(default=1, help_text="1=nearest, 2=second nearest, etc")
    sent_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["priority_rank", "-sent_at"]
        indexes = [
            models.Index(fields=["reported_incident", "status"]),
            models.Index(fields=["beacon_incident", "status"]),
            models.Index(fields=["panic_incident", "status"]),
            models.Index(fields=["guard", "status"]),
            models.Index(fields=["status", "-sent_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["reported_incident", "guard"],
                condition=models.Q(reported_incident__isnull=False),
                name="unique_guard_reported_incident_alert"
            ),
            models.UniqueConstraint(
                fields=["beacon_incident", "guard"],
                condition=models.Q(beacon_incident__isnull=False),
                name="unique_guard_beacon_incident_alert"
            ),
            models.UniqueConstraint(
                fields=["panic_incident", "guard"],
                condition=models.Q(panic_incident__isnull=False),
                name="unique_guard_panic_incident_alert"
            )
        ]
    
    def __str__(self):
        incident_id = self.reported_incident.id or self.beacon_incident.id or self.panic_incident.id
        return f"Alert: Guard {self.guard.user.full_name} → Incident {incident_id} ({self.status})"
