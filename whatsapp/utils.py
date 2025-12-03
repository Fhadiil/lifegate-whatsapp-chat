from twilio.rest import Client
from django.conf import settings

client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

def send_whatsapp_message(to, body):
    """
    Send WhatsApp message using Twilio API
    :param to: recipient number in format 'whatsapp:+234XXXXXXXXX'
    :param body: message text
    """
    message = client.messages.create(
        from_=settings.TWILIO_WHATSAPP_NUMBER,
        body=body,
        to=to
    )
    return message.sid
