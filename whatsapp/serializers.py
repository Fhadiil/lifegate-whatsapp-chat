
from rest_framework import serializers
from .models import PatientSession, MessageLog, EscalationQueue, ClinicianAvailability
from django.contrib.auth.models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']


class MessageLogSerializer(serializers.ModelSerializer):
    """Serializer for message logs"""
    
    clinician_name = serializers.SerializerMethodField()
    
    class Meta:
        model = MessageLog
        fields = [
            'id', 'content', 'is_from_user', 'is_from_clinician',
            'clinician_name', 'created_at', 'media_url'
        ]
    
    def get_clinician_name(self, obj):
        if obj.clinician:
            return obj.clinician.get_full_name()
        return None


class PatientSessionSerializer(serializers.ModelSerializer):
    """Serializer for patient sessions"""
    
    messages = MessageLogSerializer(many=True, read_only=True)
    assigned_clinician_name = serializers.SerializerMethodField()
    
    class Meta:
        model = PatientSession
        fields = [
            'id', 'phone_number', 'state', 'age', 'gender', 'weight',
            'medical_history', 'session_data', 'ai_overview', 'recommendation_plan',
            'escalated_to_clinician', 'assigned_clinician_name', 'escalation_reason',
            'created_at', 'updated_at', 'last_message_at', 'messages'
        ]
    
    def get_assigned_clinician_name(self, obj):
        if obj.assigned_clinician:
            return obj.assigned_clinician.get_full_name()
        return None


class EscalationQueueSerializer(serializers.ModelSerializer):
    """Serializer for escalation queue"""
    
    session = PatientSessionSerializer(read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    
    class Meta:
        model = EscalationQueue
        fields = [
            'id', 'session', 'priority', 'reason', 'ai_assessment',
            'assigned_to_name', 'is_resolved', 'created_at',
            'assigned_at', 'resolved_at'
        ]
    
    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return obj.assigned_to.get_full_name()
        return None


class ClinicianAvailabilitySerializer(serializers.ModelSerializer):
    """Serializer for clinician availability"""
    
    clinician = UserSerializer(read_only=True)
    
    class Meta:
        model = ClinicianAvailability
        fields = [
            'id', 'clinician', 'is_available', 'current_active_cases',
            'max_concurrent_cases', 'specialization', 'last_active'
        ]


class MessageCreateSerializer(serializers.Serializer):
    """Serializer for creating messages"""
    
    message = serializers.CharField(max_length=5000)
    
    def validate_message(self, value):
        if not value.strip():
            raise serializers.ValidationError("Message cannot be empty")
        return value.strip()