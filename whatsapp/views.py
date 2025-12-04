from .models import PatientSession
from .edis import get_next_question, save_answer
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from twilio.twiml.messaging_response import MessagingResponse
from .models import WhatsAppMessage

@csrf_exempt
def whatsapp_webhook(request):
    if request.method == 'POST':
        sender = request.POST.get('From')
        body = request.POST.get('Body', '').strip()

        # Save incoming message log
        WhatsAppMessage.objects.create(sender=sender, body=body, direction='in')

        # Retrieve or create session
        session, created = PatientSession.objects.get_or_create(
            patient_number=sender,
            is_completed=False
        )

        message_prefix = ""

        # LOGIC CHANGE HERE:
        if created:
            message_prefix = "Welcome to Lifegate AI Triage. Let's get some details to help you.\n\n"
        else:
            # Only save the answer if it's an ongoing conversation
            save_answer(session, body)

        # Get next question
        next_question = get_next_question(session)

        # Prepare response
        resp = MessagingResponse()
        
        if next_question:
            # Combine the Welcome message (if new) with the First Question
            full_message = f"{message_prefix}{next_question}"
            resp.message(full_message)
        else:
            resp.message("Thank you! Your responses have been recorded. A physician will review your report soon.")
            session.is_completed = True
            session.save()

        # Save outgoing message log
        WhatsAppMessage.objects.create(sender=sender, body=str(resp), direction='out')

        return HttpResponse(str(resp), content_type='text/xml')
    return HttpResponse("OK")