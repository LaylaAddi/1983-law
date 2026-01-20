# Identify Agency for Officer

**Type:** `identify_officer_agency`
**Model:** gpt-4o-mini
**Temperature:** 0.1
**Max Tokens:** 300

## Description

Identifies the likely law enforcement agency for an officer based on location and officer info.

Used when: User clicks "Find Agency & Address" on edit defendant page and the agency field is empty.

Analyzes:
- Officer's title/rank (Deputy → Sheriff, Trooper → Highway Patrol)
- Location (city/state from Incident Overview)
- Officer description

Called when: Looking up agency info for an individual officer defendant.

## System Message

```
You identify law enforcement agencies based on location and officer information. You know that small towns are served by County Sheriff, not local police. Be accurate. Always respond with valid JSON.
```

## User Prompt Template

**Variables:** `{location}`, `{officer_info}`

```
Based on the following information, identify the most likely law enforcement agency this officer works for.

Location: {location}
Officer info: {officer_info}

Consider:
- Title like "Deputy" suggests County Sheriff's Office
- Title like "Trooper" suggests State Highway Patrol
- Title like "Officer" or "Detective" in a city suggests City Police Department
- Small towns often don't have their own police and are served by County Sheriff

Return a JSON object:
{
    "agency_name": "Official agency name (e.g., 'Tampa Police Department', 'Hillsborough County Sheriff's Office')",
    "confidence": "high" or "medium" or "low",
    "reasoning": "Brief explanation of why this agency was identified"
}

If you cannot determine the agency with reasonable confidence, return:
{
    "agency_name": null,
    "confidence": "low",
    "reasoning": "Explanation of why agency could not be determined"
}
```
