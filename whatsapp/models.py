from django.db import models

class WhatsAppMessage(models.Model):
    sender = models.CharField(max_length=50)
    body = models.TextField()
    direction = models.CharField(max_length=10, choices=(("in", "Incoming"), ("out", "Outgoing")))
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.direction} - {self.sender} - {self.body[:20]}"


from django.utils import timezone
import uuid

class PatientSession(models.Model):
    session_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    patient_number = models.CharField(max_length=50)
    current_tier = models.IntegerField(default=1)  # Tracks EDIS tier
    symptoms_collected = models.JSONField(default=dict)  # Stores answers
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient_number} - Tier {self.current_tier}"
