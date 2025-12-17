import json
import os
import requests
from typing import Dict, List
from openai import OpenAI
from groq import Groq

class AIEngineComplete:
    """
    Complete AI Engine rewritten to use the OpenAI API
    Mirrors your Claude-based architecture exactly.
    """

    # def __init__(self):
    #     # OpenAI client
    #     self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    #     self.model = "gpt-4.1"   # You can switch to gpt-4.1-mini for cheaper cost

    #     if not os.environ.get("OPENAI_API_KEY"):
    #         print("⚠️ WARNING: No OPENAI_API_KEY found. Using fallback responses.")
    
    
    def __init__(self):
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        self.model = "llama-3.3-70b-versatile"   

        if not os.environ.get("GROQ_API_KEY"):
            print("⚠️ WARNING: No GROQ_API_KEY found. Using fallback responses.")

    # =====================================================================
    #  OPENAI API CALL 
    # =====================================================================

    # def _call_openai_api(self, system_prompt: str, conversation: List[Dict], 
    #                       max_tokens: int = 1000) -> Dict:
    #     """
    #     Core OpenAI call that replaces your Claude API call.
    #     """

    #     if not os.environ.get("OPENAI_API_KEY"):
    #         return {
    #             "success": False,
    #             "error": "No API key configured",
    #             "fallback": True
    #         }

    #     try:
    #         print("\n🤖 Calling OpenAI API...")
    #         print(f"   System prompt length: {len(system_prompt)} chars")
    #         print(f"   Conversation messages: {len(conversation)}")

    #         # Convert conversation into OpenAI format
    #         messages = [{"role": "system", "content": system_prompt}]

    #         for msg in conversation:
    #             messages.append({
    #                 "role": msg["role"],
    #                 "content": msg["content"]
    #             })

    #         # OpenAI chat request
    #         response = self.client.chat.completions.create(
    #             model=self.model,
    #             messages=messages,
    #             max_tokens=max_tokens,
    #             temperature=0.2
    #         )

    #         text = response.choices[0].message.content

    #         print(f"✅ OpenAI responded: {text[:100]}...")

    #         return {
    #             "success": True,
    #             "text": text,
    #             "usage": response.usage,
    #             "model": self.model
    #         }

    #     except Exception as e:
    #         print(f"❌ OpenAI API call failed: {str(e)}")
    #         return {
    #             "success": False,
    #             "error": str(e),
    #             "fallback": True
    #         }
    
    def _call_openai_api(self, system_prompt: str, conversation: List[Dict], max_tokens: int = 1000):

        if not os.environ.get("GROQ_API_KEY"):
            return {
                "success": False,
                "error": "No API key configured",
                "fallback": True
            }

        try:
            print("\n🤖 Calling Groq API...")
            print(f"   System prompt length: {len(system_prompt)} chars")
            print(f"   Conversation messages: {len(conversation)}")

            # Convert conversation to Groq chat format
            messages = [{"role": "system", "content": system_prompt}]
            for msg in conversation:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

            # Groq chat completion call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.2
            )

            text = response.choices[0].message.content
            print(f"✅ Groq responded: {text[:100]}...")

            return {
                "success": True,
                "text": text,
                "usage": response.usage,
                "model": self.model
            }

        except Exception as e:
            print(f"❌ Groq API call failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "fallback": True
            }


    # 
    # =====================================================================
    #  STATE MACHINE (UNCHANGED)
    # =====================================================================

    def generate_response(self, session_context: Dict, user_message: str, state: str) -> Dict:

        if state == 'NEW_USER':
            return self._handle_new_user()

        elif state == 'COLLECTING_PROFILE':
            return self._handle_profile_collection(session_context, user_message)

        elif state == 'COLLECTING_SYMPTOMS':
            return self._handle_symptom_collection(session_context, user_message)

        elif state == 'AI_FOLLOWUP_QUESTIONS':
            return self._handle_followup_questions(session_context, user_message)

        elif state == 'SUMMARY_AND_RECOMMENDATIONS':
            return self._handle_summary_generation(session_context)

        elif state == 'AWAITING_CLINICIAN_DECISION':
            return self._handle_clinician_decision(user_message)

        # Default fallback
        return {
            'response': "I'm here to help. What brings you here today?",
            'next_state': 'COLLECTING_SYMPTOMS',
            'should_escalate': False,
            'data_to_store': {}
        }

    # =====================================================================
    #  SYMPTOM COLLECTION (NOW CALLS OPENAI)
    # =====================================================================

    def _handle_symptom_collection(self, context: Dict, message: str) -> Dict:

        system_prompt = """You are a medical AI assistant conducting a patient triage interview.

Your role:
- Ask ONE clear, clinical follow-up question
- Be empathetic and professional
- Focus on onset, duration, severity, associated symptoms
- Respond ONLY with JSON in this format:

{
  "question": "Your follow-up question",
  "should_escalate": false,
  "escalation_reason": ""
}

Red flags requiring escalation:
- Chest pain
- Breathing difficulty
- Stroke signs
- Heavy bleeding
- Loss of consciousness
"""

        profile = context.get("profile", {})
        conversation = [
            {
                "role": "user",
                "content": f"Patient profile: Age {profile.get('age','unknown')}, Gender {profile.get('gender','unknown')}. Symptoms: {message}"
            }
        ]

        result = self._call_openai_api(system_prompt, conversation)

        if result.get("success"):
            try:
                data = self._parse_json_response(result["text"])
                return {
                    "response": data["question"],
                    "next_state": "AI_FOLLOWUP_QUESTIONS",
                    "should_escalate": data["should_escalate"],
                    "escalation_reason": data.get("escalation_reason"),
                    "data_to_store": {
                        "chief_complaint": message,
                        "question_count": 1
                    }
                }
            except:
                return self._fallback_symptom_response(message)

        return self._fallback_symptom_response(message)

    # =====================================================================
    #  FOLLOW-UP QUESTIONS 
    # =====================================================================

    def _handle_followup_questions(self, context: Dict, message: str) -> Dict:
        question_count = context.get("session_data", {}).get("question_count", 0)

        if question_count >= 5:
            return {
                "response": "Thank you. Let me prepare your assessment...",
                "next_state": "SUMMARY_AND_RECOMMENDATIONS",
                "should_escalate": False,
                "data_to_store": {"assessment_complete": True}
            }

        system_prompt = """You are continuing a medical triage interview. 
Ask ONE additional follow-up question.

Respond ONLY with:

{
  "question": "Next question OR empty string",
  "sufficient_info": false,
  "should_escalate": false,
  "escalation_reason": ""
}
"""

        conversation = self._build_conversation_history(context)
        conversation.append({"role": "user", "content": message})

        result = self._call_openai_api(system_prompt, conversation)

        if result.get("success"):
            try:
                data = self._parse_json_response(result["text"])

                if data["sufficient_info"]:
                    return {
                        "response": "Thank you. Let me prepare your assessment...",
                        "next_state": "SUMMARY_AND_RECOMMENDATIONS",
                        "should_escalate": data["should_escalate"],
                        "data_to_store": {"assessment_complete": True}
                    }

                return {
                    "response": data["question"],
                    "next_state": "AI_FOLLOWUP_QUESTIONS",
                    "should_escalate": data["should_escalate"],
                    "escalation_reason": data.get("escalation_reason"),
                    "data_to_store": {"question_count": question_count + 1}
                }

            except:
                return self._fallback_followup_response(question_count)

        return self._fallback_followup_response(question_count)

    # =====================================================================
    #  SUMMARY GENERATION 
    # =====================================================================

    def _handle_summary_generation(self, context: Dict) -> Dict:

        print("\n==============================")
        print("🏥 Generating Assessment (OpenAI)")
        print("==============================")

        system_prompt = """You are a medical AI assistant creating a patient summary.

Respond ONLY with JSON:

{
  "overview": "...",
  "key_observations": "...",
  "recommendations": "...",
  "medications": "...",
  "monitoring_advice": "...",
  "should_escalate": false,
  "escalation_reason": ""
}

Rules:
- No diagnoses
- Only OTC medication suggestions
- Clear practical language
"""

        conversation = self._build_conversation_history(context)
        conversation.append({"role": "user", "content": "Generate full assessment summary."})

        result = self._call_openai_api(system_prompt, conversation, max_tokens=2000)

        if result.get("success"):
            try:
                summary = self._parse_json_response(result["text"])
                formatted = self._format_summary_response(summary)

                return {
                    "response": formatted,
                    "next_state": "AWAITING_CLINICIAN_DECISION",
                    "should_escalate": summary["should_escalate"],
                    "escalation_reason": summary.get("escalation_reason"),
                    "data_to_store": {
                        "ai_overview": summary["overview"],
                        "recommendations": summary["recommendations"],
                        "full_summary": summary
                    }
                }

            except:
                return self._fallback_summary_response(context)

        return self._fallback_summary_response(context)

    # =====================================================================
    #  HELPERS 
    # =====================================================================

    def _build_conversation_history(self, context: Dict) -> List[Dict]:
        messages = []

        profile = context.get("profile", {})
        if profile.get("age"):
            messages.append({
                "role": "user",
                "content": f"Patient Profile: Age {profile['age']}, Gender {profile.get('gender','unknown')}"
            })
            messages.append({
                "role": "assistant",
                "content": "Understood. I will use this information."
            })

        for msg in context.get("conversation_history", []):
            messages.append({
                "role": "user" if msg["is_from_user"] else "assistant",
                "content": msg["content"]
            })

        return messages

    def _parse_json_response(self, text: str) -> Dict:
        clean = text.strip().replace("```json", "").replace("```", "")
        return json.loads(clean)

    def _format_summary_response(self, summary: Dict) -> str:
        return f"""
**Your Assessment**

{summary['overview']}

**Key Observations**
{summary['key_observations']}

**Recommendations**
{summary['recommendations']}

**Medication Options**
{summary['medications']}

**Monitoring Advice**
{summary['monitoring_advice']}

Would you like to speak with a clinician? (Yes/No)
"""
     
        return response
    
    # ========== FALLBACK RESPONSES ==========
    
    def _fallback_symptom_response(self, message: str) -> Dict:
        """Fallback when API call fails"""
        return {
            'response': "Thank you for sharing that. When did these symptoms start?",
            'next_state': 'AI_FOLLOWUP_QUESTIONS',
            'should_escalate': False,
            'data_to_store': {
                'chief_complaint': message,
                'question_count': 1
            }
        }
    
    def _fallback_followup_response(self, question_count: int) -> Dict:
        """Fallback follow-up questions"""
        questions = [
            "On a scale of 1-10, how would you rate the severity?",
            "Have you noticed what makes it better or worse?",
            "Do you have any other symptoms?",
            "Have you taken any medication?"
        ]
        
        if question_count >= 4:
            return {
                'response': "Thank you. Let me prepare your assessment...",
                'next_state': 'SUMMARY_AND_RECOMMENDATIONS',
                'should_escalate': False,
                'data_to_store': {'assessment_complete': True}
            }
        
        question = questions[min(question_count, len(questions) - 1)]
        
        return {
            'response': question,
            'next_state': 'AI_FOLLOWUP_QUESTIONS',
            'should_escalate': False,
            'data_to_store': {'question_count': question_count + 1}
        }
    
    def _fallback_summary_response(self, context: Dict) -> Dict:
        """Fallback summary when API fails"""
        chief_complaint = context.get('session_data', {}).get('chief_complaint', 'your symptoms')
        
        response = f"""**Your Assessment:**

Based on your description of {chief_complaint}, here are my recommendations:

**Recommendations:**
• Get adequate rest - aim for 7-8 hours of sleep
• Stay well hydrated - drink plenty of water
• Eat balanced, nutritious meals
• Monitor your symptoms closely

**Medication Options:**
Consider over-the-counter options like paracetamol for pain or fever (follow package directions).

**Important:**
If symptoms worsen, persist beyond 2-3 days, or you develop new concerning symptoms, please seek medical attention.

---

Would you like to speak with a clinician? (Reply 'Yes' or 'No')"""
        
        return {
            'response': response,
            'next_state': 'AWAITING_CLINICIAN_DECISION',
            'should_escalate': False,
            'data_to_store': {
                'ai_overview': f"Patient reported {chief_complaint}",
                'used_fallback': True
            }
        }
    
    # ========== OTHER HANDLERS ==========
    
    def _handle_new_user(self) -> Dict:
        """Welcome message"""
        welcome = """Welcome to Lifegate! 👋

I'm your AI health assistant. I can help you:
• Understand your symptoms
• Provide health recommendations
• Connect you with a clinician if needed

Reply 'Start' to begin, or type 'doctor' anytime."""
        
        return {
            'response': welcome,
            'next_state': 'COLLECTING_PROFILE',
            'should_escalate': False,
            'data_to_store': {}
        }
    
    def _handle_profile_collection(self, context: Dict, message: str) -> Dict:
        """Profile collection logic - same as before"""
        profile = context.get('profile', {})
        
        if not profile.get('age'):
            import re
            age_match = re.search(r'\b(\d{1,3})\b', message)
            if age_match:
                age = int(age_match.group(1))
                if 0 < age < 120:
                    return {
                        'response': "Thank you. What is your gender? (Male/Female/Other)",
                        'next_state': 'COLLECTING_PROFILE',
                        'should_escalate': False,
                        'data_to_store': {'profile_field': 'age', 'value': age}
                    }
            
            return {
                'response': "To provide the best care, may I know your age?",
                'next_state': 'COLLECTING_PROFILE',
                'should_escalate': False,
                'data_to_store': {}
            }
        
        elif not profile.get('gender'):
            gender = self._extract_gender(message)
            return {
                'response': "Thank you! Now, what brings you here today?",
                'next_state': 'COLLECTING_SYMPTOMS',
                'should_escalate': False,
                'data_to_store': {'profile_field': 'gender', 'value': gender}
            }
    
    def _handle_clinician_decision(self, message: str) -> Dict:
        """Handle yes/no for clinician"""
        if any(word in message.lower() for word in ['yes', 'connect', 'doctor']):
            return {
                'response': "Connecting you with a clinician now...",
                'next_state': 'CONNECT_TO_CLINICIAN',
                'should_escalate': True,
                'escalation_reason': 'Patient requested',
                'data_to_store': {}
            }
        else:
            return {
                'response': "Take care! Message us anytime if you need help. 🌟",
                'next_state': 'COMPLETED',
                'should_escalate': False,
                'data_to_store': {}
            }
    
    def _extract_gender(self, message: str) -> str:
        """Extract gender"""
        msg = message.lower()
        if any(w in msg for w in ['male', 'man', 'boy', 'm']):
            return 'Male'
        elif any(w in msg for w in ['female', 'woman', 'girl', 'f']):
            return 'Female'
        return 'Other'
    
    def check_for_clinician_request(self, message: str) -> bool:
        """Check for clinician keywords"""
        keywords = ['doctor', 'clinician', 'speak to doctor', 'human']
        return any(k in message.lower() for k in keywords)