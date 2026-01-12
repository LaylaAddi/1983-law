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

    def analyze_rights_violations(self, document_data: dict) -> dict:
        """
        Analyze document content to suggest which constitutional rights were violated.

        Args:
            document_data: Dict containing incident narrative, what_was_said,
                          physical_actions, etc.

        Returns:
            dict with 'success', 'suggestions' (list of violations with explanations)
        """
        # Build context from document data
        context_parts = []

        if document_data.get('summary'):
            context_parts.append(f"Summary: {document_data['summary']}")
        if document_data.get('detailed_narrative'):
            context_parts.append(f"What happened: {document_data['detailed_narrative']}")
        if document_data.get('what_were_you_doing'):
            context_parts.append(f"What plaintiff was doing: {document_data['what_were_you_doing']}")
        if document_data.get('initial_contact'):
            context_parts.append(f"How it started: {document_data['initial_contact']}")
        if document_data.get('what_was_said'):
            context_parts.append(f"What was said: {document_data['what_was_said']}")
        if document_data.get('physical_actions'):
            context_parts.append(f"Physical actions: {document_data['physical_actions']}")
        if document_data.get('how_it_ended'):
            context_parts.append(f"How it ended: {document_data['how_it_ended']}")

        if not context_parts:
            return {
                'success': False,
                'error': 'No incident information found. Please fill out the Incident Narrative section first.',
            }

        context = "\n\n".join(context_parts)

        prompt = f"""Analyze this incident and identify which constitutional rights were likely violated. This is for a Section 1983 civil rights complaint against police officers or government officials.

INCIDENT DETAILS:
{context}

Based on these facts, identify which rights were violated. For each violation found, provide:
1. The specific right (use exact names from the list below)
2. A conversational but professional explanation of HOW this right was violated (2-3 sentences)

AVAILABLE RIGHTS TO CONSIDER:
- first_amendment_speech: Right to free speech (includes recording police, expressing opinions)
- first_amendment_press: Freedom of the press (journalism, news gathering)
- first_amendment_assembly: Right to peaceful assembly (protests, gatherings)
- first_amendment_petition: Right to petition government (filing complaints)
- fourth_amendment_search: Protection from unreasonable searches
- fourth_amendment_seizure: Protection from unreasonable seizure of property
- fourth_amendment_arrest: Protection from unlawful arrest/detention
- fourth_amendment_force: Protection from excessive force
- fifth_amendment_self_incrimination: Right against self-incrimination
- fifth_amendment_due_process: Right to due process (federal)
- fourteenth_amendment_due_process: Right to due process (state actors)
- fourteenth_amendment_equal_protection: Right to equal protection under the law

Respond in this exact JSON format:
{{
    "violations": [
        {{
            "right": "first_amendment_speech",
            "amendment": "first",
            "explanation": "Your explanation here..."
        }}
    ],
    "summary": "A brief 1-2 sentence overall summary of the civil rights issues in this case."
}}

Only include rights that are clearly supported by the facts. Be accurate - don't suggest violations that aren't evident from the incident description. If no clear violations are found, return an empty violations array with a summary explaining why."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a civil rights legal analyst helping identify constitutional violations in Section 1983 cases. Be accurate, thorough, and write explanations that are conversational yet professional. Always respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )

            import json
            result = json.loads(response.choices[0].message.content)

            return {
                'success': True,
                'violations': result.get('violations', []),
                'summary': result.get('summary', ''),
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }

    def parse_story(self, story_text: str) -> dict:
        """
        Parse a user's story/narrative and extract structured data for all document sections.

        Args:
            story_text: Raw text from user describing their incident

        Returns:
            dict with 'success', 'sections' containing extracted fields per section
        """
        if not story_text or not story_text.strip():
            return {
                'success': False,
                'error': 'No story text provided',
            }

        prompt = f"""Analyze this personal account of a civil rights incident and extract specific information that can be used to fill out a Section 1983 complaint form.

IMPORTANT RULES:
- ONLY extract information that is EXPLICITLY stated in the text
- DO NOT guess, infer, or make up any information
- If information is not clearly provided, set the field to null
- Use the exact wording from the story when possible
- For dates/times, only extract if explicitly mentioned
- If the story contains a section labeled "Not applicable or unknown:", DO NOT ask questions about those topics in questions_to_ask - the user has already indicated they don't have that information

USER'S STORY:
{story_text}

Extract information for the following sections. Set any field to null if not explicitly mentioned:

{{
    "incident_overview": {{
        "incident_date": "YYYY-MM-DD format or partial date if only month/day given, null if not mentioned",
        "incident_time": "HH:MM format or description like 'afternoon', null if not mentioned",
        "incident_location": "specific address or location description, null if not mentioned",
        "city": "city name only if explicitly mentioned, null otherwise",
        "state": "two-letter state code only if explicitly mentioned, null otherwise"
    }},
    "incident_narrative": {{
        "summary": "2-3 sentence summary of what happened, written in third person",
        "detailed_narrative": "full chronological account, written in third person",
        "what_were_you_doing": "what the plaintiff was doing before/during incident",
        "initial_contact": "how the encounter with officials began",
        "what_was_said": "dialogue or statements made by parties",
        "physical_actions": "any physical actions taken by anyone",
        "how_it_ended": "how the encounter concluded"
    }},
    "defendants": [
        {{
            "name": "officer/official name if mentioned, null otherwise",
            "badge_number": "badge number if mentioned, null otherwise",
            "title": "title like 'Officer', 'Sergeant', etc. if mentioned",
            "agency": "department or agency name if mentioned, null otherwise",
            "description": "description of this defendant's role/actions"
        }}
    ],
    "witnesses": [
        {{
            "name": "witness name if mentioned, null otherwise",
            "description": "description like 'a woman', 'my friend', etc.",
            "what_they_saw": "what this witness observed"
        }}
    ],
    "evidence": [
        {{
            "type": "video, photo, document, etc.",
            "description": "description of the evidence"
        }}
    ],
    "damages": {{
        "physical_injuries": "description of physical injuries, null if none mentioned",
        "emotional_distress": "description of emotional harm, null if none mentioned",
        "financial_losses": "description of financial losses, null if none mentioned",
        "other_damages": "any other damages mentioned"
    }},
    "rights_violated": {{
        "suggested_violations": [
            {{
                "right": "field name like first_amendment_speech",
                "amendment": "first, fourth, fifth, or fourteenth",
                "reason": "brief explanation of why this right may have been violated"
            }}
        ]
    }},
    "questions_to_ask": []
}}

IMPORTANT: For "questions_to_ask", generate 3-8 specific questions about missing information that would help complete the complaint, such as:
- What city and state did this happen in?
- Do you know the officer's badge number?
- What agency does the officer work for?
- Did anyone witness the incident?
- Do you have any video, photos, or documentation?
- Were you physically injured? Did you seek medical treatment?
- Did you miss work or lose income because of this?

DO NOT ask about items the user marked as "Not applicable or unknown" - skip those topics entirely.
Only ask about genuinely missing information that would strengthen the complaint.

Respond with ONLY the JSON object, no additional text."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a legal document assistant that extracts structured information from personal narratives. Be extremely accurate - only extract what is explicitly stated. Never guess or infer. If information isn't clearly provided, use null. Always respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Very low temperature for accuracy
                max_tokens=3000,
                response_format={"type": "json_object"}
            )

            import json
            result = json.loads(response.choices[0].message.content)

            return {
                'success': True,
                'sections': result,
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
