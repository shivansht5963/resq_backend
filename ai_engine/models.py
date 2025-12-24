from django.db import models


class AIEvent(models.Model):
    """AI detection event (Vision or Audio)."""

    class EventType(models.TextChoices):
        VISION = "VISION", "Vision Detection"
        AUDIO = "AUDIO", "Audio Detection"

    # Support all three incident types
    reported_incident = models.ForeignKey(
        "incidents.ReportedIncident",
        on_delete=models.CASCADE,
        related_name="ai_events",
        null=True,
        blank=True
    )
    beacon_incident = models.ForeignKey(
        "incidents.BeaconIncident",
        on_delete=models.CASCADE,
        related_name="ai_events",
        null=True,
        blank=True
    )
    panic_incident = models.ForeignKey(
        "incidents.PanicButtonIncident",
        on_delete=models.CASCADE,
        related_name="ai_events",
        null=True,
        blank=True
    )
    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices,
        db_index=True
    )
    confidence_score = models.FloatField(
        help_text="Confidence score between 0 and 1"
    )
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["reported_incident", "-created_at"]),
            models.Index(fields=["beacon_incident", "-created_at"]),
            models.Index(fields=["panic_incident", "-created_at"]),
            models.Index(fields=["event_type", "-created_at"]),
        ]

    def __str__(self):
        incident_id = self.reported_incident.id or self.beacon_incident.id or self.panic_incident.id
        return f"AIEvent ({self.get_event_type_display()}) - Incident {str(incident_id)[:8]}"
