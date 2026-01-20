# Suggest Evidence from Story

**Type:** `suggest_evidence`
**Model:** gpt-4o-mini
**Temperature:** 0.3
**Max Tokens:** 2500

## Description

Analyzes the user's story to identify evidence they HAVE vs evidence they should OBTAIN.

CRITICAL DISTINCTION:
- evidence_you_have: Items the user indicates they possess or created (recordings, photos, documents)
- evidence_to_obtain: Items that may exist but user doesn't have yet (body cams, police reports, etc.)

Called when: User clicks "Analyze Story & Suggest" in the Evidence section.

## System Message

```
You are a legal assistant helping identify evidence for a Section 1983 civil rights complaint. Distinguish between evidence the user HAS versus evidence they should OBTAIN. If the user mentions recording, filming, photographing, or documenting something, assume they HAVE that evidence. Always respond with valid JSON.
```

## User Prompt Template

**Variables:** `{story_text}`, `{existing}`

```
Analyze this story and categorize evidence into TWO separate lists:

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
