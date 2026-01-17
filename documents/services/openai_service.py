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
        # Set timeout to 45 seconds per call - Gunicorn timeout is 120s
        self.client = OpenAI(api_key=api_key, timeout=45.0)

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
- Extract ALL information from the text, including details that can be inferred from context
- Example: "city hall in Oklahoma City" means location="City Hall", city="Oklahoma City", state="OK", location_type="government building"
- Example: "I was recording" means was_recording=true
- For dates/times, extract if mentioned in any format
- If the story contains "Not applicable or unknown:", DO NOT ask questions about those topics

AGENCY INFERENCE RULES:
- If a city and state are mentioned but no specific agency, INFER the most likely agency name
- For police officers in a city, infer "[City] Police Department" (e.g., "Tampa Police Department")
- For sheriff's deputies, infer "[County] County Sheriff's Office"
- For state troopers, infer "[State] Highway Patrol" or "[State] State Police"
- Set "agency_inferred" to true when you infer the agency, false when explicitly stated

USER'S STORY:
{story_text}

Extract information for the following sections. Fill in as many fields as possible based on the story:

{{
    "incident_overview": {{
        "incident_date": "YYYY-MM-DD format or partial date, null if not mentioned",
        "incident_time": "HH:MM format or description like 'afternoon', null if not mentioned",
        "incident_location": "address or location name like 'City Hall', 'Main Street', etc.",
        "city": "city name - extract from context (e.g., 'Oklahoma City' from the story)",
        "state": "two-letter state code - infer from city if possible (e.g., OK for Oklahoma City)",
        "location_type": "type of location: 'government building', 'public sidewalk', 'police station', 'courthouse', 'public park', etc.",
        "was_recording": "true if recording/filming mentioned, false if explicitly not, null if unknown",
        "recording_device": "device used: 'cell phone', 'camera', etc. if mentioned"
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
            "agency": "department or agency name - INFER from city/state if not explicitly stated",
            "agency_inferred": "true if agency was inferred from location, false if explicitly stated in story",
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
            "type": "video, photo, document, body_cam, surveillance, etc.",
            "description": "description of the evidence - INCLUDE recordings even if deleted/seized, and potential evidence like body cam footage"
        }}
    ],
    "damages": {{
        "physical_injuries": "description of physical injuries, null if none mentioned",
        "emotional_distress": "emotional harm: humiliation, fear, anxiety, loss of irreplaceable memories/photos, etc.",
        "financial_losses": "financial impact: missed work, damaged property value, etc.",
        "other_damages": "property damage, destroyed data, reputation harm, etc."
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

QUESTIONS TO ASK - Generate 3-8 follow-up questions, but ONLY for information NOT already in the story:
- Do NOT ask about location if the story mentions where it happened
- Do NOT ask about recording if the story mentions filming/recording
- Do NOT ask about city/state if mentioned in the story
- DO ask about: officer names/badge numbers, witnesses, evidence, injuries, financial losses - IF NOT mentioned
- Skip topics marked "Not applicable or unknown"

Respond with ONLY the JSON object."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a legal document assistant that extracts structured information from personal narratives. Be thorough - extract all information stated and reasonably inferred from context. Include evidence even if it was deleted or seized. Always respond with valid JSON."
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

    def suggest_relief(self, extracted_data: dict) -> dict:
        """
        Analyze extracted story data and suggest appropriate relief for Section 1983 complaint.

        Args:
            extracted_data: Dict containing rights_violated, damages, evidence, etc.

        Returns:
            dict with 'success', 'relief' containing recommendations for each relief type
        """
        if not extracted_data:
            return {
                'success': False,
                'error': 'No extracted data provided',
            }

        # Build context from extracted data
        rights = extracted_data.get('rights_violated', {}).get('suggested_violations', [])
        damages = extracted_data.get('damages', {})
        evidence = extracted_data.get('evidence', [])
        narrative = extracted_data.get('incident_narrative', {})

        context = f"""
RIGHTS VIOLATED:
{rights}

DAMAGES:
- Physical injuries: {damages.get('physical_injuries', 'None mentioned')}
- Emotional distress: {damages.get('emotional_distress', 'None mentioned')}
- Financial losses: {damages.get('financial_losses', 'None mentioned')}
- Other damages: {damages.get('other_damages', 'None mentioned')}

EVIDENCE:
{evidence}

INCIDENT SUMMARY:
{narrative.get('summary', 'No summary available')}
"""

        prompt = f"""Based on this Section 1983 civil rights case information, recommend appropriate relief:

{context}

Analyze and provide recommendations for each type of relief. Return a JSON object:

{{
    "compensatory_damages": {{
        "recommended": true/false,
        "reason": "Brief explanation of why compensatory damages are appropriate based on the specific damages suffered"
    }},
    "punitive_damages": {{
        "recommended": true/false,
        "reason": "Brief explanation - recommend if conduct was willful, malicious, or showed reckless disregard for rights"
    }},
    "declaratory_relief": {{
        "recommended": true/false,
        "reason": "Brief explanation - recommend if a court declaration that rights were violated would be valuable",
        "suggested_declaration": "What should be declared, e.g., 'Filming in public areas of government buildings is protected by the First Amendment'"
    }},
    "injunctive_relief": {{
        "recommended": true/false,
        "reason": "Brief explanation - recommend if policy changes or training are needed to prevent future violations",
        "suggested_injunction": "What changes should be ordered, if any"
    }},
    "attorney_fees": {{
        "recommended": true,
        "reason": "42 U.S.C. § 1988 allows recovery of attorney fees in civil rights cases - always recommend"
    }},
    "jury_trial": {{
        "recommended": true/false,
        "reason": "Brief explanation - juries are often sympathetic to civil rights plaintiffs"
    }}
}}

Be specific to THIS case. Reference the actual violations, damages, and evidence when explaining recommendations."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a legal assistant helping prepare Section 1983 civil rights complaints. Provide thoughtful relief recommendations based on the specific facts of each case. Always respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )

            import json
            result = json.loads(response.choices[0].message.content)

            return {
                'success': True,
                'relief': result,
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }

    def suggest_agency(self, context: dict) -> dict:
        """
        Suggest the correct law enforcement agency name based on location and context.

        Args:
            context: Dict containing city, state, defendant_name, title, description

        Returns:
            dict with 'success', 'suggestions' (list of agency options with confidence)
        """
        city = context.get('city', '')
        state = context.get('state', '')
        defendant_name = context.get('defendant_name', '')
        title = context.get('title', '')
        description = context.get('description', '')

        if not city and not state:
            return {
                'success': False,
                'error': 'City or state is required to suggest an agency',
            }

        prompt = f"""Based on the following information about a law enforcement encounter, suggest the most likely government agency or agencies involved.

LOCATION:
- City: {city or 'Unknown'}
- State: {state or 'Unknown'}

DEFENDANT INFORMATION:
- Name/Description: {defendant_name or 'Unknown officer'}
- Title/Rank: {title or 'Unknown'}
- Role in incident: {description or 'Not provided'}

INSTRUCTIONS:
1. Research and provide the OFFICIAL, CORRECT name of the law enforcement agency
2. For city police, use the official department name (e.g., "Miami Police Department", "City of Miami Police Department")
3. For county sheriff, use official name (e.g., "Miami-Dade County Sheriff's Office", "Orange County Sheriff's Department")
4. For state police/highway patrol, use the correct state agency name
5. Consider if multiple agencies might be involved based on the context
6. Include the agency type for clarity

Return a JSON object with this format:
{{
    "suggestions": [
        {{
            "agency_name": "Official Agency Name",
            "agency_type": "municipal_police|county_sheriff|state_police|federal|other",
            "confidence": "high|medium|low",
            "reason": "Brief explanation of why this agency is suggested"
        }}
    ],
    "notes": "Any additional context or warnings about the suggestion"
}}

Provide 1-3 suggestions, with the most likely first. Only include suggestions you're reasonably confident about."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a legal research assistant helping identify the correct government agency names for Section 1983 civil rights complaints. Accuracy is critical - provide official agency names as they would appear in legal documents. Use your knowledge of U.S. law enforcement agencies."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )

            import json
            result = json.loads(response.choices[0].message.content)

            return {
                'success': True,
                'suggestions': result.get('suggestions', []),
                'notes': result.get('notes', ''),
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
