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
- Incident details (date, time, location)
- Officer/defendant information
- Witness information
- Evidence mentioned
- Damages suffered
- Rights that may have been violated

Called when: User submits their story in the "Tell Your Story" step.''',
                'system_message': 'You are a legal document assistant that extracts structured information from personal narratives. Be thorough - extract all information stated and reasonably inferred from context. Include evidence even if it was deleted or seized. Always respond with valid JSON.',
                'user_prompt_template': '''Analyze this personal account of a civil rights incident and extract specific information that can be used to fill out a Section 1983 complaint form.

IMPORTANT RULES:
- Extract ALL information from the text, including details that can be inferred from context
- Example: "city hall in Oklahoma City" means location="City Hall", city="Oklahoma City", state="OK", location_type="government building"
- Example: "I was recording" means was_recording=true
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

USER'S STORY:
{story_text}

Extract information for the following sections. Fill in as many fields as possible based on the story:

{{
    "incident_overview": {{
        "incident_date": "YYYY-MM-DD format or partial date, null if not mentioned",
        "incident_time": "HH:MM AM/PM format ONLY if AM/PM is clear, description like 'afternoon' if general, null if not mentioned or if AM/PM is ambiguous",
        "incident_location": "address or location name like 'City Hall', 'Main Street', etc.",
        "city": "city name - extract from context",
        "state": "two-letter state code - infer from city if possible",
        "location_type": "type of location: 'government building', 'public sidewalk', etc.",
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
            "agency": "department or agency name - use County Sheriff for small towns",
            "agency_inferred": "true if agency was inferred from location",
            "description": "description of this defendant's role/actions"
        }}
    ],
    "witnesses": [
        {{
            "name": "witness name if known, or descriptive label like 'bystander', 'store employee'",
            "description": "brief description of who they are",
            "what_they_saw": "what they witnessed"
        }}
    ],
    "evidence": [
        {{
            "evidence_type": "video|audio|photo|document|body_cam|dash_cam|surveillance|other",
            "title": "brief title like 'My cell phone recording' or 'Body camera footage'",
            "description": "what this evidence shows or contains",
            "date_created": "YYYY-MM-DD if mentioned, use incident date if evidence was captured during incident, null otherwise",
            "is_in_possession": "true if user has/captured this evidence, false if it needs to be requested (body cam, dash cam, surveillance)",
            "needs_subpoena": "true if evidence needs to be subpoenaed from police/third party",
            "notes": "additional details like duration, file format, or how to obtain"
        }}
    ],
    "damages": {{...}},
    "rights_violated": {{...}},
    "questions_to_ask": []
}}

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
                'max_tokens': 3000,
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

Analyzes:
- Cross-document consistency (dates, times, names, locations)
- Missing required information
- Legal document formatting
- Practical fixable issues

Called when: User clicks "AI Review" on the document review page.''',
                'system_message': '''You are a legal document proofreader checking a Section 1983 complaint for errors and inconsistencies.
Your job is to find PRACTICAL issues that can be fixed - not to critique legal strategy.
Focus on: inconsistent facts, missing information, formatting problems, and unclear writing.
Compare information ACROSS all sections to find contradictions.
Always respond with valid JSON.''',
                'user_prompt_template': '''Review this Section 1983 civil rights complaint for errors, inconsistencies, and missing information.

DOCUMENT DATA:
{document_json}

PRIORITY 1 - CROSS-DOCUMENT CONSISTENCY (check these carefully):
- Does the incident TIME match in all sections? (e.g., narrative says "9:30 AM" but damages says "2:30 PM")
- Does the incident DATE match in all sections?
- Does the incident LOCATION match in all sections?
- Are defendant NAMES spelled consistently throughout?
- Are officer BADGE NUMBERS consistent if mentioned multiple times?
- Do the FACTS in the narrative match what's described in damages and rights violated?

PRIORITY 2 - MISSING REQUIRED INFORMATION:
- Is the incident date specified? (not just "on or about")
- Is the incident time specified with AM/PM?
- Is the incident location specific (address or clear description)?
- Are defendants identified with name OR badge number OR physical description?
- Is at least one constitutional right violation selected?
- Is at least one type of damage described?
- Is the plaintiff's county of residence stated?

PRIORITY 3 - FORMATTING AND CLARITY:
- Is the narrative written in third person? (should say "Plaintiff" not "I")
- Are paragraphs properly structured for a legal document?
- Is the chronology of events clear?
- Are there any placeholder texts like "[insert]", "[DATE]", "[TIME]", "TBD", etc.?

DO NOT flag these as issues:
- Legal strategy opinions (e.g., "claims may be weak")
- Suggestions to add more evidence (user may not have more)
- Requests for information that isn't required for filing

Return a JSON object with issues found:
{{
    "overall_assessment": "ready|needs_fixes|has_errors",
    "issues": [
        {{
            "section": "incident_overview|incident_narrative|defendants|damages|rights_violated|relief_sought|plaintiff_info",
            "severity": "error|warning|suggestion",
            "title": "Brief issue title (5-10 words)",
            "description": "Specific explanation - quote the inconsistent text if applicable",
            "suggestion": "Exact fix needed (be specific, not vague)"
        }}
    ],
    "consistency_check": {{
        "times_match": true/false,
        "dates_match": true/false,
        "locations_match": true/false,
        "names_match": true/false
    }},
    "missing_fields": ["List of required fields that are empty or missing"],
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

The field_updates should map to actual database fields that need to be updated. Common fields:
- For narrative: "detailed_narrative"
- For damages: "physical_injury_description", "emotional_distress_description", etc.
- For incident: "incident_location", "incident_date", etc.

If the fix requires updating multiple fields, include all of them.''',
                'available_variables': 'section_type, current_content, issue_title, issue_description, issue_suggestion, document_context',
                'model_name': 'gpt-4o-mini',
                'temperature': 0.2,
                'max_tokens': 2000,
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
