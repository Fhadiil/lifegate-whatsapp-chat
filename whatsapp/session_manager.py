# whatsapp/session_manager.py

from .models import PatientSession, MessageLog
from django.utils import timezone

class SessionManager:
    """Manages patient session state and transitions"""
    
    STATE_TRANSITIONS = {
        'NEW_USER': ['COLLECTING_PROFILE'],
        'COLLECTING_PROFILE': ['COLLECTING_SYMPTOMS', 'CONNECT_TO_CLINICIAN'],
        'COLLECTING_SYMPTOMS': ['AI_FOLLOWUP_QUESTIONS', 'CONNECT_TO_CLINICIAN'],
        'AI_FOLLOWUP_QUESTIONS': ['SUMMARY_AND_RECOMMENDATIONS', 'CONNECT_TO_CLINICIAN'],
        'SUMMARY_AND_RECOMMENDATIONS': ['AWAITING_CLINICIAN_DECISION', 'COMPLETED'],
        'AWAITING_CLINICIAN_DECISION': ['CONNECT_TO_CLINICIAN', 'COMPLETED'],
        'CONNECT_TO_CLINICIAN': ['CLINICIAN_CHAT_ACTIVE'],
        'CLINICIAN_CHAT_ACTIVE': ['COMPLETED'],
    }
    
    def __init__(self, phone_number):
        self.phone_number = phone_number
        self.session = self.get_or_create_session()
    
    def get_or_create_session(self):
        """Get existing session or create new one"""
        session, created = PatientSession.objects.get_or_create(
            phone_number=self.phone_number,
            defaults={'state': 'NEW_USER'}
        )
        
        if not created:
            session.last_message_at = timezone.now()
            session.save(update_fields=['last_message_at'])
        
        return session
    
    def log_message(self, content, is_from_user=True, is_from_clinician=False, clinician=None, message_sid=None):
        """Log a message in the conversation"""
        return MessageLog.objects.create(
            session=self.session,
            content=content,
            is_from_user=is_from_user,
            is_from_clinician=is_from_clinician,
            clinician=clinician,
            message_sid=message_sid
        )
    
    def get_current_state(self):
        """Get current session state"""
        return self.session.state
    
    def transition_to(self, new_state):
        """Safely transition to a new state"""
        current_state = self.session.state
        
        if new_state in self.STATE_TRANSITIONS.get(current_state, []):
            self.session.state = new_state
            self.session.save(update_fields=['state', 'updated_at'])
            return True
        else:
            # Allow some emergency transitions
            if new_state in ['CONNECT_TO_CLINICIAN', 'COMPLETED']:
                self.session.state = new_state
                self.session.save(update_fields=['state', 'updated_at'])
                return True
            return False
    
    def update_profile(self, **kwargs):
        """Update patient profile fields"""
        for key, value in kwargs.items():
            if hasattr(self.session, key):
                setattr(self.session, key, value)
        self.session.save()
    
    def get_conversation_history(self, limit=None):
        """Get message history"""
        messages = self.session.messages.all()
        if limit:
            messages = messages[:limit]
        return [
            {
                'content': msg.content,
                'is_from_user': msg.is_from_user,
                'is_from_clinician': msg.is_from_clinician,
                'timestamp': msg.created_at.isoformat()
            }
            for msg in messages
        ]
    
    def store_data(self, key, value):
        """Store arbitrary data in session"""
        self.session.update_session_data(key, value)
    
    def get_data(self, key, default=None):
        """Retrieve data from session"""
        return self.session.session_data.get(key, default)
    
    def is_profile_complete(self):
        """Check if basic profile is collected"""
        return all([
            self.session.age,
            self.session.gender
        ])
    
    def get_profile_completion_status(self):
        """Returns what profile fields are still needed"""
        needed = []
        if not self.session.age:
            needed.append('age')
        if not self.session.gender:
            needed.append('gender')
        return needed
    
    def escalate_to_clinician(self, reason, ai_assessment=None):
        """Mark session for clinician escalation"""
        from .clinician_escalation import ClinicianEscalation
        
        self.session.escalated_to_clinician = True
        self.session.escalation_reason = reason
        if ai_assessment:
            self.session.ai_overview = ai_assessment
        self.session.save()
        
        # Create escalation queue entry
        escalation = ClinicianEscalation()
        return escalation.create_escalation(self.session, reason, ai_assessment)
    
    def get_full_context(self):
        """Get complete session context for AI or clinician"""
        return {
            'phone_number': self.phone_number,
            'state': self.session.state,
            'profile': {
                'age': self.session.age,
                'gender': self.session.gender,
                'weight': self.session.weight,
                'medical_history': self.session.medical_history
            },
            'session_data': self.session.session_data,
            'conversation_history': self.get_conversation_history(),
            'escalated': self.session.escalated_to_clinician,
            'ai_overview': self.session.ai_overview,
            'recommendations': self.session.recommendation_plan
        }