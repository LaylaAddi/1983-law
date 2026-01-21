# Lookup Federal District Court

**Prompt Type:** `lookup_federal_court`

**Purpose:** Uses web search to find the correct federal district court for a given city and state when the static lookup database doesn't have the city listed.

**Called When:** Static court lookup fails to find the city in its database (small towns, rural areas, unincorporated communities).

**Variables Available:**
- `{city}` - The city name
- `{state}` - The state (two-letter code or full name)

---

## System Message

```
You are a legal research assistant that identifies federal district court jurisdictions. Use web search to find accurate, current information. Always respond with valid JSON.
```

---

## User Prompt Template

```
What federal district court has jurisdiction over {city}, {state}?

Search for the correct United States District Court that covers this location. Federal district courts have names like:
- "United States District Court for the Northern District of New York"
- "United States District Court for the Southern District of California"
- "United States District Court for the District of Alaska" (single-district states)

Return a JSON object:
{
    "court_name": "Full official court name",
    "district": "The district name (e.g., 'Northern', 'Southern', 'Eastern', 'Western', or 'District' for single-district states)",
    "confidence": "high" or "medium",
    "source": "Brief note about how this was determined"
}

Be accurate - this is for legal filings.
```

---

## Expected Response Format

```json
{
    "court_name": "United States District Court for the Northern District of New York",
    "district": "Northern",
    "confidence": "high",
    "source": "Russell, NY is in St. Lawrence County, which is within the Northern District of New York"
}
```

---

## Model Settings

- **Model:** gpt-4o-mini
- **Temperature:** 0.1 (low for accuracy)
- **Max Tokens:** 500
- **Web Search:** Enabled (required for accurate results)

---

## Notes

- This prompt is used as a fallback when the static court lookup database doesn't contain the city
- Web search should be enabled for this prompt to work accurately
- The response is used to auto-fill the court name in the Incident Overview section
- Results should be cached to avoid repeated lookups for the same location
