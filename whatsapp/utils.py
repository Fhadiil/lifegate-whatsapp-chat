# whatsapp/utils.py
from twilio.rest import Client
from django.conf import settings

def send_whatsapp_message(to, body):
    """
    Send WhatsApp message using Twilio. 'to' must be like 'whatsapp:+234XXXXXXXXX'.
    Returns message SID.
    """
    account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
    auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None)
    from_number = getattr(settings, "TWILIO_WHATSAPP_NUMBER", None)
    if not (account_sid and auth_token and from_number):
        raise RuntimeError("Twilio credentials not configured in settings or .env.")
    client = Client(account_sid, auth_token)
    msg = client.messages.create(
        body=body,
        from_=from_number,
        to=to
    )
    return msg.sid
