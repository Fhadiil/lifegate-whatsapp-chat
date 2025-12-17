from groq import Groq
import logging

logger = logging.getLogger(__name__)

class GroqAIEngine:
    """Chat + context engine powered by Groq (free testing)."""

    def __init__(self, api_key):
        self.client = Groq(api_key=api_key)

    def run(self, system_prompt, conversation_history):
        """
        system_prompt: string
        conversation_history: list of {role: "user"/"assistant", content: "..."}
        """

        try:
            logger.info("Calling Groq API...")

            messages = [{"role": "system", "content": system_prompt}]
            messages += conversation_history

            response = self.client.chat.completions.create(
                model="llama3-70b-8192",   # strong + free
                messages=messages,
                temperature=0.2,
                max_tokens=300
            )

            ai_reply = response.choices[0].message["content"]
            return ai_reply

        except Exception as e:
            logger.error(f"Groq API Error: {e}")
            return (
                "Sorry, I’m having trouble processing your request right now. "
                "Please try again shortly."
            )
