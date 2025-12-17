
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

from .whatsapp_handler import WhatsAppHandler, WhatsAppTemplates
from .session_manager import SessionManager
from .ai_engine import AIEngineComplete
from .clinician_escalation import ClinicianEscalation, ClinicianMessaging
from .models import PatientSession, EscalationQueue, MessageLog, ClinicianAvailability

import json


@csrf_exempt
@require_http_methods(["POST"])
def whatsapp_webhook(request):
    """
    Main webhook endpoint for receiving WhatsApp messages from Twilio
    """
    
    whatsapp = WhatsAppHandler()
    
    # Validate webhook (optional but recommended for production)
    # if not whatsapp.validate_webhook(request):
    #     return HttpResponse("Invalid request", status=403)
    
    try:
        # Parse incoming message
        message_data = whatsapp.parse_incoming_message(request.POST.dict())
        
        from_number = message_data['from']
        user_message = message_data['body']
        message_sid = message_data['message_sid']
        
        # Initialize session manager
        session_mgr = SessionManager(from_number)
        
        # Log incoming message
        session_mgr.log_message(
            content=user_message,
            is_from_user=True,
            message_sid=message_sid
        )
        
        # Check if clinician chat is active
        if session_mgr.get_current_state() == 'CLINICIAN_CHAT_ACTIVE':
            # Forward message to clinician (via notification system)
            # For now, just acknowledge receipt
            response_text = "Your message has been sent to the doctor. They will respond shortly."
            whatsapp.send_message(from_number, response_text)
            session_mgr.log_message(response_text, is_from_user=False)
            return HttpResponse("OK", status=200)
        
        # Initialize AI engine
        ai_engine = AIEngineComplete()
        
        # Check if user wants to speak with a clinician immediately
        if ai_engine.check_for_clinician_request(user_message):
            return handle_clinician_request(session_mgr, from_number, whatsapp)
        
        # Get current state and generate AI response
        current_state = session_mgr.get_current_state()
        context = session_mgr.get_full_context()
        
        # Generate AI response
        ai_response = ai_engine.generate_response(context, user_message, current_state)
        
        # Handle state transition
        if ai_response.get('next_state'):
            session_mgr.transition_to(ai_response['next_state'])
        
        # Store any data from AI response
        if ai_response.get('data_to_store'):
            for key, value in ai_response['data_to_store'].items():
                if key == 'profile_field':
                    # Update profile field
                    profile_field = value
                    profile_value = ai_response['data_to_store'].get('value')
                    session_mgr.update_profile(**{profile_field: profile_value})
                else:
                    session_mgr.store_data(key, value)
        
        # Handle escalation if needed
        if ai_response.get('should_escalate'):
            escalation_reason = ai_response.get('escalation_reason', 'AI determined clinician review needed')
            ai_assessment = ai_response.get('data_to_store', {}).get('ai_overview', '')
            
            escalation = session_mgr.escalate_to_clinician(escalation_reason, ai_assessment)
            
            if escalation.assigned_to:
                # Clinician assigned immediately
                response_text = WhatsAppTemplates.clinician_joined(escalation.assigned_to.get_full_name())
            else:
                # Added to queue
                response_text = WhatsAppTemplates.clinician_unavailable()
            
            whatsapp.send_message(from_number, response_text)
            session_mgr.log_message(response_text, is_from_user=False)
        
        # If AI generated an assessment, send immediately instead of waiting for next user message
        if ai_response.get("final_assessment"):
            assessment_text = ai_response["final_assessment"]
            
            whatsapp.send_message(from_number, assessment_text)
            session_mgr.log_message(assessment_text, is_from_user=False)
            return HttpResponse("OK", status=200)

        # Otherwise send the normal AI response
        response_text = ai_response['response']

        if ai_response.get('buttons'):
            whatsapp.send_message_with_buttons(from_number, response_text, ai_response['buttons'])
        else:
            whatsapp.send_message(from_number, response_text)

        session_mgr.log_message(response_text, is_from_user=False)

        return HttpResponse("OK", status=200)

        
    except Exception as e:
        print(f"Error in webhook: {e}")
        # Send error message to user
        try:
            whatsapp.send_message(from_number, WhatsAppTemplates.error_message())
        except:
            pass
        
        return HttpResponse("Error", status=500)


def handle_clinician_request(session_mgr, from_number, whatsapp):
    """Handle immediate clinician connection request"""
    
    # Transition to clinician connection state
    session_mgr.transition_to('CONNECT_TO_CLINICIAN')
    
    # Create escalation
    reason = "Patient requested direct clinician consultation"
    context = session_mgr.get_full_context()
    
    # Generate quick AI overview
    ai_engine = AIEngineComplete()
    conversation_summary = "\n".join([
        msg['content'] for msg in context['conversation_history'][-5:]
        if msg['is_from_user']
    ])
    
    ai_overview = f"Patient requested clinician. Recent messages: {conversation_summary}"
    
    escalation = session_mgr.escalate_to_clinician(reason, ai_overview)
    
    # Send appropriate response
    if escalation.assigned_to:
        response_text = WhatsAppTemplates.clinician_joined(escalation.assigned_to.get_full_name())
    else:
        response_text = WhatsAppTemplates.escalation_message()
    
    whatsapp.send_message(from_number, response_text)
    session_mgr.log_message(response_text, is_from_user=False)
    
    return HttpResponse("OK", status=200)


# ===== API ENDPOINTS FOR CLINICIAN PORTAL =====

@login_required
@require_http_methods(["GET"])
def clinician_queue(request):
    """Get escalation queue for clinician"""
    
    clinician = request.user
    escalation_mgr = ClinicianEscalation()
    
    # Get assigned cases
    assigned_cases = escalation_mgr.get_clinician_queue(clinician)
    
    # Get pending cases (if admin/supervisor)
    if request.user.is_staff:
        pending_cases = escalation_mgr.get_pending_escalations()
    else:
        pending_cases = []
    
    # Format response
    assigned_data = [
        {
            'id': case.id,
            'patient_phone': case.session.phone_number,
            'priority': case.priority,
            'reason': case.reason,
            'created_at': case.created_at.isoformat(),
            'assigned_at': case.assigned_at.isoformat() if case.assigned_at else None
        }
        for case in assigned_cases
    ]
    
    pending_data = [
        {
            'id': case.id,
            'patient_phone': case.session.phone_number,
            'priority': case.priority,
            'reason': case.reason,
            'created_at': case.created_at.isoformat()
        }
        for case in pending_cases
    ]
    
    return JsonResponse({
        'assigned_cases': assigned_data,
        'pending_cases': pending_data
    })


@login_required
@require_http_methods(["GET"])
def case_detail(request, case_id):
    """Get detailed information about a specific case"""
    
    escalation = get_object_or_404(EscalationQueue, id=case_id)
    
    # Check permissions
    if escalation.assigned_to != request.user and not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    escalation_mgr = ClinicianEscalation()
    summary = escalation_mgr.get_escalation_summary(escalation)
    
    return JsonResponse(summary)


@login_required
@require_http_methods(["POST"])
def send_clinician_message(request, case_id):
    """Send a message from clinician to patient"""
    
    try:
        data = json.loads(request.body)
        message = data.get('message')
        
        if not message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        escalation = get_object_or_404(EscalationQueue, id=case_id)
        
        # Check permissions
        if escalation.assigned_to != request.user:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        
        # Send message
        ClinicianMessaging.send_clinician_message(
            escalation.session,
            request.user,
            message
        )
        
        return JsonResponse({'status': 'Message sent'})
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def accept_case(request, case_id):
    """Clinician accepts a pending case"""
    
    escalation = get_object_or_404(EscalationQueue, id=case_id)
    
    if escalation.assigned_to:
        return JsonResponse({'error': 'Case already assigned'}, status=400)
    
    escalation_mgr = ClinicianEscalation()
    success = escalation_mgr.assign_to_clinician(escalation, request.user)
    
    if success:
        # Notify patient
        whatsapp = WhatsAppHandler()
        message = WhatsAppTemplates.clinician_joined(request.user.get_full_name())
        whatsapp.send_message(escalation.session.phone_number, message)
        
        return JsonResponse({'status': 'Case accepted'})
    else:
        return JsonResponse({'error': 'Failed to accept case'}, status=500)


@login_required
@require_http_methods(["POST"])
def resolve_case(request, case_id):
    """Mark a case as resolved"""
    
    escalation = get_object_or_404(EscalationQueue, id=case_id)
    
    # Check permissions
    if escalation.assigned_to != request.user and not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    escalation_mgr = ClinicianEscalation()
    escalation_mgr.resolve_escalation(escalation)
    
    # Send closing message to patient
    whatsapp = WhatsAppHandler()
    whatsapp.send_message(
        escalation.session.phone_number,
        WhatsAppTemplates.session_complete()
    )
    
    return JsonResponse({'status': 'Case resolved'})


@login_required
@require_http_methods(["GET"])
def session_history(request, phone_number):
    """Get conversation history for a patient"""
    
    try:
        session = PatientSession.objects.get(phone_number=phone_number)
        messages = MessageLog.objects.filter(session=session).order_by('created_at')
        
        history = [
            {
                'content': msg.content,
                'is_from_user': msg.is_from_user,
                'is_from_clinician': msg.is_from_clinician,
                'clinician': msg.clinician.get_full_name() if msg.clinician else None,
                'timestamp': msg.created_at.isoformat()
            }
            for msg in messages
        ]
        
        return JsonResponse({
            'phone_number': phone_number,
            'history': history,
            'profile': {
                'age': session.age,
                'gender': session.gender,
                'weight': session.weight,
                'medical_history': session.medical_history
            }
        })
        
    except PatientSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)


# ===== ADMIN ENDPOINTS =====

@login_required
@require_http_methods(["GET"])
def admin_dashboard(request):
    """Admin dashboard statistics"""
    
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    from django.db.models import Count, Q
    from datetime import timedelta
    from django.utils import timezone
    
    # Statistics
    today = timezone.now().date()
    week_ago = timezone.now() - timedelta(days=7)
    
    stats = {
        'active_sessions': PatientSession.objects.filter(
            state__in=['COLLECTING_SYMPTOMS', 'AI_FOLLOWUP_QUESTIONS', 'CLINICIAN_CHAT_ACTIVE']
        ).count(),
        'pending_escalations': EscalationQueue.objects.filter(
            is_resolved=False,
            assigned_to__isnull=True
        ).count(),
        'sessions_today': PatientSession.objects.filter(
            created_at__date=today
        ).count(),
        'sessions_this_week': PatientSession.objects.filter(
            created_at__gte=week_ago
        ).count(),
        'escalation_rate': calculate_escalation_rate(),
        'available_clinicians': ClinicianAvailability.objects.filter(
            is_available=True
        ).count()
    }
    
    return JsonResponse(stats)


def calculate_escalation_rate():
    """Calculate percentage of sessions that get escalated"""
    from django.db.models import Count
    
    total = PatientSession.objects.count()
    if total == 0:
        return 0
    
    escalated = PatientSession.objects.filter(escalated_to_clinician=True).count()
    return round((escalated / total) * 100, 2)