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

AGENCY INFERENCE RULES - CRITICAL:
- IMPORTANT: Many small towns, villages, and unincorporated communities do NOT have their own police department
- For unincorporated areas or small towns (population under 5,000): Use COUNTY SHERIFF'S OFFICE, NOT "[City] Police Department"
- Example: "Zama, Mississippi" is an unincorporated community → use "Attala County Sheriff's Office" NOT "Zama Police Department"
- For larger cities (population over 10,000): May infer "[City] Police Department"
- For sheriff's deputies: Use "[County] County Sheriff's Office"
- For state troopers: Use "[State] Highway Patrol" or "[State] State Police"
- When uncertain if a place has local police, mark agency_inferred=true and use "Unknown - verify jurisdiction"
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

        # Use chat completions with a detailed prompt about jurisdiction
        prompt = f"""Determine the law enforcement agencies that have jurisdiction in {city}, {state}.

CRITICAL: Many small towns, villages, and unincorporated communities do NOT have their own police department.
In these cases, law enforcement is provided by:
1. The COUNTY SHERIFF'S OFFICE (primary for rural/unincorporated areas)
2. State Highway Patrol (for state roads)
3. A nearby larger city's police (rare, only with agreements)

ANALYSIS REQUIRED:
1. Is {city} a major city (population over 10,000) that would have its own police department?
2. Or is it a small town, village, CDP, or unincorporated community?
3. What county is {city}, {state} located in?

IMPORTANT EXAMPLES:
- "Zama, Mississippi" = unincorporated community in Attala County → Attala County Sheriff's Office (NO local police)
- "New York City" = major city → NYPD (has local police)
- "Smallville, Kansas" (fictional small town) → likely County Sheriff
- Unincorporated areas ALWAYS use County Sheriff

Return a JSON object:
{{
    "location_type": "major_city|small_town|village|unincorporated|cdp",
    "has_local_police": true only if this is a city large enough to have its own police department,
    "county_name": "Name of the county (e.g., 'Attala' not 'Attala County')",
    "agencies": [
        {{
            "name": "Full official name (e.g., 'Attala County Sheriff's Office')",
            "type": "sheriff|police|state_patrol",
            "is_primary": true if this is the most likely agency with jurisdiction,
            "confidence": "high|medium|low",
            "notes": "Brief explanation"
        }}
    ],
    "verification_warning": "User-facing warning about verifying the agency"
}}

Be conservative: If uncertain whether a place has local police, assume it does NOT and suggest County Sheriff as primary."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a legal research assistant with knowledge of US law enforcement jurisdictions. You know that small towns and unincorporated areas are served by county sheriffs, not local police. Be accurate about which locations have their own police departments."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1500,
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
