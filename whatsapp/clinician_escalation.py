from .models import EscalationQueue, ClinicianAvailability, PatientSession
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q

class ClinicianEscalation:
    """Handles escalation logic and clinician assignment"""
    
    URGENT_KEYWORDS = [
        'chest pain', 'can\'t breathe', 'difficulty breathing',
        'severe pain', 'bleeding heavily', 'unconscious',
        'seizure', 'stroke', 'heart attack', 'suicide'
    ]
    
    HIGH_PRIORITY_KEYWORDS = [
        'severe', 'intense', 'unbearable', 'emergency',
        'very bad', 'getting worse', 'spreading'
    ]
    
    def create_escalation(self, session: PatientSession, reason: str, ai_assessment: str = None) -> EscalationQueue:
        """Create an escalation request"""
        
        # Determine priority based on symptoms and reason
        priority = self._calculate_priority(session, reason)
        
        # Create or update escalation queue entry
        escalation, created = EscalationQueue.objects.get_or_create(
            session=session,
            defaults={
                'priority': priority,
                'reason': reason,
                'ai_assessment': ai_assessment or "No AI assessment available"
            }
        )
        
        if not created:
            # Update existing escalation
            escalation.priority = priority
            escalation.reason = reason
            if ai_assessment:
                escalation.ai_assessment = ai_assessment
            escalation.save()
        
        # Try to assign immediately if clinician available
        self.assign_to_available_clinician(escalation)
        
        return escalation
    
    def _calculate_priority(self, session: PatientSession, reason: str) -> str:
        """Calculate escalation priority based on symptoms and context"""
        
        # Get all messages from the session
        all_messages = ' '.join([
            msg.content.lower() 
            for msg in session.messages.filter(is_from_user=True)
        ])
        
        # Check for urgent keywords
        if any(keyword in all_messages for keyword in self.URGENT_KEYWORDS):
            return 'URGENT'
        
        # Check for high priority indicators
        if any(keyword in all_messages for keyword in self.HIGH_PRIORITY_KEYWORDS):
            return 'HIGH'
        
        # Check for vulnerable populations
        if session.age:
            if session.age < 2 or session.age > 65:
                return 'HIGH'
        
        # Check if pregnant (from medical history)
        if session.medical_history:
            if 'pregnant' in session.medical_history.lower():
                return 'HIGH'
        
        # Default to medium priority
        return 'MEDIUM'
    
    def assign_to_available_clinician(self, escalation: EscalationQueue) -> bool:
        """Try to assign escalation to an available clinician"""
        
        # Find available clinicians
        available_clinicians = ClinicianAvailability.objects.filter(
            is_available=True,
            current_active_cases__lt=models.F('max_concurrent_cases')
        ).select_related('clinician')
        
        if not available_clinicians.exists():
            return False
        
        # Prioritize by workload (least busy first)
        clinician_availability = available_clinicians.order_by('current_active_cases').first()
        
        if clinician_availability:
            return self.assign_to_clinician(escalation, clinician_availability.clinician)
        
        return False
    
    def assign_to_clinician(self, escalation: EscalationQueue, clinician: User) -> bool:
        """Assign an escalation to a specific clinician"""
        
        try:
            # Update escalation
            escalation.assigned_to = clinician
            escalation.assigned_at = timezone.now()
            escalation.save()
            
            # Update session
            session = escalation.session
            session.assigned_clinician = clinician
            session.state = 'CLINICIAN_CHAT_ACTIVE'
            session.save()
            
            # Update clinician workload
            availability = ClinicianAvailability.objects.get(clinician=clinician)
            availability.current_active_cases += 1
            availability.save()
            
            # Send notification to clinician (implementation depends on notification system)
            self._notify_clinician(clinician, escalation)
            
            return True
            
        except Exception as e:
            print(f"Error assigning to clinician: {e}")
            return False
    
    def resolve_escalation(self, escalation: EscalationQueue):
        """Mark escalation as resolved and update clinician workload"""
        
        escalation.is_resolved = True
        escalation.resolved_at = timezone.now()
        escalation.save()
        
        # Update session
        session = escalation.session
        session.state = 'COMPLETED'
        session.save()
        
        # Update clinician workload
        if escalation.assigned_to:
            try:
                availability = ClinicianAvailability.objects.get(clinician=escalation.assigned_to)
                availability.current_active_cases = max(0, availability.current_active_cases - 1)
                availability.save()
            except ClinicianAvailability.DoesNotExist:
                pass
    
    def get_pending_escalations(self):
        """Get all pending escalations ordered by priority"""
        return EscalationQueue.objects.filter(
            is_resolved=False,
            assigned_to__isnull=True
        ).select_related('session').order_by('-priority', 'created_at')
    
    def get_clinician_queue(self, clinician: User):
        """Get all cases assigned to a specific clinician"""
        return EscalationQueue.objects.filter(
            assigned_to=clinician,
            is_resolved=False
        ).select_related('session').order_by('-priority', 'assigned_at')
    
    def _notify_clinician(self, clinician: User, escalation: EscalationQueue):
        """Send notification to clinician (implement based on your notification system)"""
        # This would integrate with email, SMS, push notifications, etc.
        # For now, just a placeholder
        
        notification_data = {
            'clinician_id': clinician.id,
            'escalation_id': escalation.id,
            'patient_phone': escalation.session.phone_number,
            'priority': escalation.priority,
            'reason': escalation.reason
        }
        
        # TODO: Implement actual notification system
        print(f"Notification sent to {clinician.username}: New case escalation")
        
        return notification_data
    
    def get_escalation_summary(self, escalation: EscalationQueue) -> dict:
        """Generate a comprehensive summary for clinician review"""
        
        session = escalation.session
        
        # Get conversation history
        messages = session.messages.all().order_by('created_at')
        
        conversation_summary = []
        for msg in messages:
            sender = "Patient" if msg.is_from_user else "AI Assistant"
            conversation_summary.append({
                'sender': sender,
                'message': msg.content,
                'timestamp': msg.created_at.isoformat()
            })
        
        return {
            'patient_info': {
                'phone': session.phone_number,
                'age': session.age,
                'gender': session.gender,
                'weight': session.weight,
                'medical_history': session.medical_history
            },
            'escalation_info': {
                'priority': escalation.priority,
                'reason': escalation.reason,
                'created_at': escalation.created_at.isoformat()
            },
            'ai_assessment': {
                'overview': session.ai_overview,
                'recommendations': session.recommendation_plan,
                'full_assessment': escalation.ai_assessment
            },
            'conversation_history': conversation_summary,
            'session_data': session.session_data
        }


class ClinicianMessaging:
    """Handles messaging between clinicians and patients"""
    
    @staticmethod
    def send_clinician_message(session: PatientSession, clinician: User, message: str):
        """Send a message from clinician to patient"""
        from .models import MessageLog
        from .whatsapp_handler import WhatsAppHandler
        
        # Log the message
        MessageLog.objects.create(
            session=session,
            content=message,
            is_from_user=False,
            is_from_clinician=True,
            clinician=clinician
        )
        
        # Send via WhatsApp
        whatsapp = WhatsAppHandler()
        whatsapp.send_message(session.phone_number, message)
    
    @staticmethod
    def get_active_clinician_sessions(clinician: User):
        """Get all active sessions for a clinician"""
        return PatientSession.objects.filter(
            assigned_clinician=clinician,
            state='CLINICIAN_CHAT_ACTIVE'
        ).order_by('-last_message_at')