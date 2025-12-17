#!/usr/bin/env python
"""
Debug script to check session state
Run: python debug_session.py +1234567890
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lifegate_backend.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from whatsapp.models import PatientSession, MessageLog
from whatsapp.session_manager import SessionManager

def debug_session(phone_number):
    """Debug a specific session"""
    
    print("\n" + "="*60)
    print(f"🔍 DEBUGGING SESSION: {phone_number}")
    print("="*60)
    
    try:
        # Get session
        session = PatientSession.objects.get(phone_number=phone_number)
        
        print(f"\n📱 Session Info:")
        print(f"   Phone: {session.phone_number}")
        print(f"   State: {session.state}")
        print(f"   Created: {session.created_at}")
        print(f"   Last Message: {session.last_message_at}")
        
        print(f"\n👤 Profile:")
        print(f"   Age: {session.age}")
        print(f"   Gender: {session.gender}")
        print(f"   Weight: {session.weight}")
        print(f"   Medical History: {session.medical_history}")
        
        print(f"\n💾 Session Data:")
        for key, value in session.session_data.items():
            print(f"   {key}: {value}")
        
        print(f"\n🔄 Escalation:")
        print(f"   Escalated: {session.escalated_to_clinician}")
        if session.assigned_clinician:
            print(f"   Clinician: {session.assigned_clinician.get_full_name()}")
        
        # Get messages
        messages = MessageLog.objects.filter(session=session).order_by('created_at')
        
        print(f"\n💬 Messages ({messages.count()}):")
        for msg in messages:
            sender = "👤 User" if msg.is_from_user else "🤖 Bot"
            if msg.is_from_clinician:
                sender = f"👨‍⚕️ {msg.clinician.username}"
            timestamp = msg.created_at.strftime("%H:%M:%S")
            print(f"   [{timestamp}] {sender}: {msg.content[:60]}...")
        
        # Test state transition
        print(f"\n🔄 Testing State Transitions:")
        mgr = SessionManager(phone_number)
        current_state = mgr.get_current_state()
        print(f"   Current: {current_state}")
        
        from whatsapp.session_manager import SessionManager
        possible_next = SessionManager.STATE_TRANSITIONS.get(current_state, [])
        print(f"   Possible next states: {possible_next}")
        
        # Show what should happen next
        print(f"\n💡 What Should Happen Next:")
        if current_state == 'NEW_USER':
            print("   ➜ Should show welcome message")
            print("   ➜ Transition to COLLECTING_PROFILE")
        elif current_state == 'COLLECTING_PROFILE':
            if not session.age:
                print("   ➜ Should ask for age")
            elif not session.gender:
                print("   ➜ Should ask for gender")
            else:
                print("   ➜ Should transition to COLLECTING_SYMPTOMS")
        elif current_state == 'COLLECTING_SYMPTOMS':
            print("   ➜ Should process symptom and ask follow-up")
            print("   ➜ Transition to AI_FOLLOWUP_QUESTIONS")
        elif current_state == 'AI_FOLLOWUP_QUESTIONS':
            q_count = session.session_data.get('question_count', 0)
            print(f"   ➜ Questions asked: {q_count}")
            if q_count >= 4:
                print("   ➜ Should generate summary")
                print("   ➜ Transition to SUMMARY_AND_RECOMMENDATIONS")
            else:
                print("   ➜ Should ask next question")
        else:
            print(f"   ➜ State: {current_state}")
        
    except PatientSession.DoesNotExist:
        print(f"\n❌ No session found for {phone_number}")
        print("\n💡 This means:")
        print("   • User hasn't sent any messages yet")
        print("   • Or phone number format is wrong")
        print("\n📝 Try sending a WhatsApp message first")
        
        # Show all sessions
        all_sessions = PatientSession.objects.all().order_by('-created_at')
        if all_sessions.exists():
            print(f"\n📋 Existing Sessions ({all_sessions.count()}):")
            for sess in all_sessions[:5]:
                print(f"   • {sess.phone_number} - {sess.state} - {sess.created_at.strftime('%Y-%m-%d %H:%M')}")
    
    print("\n" + "="*60 + "\n")

def reset_session(phone_number):
    """Reset a session to start over"""
    
    print(f"\n🔄 Resetting session: {phone_number}")
    
    try:
        session = PatientSession.objects.get(phone_number=phone_number)
        
        # Reset to NEW_USER state
        session.state = 'NEW_USER'
        session.age = None
        session.gender = None
        session.weight = None
        session.medical_history = None
        session.session_data = {}
        session.ai_overview = None
        session.recommendation_plan = None
        session.escalated_to_clinician = False
        session.assigned_clinician = None
        session.escalation_reason = None
        session.save()
        
        print("✅ Session reset successfully!")
        print("   State: NEW_USER")
        print("   Profile: Cleared")
        print("   Session data: Cleared")
        print("\n💬 Send a new WhatsApp message to start fresh")
        
    except PatientSession.DoesNotExist:
        print("❌ Session not found")

def list_all_sessions():
    """List all sessions"""
    
    print("\n" + "="*60)
    print("📋 ALL SESSIONS")
    print("="*60)
    
    sessions = PatientSession.objects.all().order_by('-last_message_at')
    
    if not sessions.exists():
        print("\n❌ No sessions found")
        print("   Start by sending a WhatsApp message")
        return
    
    print(f"\nTotal Sessions: {sessions.count()}\n")
    
    for sess in sessions:
        status = "🟢" if sess.state in ['COLLECTING_SYMPTOMS', 'AI_FOLLOWUP_QUESTIONS'] else "⚪"
        print(f"{status} {sess.phone_number}")
        print(f"   State: {sess.state}")
        print(f"   Profile: Age {sess.age}, {sess.gender}")
        print(f"   Messages: {sess.messages.count()}")
        print(f"   Last Active: {sess.last_message_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

def main():
    if len(sys.argv) < 2:
        print("\n📱 Usage:")
        print("   python debug_session.py <phone_number>     - Debug specific session")
        print("   python debug_session.py --list              - List all sessions")
        print("   python debug_session.py <phone> --reset     - Reset a session")
        print("\nExample:")
        print("   python debug_session.py +1234567890")
        print("   python debug_session.py --list")
        return
    
    if sys.argv[1] == '--list':
        list_all_sessions()
    elif len(sys.argv) == 3 and sys.argv[2] == '--reset':
        reset_session(sys.argv[1])
    else:
        debug_session(sys.argv[1])

if __name__ == "__main__":
    main()