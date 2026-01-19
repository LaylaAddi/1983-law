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

    def _get_prompt(self, prompt_type: str) -> dict:
        """
        Fetch a prompt from the database AIPrompt model.

        Args:
            prompt_type: The type of prompt (e.g., 'parse_story', 'analyze_rights')

        Returns:
            dict with prompt config

        Raises:
            ValueError: If prompt not found or inactive. Run 'python manage.py seed_ai_prompts' to fix.
        """
        from documents.models import AIPrompt
        prompt = AIPrompt.objects.filter(
            prompt_type=prompt_type,
            is_active=True
        ).first()

        if not prompt:
            raise ValueError(
                f"AI prompt '{prompt_type}' not found or inactive. "
                f"Run 'python manage.py seed_ai_prompts' to populate prompts."
            )

        return {
            'system_message': prompt.system_message,
            'user_prompt_template': prompt.user_prompt_template,
            'model_name': prompt.model_name,
            'temperature': prompt.temperature,
            'max_tokens': prompt.max_tokens,
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

        # Get prompt from database (required)
        prompt = self._get_prompt('analyze_rights')
        user_prompt = prompt['user_prompt_template'].format(context=context)

        try:
            response = self.client.chat.completions.create(
                model=prompt['model_name'],
                messages=[
                    {"role": "system", "content": prompt['system_message']},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=prompt['temperature'],
                max_tokens=prompt['max_tokens'],
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

        # Get prompt from database (required)
        prompt = self._get_prompt('parse_story')
        user_prompt = prompt['user_prompt_template'].format(story_text=story_text)

        try:
            response = self.client.chat.completions.create(
                model=prompt['model_name'],
                messages=[
                    {"role": "system", "content": prompt['system_message']},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=prompt['temperature'],
                max_tokens=prompt['max_tokens'],
                response_format={"type": "json_object"}
            )

            import json
            result = json.loads(response.choices[0].message.content)

            # Post-process: Verify inferred agencies using smart lookup
            result = self._verify_inferred_agencies(result)

            return {
                'success': True,
                'sections': result,
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }

    def _verify_inferred_agencies(self, parsed_result: dict) -> dict:
        """
        Post-process parsed story to verify/correct inferred agency names.
        Uses find_law_enforcement_agency to check if suggested agency actually exists.
        """
        try:
            # Get city and state from incident overview
            incident = parsed_result.get('incident_overview', {})
            city = incident.get('city', '')
            state = incident.get('state', '')

            if not city or not state:
                return parsed_result

            # Check if any defendants have inferred agencies
            defendants = parsed_result.get('defendants', [])
            has_inferred = any(d.get('agency_inferred', False) for d in defendants)

            if not has_inferred:
                return parsed_result

            # Use smart lookup to find correct agency
            agency_info = self.find_law_enforcement_agency(city, state)

            if not agency_info.get('success'):
                return parsed_result

            # If location doesn't have local police, update inferred agencies
            if not agency_info.get('has_local_police', True):
                primary_agency = None
                for agency in agency_info.get('agencies', []):
                    if agency.get('is_primary'):
                        primary_agency = agency.get('name')
                        break

                if primary_agency:
                    # Update defendants with inferred agencies
                    for defendant in defendants:
                        if defendant.get('agency_inferred', False):
                            old_agency = defendant.get('agency', '')
                            # Don't replace if it's already a sheriff's office
                            if 'sheriff' not in old_agency.lower():
                                defendant['agency'] = primary_agency
                                defendant['agency_verification_note'] = (
                                    f"Updated from '{old_agency}' - {city} does not have its own police department. "
                                    f"Located in {agency_info.get('county_name', 'unknown')} County."
                                )

            # Add verification warning to result
            parsed_result['agency_verification_warning'] = agency_info.get('verification_warning', '')
            parsed_result['location_has_local_police'] = agency_info.get('has_local_police', True)
            parsed_result['county_name'] = agency_info.get('county_name', '')

        except Exception:
            # If verification fails, just return original result
            pass

        return parsed_result

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

        # Get prompt from database (required)
        prompt = self._get_prompt('suggest_relief')
        user_prompt = prompt['user_prompt_template'].format(context=context)

        try:
            response = self.client.chat.completions.create(
                model=prompt['model_name'],
                messages=[
                    {"role": "system", "content": prompt['system_message']},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=prompt['temperature'],
                max_tokens=prompt['max_tokens'],
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
        Suggest defendants (both individual officers and agencies) based on story and location.

        Args:
            context: Dict containing city, state, story_text, existing_defendants, etc.

        Returns:
            dict with 'success', 'suggestions' (list of defendant suggestions - both individuals and agencies)
        """
        city = context.get('city', '')
        state = context.get('state', '')
        story_text = context.get('story_text', '')
        existing_defendants = context.get('existing_defendants', [])
        defendant_name = context.get('defendant_name', '')
        title = context.get('title', '')
        description = context.get('description', '')

        if not city and not state:
            return {
                'success': False,
                'error': 'City or state is required to suggest defendants',
            }

        # Format existing defendants for the prompt
        existing_list = ""
        if existing_defendants:
            existing_list = "\n".join([f"- {d.get('name', 'Unknown')} ({d.get('type', 'unknown')})" for d in existing_defendants])
        else:
            existing_list = "None yet"

        # First, use web search to find the correct law enforcement agency for this location
        agency_info = self.find_law_enforcement_agency(city, state)
        agency_context = ""
        if agency_info.get('success'):
            agencies = agency_info.get('agencies', [])
            county = agency_info.get('county_name', '')
            has_local_police = agency_info.get('has_local_police', True)

            if agencies:
                agency_context = f"""
VERIFIED LAW ENFORCEMENT INFORMATION (from web search):
- County: {county}
- Has local police department: {'Yes' if has_local_police else 'NO - use County Sheriff'}
- Agencies with jurisdiction:
"""
                for a in agencies:
                    agency_context += f"  * {a.get('name')} ({a.get('type')}) - {'PRIMARY' if a.get('is_primary') else 'alternative'}\n"
                    if a.get('address'):
                        agency_context += f"    Address: {a.get('address')}\n"

        prompt = f"""Based on the following story about a civil rights violation, identify ALL defendants that should be named in a Section 1983 complaint.

LOCATION:
- City: {city or 'Unknown'}
- State: {state or 'Unknown'}
{agency_context}

PLAINTIFF'S STORY:
{story_text or 'No story provided - use form context below'}

ADDITIONAL CONTEXT (from form):
- Name/Description: {defendant_name or 'Not provided'}
- Title/Rank: {title or 'Not provided'}
- Role in incident: {description or 'Not provided'}

ALREADY ADDED DEFENDANTS (DO NOT SUGGEST THESE - they are already saved):
{existing_list}

INSTRUCTIONS:
Read the story carefully and identify ALL potential defendants mentioned:
1. INDIVIDUAL OFFICERS/EMPLOYEES - Any government employee who violated rights (police officers, security guards, government clerks, etc.)
2. GOVERNMENT AGENCIES - Their employing agencies/municipalities (for Monell liability claims)

For EACH person mentioned in the story who may have violated rights:
- Extract their name exactly as mentioned (e.g., "Officer Stevens", "Security Guard Bob")
- Determine their employing agency based on context
- Provide the official agency headquarters address

CRITICAL RULES FOR AGENCIES:
- IMPORTANT: Use the VERIFIED LAW ENFORCEMENT INFORMATION above if provided - it contains the ACTUAL agencies with jurisdiction
- Small towns often do NOT have their own police department - use County Sheriff instead
- Do NOT invent "[City] Police Department" if web search shows no local police exists
- Do NOT suggest any defendant already in the "ALREADY ADDED DEFENDANTS" list
- Security guards at government buildings = employed by the city (e.g., "City of Oklahoma City")
- Include BOTH the individual AND their employing agency as separate defendants

Return a JSON object with this format:
{{
    "suggestions": [
        {{
            "defendant_type": "agency",
            "name": "Official Agency Name",
            "agency_name": "",
            "title_rank": "",
            "address": "Full headquarters address",
            "confidence": "high|medium|low",
            "reason": "Why this defendant should be named"
        }},
        {{
            "defendant_type": "individual",
            "name": "Person's name from story",
            "agency_name": "Their employing agency",
            "title_rank": "Their title (Officer, Security Guard, etc.)",
            "address": "Agency headquarters address",
            "confidence": "high|medium|low",
            "reason": "Their role in the violation"
        }}
    ],
    "notes": "Any important notes"
}}"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a legal research assistant helping identify ALL defendants for Section 1983 civil rights complaints. Read the plaintiff's story carefully and extract every government employee mentioned who may have violated their rights. Include both individuals AND their employing agencies. Do not suggest duplicates of already-added defendants."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=3000,
                response_format={"type": "json_object"}
            )

            import json
            result = json.loads(response.choices[0].message.content)

            # Build comprehensive verification warning
            notes = result.get('notes', '')

            # Add agency verification context
            verification_parts = []
            if agency_info.get('success'):
                if not agency_info.get('has_local_police', True):
                    verification_parts.append(
                        f"NOTE: {city} does not appear to have its own police department. "
                        f"Law enforcement is likely provided by {agency_info.get('county_name', 'the county')} Sheriff's Office."
                    )
                verification_parts.append(agency_info.get('verification_warning', ''))

            verification_parts.append(
                "IMPORTANT: You MUST verify the correct law enforcement agency before filing. "
                "Small communities are often served by County Sheriff, not a local police department. "
                "Search online or call the agency to confirm jurisdiction and address."
            )

            verification_warning = ' '.join(filter(None, verification_parts))

            return {
                'success': True,
                'suggestions': result.get('suggestions', []),
                'notes': notes,
                'verification_warning': verification_warning,
                'has_local_police': agency_info.get('has_local_police', True) if agency_info.get('success') else None,
                'county_name': agency_info.get('county_name', '') if agency_info.get('success') else '',
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }

    def find_law_enforcement_agency(self, city: str, state: str) -> dict:
        """
        Find the correct law enforcement agency for a location.
        Handles small towns that don't have their own police department.

        Args:
            city: City/town name
            state: State name or abbreviation

        Returns:
            dict with 'success', 'agencies' (list of possible agencies with addresses)
        """
        if not city or not state:
            return {
                'success': False,
                'error': 'City and state are required',
            }

        # Get prompt from database (required)
        prompt = self._get_prompt('find_law_enforcement')
        user_prompt = prompt['user_prompt_template'].format(city=city, state=state)

        try:
            response = self.client.chat.completions.create(
                model=prompt['model_name'],
                messages=[
                    {"role": "system", "content": prompt['system_message']},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=prompt['temperature'],
                max_tokens=prompt['max_tokens'],
                response_format={"type": "json_object"}
            )

            import json
            result = json.loads(response.choices[0].message.content)

            return {
                'success': True,
                'has_local_police': result.get('has_local_police', False),
                'county_name': result.get('county_name', ''),
                'location_type': result.get('location_type', 'unknown'),
                'agencies': result.get('agencies', []),
                'verification_warning': result.get('verification_warning',
                    'IMPORTANT: Please verify the correct law enforcement agency. Small communities may be served by County Sheriff rather than a local police department.'),
            }

        except Exception as e:
            # If this fails, return a conservative response
            return {
                'success': True,  # Still return success so we show warning
                'has_local_police': False,  # Assume no local police to be safe
                'county_name': '',
                'agencies': [],
                'verification_warning': f'Could not verify law enforcement agency for {city}, {state}. Please search online to find the correct agency - small towns are typically served by the County Sheriff, not a local police department.',
            }

    def lookup_agency_address(self, agency_name: str, city: str = '', state: str = '') -> dict:
        """
        Look up the official address for a government agency using web search.

        Args:
            agency_name: Name of the agency (e.g., "Tampa Police Department")
            city: City for context
            state: State for context

        Returns:
            dict with 'success', 'address', 'source'
        """
        if not agency_name:
            return {
                'success': False,
                'error': 'Agency name is required',
            }

        location_context = ""
        if city and state:
            location_context = f" in {city}, {state}"
        elif city:
            location_context = f" in {city}"
        elif state:
            location_context = f" in {state}"

        query = f"What is the official headquarters address for {agency_name}{location_context}? I need the physical street address for legal service of process."

        try:
            # Use OpenAI with web search tool
            response = self.client.responses.create(
                model="gpt-4o-mini",
                tools=[{"type": "web_search_preview"}],
                input=query
            )

            # Extract the text response
            address_text = ""
            for item in response.output:
                if hasattr(item, 'content'):
                    for content in item.content:
                        if hasattr(content, 'text'):
                            address_text = content.text
                            break

            if not address_text:
                return {
                    'success': False,
                    'error': 'No address found in search results',
                }

            # Parse the response to extract just the address
            parse_prompt = f"""Extract the complete mailing address from this text. Return a JSON object:

Text: {address_text}

Return format:
{{
    "address": "Street Address, City, State ZIP (example: 123 Main Street, Tampa, FL 33602)",
    "confidence": "high" or "medium" or "low",
    "source_note": "Brief note about the source"
}}

IMPORTANT: The address MUST include:
- Street number and name
- City name
- State abbreviation (2 letters)
- ZIP code

If no clear address is found, return:
{{
    "address": null,
    "confidence": "low",
    "source_note": "Could not find official address"
}}"""

            parse_response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Extract addresses from text. Return only valid JSON."},
                    {"role": "user", "content": parse_prompt}
                ],
                temperature=0.1,
                max_tokens=500,
                response_format={"type": "json_object"}
            )

            import json
            result = json.loads(parse_response.choices[0].message.content)

            if result.get('address'):
                return {
                    'success': True,
                    'address': result['address'],
                    'confidence': result.get('confidence', 'medium'),
                    'source_note': result.get('source_note', 'Found via web search'),
                }
            else:
                return {
                    'success': False,
                    'error': 'Could not find official address for this agency',
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }

    def suggest_section_content(self, section_type: str, story_text: str, existing_data: dict = None) -> dict:
        """
        Analyze story and suggest content for a specific section.

        Args:
            section_type: Type of section ('damages', 'witnesses', 'evidence', 'rights_violated')
            story_text: The user's story text
            existing_data: Optional dict of existing data in the section

        Returns:
            dict with 'success' and section-specific suggestions
        """
        if not story_text or not story_text.strip():
            return {
                'success': False,
                'error': 'No story text available. Please complete the "Tell Your Story" section first.',
            }

        existing_data = existing_data or {}

        # Map section types to prompt types in the database
        prompt_type_map = {
            'damages': 'suggest_damages',
            'witnesses': 'suggest_witnesses',
            'evidence': 'suggest_evidence',
            'rights_violated': 'suggest_rights_violated',
        }

        if section_type not in prompt_type_map:
            return {
                'success': False,
                'error': f'Unknown section type: {section_type}',
            }

        try:
            # Get prompt from database
            prompt = self._get_prompt(prompt_type_map[section_type])

            # Format the user prompt with variables
            user_prompt = prompt['user_prompt_template'].format(
                story_text=story_text,
                existing=existing_data.get('existing', 'None yet')
            )

            response = self.client.chat.completions.create(
                model=prompt['model_name'],
                messages=[
                    {"role": "system", "content": prompt['system_message']},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=prompt['temperature'],
                max_tokens=prompt['max_tokens'],
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
