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
        "incident_date": "MUST be YYYY-MM-DD format (e.g., 2024-03-15). Convert any date mentioned (March 15, last Tuesday, etc.) to this format. Use current year if not specified. null if date cannot be determined.",
        "incident_time": "MUST be HH:MM format in 24-hour time (e.g., 14:30 for 2:30 PM, 09:15 for 9:15 AM). Convert any time mentioned (around 3pm, afternoon, etc.) to best estimate. null if time cannot be determined.",
        "incident_location": "Specific address or location name like '123 Main Street', 'City Hall', 'corner of 5th and Main'. Be as specific as possible.",
        "city": "city name - MUST extract from context. Look for city names mentioned anywhere in the story.",
        "state": "two-letter state code (e.g., CA, NY, TX) - infer from city if possible",
        "location_type": "type of location: 'government building', 'public sidewalk', 'private residence', 'parking lot', etc.",
        "was_recording": "true if recording/filming mentioned, false if explicitly not, null if unknown",
        "recording_device": "device used: 'cell phone', 'camera', 'body camera', etc. if mentioned"
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
    "witnesses": [
        {
            "name": "witness name if known, or descriptive label like 'bystander', 'store employee'",
            "description": "brief description of who they are",
            "what_they_saw": "what they witnessed"
        }
    ],
    "evidence": [
        {
            "evidence_type": "video|audio|photo|document|body_cam|dash_cam|surveillance|other",
            "title": "brief title like 'My cell phone recording' or 'Body camera footage'",
            "description": "what this evidence shows or contains",
            "date_created": "YYYY-MM-DD if mentioned, use incident date if evidence was captured during incident, null otherwise",
            "is_in_possession": "true if user has/captured this evidence, false if it needs to be requested (body cam, dash cam, surveillance)",
            "needs_subpoena": "true if evidence needs to be subpoenaed from police/third party",
            "notes": "additional details like duration, file format, or how to obtain"
        }
    ],
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
