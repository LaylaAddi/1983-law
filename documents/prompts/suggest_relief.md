# Suggest Legal Relief

**Type:** `suggest_relief`
**Model:** gpt-4o-mini
**Temperature:** 0.2
**Max Tokens:** 1500

## Description

Recommends appropriate legal relief based on the case details.

Analyzes rights violated, damages suffered, and evidence to suggest:
- Compensatory damages
- Punitive damages
- Declaratory relief
- Injunctive relief
- Attorney fees
- Jury trial recommendation

Called when: User clicks "Suggest Relief" in the Relief Sought section.

## System Message

```
You are a legal assistant helping prepare Section 1983 civil rights complaints. Provide thoughtful relief recommendations based on the specific facts of each case. Always respond with valid JSON.
```

## User Prompt Template

**Variables:** `{context}`

```
Based on this Section 1983 civil rights case information, recommend appropriate relief:

{context}

Analyze and provide recommendations for each type of relief. Return a JSON object:

{
    "compensatory_damages": {
        "recommended": true/false,
        "reason": "Brief explanation of why compensatory damages are appropriate based on the specific damages suffered"
    },
    "punitive_damages": {
        "recommended": true/false,
        "reason": "Brief explanation - recommend if conduct was willful, malicious, or showed reckless disregard for rights"
    },
    "declaratory_relief": {
        "recommended": true/false,
        "reason": "Brief explanation - recommend if a court declaration that rights were violated would be valuable",
        "suggested_declaration": "What should be declared"
    },
    "injunctive_relief": {
        "recommended": true/false,
        "reason": "Brief explanation - recommend if policy changes or training are needed",
        "suggested_injunction": "What changes should be ordered"
    },
    "attorney_fees": {
        "recommended": true,
        "reason": "42 U.S.C. § 1988 allows recovery of attorney fees in civil rights cases"
    },
    "jury_trial": {
        "recommended": true/false,
        "reason": "Brief explanation"
    }
}

Be specific to THIS case.
```
