from django.db import models


class AIEvent(models.Model):
    """AI detection event (Vision or Audio). Logs detection, optionally triggers incident."""

    class EventType(models.TextChoices):
        VIOLENCE = "VIOLENCE", "Violence Detected"
        SCREAM = "SCREAM", "Scream Detected"

    id = models.AutoField(primary_key=True)
    beacon = models.ForeignKey(
        "incidents.Beacon",
        on_delete=models.PROTECT,
        related_name="ai_events",
        null=True,
        blank=True,
        help_text="Location where AI detected the event"
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
            models.Index(fields=["beacon", "-created_at"]),
            models.Index(fields=["event_type", "-created_at"]),
            models.Index(fields=["confidence_score", "-created_at"]),
        ]

    def __str__(self):
        beacon_name = self.beacon.location_name if self.beacon else "No Location"
        return f"AIEvent ({self.get_event_type_display()}) at {beacon_name} - conf={self.confidence_score:.2f}"

