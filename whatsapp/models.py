# whatsapp/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json

class PatientSession(models.Model):
    """Tracks a patient's conversation session"""
    
    STATE_CHOICES = [
        ('NEW_USER', 'New User'),
        ('COLLECTING_PROFILE', 'Collecting Profile'),
        ('COLLECTING_SYMPTOMS', 'Collecting Symptoms'),
        ('AI_FOLLOWUP_QUESTIONS', 'AI Follow-up Questions'),
        ('SUMMARY_AND_RECOMMENDATIONS', 'Summary and Recommendations'),
        ('AWAITING_CLINICIAN_DECISION', 'Awaiting Clinician Decision'),
        ('CONNECT_TO_CLINICIAN', 'Connect to Clinician'),
        ('CLINICIAN_CHAT_ACTIVE', 'Clinician Chat Active'),
        ('COMPLETED', 'Completed'),
    ]
    
    phone_number = models.CharField(max_length=20, unique=True, db_index=True)
    state = models.CharField(max_length=50, choices=STATE_CHOICES, default='NEW_USER')
    
    # Patient Profile
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=20, null=True, blank=True)
    weight = models.FloatField(null=True, blank=True)
    medical_history = models.TextField(null=True, blank=True)
    
    # Session Data
    session_data = models.JSONField(default=dict)  # Stores conversation context
    ai_overview = models.TextField(null=True, blank=True)
    recommendation_plan = models.TextField(null=True, blank=True)
    
    # Escalation
    escalated_to_clinician = models.BooleanField(default=False)
    assigned_clinician = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assigned_sessions'
    )
    escalation_reason = models.TextField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-last_message_at']
        indexes = [
            models.Index(fields=['phone_number', 'state']),
            models.Index(fields=['escalated_to_clinician', 'assigned_clinician']),
        ]
    
    def __str__(self):
        return f"{self.phone_number} - {self.state}"
    
    def get_session_context(self):
        """Returns formatted context for AI"""
        return {
            'phone_number': self.phone_number,
            'age': self.age,
            'gender': self.gender,
            'weight': self.weight,
            'medical_history': self.medical_history,
            'state': self.state,
            'session_data': self.session_data,
            'message_history': list(self.messages.values('content', 'is_from_user', 'created_at'))
        }
    
    def update_session_data(self, key, value):
        """Safely update session data"""
        self.session_data[key] = value
        self.save(update_fields=['session_data', 'updated_at'])


class MessageLog(models.Model):
    """Stores all messages in a conversation"""
    
    session = models.ForeignKey(
        PatientSession, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    content = models.TextField()
    is_from_user = models.BooleanField(default=True)
    is_from_clinician = models.BooleanField(default=False)
    clinician = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    message_sid = models.CharField(max_length=100, null=True, blank=True)
    media_url = models.URLField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
        ]
    
    def __str__(self):
        sender = "User" if self.is_from_user else "System"
        if self.is_from_clinician:
            sender = f"Clinician ({self.clinician.username})"
        return f"{sender}: {self.content[:50]}"


class ClinicianAvailability(models.Model):
    """Tracks clinician availability and workload"""
    
    clinician = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        related_name='availability'
    )
    is_available = models.BooleanField(default=False)
    current_active_cases = models.IntegerField(default=0)
    max_concurrent_cases = models.IntegerField(default=5)
    
    specialization = models.CharField(max_length=100, null=True, blank=True)
    
    last_active = models.DateTimeField(auto_now=True)
    
    def can_accept_case(self):
        return self.is_available and self.current_active_cases < self.max_concurrent_cases
    
    def __str__(self):
        return f"{self.clinician.username} - {'Available' if self.is_available else 'Unavailable'}"


class EscalationQueue(models.Model):
    """Queue for cases waiting for clinician assignment"""
    
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    
    session = models.OneToOneField(
        PatientSession,
        on_delete=models.CASCADE,
        related_name='escalation'
    )
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    reason = models.TextField()
    ai_assessment = models.TextField()
    
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='escalation_queue'
    )
    is_resolved = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-priority', 'created_at']
    
    def __str__(self):
        return f"Escalation for {self.session.phone_number} - {self.priority}"