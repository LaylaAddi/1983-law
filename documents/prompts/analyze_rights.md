# Analyze Constitutional Rights Violations

**Type:** `analyze_rights`
**Model:** gpt-4o-mini
**Temperature:** 0.3
**Max Tokens:** 2000

## Description

Analyzes incident details to identify which constitutional rights were violated.

Reviews the incident narrative and suggests applicable:
- First Amendment violations (speech, press, assembly, petition)
- Fourth Amendment violations (search, seizure, arrest, excessive force)
- Fifth Amendment violations (self-incrimination, due process)
- Fourteenth Amendment violations (due process, equal protection)

Called when: User clicks "Analyze Rights" in the Rights Violated section.

## System Message

```
You are a civil rights legal analyst helping identify constitutional violations in Section 1983 cases. Be accurate, thorough, and write explanations that are conversational yet professional. Always respond with valid JSON.
```

## User Prompt Template

**Variables:** `{context}`

```
Analyze this incident and identify which constitutional rights were likely violated. This is for a Section 1983 civil rights complaint against police officers or government officials.

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
{
    "violations": [
        {
            "right": "first_amendment_speech",
            "amendment": "first",
            "explanation": "Your explanation here..."
        }
    ],
    "summary": "A brief 1-2 sentence overall summary of the civil rights issues in this case."
}

Only include rights that are clearly supported by the facts.
```
