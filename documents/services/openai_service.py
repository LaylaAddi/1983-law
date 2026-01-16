"""
OpenAI service for AI-powered features in Section 1983 complaint building.
"""
from django.conf import settings
from openai import OpenAI


class OpenAIService:
    """Service for interacting with OpenAI API for legal document assistance."""

    def __init__(self):
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured in settings")
        self.client = OpenAI(api_key=api_key)

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

        prompt = f"""Analyze this personal account of a civil rights incident and extract ALL possible information for a Section 1983 complaint form.

EXTRACTION RULES:
- Be THOROUGH - extract everything stated AND reasonably inferred from context
- Fill in as many fields as possible - do not leave fields null unless truly unknown
- If the user describes an action, infer who did it and what rights it may have violated
- Convert casual language to formal legal descriptions (e.g., "they grabbed me" → "Officers used physical force to restrain Plaintiff")
- If the story mentions a location with city/state, use that for all relevant fields
- If the story contains "Not applicable or unknown:" section, skip those topics in questions_to_ask

AGENCY INFERENCE RULES:
- If a city and state are mentioned but no specific agency, INFER the most likely agency name
- For police officers in a city, infer "[City] Police Department" (e.g., "Tampa Police Department")
- For sheriff's deputies, infer "[County] County Sheriff's Office"
- For state troopers, infer "[State] Highway Patrol" or "[State] State Police"
- Set "agency_inferred" to true when you infer the agency, false when explicitly stated

USER'S STORY:
{story_text}

Extract information for the following sections. Be thorough - fill in fields based on context, not just explicit statements:

{{
    "incident_overview": {{
        "incident_date": "YYYY-MM-DD format, or partial like '2024-06' if only month known",
        "incident_time": "HH:MM format or description like 'afternoon', 'evening'",
        "incident_location": "specific address or location description",
        "city": "city name - infer from context if location is described",
        "state": "two-letter state code - infer from context if location is described",
        "location_type": "type of location like 'public sidewalk', 'government building', 'police station', etc. - infer from context",
        "was_recording": "true if filming/recording mentioned, false if explicitly not recording, null only if completely unknown",
        "recording_device": "device used like 'cell phone', 'camera', etc."
    }},
    "incident_narrative": {{
        "summary": "2-3 sentence summary of what happened, written in third person for legal document",
        "detailed_narrative": "full chronological account in third person, written formally for legal filing",
        "what_were_you_doing": "what the plaintiff was doing before/during incident",
        "initial_contact": "how the encounter with officials began",
        "what_was_said": "dialogue or statements made by all parties",
        "physical_actions": "any physical actions taken by anyone",
        "how_it_ended": "how the encounter concluded"
    }},
    "defendants": [
        {{
            "name": "officer/official name if known, otherwise 'John Doe' or 'Jane Doe'",
            "badge_number": "badge number if mentioned",
            "title": "title like 'Officer', 'Sergeant', 'Deputy', etc. - infer from context",
            "agency": "department or agency name - ALWAYS infer from city/state if not explicit",
            "agency_inferred": "true if agency was inferred, false if explicitly stated",
            "agency_address": "official address for service of process if known",
            "description": "description of this defendant's role and specific actions in the incident"
        }}
    ],
    "witnesses": [
        {{
            "name": "witness name, or 'Unknown bystander' if not named",
            "description": "description like 'female bystander', 'store employee', etc.",
            "what_they_saw": "what this witness could have observed"
        }}
    ],
    "evidence": [
        {{
            "type": "video, photo, document, body_cam, dash_cam, surveillance, etc.",
            "description": "description of the evidence and what it shows"
        }}
    ],
    "damages": {{
        "physical_injuries": "description of physical injuries - include minor injuries like bruises, pain",
        "emotional_distress": "description of emotional harm - fear, humiliation, anxiety, etc.",
        "financial_losses": "any financial impact - missed work, legal fees, damaged property",
        "other_damages": "reputation harm, relationship impacts, etc."
    }},
    "rights_violated": {{
        "suggested_violations": [
            {{
                "right": "field name like first_amendment_speech, fourth_amendment_seizure, etc.",
                "amendment": "first, fourth, fifth, or fourteenth",
                "reason": "specific explanation of how this right was violated based on the story"
            }}
        ]
    }},
    "questions_to_ask": ["GENERATE 3-8 QUESTIONS HERE - see instructions below"]
}}

CRITICAL - QUESTIONS TO ASK:
You MUST generate 3-8 follow-up questions to gather missing information. Examples:
- "What is the exact date this incident occurred?"
- "What city and state did this happen in?"
- "Do you know any of the officers' names or badge numbers?"
- "What agency employed the officers involved?"
- "Did anyone else witness the incident?"
- "Do you have any video, photos, or documentation of the incident?"
- "Were you physically injured? Did you seek medical treatment?"
- "Did you miss work or lose income because of this incident?"
- "Were you detained, arrested, or given any citations?"
- "What happened to any recordings or property during the incident?"

SKIP questions about topics in "Not applicable or unknown:" section.
ALWAYS ask about: officer identification, evidence, injuries/damages, and witnesses if not fully covered.

Respond with ONLY the JSON object."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a legal document assistant that extracts structured information from personal narratives. Be thorough - extract all information that is stated or can be reasonably inferred from context. For agencies, infer the most likely agency name from location when not explicitly stated. Always respond with valid JSON."
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
