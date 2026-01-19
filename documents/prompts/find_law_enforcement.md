# Find Law Enforcement Agency

**Type:** `find_law_enforcement`
**Model:** gpt-4o-mini
**Temperature:** 0.1
**Max Tokens:** 1500

## Description

Identifies the correct law enforcement agency for a given location.

CRITICAL for small towns: Many small towns, villages, and unincorporated communities do NOT have their own police department. This prompt helps identify whether to use County Sheriff instead.

Called when: User enters a city/state, or when verifying AI-suggested agencies.

## System Message

```
You are a legal research assistant with knowledge of US law enforcement jurisdictions. You know that small towns and unincorporated areas are served by county sheriffs, not local police. Be accurate about which locations have their own police departments.
```

## User Prompt Template

**Variables:** `{city}`, `{state}`

```
Determine the law enforcement agencies that have jurisdiction in {city}, {state}.

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
{
    "location_type": "major_city|small_town|village|unincorporated|cdp",
    "has_local_police": true only if this is a city large enough to have its own police department,
    "county_name": "Name of the county (e.g., 'Attala' not 'Attala County')",
    "agencies": [
        {
            "name": "Full official name (e.g., 'Attala County Sheriff's Office')",
            "type": "sheriff|police|state_patrol",
            "is_primary": true if this is the most likely agency with jurisdiction,
            "confidence": "high|medium|low",
            "notes": "Brief explanation"
        }
    ],
    "verification_warning": "User-facing warning about verifying the agency"
}

Be conservative: If uncertain whether a place has local police, assume it does NOT and suggest County Sheriff as primary.
```
