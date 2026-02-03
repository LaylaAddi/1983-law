"""
Management command to seed AI prompts from hardcoded values.
Run this after initial migration to populate the AIPrompt table.
"""
from django.core.management.base import BaseCommand
from documents.models import AIPrompt


class Command(BaseCommand):
    help = 'Seed AI prompts with initial values from hardcoded prompts'

    def handle(self, *args, **options):
        prompts = [
            {
                'prompt_type': 'find_law_enforcement',
                'title': 'Find Law Enforcement Agency',
                'description': '''Identifies the correct law enforcement agency for a given location.

CRITICAL for small towns: Many small towns, villages, and unincorporated communities do NOT have their own police department. This prompt helps identify whether to use County Sheriff instead.

Called when: User enters a city/state, or when verifying AI-suggested agencies.''',
                'system_message': 'You are a legal research assistant with knowledge of US law enforcement jurisdictions. You know that small towns and unincorporated areas are served by county sheriffs, not local police. Be accurate about which locations have their own police departments.',
                'user_prompt_template': '''Determine the law enforcement agencies that have jurisdiction in {city}, {state}.

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

Be conservative: If uncertain whether a place has local police, assume it does NOT and suggest County Sheriff as primary.''',
                'available_variables': 'city, state',
                'model_name': 'gpt-4o-mini',
                'temperature': 0.1,
                'max_tokens': 1500,
            },
            {
                'prompt_type': 'parse_story',
                'title': 'Parse User Story',
                'description': '''Analyzes the user's story about their civil rights incident and extracts structured data.

This is the MAIN prompt that processes "Tell Your Story" input. It extracts:
- Incident details (date, time, location, address)
- Officer/defendant information (individual officers AND government agencies)
- Witness information (including whether witnesses were recording)
- Evidence mentioned (plaintiff recordings, body cams, surveillance, etc.)
- Damages suffered (physical, emotional, financial, medical, lost wages)
- Rights that may have been violated
- Recording details (was plaintiff recording? what device?)

Called when: User submits their story in the wizard or "Tell Your Story" step.
Field names match wizard stepData keys directly for clean mapping.''',
                'system_message': 'You are a legal document assistant that extracts structured information from personal narratives about civil rights violations. Be EXTREMELY thorough - extract every detail stated AND reasonably inferred from context. If the plaintiff mentions recording, that is evidence they HAVE. If officers had body cameras, that is evidence to OBTAIN. Include evidence even if it was deleted or seized. Always respond with valid JSON.',
                'user_prompt_template': '''Analyze this personal account of a civil rights incident and extract ALL possible information for a Section 1983 complaint.

IMPORTANT RULES:
- Extract EVERY detail from the text, including details inferred from context
- Example: "city hall in Oklahoma City" → incident_location="City Hall", address="", city="Oklahoma City", state="OK", location_type="city_hall"
- Example: "I was recording on my Samsung" → was_recording=true, recording_device="Samsung phone"
- Example: "my friend was filming" → witness with was_recording=true
- For dates/times, extract if mentioned in any format (e.g., "last Tuesday", "March 15th", "around 3pm")
- If the story contains "Not applicable or unknown:", DO NOT ask questions about those topics

CRITICAL - DATE AND TIME ARE REQUIRED:
- Date and time of the incident are MANDATORY for legal filings
- If date is NOT clearly stated, you MUST include a question asking for the exact date in questions_to_ask
- If time is NOT clearly stated, you MUST include a question asking for the approximate time in questions_to_ask
- TIME MUST INCLUDE AM/PM - If user provides time WITHOUT AM/PM (e.g., "930", "9:30", "2:30"), you MUST:
  1. Ask for clarification: "You mentioned the incident happened at [time]. Was that AM or PM?"
  2. Do NOT guess or assume AM or PM - this is legally critical
  3. Do NOT use the ambiguous time anywhere in the document until clarified
- These questions should be the FIRST questions in the list

AGENCY INFERENCE RULES - CRITICAL:
- IMPORTANT: Many small towns, villages, and unincorporated communities do NOT have their own police department
- For unincorporated areas or small towns (population under 5,000): Use COUNTY SHERIFF'S OFFICE, NOT "[City] Police Department"
- Example: "Zama, Mississippi" is an unincorporated community → use "Attala County Sheriff's Office" NOT "Zama Police Department"
- For larger cities (population over 10,000): May infer "[City] Police Department"
- For sheriff's deputies: Use "[County] County Sheriff's Office"
- For state troopers: Use "[State] Highway Patrol" or "[State] State Police"
- When uncertain if a place has local police, mark agency_inferred=true and use "Unknown - verify jurisdiction"
- Set "agency_inferred" to true when you infer the agency, false when explicitly stated

DEFENDANT TYPE RULES:
- "individual" = a specific person (officer, guard, clerk, etc.)
- "agency" = a government entity (police department, sheriff's office, city, county)
- ALWAYS include BOTH the individual officers AND their employing agency as separate defendants
- Example: If "Officer Smith of Tampa PD" → two defendants: Officer Smith (individual) + Tampa Police Department (agency)

USER'S STORY:
{story_text}

Extract information for the following sections. Fill in as many fields as possible based on the story:

{{
    "incident_overview": {{
        "incident_date": "YYYY-MM-DD format or partial date, null if not mentioned",
        "incident_time": "HH:MM AM/PM format ONLY if AM/PM is clear, description like 'afternoon' if general, null if not mentioned or if AM/PM is ambiguous",
        "incident_location": "location name like 'City Hall', 'Corner of 5th and Main St', etc.",
        "address": "street address if mentioned or known (e.g., '123 Main St'), empty string if not known",
        "city": "city name - extract from context",
        "state": "two-letter state code - infer from city if possible",
        "location_type": "MUST be one of these exact keys: sidewalk, public_easement, home, vehicle, business, park, police_station, fire_station, courthouse, city_hall, dmv, post_office, public_library, government_office, dot_inspection, jail_prison, school, hospital, public_transit, parking_lot, highway, other",
        "location_type_other": "description if location_type is 'other', empty string otherwise",
        "was_recording": true/false/null,
        "recording_device": "device used: 'cell phone', 'Samsung phone', 'GoPro', etc. if mentioned, empty string otherwise"
    }},
    "incident_narrative": {{
        "summary": "2-3 sentence summary of what happened, written in third person",
        "detailed_narrative": "full chronological account, written in third person - be thorough",
        "what_were_you_doing": "what the plaintiff was doing before/during incident",
        "initial_contact": "how the encounter with officials began",
        "what_was_said": "ALL dialogue or statements made by any parties - quote when possible",
        "physical_actions": "ALL physical actions taken by anyone - be specific about force used",
        "how_it_ended": "how the encounter concluded - arrests, citations, release, etc."
    }},
    "defendants": [
        {{
            "name": "officer/official name if mentioned, 'Unknown Officer' if unnamed but described",
            "badge_number": "badge number if mentioned, empty string otherwise",
            "title_rank": "title like 'Officer', 'Sergeant', 'Deputy', 'Security Guard', etc.",
            "agency_name": "department or agency name - use County Sheriff for small towns",
            "agency_inferred": true/false,
            "defendant_type": "individual or agency",
            "description": "description of this defendant's role/actions in the incident"
        }}
    ],
    "witnesses": [
        {{
            "name": "witness name if known, or descriptive label like 'bystander', 'store employee', 'friend'",
            "description": "brief description of who they are and their relationship to plaintiff",
            "what_they_saw": "what they witnessed - be specific",
            "was_recording": true/false/null,
            "recording_device": "device used if mentioned, empty string otherwise"
        }}
    ],
    "evidence": [
        {{
            "evidence_type": "video|audio|photo|document|body_cam|dash_cam|surveillance|other",
            "title": "brief title like 'My cell phone recording' or 'Body camera footage'",
            "description": "what this evidence shows or contains",
            "date_created": "YYYY-MM-DD if mentioned, use incident date if evidence was captured during incident, null otherwise",
            "is_in_possession": true/false,
            "needs_subpoena": true/false,
            "notes": "additional details like duration, file format, or how to obtain"
        }}
    ],
    "damages": {{
        "physical_injuries": "describe ALL physical injuries mentioned (bruises, cuts, pain, etc.) or empty string",
        "medical_treatment": "describe any medical treatment received or needed (ER visit, ambulance, etc.) or empty string",
        "emotional_distress": "describe emotional/psychological impact (anxiety, fear, PTSD, humiliation, etc.) or empty string",
        "financial_losses": "describe financial losses (property damage, phone broken, car towed, etc.) or empty string",
        "lost_wages": "describe any missed work or lost income mentioned, or empty string",
        "ongoing_effects": "describe any ongoing or lasting effects mentioned, or empty string"
    }},
    "rights_violated": {{
        "suggested_violations": [
            {{
                "right": "the specific right violated (e.g., 'Fourth Amendment - Excessive Force', 'First Amendment - Recording')",
                "amendment": "first|fourth|fifth|fourteenth",
                "explanation": "1-2 sentence explanation of how this right was violated based on the facts"
            }}
        ]
    }},
    "questions_to_ask": [
        "question text here - ask about missing critical details"
    ]
}}

EVIDENCE EXTRACTION - BE THOROUGH:
- If plaintiff was recording → include their recording as evidence they HAVE
- If officers wore body cameras → include body cam footage as evidence to OBTAIN
- If dashcam likely exists (traffic stop) → include dashcam as evidence to OBTAIN
- If incident was near businesses → suggest surveillance footage to OBTAIN
- If plaintiff was injured → suggest medical records as evidence to OBTAIN
- If there was an arrest → suggest arrest report, booking records as evidence to OBTAIN
- 911 calls → suggest 911 recordings as evidence to OBTAIN

QUESTIONS TO ASK - Generate follow-up questions for CRITICAL missing information:

1. ALWAYS ask for date if not explicitly stated (e.g., "What was the exact date of this incident?")
2. ALWAYS ask for time if not explicitly stated (e.g., "What time did this incident occur?")
3. If time is given WITHOUT AM/PM (e.g., "930", "9:30", "2 o'clock"), ALWAYS ask: "You mentioned the incident happened at [time]. Was that AM or PM?"
4. Then add 2-6 other relevant questions for missing details

Date and time questions MUST come first if those are missing.
AM/PM clarification MUST be asked if time is ambiguous - do NOT guess.

Respond with ONLY the JSON object.''',
                'available_variables': 'story_text',
                'model_name': 'gpt-4o-mini',
                'temperature': 0.1,
                'max_tokens': 4000,
            },
            {
                'prompt_type': 'analyze_rights',
                'title': 'Analyze Constitutional Rights Violations',
                'description': '''Analyzes incident details to identify which constitutional rights were violated.

Reviews the incident narrative and suggests applicable:
- First Amendment violations (speech, press, assembly, petition)
- Fourth Amendment violations (search, seizure, arrest, excessive force)
- Fifth Amendment violations (self-incrimination, due process)
- Fourteenth Amendment violations (due process, equal protection)

Called when: User clicks "Analyze Rights" in the Rights Violated section.''',
                'system_message': 'You are a civil rights legal analyst helping identify constitutional violations in Section 1983 cases. Be accurate, thorough, and write explanations that are conversational yet professional. Always respond with valid JSON.',
                'user_prompt_template': '''Analyze this incident and identify which constitutional rights were likely violated. This is for a Section 1983 civil rights complaint against police officers or government officials.

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

Only include rights that are clearly supported by the facts.''',
                'available_variables': 'context',
                'model_name': 'gpt-4o-mini',
                'temperature': 0.3,
                'max_tokens': 2000,
            },
            {
                'prompt_type': 'suggest_relief',
                'title': 'Suggest Legal Relief',
                'description': '''Recommends appropriate legal relief based on the case details.

Analyzes rights violated, damages suffered, and evidence to suggest:
- Compensatory damages
- Punitive damages
- Declaratory relief
- Injunctive relief
- Attorney fees
- Jury trial recommendation

Called when: User clicks "Suggest Relief" in the Relief Sought section.''',
                'system_message': 'You are a legal assistant helping prepare Section 1983 civil rights complaints. Provide thoughtful relief recommendations based on the specific facts of each case. Always respond with valid JSON.',
                'user_prompt_template': '''Based on this Section 1983 civil rights case information, recommend appropriate relief:

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
        "suggested_declaration": "What should be declared"
    }},
    "injunctive_relief": {{
        "recommended": true/false,
        "reason": "Brief explanation - recommend if policy changes or training are needed",
        "suggested_injunction": "What changes should be ordered"
    }},
    "attorney_fees": {{
        "recommended": true,
        "reason": "42 U.S.C. § 1988 allows recovery of attorney fees in civil rights cases"
    }},
    "jury_trial": {{
        "recommended": true/false,
        "reason": "Brief explanation"
    }}
}}

Be specific to THIS case.''',
                'available_variables': 'context',
                'model_name': 'gpt-4o-mini',
                'temperature': 0.2,
                'max_tokens': 1500,
            },
            {
                'prompt_type': 'suggest_damages',
                'title': 'Suggest Damages from Story',
                'description': '''Analyzes the user's story to identify potential damages for the complaint.

Identifies:
- Physical injuries (pain, medical treatment)
- Emotional distress (fear, anxiety, humiliation, PTSD)
- Economic losses (lost wages, medical bills, property damage)
- Constitutional injury (the violation itself)
- Reputational harm

Called when: User clicks "Analyze Story & Suggest" in the Damages section.''',
                'system_message': 'You are a legal assistant helping identify damages for a Section 1983 civil rights complaint. Analyze the story and identify ALL potential damages the plaintiff may have suffered. Always respond with valid JSON.',
                'user_prompt_template': '''Analyze this story and identify all damages the plaintiff may have suffered:

STORY:
{story_text}

EXISTING DAMAGES ALREADY RECORDED:
{existing}

Identify any damages mentioned or implied in the story that aren't already recorded. Even if no explicit injuries are mentioned, consider:
- The emotional impact of the constitutional violation
- Any inconvenience or disruption described
- Potential for ongoing effects

Return JSON format:
{{
    "suggestions": [
        {{
            "damage_type": "physical|emotional|economic|constitutional|reputational",
            "description": "Clear description of the damage",
            "details": "Supporting details from the story"
        }}
    ],
    "notes": "Any additional context about potential damages"
}}''',
                'available_variables': 'story_text, existing',
                'model_name': 'gpt-4o-mini',
                'temperature': 0.3,
                'max_tokens': 2000,
            },
            {
                'prompt_type': 'suggest_witnesses',
                'title': 'Suggest Witnesses from Story',
                'description': '''Analyzes the user's story to identify potential witnesses.

Identifies:
- People explicitly named who saw the incident
- Bystanders mentioned
- Other officers/employees present
- Anyone the plaintiff spoke to before/during/after
- People who may have video or other evidence

Called when: User clicks "AI Suggest Witnesses" in the Witnesses section.''',
                'system_message': 'You are a legal assistant helping identify potential witnesses for a Section 1983 civil rights complaint. Analyze the story and identify ALL potential witnesses mentioned or implied. Always respond with valid JSON.',
                'user_prompt_template': '''Analyze this story and identify all potential witnesses:

STORY:
{story_text}

EXISTING WITNESSES ALREADY RECORDED:
{existing}

Identify anyone mentioned who could serve as a witness, including people who may not be explicitly named.

Return JSON format:
{{
    "suggestions": [
        {{
            "name": "Name if known, or description like 'Unknown bystander'",
            "relationship": "How they relate to the incident",
            "what_they_witnessed": "What they likely saw or know",
            "contact_info": "Any contact info mentioned, or 'Unknown'"
        }}
    ],
    "notes": "Tips for finding additional witnesses"
}}''',
                'available_variables': 'story_text, existing',
                'model_name': 'gpt-4o-mini',
                'temperature': 0.3,
                'max_tokens': 2000,
            },
            {
                'prompt_type': 'suggest_evidence',
                'title': 'Suggest Evidence from Story',
                'description': '''Analyzes the user's story to identify evidence they HAVE vs evidence they should OBTAIN.

CRITICAL DISTINCTION:
- evidence_you_have: Items the user indicates they possess or created (recordings, photos, documents)
- evidence_to_obtain: Items that may exist but user doesn't have yet (body cams, police reports, etc.)

Called when: User clicks "Analyze Story & Suggest" in the Evidence section.''',
                'system_message': 'You are a legal assistant helping identify evidence for a Section 1983 civil rights complaint. Distinguish between evidence the user HAS versus evidence they should OBTAIN. If the user mentions recording, filming, photographing, or documenting something, assume they HAVE that evidence. Always respond with valid JSON.',
                'user_prompt_template': '''Analyze this story and categorize evidence into TWO separate lists:

STORY:
{story_text}

EXISTING EVIDENCE ALREADY RECORDED:
{existing}

INSTRUCTIONS:

1. "evidence_you_have" - Include if the story indicates the user has this evidence:
   - ANY mention of recording/filming: "I was recording", "I recorded", "I filmed", "my phone was recording"
   - ANY mention of photos: "I took photos", "I photographed", "I have pictures"
   - ANY mention of the device used: "on my phone", "with my camera", "samsung phone"
   - Documents they kept: receipts, tickets, citations they received
   - IMPORTANT: If they say "I was recording" - they HAVE a recording. Include it!

2. "evidence_to_obtain" - Evidence that likely EXISTS but user needs to REQUEST:
   - Body camera footage from officers
   - Police dashcam footage
   - Police reports, incident reports, arrest records
   - 911 call recordings
   - Surveillance footage from nearby businesses
   - Medical records (if injured)
   - Witness statements

Return JSON format:
{{
    "evidence_you_have": [
        {{
            "evidence_type": "video|audio|document|physical|digital|photo",
            "description": "What the evidence is",
            "details": "Specific details from story about this evidence"
        }}
    ],
    "evidence_to_obtain": [
        {{
            "evidence_type": "video|audio|document|physical|digital|witness_statement",
            "description": "What the evidence is",
            "how_to_obtain": "How to request/get this evidence (FOIA, subpoena, etc.)",
            "why_important": "Why this evidence matters for the case"
        }}
    ],
    "tips": "General tips for preserving evidence and making requests"
}}''',
                'available_variables': 'story_text, existing',
                'model_name': 'gpt-4o-mini',
                'temperature': 0.3,
                'max_tokens': 2500,
            },
            {
                'prompt_type': 'suggest_rights_violated',
                'title': 'Suggest Rights Violations from Story',
                'description': '''Analyzes the user's story to identify constitutional rights violations.

Identifies violations of:
- First Amendment: Free speech, recording police, religion, assembly, petition
- Fourth Amendment: Unreasonable search/seizure, excessive force, false arrest
- Fifth Amendment: Due process, self-incrimination
- Eighth Amendment: Cruel and unusual punishment
- Fourteenth Amendment: Equal protection, due process

Called when: User clicks "Analyze Story & Suggest" in the Rights Violated section.''',
                'system_message': 'You are a legal assistant helping identify constitutional rights violations for a Section 1983 complaint. Analyze the story and identify ALL potential constitutional violations. Always respond with valid JSON.',
                'user_prompt_template': '''Analyze this story and identify all constitutional rights that may have been violated:

STORY:
{story_text}

EXISTING RIGHTS VIOLATIONS ALREADY RECORDED:
{existing}

Focus on identifying clear constitutional violations that would support a Section 1983 claim.

Return JSON format:
{{
    "suggestions": [
        {{
            "amendment": "1st|4th|5th|8th|14th",
            "right": "Specific right violated",
            "description": "How it was violated based on the story",
            "strength": "strong|moderate|weak"
        }}
    ],
    "notes": "Analysis of the strongest claims"
}}''',
                'available_variables': 'story_text, existing',
                'model_name': 'gpt-4o-mini',
                'temperature': 0.3,
                'max_tokens': 2000,
            },
            {
                'prompt_type': 'identify_officer_agency',
                'title': 'Identify Agency for Officer',
                'description': '''Identifies the likely law enforcement agency for an officer based on location and officer info.

Used when: User clicks "Find Agency & Address" on edit defendant page and the agency field is empty.

Analyzes:
- Officer's title/rank (Deputy → Sheriff, Trooper → Highway Patrol)
- Location (city/state from Incident Overview)
- Officer description

Called when: Looking up agency info for an individual officer defendant.''',
                'system_message': 'You identify law enforcement agencies based on location and officer information. You know that small towns are served by County Sheriff, not local police. Be accurate. Always respond with valid JSON.',
                'user_prompt_template': '''Based on the following information, identify the most likely law enforcement agency this officer works for.

Location: {location}
Officer info: {officer_info}

Consider:
- Title like "Deputy" suggests County Sheriff's Office
- Title like "Trooper" suggests State Highway Patrol
- Title like "Officer" or "Detective" in a city suggests City Police Department
- Small towns often don't have their own police and are served by County Sheriff

Return a JSON object:
{{
    "agency_name": "Official agency name (e.g., 'Tampa Police Department', 'Hillsborough County Sheriff's Office')",
    "confidence": "high" or "medium" or "low",
    "reasoning": "Brief explanation of why this agency was identified"
}}

If you cannot determine the agency with reasonable confidence, return:
{{
    "agency_name": null,
    "confidence": "low",
    "reasoning": "Explanation of why agency could not be determined"
}}''',
                'available_variables': 'location, officer_info',
                'model_name': 'gpt-4o-mini',
                'temperature': 0.1,
                'max_tokens': 300,
            },
            {
                'prompt_type': 'lookup_federal_court',
                'title': 'Lookup Federal District Court',
                'description': '''Uses web search to find the correct federal district court for a given city and state.

Called when: Static court lookup fails to find the city in its database (small towns, rural areas).

Returns the official name of the federal district court with jurisdiction.''',
                'system_message': 'You are a legal research assistant that identifies federal district court jurisdictions. Use web search to find accurate, current information. Always respond with valid JSON.',
                'user_prompt_template': '''What federal district court has jurisdiction over {city}, {state}?

Search for the correct United States District Court that covers this location. Federal district courts have names like:
- "United States District Court for the Northern District of New York"
- "United States District Court for the Southern District of California"
- "United States District Court for the District of Alaska" (single-district states)

Return a JSON object:
{{
    "court_name": "Full official court name",
    "district": "The district name (e.g., 'Northern', 'Southern', 'Eastern', 'Western', or 'District' for single-district states)",
    "confidence": "high" or "medium",
    "source": "Brief note about how this was determined"
}}

Be accurate - this is for legal filings.''',
                'available_variables': 'city, state',
                'model_name': 'gpt-4o-mini',
                'temperature': 0.1,
                'max_tokens': 500,
            },
            {
                'prompt_type': 'review_document',
                'title': 'Review Legal Document',
                'description': '''Comprehensive AI review of the Section 1983 complaint document.

Analyzes the ACTUAL RENDERED DOCUMENT TEXT as displayed to the user:
- Cross-document consistency (dates, times, names, locations)
- Missing required information
- Legal document formatting
- Practical fixable issues

Called when: User clicks "AI Review" on the document review page.''',
                'system_message': '''You are a legal document proofreader checking a Section 1983 complaint for errors and inconsistencies.
Your job is to find PRACTICAL issues that can be fixed - not to critique legal strategy.
Focus on: inconsistent facts, missing information, formatting problems, and unclear writing.
You are reviewing the ACTUAL DOCUMENT TEXT as it appears to the user, not raw database fields.
Always respond with valid JSON.''',
                'user_prompt_template': '''Review this Section 1983 civil rights complaint for errors, inconsistencies, and missing information.

This is the ACTUAL DOCUMENT as it will appear when filed. Review the text below:

{document_json}

PRIORITY 1 - DOCUMENT COMPLETENESS:
- Are there any placeholder texts like "[DATE]", "[LOCATION]", "[NAME]", "[CITY, STATE]", etc.?
- Is the incident date and time clearly stated?
- Is the incident location specific?
- Are all defendants properly identified?
- Is the narrative complete and coherent?

PRIORITY 2 - FORMATTING AND CLARITY:
- Is the narrative written in third person? (should say "Plaintiff" not "I", "me", "my")
- Is the writing clear and professional for a legal document?
- Is the chronology of events clear?
- Are the causes of action properly connected to the facts?

PRIORITY 3 - LEGAL DOCUMENT REQUIREMENTS:
- Is at least one constitutional right violation clearly stated?
- Is at least one type of damage described?
- Is the relief sought section complete?

DO NOT flag these as issues:
- Legal strategy opinions (e.g., "claims may be weak")
- Suggestions to add more evidence (user may not have more)
- Minor stylistic preferences
- Information that isn't required for filing

Return a JSON object with issues found:
{{
    "overall_assessment": "ready|needs_fixes|has_errors",
    "issues": [
        {{
            "section": "incident_overview|incident_narrative|defendants|damages|rights_violated|relief_sought|plaintiff_info",
            "severity": "error|warning|suggestion",
            "title": "Brief issue title (5-10 words)",
            "description": "Specific explanation - quote the problematic text if applicable",
            "suggestion": "Exact fix needed (be specific, not vague)"
        }}
    ],
    "strengths": ["List 1-3 things the document does well"],
    "summary": "1-2 sentence summary focusing on the most important fixes needed"
}}

Find 2-5 ACTIONABLE issues. Every issue must have a specific, concrete fix.''',
                'available_variables': 'document_json',
                'model_name': 'gpt-4o-mini',
                'temperature': 0.3,
                'max_tokens': 2500,
            },
            {
                'prompt_type': 'rewrite_section',
                'title': 'Rewrite Section to Fix Issue',
                'description': '''Rewrites a specific section of the complaint to address an identified issue.

Used during the step-through fix workflow after AI review identifies issues.
Takes the current section content and the issue to fix, returns improved text.

Called when: User clicks "Apply Fix" during step-through review.''',
                'system_message': '''You are an experienced civil rights attorney helping improve a Section 1983 complaint.
Your task is to rewrite a specific section to address an identified issue.

CRITICAL RULES - VIOLATION OF THESE IS UNACCEPTABLE:
1. NEVER use placeholder text like [insert time], [DATE], [LOCATION], [NAME], etc.
2. NEVER remove or lose ANY factual information from the original content
3. If a specific time, date, name, address, or location exists in the original, it MUST appear in your rewrite EXACTLY
4. If information is missing from the original, leave it missing - do NOT add placeholders
5. Your job is to IMPROVE PRESENTATION, not to add or remove facts

Write in proper legal document style appropriate for federal court.
Always respond with valid JSON.''',
                'user_prompt_template': '''Rewrite this section of a Section 1983 complaint to address the identified issue.

SECTION TYPE: {section_type}

CURRENT CONTENT:
{current_content}

ISSUE TO FIX:
Title: {issue_title}
Description: {issue_description}
Suggestion: {issue_suggestion}

FULL DOCUMENT CONTEXT (for reference only, do not rewrite):
{document_context}

ABSOLUTE REQUIREMENTS - READ CAREFULLY:
1. Every specific fact in CURRENT CONTENT must appear in your rewrite:
   - Times (e.g., "2:30 PM" must stay "2:30 PM")
   - Dates (e.g., "January 15, 2024" must stay "January 15, 2024")
   - Names (e.g., "Officer John Smith" must stay "Officer John Smith")
   - Locations (e.g., "123 Main Street" must stay "123 Main Street")
   - Amounts (e.g., "$5,000" must stay "$5,000")

2. NEVER use placeholders like:
   - [insert time]
   - [DATE]
   - [LOCATION]
   - [NAME]
   - [amount]
   If data is missing, write around it naturally without calling attention to it.

3. Only improve HOW the information is presented, not WHAT information is included.

Return a JSON object:
{{
    "rewritten_content": "The improved section text with ALL original facts preserved exactly",
    "changes_summary": "Brief explanation of what was changed and why (1-2 sentences)",
    "field_updates": {{
        "field_name": "new_value"
    }}
}}

CRITICAL: field_updates is REQUIRED for the fix to be saved. Map to actual database fields:

For incident_overview section (MUST use these exact field names):
- "incident_location": "Location name" (e.g., "City Hall, Waterloo, Iowa")
- "city": "City name" (e.g., "Waterloo")
- "state": "State abbreviation" (e.g., "Iowa")
- "incident_date": "YYYY-MM-DD" format (e.g., "2024-01-15")
- "incident_time": "HH:MM:SS" 24-hour format (e.g., "14:30:00")

For incident_narrative section:
- "detailed_narrative": The full narrative text

For damages section:
- "physical_injury_description", "emotional_distress_description", "property_damage_description"

For rights_violated section:
- "fourth_amendment_details", "first_amendment_details", "fourteenth_amendment_details"

IMPORTANT: Include ALL fields that need updating. For location consistency issues, typically update "incident_location" field.''',
                'available_variables': 'section_type, current_content, issue_title, issue_description, issue_suggestion, document_context',
                'model_name': 'gpt-4o-mini',
                'temperature': 0.2,
                'max_tokens': 2000,
            },
            {
                'prompt_type': 'generate_facts',
                'title': 'Generate Statement of Facts',
                'description': '''Generates the STATEMENT OF FACTS section for the Section 1983 complaint.

Uses AI to write a formal legal narrative based on:
- Incident details (date, time, location)
- Plaintiff's narrative and what happened
- Defendant information
- Witness information and evidence they captured
- Video transcript evidence (if provided)

Called when: Document is generated on the Final Review page.''',
                'system_message': 'You are an expert legal writer drafting Section 1983 civil rights complaints for federal court. Write clear, factual, professional legal prose. Use numbered paragraphs and formal legal style.',
                'user_prompt_template': '''Write the STATEMENT OF FACTS section for a Section 1983 federal complaint based on these details:

PLAINTIFF: {plaintiff_name}
DATE: {incident_date}
TIME: {incident_time}
LOCATION: {incident_location}, {city}, {state}
WAS RECORDING: {was_recording}

NARRATIVE DETAILS:
- What plaintiff was doing: {what_were_you_doing}
- What happened: {detailed_narrative}
- What was said: {what_was_said}
- Physical actions: {physical_actions}
- How it ended: {how_it_ended}

DEFENDANTS: {defendants}{witness_section}{video_section}

REQUIREMENTS:
1. Write in formal legal style with numbered paragraphs
2. Use third person ("Plaintiff" not "I")
3. Be chronological and specific about times, locations, actions
4. State facts objectively without legal conclusions
5. Each paragraph should focus on one key fact or event
6. Start paragraph numbers at 10 (previous sections used 1-9)
7. Reference defendants by name where known
8. Include specific details that support the constitutional claims
9. If witnesses captured video/photo evidence, include a paragraph stating that the incident was recorded and describing what the recording captured
10. If witnesses have prior interactions with defendants, this may be relevant to establishing pattern or motive - include if appropriate
11. ONLY if VIDEO EVIDENCE TRANSCRIPTS are provided above, incorporate key quotes from the video with proper attribution (e.g., "As captured on video at [timestamp], Defendant [Name] stated: '[quote]'"). Do NOT invent or reference timestamps unless actual transcript text is provided above
12. If WAS RECORDING is True but no VIDEO EVIDENCE TRANSCRIPTS are provided, you may mention that the incident was recorded, but do NOT reference specific timestamps or quote content that was not provided

Write ONLY the Statement of Facts section, starting with the header "STATEMENT OF FACTS".''',
                'available_variables': 'plaintiff_name, incident_date, incident_time, incident_location, city, state, was_recording, what_were_you_doing, detailed_narrative, what_was_said, physical_actions, how_it_ended, defendants, witness_section, video_section',
                'model_name': 'gpt-4o-mini',
                'temperature': 0.3,
                'max_tokens': 2000,
            },
            {
                'prompt_type': 'review_final_document',
                'title': 'Review Final Document Text',
                'description': '''Reviews the ACTUAL GENERATED DOCUMENT TEXT (not raw input data).

Used on the Final Review page (/documents/{id}/final/) to review the complete
legal document text that has been generated and potentially edited by the user.

Analyzes:
- Legal sufficiency for Section 1983 claim
- Factual specificity for motion to dismiss
- Proper case law citations
- Prayer for relief completeness
- Technical formatting issues

Called when: User clicks "AI Review" on the Final Review page.''',
                'system_message': '''You are an expert civil rights attorney reviewing a Section 1983 federal complaint.
Review the document for:
1. Legal sufficiency - Does it state a valid claim under 42 U.S.C. § 1983?
2. Factual specificity - Are the facts specific enough to survive a motion to dismiss?
3. Legal arguments - Are the constitutional violations properly pled with supporting case law?
4. Prayer for relief - Is the relief requested appropriate and comprehensive?
5. Technical issues - Formatting, numbering, signature block completeness

Provide specific, actionable suggestions for improvement. For each issue found, specify:
- The section where the issue is located
- What the problem is
- Suggested fix with example text if applicable

Always respond with valid JSON.''',
                'user_prompt_template': '''Please review this Section 1983 federal complaint:

{document_text}

Format your response as JSON with this structure:
{{
    "overall_assessment": "brief overall assessment",
    "strengths": ["list of strengths"],
    "issues": [
        {{
            "section": "section name (introduction, jurisdiction, parties, facts, causes_of_action, prayer, jury_demand, signature)",
            "severity": "high/medium/low",
            "issue": "description of issue",
            "suggestion": "how to fix it",
            "example_text": "optional example of improved text"
        }}
    ],
    "ready_for_filing": true/false
}}''',
                'available_variables': 'document_text',
                'model_name': 'gpt-4o-mini',
                'temperature': 0.3,
                'max_tokens': 3000,
            },
            {
                'prompt_type': 'wizard_analyze_case',
                'title': 'Wizard Case Analysis',
                'description': '''Runs the final case analysis in the wizard flow.

Analyzes the full case details collected across all 7 wizard steps and produces:
- Constitutional violation analysis with strength ratings
- Case law references (if user opted in)
- Document preview (caption, parties, facts summary, causes of action)
- Relief recommendations

Called when: User clicks "Analyze My Case" on wizard step 7.

NOTE: The case_law section is conditionally included based on use_case_law flag.
The view appends the case_law instructions to the system message when enabled.''',
                'system_message': '''You are an expert civil rights attorney analyzing a potential Section 1983 case. \
Analyze the following case details and provide:
1. 'violations': An array of potential constitutional violations. For each:
   - 'amendment': Which amendment (e.g., 'Fourth Amendment')
   - 'violation_type': Short label (e.g., 'Unreasonable Search')
   - 'description': 2-3 sentence explanation of why this applies
   - 'strength': 'strong', 'moderate', or 'worth_including'
3. 'preview': A document preview with:
   - 'caption': The court caption text
   - 'parties_description': Description of parties
   - 'factual_summary': 2-3 paragraph summary of key facts
   - 'causes_of_action': Array of cause of action titles
   - 'relief_summary': What relief would be sought
4. 'relief_recommendations': Array of recommended relief types:
   - 'type': compensatory_damages, punitive_damages, declaratory_relief, injunctive_relief, attorney_fees, jury_trial
   - 'recommended': true/false
   - 'reason': Why this is or isn't recommended

Respond with valid JSON only.''',
                'user_prompt_template': '{case_summary}',
                'available_variables': 'case_summary',
                'model_name': 'gpt-4o-mini',
                'temperature': 0.3,
                'max_tokens': 3000,
            },
        ]

        created_count = 0
        updated_count = 0

        for prompt_data in prompts:
            prompt, created = AIPrompt.objects.update_or_create(
                prompt_type=prompt_data['prompt_type'],
                defaults=prompt_data
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created: {prompt.title}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'Updated: {prompt.title}'))

        self.stdout.write(self.style.SUCCESS(
            f'\nDone! Created {created_count}, updated {updated_count} prompts.'
        ))
        self.stdout.write(
            '\nYou can now edit these prompts in the admin at: /admin/documents/aiprompt/'
        )
