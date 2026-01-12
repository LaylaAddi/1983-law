"""
OpenAI service for rewriting narrative text in legal format.
"""
from django.conf import settings
from openai import OpenAI


class OpenAIService:
    """Service for interacting with OpenAI API for legal text rewriting."""

    REWRITE_PROMPT = """You are a legal writing assistant helping someone write a Section 1983 civil rights complaint. Rewrite the following text to be:

- Clear and factual (not emotional)
- Written in third person ("Plaintiff" not "I")
- Specific about actions, times, and people
- Professional legal tone
- Properly structured for a legal document

Original text:
"{user_text}"

Provide only the rewritten text, no explanations or commentary."""

    FIELD_PROMPTS = {
        'summary': """Rewrite this incident summary to be a clear, concise 2-3 sentence overview suitable for a Section 1983 complaint. Use third person ("Plaintiff") and professional legal tone.

Original text:
"{user_text}"

Provide only the rewritten summary, no explanations.""",

        'detailed_narrative': """Rewrite this detailed narrative for a Section 1983 complaint. Make it:
- Chronological and factual
- Written in third person ("Plaintiff")
- Specific about actions, times, and people involved
- Professional legal tone

Original text:
"{user_text}"

Provide only the rewritten narrative, no explanations.""",

        'what_were_you_doing': """Rewrite this description of the plaintiff's activities before/during the incident. Use third person and professional legal tone.

Original text:
"{user_text}"

Provide only the rewritten text, no explanations.""",

        'initial_contact': """Rewrite this description of how the encounter with officers began. Use third person ("Plaintiff"), be factual and specific.

Original text:
"{user_text}"

Provide only the rewritten text, no explanations.""",

        'what_was_said': """Rewrite this dialogue/conversation description for a legal document. Use third person, indicate who said what clearly, and maintain factual accuracy.

Original text:
"{user_text}"

Provide only the rewritten text, no explanations.""",

        'physical_actions': """Rewrite this description of physical actions for a Section 1983 complaint. Be specific about who did what, use third person, and maintain professional legal tone.

Original text:
"{user_text}"

Provide only the rewritten text, no explanations.""",

        'how_it_ended': """Rewrite this description of how the encounter ended. Use third person ("Plaintiff") and professional legal tone.

Original text:
"{user_text}"

Provide only the rewritten text, no explanations.""",
    }

    def __init__(self):
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured in settings")
        self.client = OpenAI(api_key=api_key)

    def rewrite_text(self, text: str, field_name: str = None) -> dict:
        """
        Rewrite user text in legal format.

        Args:
            text: The original user text to rewrite
            field_name: Optional field name to use field-specific prompt

        Returns:
            dict with 'success', 'original', 'rewritten', and optionally 'error'
        """
        if not text or not text.strip():
            return {
                'success': False,
                'error': 'No text provided to rewrite',
                'original': text,
                'rewritten': None,
            }

        # Use field-specific prompt if available, otherwise use generic
        if field_name and field_name in self.FIELD_PROMPTS:
            prompt = self.FIELD_PROMPTS[field_name].format(user_text=text)
        else:
            prompt = self.REWRITE_PROMPT.format(user_text=text)

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Cost-effective model for rewriting
                messages=[
                    {
                        "role": "system",
                        "content": "You are a legal writing assistant specializing in Section 1983 civil rights complaints. You help rewrite text to be clear, factual, and professionally formatted for legal documents."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Low temperature for consistent, professional output
                max_tokens=1000,
            )

            rewritten_text = response.choices[0].message.content.strip()

            return {
                'success': True,
                'original': text,
                'rewritten': rewritten_text,
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'original': text,
                'rewritten': None,
            }
