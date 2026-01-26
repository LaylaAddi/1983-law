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

    def _identify_agency_for_officer(self, city: str, state: str,
                                      officer_name: str = '', officer_title: str = '',
                                      officer_description: str = '') -> dict:
        """
        Identify the likely law enforcement agency for an officer based on location and officer info.

        Args:
            city: City where incident occurred
            state: State where incident occurred
            officer_name: Name of the officer
            officer_title: Title/rank (e.g., "Sergeant", "Deputy", "Trooper")
            officer_description: Description of the officer

        Returns:
            dict with 'success' and 'agency_name'
        """
        if not city and not state:
            return {'success': False, 'error': 'Location required to identify agency'}

        # Build context from officer info
        officer_context = []
        if officer_title:
            officer_context.append(f"title/rank: {officer_title}")
        if officer_description:
            officer_context.append(f"description: {officer_description}")

        officer_info = ", ".join(officer_context) if officer_context else "unknown officer"

        location = f"{city}, {state}" if city and state else (city or state)

        try:
            # Get prompt from database
            prompt_config = self._get_prompt('identify_officer_agency')

            # Format the user prompt with variables
            user_prompt = prompt_config['user_prompt_template'].format(
                location=location,
                officer_info=officer_info
            )

            response = self.client.chat.completions.create(
                model=prompt_config['model_name'],
                messages=[
                    {"role": "system", "content": prompt_config['system_message']},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=prompt_config['temperature'],
                max_tokens=prompt_config['max_tokens'],
                response_format={"type": "json_object"}
            )

            import json
            result = json.loads(response.choices[0].message.content)

            if result.get('agency_name'):
                return {
                    'success': True,
                    'agency_name': result['agency_name'],
                    'confidence': result.get('confidence', 'medium'),
                    'reasoning': result.get('reasoning', ''),
                }
            else:
                return {
                    'success': False,
                    'error': result.get('reasoning', 'Could not identify agency'),
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }

    def lookup_agency_address(self, agency_name: str, city: str = '', state: str = '',
                               officer_name: str = '', officer_title: str = '',
                               officer_description: str = '') -> dict:
        """
        Look up the official address for a government agency using web search.
        If agency_name is not provided but officer info and location are available,
        will first identify the likely agency.

        Args:
            agency_name: Name of the agency (e.g., "Tampa Police Department")
            city: City for context
            state: State for context
            officer_name: Name of the officer (for agency identification)
            officer_title: Title/rank of the officer (for agency identification)
            officer_description: Description of the officer (for agency identification)

        Returns:
            dict with 'success', 'address', 'source', and optionally 'suggested_agency'
        """
        location_context = ""
        if city and state:
            location_context = f" in {city}, {state}"
        elif city:
            location_context = f" in {city}"
        elif state:
            location_context = f" in {state}"

        # If no agency name but we have officer info and location, identify the agency first
        suggested_agency = None
        if not agency_name and location_context:
            agency_result = self._identify_agency_for_officer(
                city=city, state=state,
                officer_name=officer_name, officer_title=officer_title,
                officer_description=officer_description
            )
            if agency_result.get('success') and agency_result.get('agency_name'):
                suggested_agency = agency_result['agency_name']
                agency_name = suggested_agency

        if not agency_name:
            return {
                'success': False,
                'error': 'Agency name is required. Please enter the agency name or provide location info to identify it.',
            }

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
                response_data = {
                    'success': True,
                    'address': result['address'],
                    'confidence': result.get('confidence', 'medium'),
                    'source_note': result.get('source_note', 'Found via web search'),
                }
                if suggested_agency:
                    response_data['suggested_agency'] = suggested_agency
                return response_data
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

    def lookup_federal_court(self, city: str, state: str) -> dict:
        """
        Look up the federal district court with jurisdiction over a location using web search.

        This is used as a fallback when the static court lookup doesn't have the city
        in its database (small towns, rural areas).

        Args:
            city: City/town name
            state: State name or abbreviation

        Returns:
            dict with 'success', 'court_name', 'district', 'confidence'
        """
        if not city or not state:
            return {
                'success': False,
                'error': 'City and state are required',
            }

        try:
            # Get prompt from database
            prompt = self._get_prompt('lookup_federal_court')
            user_prompt = prompt['user_prompt_template'].format(city=city, state=state)

            # Use GPT with web search to find the correct federal court
            response = self.client.responses.create(
                model=prompt['model_name'],
                tools=[{"type": "web_search_preview"}],
                input=f"{prompt['system_message']}\n\n{user_prompt}"
            )

            # Extract the text response
            response_text = ""
            for item in response.output:
                if hasattr(item, 'content'):
                    for content in item.content:
                        if hasattr(content, 'text'):
                            response_text = content.text
                            break

            if not response_text:
                return {
                    'success': False,
                    'error': 'No response from web search',
                }

            # Parse the response to extract structured data
            parse_prompt = f"""Extract the federal district court information from this text. Return a JSON object:

Text: {response_text}

Return format:
{{
    "court_name": "Full official court name (e.g., 'United States District Court for the Northern District of New York')",
    "district": "The district name (e.g., 'Northern', 'Southern', 'Eastern', 'Western', or 'District' for single-district states)",
    "confidence": "high" or "medium",
    "source": "Brief note about how this was determined"
}}

If no clear court can be determined, return:
{{
    "court_name": null,
    "district": null,
    "confidence": "low",
    "source": "Could not determine federal court"
}}"""

            parse_response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Extract federal court information from text. Return only valid JSON."},
                    {"role": "user", "content": parse_prompt}
                ],
                temperature=0.1,
                max_tokens=500,
                response_format={"type": "json_object"}
            )

            import json
            result = json.loads(parse_response.choices[0].message.content)

            if result.get('court_name'):
                return {
                    'success': True,
                    'court_name': result['court_name'],
                    'district': result.get('district', ''),
                    'confidence': result.get('confidence', 'medium'),
                    'source': result.get('source', 'Found via web search'),
                    'method': 'gpt_web_search',
                }
            else:
                return {
                    'success': False,
                    'error': 'Could not determine federal court for this location',
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

            # Build response with success flag
            response_data = {
                'success': True,
                'suggestions': result.get('suggestions', []),
                'notes': result.get('notes', ''),
            }

            # For evidence section, also include the new two-category format
            if section_type == 'evidence':
                response_data['evidence_you_have'] = result.get('evidence_you_have', [])
                response_data['evidence_to_obtain'] = result.get('evidence_to_obtain', [])
                response_data['tips'] = result.get('tips', '')

            return response_data

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }

    def review_document(self, document_data: dict) -> dict:
        """
        Perform AI review of a Section 1983 complaint document.

        Analyzes legal strength, clarity, and completeness.
        Returns structured feedback with issues keyed by section.

        Args:
            document_data: Dict containing all document sections data

        Returns:
            dict with 'success', 'issues' list, 'strengths', 'summary'
        """
        import json

        try:
            # Get prompt from database
            prompt = self._get_prompt('review_document')

            # Convert document data to JSON string for the prompt
            document_json = json.dumps(document_data, indent=2, default=str)

            user_prompt = prompt['user_prompt_template'].format(
                document_json=document_json
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

            result = json.loads(response.choices[0].message.content)

            return {
                'success': True,
                'overall_assessment': result.get('overall_assessment', 'needs_work'),
                'issues': result.get('issues', []),
                'strengths': result.get('strengths', []),
                'summary': result.get('summary', ''),
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }

    def rewrite_section(self, section_type: str, current_content: str,
                        issue: dict, document_data: dict) -> dict:
        """
        Rewrite a section to fix an identified issue.

        Args:
            section_type: Type of section (e.g., 'incident_narrative', 'damages')
            current_content: Current text content of the section
            issue: Dict with 'title', 'description', 'suggestion' from review
            document_data: Full document data for context

        Returns:
            dict with 'success', 'rewritten_content', 'changes_summary', 'field_updates'
        """
        import json

        try:
            prompt = self._get_prompt('rewrite_section')

            # Create a condensed document context (not the full JSON)
            context_parts = []
            if document_data.get('plaintiff', {}).get('first_name'):
                p = document_data['plaintiff']
                context_parts.append(f"Plaintiff: {p.get('first_name', '')} {p.get('last_name', '')}")
            if document_data.get('incident', {}).get('incident_date'):
                inc = document_data['incident']
                time_str = inc.get('incident_time', '')
                context_parts.append(f"Incident: {inc.get('incident_date', '')} at {time_str}, {inc.get('incident_location', '')}, {inc.get('city', '')}, {inc.get('state', '')}")
            if document_data.get('defendants'):
                def_names = [d.get('name', '') for d in document_data['defendants'][:3]]
                context_parts.append(f"Defendants: {', '.join(def_names)}")
            # Include narrative for context (has story details that may mention times, dates, etc.)
            if document_data.get('narrative', {}).get('detailed_narrative'):
                narrative = document_data['narrative']['detailed_narrative'][:500]
                context_parts.append(f"Story: {narrative}...")
            elif document_data.get('narrative', {}).get('summary'):
                context_parts.append(f"Summary: {document_data['narrative']['summary'][:200]}...")

            document_context = '\n'.join(context_parts) if context_parts else 'No additional context available'

            user_prompt = prompt['user_prompt_template'].format(
                section_type=section_type,
                current_content=current_content or '(No content yet)',
                issue_title=issue.get('title', ''),
                issue_description=issue.get('description', ''),
                issue_suggestion=issue.get('suggestion', ''),
                document_context=document_context
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

            result = json.loads(response.choices[0].message.content)

            return {
                'success': True,
                'rewritten_content': result.get('rewritten_content', ''),
                'changes_summary': result.get('changes_summary', ''),
                'field_updates': result.get('field_updates', {}),
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
