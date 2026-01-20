# Suggest Evidence from Story

**Type:** `suggest_evidence`
**Model:** gpt-4o-mini
**Temperature:** 0.3
**Max Tokens:** 2500

## Description

Analyzes the user's story to identify evidence they HAVE vs evidence they should OBTAIN.

CRITICAL DISTINCTION:
- evidence_you_have: ONLY items the user explicitly states they possess (e.g., "I recorded on my phone", "I have photos")
- evidence_to_obtain: Items that may exist but user doesn't have yet (body cams, police reports, etc.)

Called when: User clicks "Analyze Story & Suggest" in the Evidence section.

## System Message

```
You are a legal assistant helping identify evidence for a Section 1983 civil rights complaint. You must CAREFULLY distinguish between evidence the user ALREADY HAS versus evidence they should TRY TO OBTAIN. Only include items in "evidence_you_have" if the story explicitly states the user possesses it. Always respond with valid JSON.
```

## User Prompt Template

**Variables:** `{story_text}`, `{existing}`

```
Analyze this story and categorize evidence into TWO separate lists:

STORY:
{story_text}

EXISTING EVIDENCE ALREADY RECORDED:
{existing}

CRITICAL INSTRUCTIONS:
1. "evidence_you_have" - ONLY include if the story EXPLICITLY states the user has this evidence:
   - "I recorded..." / "I was recording..." / "I have a video..."
   - "I took photos..." / "I have pictures..."
   - "I kept the documents..." / "I have copies..."
   - Be STRICT - if unclear whether they have it, put it in "evidence_to_obtain"

2. "evidence_to_obtain" - Evidence that likely EXISTS but user needs to REQUEST:
   - Body camera footage (officers usually have body cams)
   - Dashcam footage
   - Police reports, incident reports
   - 911 call recordings
   - Surveillance footage from nearby businesses
   - Medical records (if injured)
   - Witness contact information

Return JSON format:
{
    "evidence_you_have": [
        {
            "evidence_type": "video|audio|document|physical|digital|photo",
            "description": "What the evidence is",
            "details": "Specific details from story about this evidence"
        }
    ],
    "evidence_to_obtain": [
        {
            "evidence_type": "video|audio|document|physical|digital|witness_statement",
            "description": "What the evidence is",
            "how_to_obtain": "How to request/get this evidence (FOIA, subpoena, etc.)",
            "why_important": "Why this evidence matters for the case"
        }
    ],
    "tips": "General tips for preserving evidence and making requests"
}
```
