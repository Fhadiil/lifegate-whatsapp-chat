# lifegate/whatsapp_handler.py

import os
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

class WhatsAppHandler:
    """Handles WhatsApp messaging via Twilio API"""
    
    def __init__(self):
        self.account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        self.auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        self.whatsapp_number = os.environ.get('TWILIO_WHATSAPP_NUMBER')  # Format: whatsapp:+1234567890
        
        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
        else:
            self.client = None
            print("Warning: Twilio credentials not configured")
    
    def send_message(self, to_number: str, message: str, media_url: str = None):
        """
        Send a WhatsApp message to a user
        
        Args:
            to_number: Recipient's phone number (format: +1234567890 or whatsapp:+1234567890)
            message: Message text
            media_url: Optional media URL for images/documents
        """
        
        if not self.client:
            print(f"[MOCK] Would send to {to_number}: {message}")
            return None
        
        # Ensure proper WhatsApp format
        if not to_number.startswith('whatsapp:'):
            to_number = f'whatsapp:{to_number}'
        
        try:
            message_params = {
                'from_': self.whatsapp_number,
                'to': to_number,
                'body': message
            }
            
            if media_url:
                message_params['media_url'] = [media_url]
            
            sent_message = self.client.messages.create(**message_params)
            
            return {
                'sid': sent_message.sid,
                'status': sent_message.status,
                'to': to_number
            }
            
        except Exception as e:
            print(f"Error sending WhatsApp message: {e}")
            return None
    
    def send_message_with_buttons(self, to_number: str, message: str, buttons: list):
        """
        Send a message with interactive buttons
        Note: Twilio WhatsApp button support varies by API version
        
        Args:
            to_number: Recipient's phone number
            message: Message text
            buttons: List of button labels
        """
        
        # For basic Twilio WhatsApp, we append button options to the message
        # More advanced button support requires WhatsApp Business API
        
        if buttons:
            button_text = "\n\n" + "\n".join([f"• {btn}" for btn in buttons])
            full_message = message + button_text
        else:
            full_message = message
        
        return self.send_message(to_number, full_message)
    
    def parse_incoming_message(self, request_data: dict) -> dict:
        """
        Parse incoming webhook data from Twilio
        
        Args:
            request_data: POST data from Twilio webhook
            
        Returns:
            dict with parsed message data
        """
        
        # Extract phone number (remove 'whatsapp:' prefix)
        from_number = request_data.get('From', '')
        if from_number.startswith('whatsapp:'):
            from_number = from_number.replace('whatsapp:', '')
        
        return {
            'from': from_number,
            'body': request_data.get('Body', ''),
            'message_sid': request_data.get('MessageSid', ''),
            'num_media': int(request_data.get('NumMedia', 0)),
            'media_url': request_data.get('MediaUrl0') if int(request_data.get('NumMedia', 0)) > 0 else None,
            'profile_name': request_data.get('ProfileName', ''),
            'wa_id': request_data.get('WaId', '')
        }
    
    def create_response(self, message: str) -> str:
        """
        Create a TwiML response for immediate webhook reply
        (Alternative to sending via API)
        
        Args:
            message: Response message
            
        Returns:
            TwiML XML string
        """
        
        response = MessagingResponse()
        response.message(message)
        return str(response)
    
    def validate_webhook(self, request):
        """
        Validate that webhook request is from Twilio
        
        Args:
            request: Django request object
            
        Returns:
            bool: True if valid Twilio request
        """
        from twilio.request_validator import RequestValidator
        
        if not self.auth_token:
            return True  # Skip validation in dev mode
        
        validator = RequestValidator(self.auth_token)
        
        # Get the URL Twilio used to make the request
        url = request.build_absolute_uri()
        
        # Get POST data
        post_data = request.POST.dict()
        
        # Get X-Twilio-Signature header
        signature = request.META.get('HTTP_X_TWILIO_SIGNATURE', '')
        
        return validator.validate(url, post_data, signature)
    
    def send_typing_indicator(self, to_number: str):
        """
        Simulate typing indicator (if supported by Twilio API version)
        Note: Basic WhatsApp API may not support this
        """
        # This is a placeholder - actual implementation depends on Twilio API capabilities
        pass
    
    def format_rich_message(self, content: dict) -> str:
        """
        Format a rich message with sections
        
        Args:
            content: dict with 'title', 'body', 'footer', etc.
            
        Returns:
            Formatted message string
        """
        
        parts = []
        
        if content.get('title'):
            parts.append(f"*{content['title']}*")
            parts.append("")
        
        if content.get('body'):
            parts.append(content['body'])
            parts.append("")
        
        if content.get('bullets'):
            for bullet in content['bullets']:
                parts.append(f"• {bullet}")
            parts.append("")
        
        if content.get('footer'):
            parts.append(f"_{content['footer']}_")
        
        return "\n".join(parts)


class WhatsAppTemplates:
    """Pre-defined message templates for consistency"""
    
    @staticmethod
    def welcome_message():
        return """Welcome to Lifegate! 👋

I'm your AI health assistant. I can help you:
• Understand your symptoms
• Provide health recommendations
• Connect you with a clinician if needed

All conversations are confidential and secure.

Reply 'Start' to begin, or type 'Doctor' anytime to speak with a clinician directly."""
    
    @staticmethod
    def escalation_message():
        return """I'll connect you with a clinician right away. 

A doctor will join this chat shortly. Please wait a moment...

⏱️ Average wait time: 2-5 minutes"""
    
    @staticmethod
    def clinician_joined(clinician_name: str):
        return f"""Dr. {clinician_name} has joined the chat. 👨‍⚕️

You can now discuss your concerns directly with the doctor."""
    
    @staticmethod
    def session_complete():
        return """Thank you for using Lifegate! 

Take care and feel better soon. If you need assistance again, just send us a message anytime. 🌟

Stay healthy!"""
    
    @staticmethod
    def error_message():
        return """I apologize, but I'm having trouble processing your request right now. 

Please try again in a moment, or type 'Doctor' to speak with a clinician directly."""
    
    @staticmethod
    def clinician_unavailable():
        return """All our clinicians are currently busy. 

We've added you to the queue and a doctor will reach out as soon as possible.

Priority: Based on your symptoms
Expected wait: 10-15 minutes

You'll receive a message when a clinician is available."""