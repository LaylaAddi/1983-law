# Parse User Story

**Type:** `parse_story`
**Model:** gpt-4o-mini
**Temperature:** 0.1
**Max Tokens:** 3000

## Description

Analyzes the user's story about their civil rights incident and extracts structured data.

This is the MAIN prompt that processes "Tell Your Story" input. It extracts:
- Incident details (date, time, location)
- Officer/defendant information
- Witness information
- Evidence mentioned
- Damages suffered
- Rights that may have been violated

Called when: User submits their story in the "Tell Your Story" step.

## System Message

```
You are a legal document assistant that extracts structured information from personal narratives. Be thorough - extract all information stated and reasonably inferred from context. Include evidence even if it was deleted or seized. Always respond with valid JSON.
```

## User Prompt Template

**Variables:** `{story_text}`

```
Analyze this personal account of a civil rights incident and extract specific information that can be used to fill out a Section 1983 complaint form.

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

{
    "incident_overview": {
        "incident_date": "YYYY-MM-DD format or partial date, null if not mentioned",
        "incident_time": "HH:MM format or description like 'afternoon', null if not mentioned",
        "incident_location": "address or location name like 'City Hall', 'Main Street', etc.",
        "city": "city name - extract from context",
        "state": "two-letter state code - infer from city if possible",
        "location_type": "type of location: 'government building', 'public sidewalk', etc.",
        "was_recording": "true if recording/filming mentioned, false if explicitly not, null if unknown",
        "recording_device": "device used: 'cell phone', 'camera', etc. if mentioned"
    },
    "incident_narrative": {
        "summary": "2-3 sentence summary of what happened, written in third person",
        "detailed_narrative": "full chronological account, written in third person",
        "what_were_you_doing": "what the plaintiff was doing before/during incident",
        "initial_contact": "how the encounter with officials began",
        "what_was_said": "dialogue or statements made by parties",
        "physical_actions": "any physical actions taken by anyone",
        "how_it_ended": "how the encounter concluded"
    },
    "defendants": [
        {
            "name": "officer/official name if mentioned, null otherwise",
            "badge_number": "badge number if mentioned, null otherwise",
            "title": "title like 'Officer', 'Sergeant', etc. if mentioned",
            "agency": "department or agency name - use County Sheriff for small towns",
            "agency_inferred": "true if agency was inferred from location",
            "description": "description of this defendant's role/actions"
        }
    ],
    "witnesses": [...],
    "evidence": [...],
    "damages": {...},
    "rights_violated": {...},
    "questions_to_ask": []
}

QUESTIONS TO ASK - Generate follow-up questions for CRITICAL missing information:

1. ALWAYS ask for date if not explicitly stated (e.g., "What was the exact date of this incident?")
2. ALWAYS ask for time if not explicitly stated (e.g., "What time did this incident occur?")
3. Then add 2-6 other relevant questions for missing details

Date and time questions MUST come first if those are missing.

Respond with ONLY the JSON object.
```
