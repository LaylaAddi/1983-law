# 1983 Law App - Handoff Document

## What This App Does

A web application to help people create Section 1983 civil rights complaints. Users fill out an interview-style form, and the app helps them build their legal document step by step.

---

## Current State (Latest Session: January 2026)

The app is functional with all core features complete including AI-powered story parsing with auto-fill.

### Core Features Built

1. **User Authentication** (`accounts` app)
   - Email-based login (not username)
   - Registration, login, logout
   - Password recovery
   - User profile with first/middle/last name
   - `is_test_user` flag for testing features
   - `is_staff` flag for admin features

2. **Document Builder** (`documents` app)
   - Create new case documents
   - **Tell Your Story is MANDATORY first step** (blocks section access until done)
   - 10 interview sections (see below)
   - Save progress, come back later
   - Section status tracking with AUTO-COMPLETION

3. **Document Flow**
   ```
   Create Document → Tell Your Story (mandatory) → AI Fills Sections → Review/Edit → Preview → PDF
   ```
   - User MUST tell their story before accessing any section
   - Story is saved to `Document.story_text` field
   - AI extracts data and AUTO-SAVES to all relevant sections
   - Sections auto-complete when data meets criteria (no manual marking needed)

4. **Interview Sections** (in order)
   - Plaintiff Information (with attorney option)
   - Incident Overview (with court lookup)
   - Defendants (add multiple)
   - Incident Narrative
   - Rights Violated (checkboxes for amendments)
   - Witnesses (add multiple)
   - Evidence (add multiple)
   - Damages
   - Prior Complaints
   - Relief Sought (with recommended defaults)

5. **AI Features** (OpenAI GPT-4o-mini) - FULLY INTEGRATED
   - **ChatGPT Rewrite** - Rewrites narrative text in legal format
   - **Rights Violation Analyzer** - Suggests which rights were violated
   - **Tell Your Story** - User writes story, AI extracts and AUTO-SAVES to all sections
   - **Parse Story API** - `/documents/{id}/parse-story/`
   - **Apply Story Fields API** - `/documents/{id}/apply-story-fields/` (NEW)

6. **Admin Features**
   - Delete button on documents list (staff only)
   - CASCADE delete removes all related data

7. **Helper Features**
   - Federal district court lookup by city/state
   - State dropdowns on all address forms
   - Contextual help tooltips
   - "Use Recommended" button for Relief Sought
   - Test user mode with 20 sample stories

---

## Tell Your Story Feature (DETAILED)

This is the main AI feature. Here's how it works:

### User Flow
1. User creates new document
2. Redirected to Tell Your Story page (mandatory)
3. User types their story (or selects test story if `is_test_user`)
4. Click "Analyze My Story"
5. AI extracts data and displays in accordion
6. If missing info, questions appear with input fields
7. User can answer questions or mark N/A
8. Click "Re-analyze with Updates" to refine
9. Click "Continue to Document" to AUTO-SAVE all extracted data
10. Sections are auto-marked complete if data meets criteria
11. User reviews/edits sections as needed

### Key Files
- `templates/documents/tell_your_story.html` - Page template
- `static/js/tell-story.js` - All frontend logic
- `documents/services/openai_service.py` - `parse_story()` method
- `documents/views.py` - `parse_story_view()` and `apply_story_fields()` endpoints

### Auto-Save Behavior
When user clicks "Continue to Document":
- ALL extracted fields are sent to `/apply-story-fields/` endpoint
- Data is saved to appropriate models (IncidentOverview, IncidentNarrative, Defendant, etc.)
- Each section is checked against completion criteria
- Sections meeting criteria are auto-marked "completed"
- User is redirected to document detail page

### Section Auto-Completion Criteria
| Section | Auto-completes when... |
|---------|----------------------|
| Plaintiff Info | Has first name + last name + phone or email |
| Incident Overview | Has date + location + city |
| Incident Narrative | Has detailed narrative (50+ chars) |
| Defendants | At least one defendant with name |
| Witnesses | At least one witness added |
| Evidence | At least one evidence item added |
| Damages | Has any damage description |
| Rights Violated | At least one amendment selected |

### N/A Questions Feature
- User can mark questions as "N/A" (Not Applicable)
- N/A items are stored in sessionStorage
- When re-analyzing, N/A questions are filtered out client-side
- Prevents same questions from reappearing

---

## AI Service Details

### Files
- `documents/services/openai_service.py` - OpenAI API integration
- `documents/test_stories.py` - 20 sample test stories

### OpenAI Service Methods
1. `rewrite_text(text, field_name)` - Rewrites text in legal format
2. `analyze_rights_violations(document_data)` - Suggests rights violated
3. `parse_story(story_text)` - Extracts structured data from user's story

### Parse Story Response Structure
```json
{
  "incident_overview": {
    "incident_date": "2024-08-15",
    "incident_time": "14:30",
    "incident_location": "123 Main St",
    "city": "Austin",
    "state": "TX"
  },
  "incident_narrative": {
    "summary": "...",
    "detailed_narrative": "...",
    "what_were_you_doing": "...",
    "initial_contact": "...",
    "what_was_said": "...",
    "physical_actions": "...",
    "how_it_ended": "..."
  },
  "defendants": [
    {
      "name": "Officer Smith",
      "badge_number": "1234",
      "title": "Sergeant",
      "agency": "Austin PD",
      "description": "..."
    }
  ],
  "witnesses": [...],
  "evidence": [...],
  "damages": {
    "physical_injuries": "...",
    "emotional_distress": "...",
    "financial_losses": "..."
  },
  "rights_violated": {
    "suggested_violations": [
      {
        "right": "freedom_of_speech",
        "amendment": "first",
        "reason": "..."
      }
    ]
  },
  "questions_to_ask": [
    "What is the officer's badge number?",
    "Were there any witnesses?"
  ]
}
```

---

## Tech Stack

- **Backend:** Django 4.2, Python 3.11
- **Database:** PostgreSQL (via Docker)
- **Frontend:** Bootstrap 5, vanilla JavaScript
- **AI:** OpenAI API (GPT-4o-mini)
- **Deployment:** Docker Compose

---

## How to Run

```powershell
# Start containers
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser (first time only)
docker-compose exec web python manage.py createsuperuser

# View app
# http://localhost:8000
```

---

## File Structure (Key Files)

```
1983-law/
├── accounts/           # User auth app
│   ├── models.py       # Custom User model (email login, is_test_user, is_staff)
│   ├── views.py        # Login, register, profile views
│   └── forms.py        # Auth forms
│
├── documents/          # Main document builder app
│   ├── models.py       # Document, Section, PlaintiffInfo, etc.
│   ├── views.py        # Section edit, preview, AJAX endpoints
│   │                   # Key functions: section_edit, apply_story_fields,
│   │                   #                parse_story_view, check_section_complete
│   ├── forms.py        # All section forms + US_STATES dropdown
│   ├── help_content.py # Tooltips and help text for each field
│   ├── test_stories.py # 20 sample stories for testing AI
│   ├── urls.py         # URL routing
│   └── services/
│       ├── court_lookup_service.py
│       └── openai_service.py  # AI integration (parse_story, rewrite_text, etc.)
│
├── templates/
│   ├── base.html
│   ├── accounts/
│   └── documents/
│       ├── document_list.html      # Has admin delete button
│       ├── document_detail.html    # Blocked until story told
│       ├── document_preview.html   # Full document preview
│       ├── section_edit.html
│       └── tell_your_story.html    # AI story parsing page
│
├── static/
│   ├── js/
│   │   ├── tell-story.js           # Tell Your Story logic (handleApplyAll, etc.)
│   │   ├── rewrite.js
│   │   └── rights-analyze.js
│   └── css/
│       └── tell-story.css
│
└── docker-compose.yml
```

---

## Database Models (documents/models.py)

| Model | Purpose | Key Fields |
|-------|---------|------------|
| Document | Main case container | title, user, story_text, story_told_at |
| DocumentSection | Links document to section + status | section_type, status, order |
| PlaintiffInfo | Plaintiff details | first_name, last_name, phone, email, attorney fields |
| IncidentOverview | When/where | incident_date, incident_location, city, state |
| Defendant | Officers/agencies (multiple) | name, badge_number, title_rank, agency_name |
| IncidentNarrative | What happened | detailed_narrative, what_were_you_doing, what_was_said |
| RightsViolated | Amendments violated | first_amendment, fourth_amendment, etc. + details |
| Witness | People who saw (multiple) | name, what_they_witnessed |
| Evidence | Documents/videos (multiple) | evidence_type, description |
| Damages | Harm suffered | physical_injury_description, emotional_distress_description |
| PriorComplaints | Previous filings | filed_complaint, complaint_details |
| ReliefSought | What plaintiff wants | compensatory_damages, punitive_damages, etc. |

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/documents/{id}/parse-story/` | POST | Send story text, get AI-extracted data |
| `/documents/{id}/apply-story-fields/` | POST | Save extracted fields to database |
| `/documents/{id}/section/{type}/save/` | POST | AJAX save for section forms |
| `/documents/{id}/section/{type}/delete-item/{item_id}/` | POST | Delete defendant/witness/evidence |

---

## What's NOT Built Yet

- PDF generation of the complaint
- E-filing integration
- Payment/subscription (DO NOT BUILD - user doesn't want Stripe)
- Video extraction (DO NOT BUILD - user didn't ask for this)

---

## Recent Changes (This Session)

1. **Simplified Tell Your Story Flow**
   - Removed field selection checkboxes
   - Auto-apply ALL extracted fields
   - Cleaner UI - just review and continue

2. **Auto-Complete Sections**
   - Sections auto-mark as "completed" when AI data meets criteria
   - No manual status clicking needed
   - `check_section_complete()` function handles logic

3. **N/A Questions Persistence**
   - N/A items stored in sessionStorage
   - Filtered out client-side on re-analyze
   - Won't reappear even if GPT ignores prompt

4. **Preview Page Fixes**
   - Fixed field name mismatches (template vs model)
   - Defendants: title_rank, agency_name, description
   - Narrative: detailed_narrative, what_were_you_doing, what_was_said
   - Damages: physical_injury_description, emotional_distress_description

5. **Admin Delete Button**
   - Staff users see delete button on documents list
   - CASCADE delete removes all related data

---

## Instructions for Next Claude Session

**IMPORTANT:**
- Do NOT start building features automatically
- Ask what the user wants to work on
- Go step by step - explain what you plan to do BEFORE doing it
- Get approval before writing code
- Update this HANDOFF.md after completing features

**To continue work:**
1. User will tell you what feature they want
2. You explain the plan
3. User approves
4. You implement
5. User tests
6. Update HANDOFF.md
7. Repeat

---

## Git Workflow

### For User: Merge feature branch to master
```bash
git checkout master
git pull origin master
git merge claude/feature-branch-name
git push origin master
```

### For Next Claude Session: Create new branch
```bash
git checkout master
git pull origin master
git checkout -b claude/new-feature-XYZ
```

Branch naming: `claude/<feature-description>-<random-id>`

---

## Quick Commands

```powershell
# Start app
docker-compose up -d

# View logs
docker-compose logs -f web

# Run migrations
docker-compose exec web python manage.py migrate

# Django shell
docker-compose exec web python manage.py shell

# Stop app
docker-compose down

# Make user a test user (in Django shell)
from accounts.models import User
u = User.objects.get(email='your@email.com')
u.is_test_user = True
u.save()

# Make user admin (in Django shell)
u.is_staff = True
u.save()
```

---

## Environment Variables Needed

```
OPENAI_API_KEY=sk-...  # Required for AI features
```

---

## Known Issues / Future Improvements

1. **Mobile App** - Tell Your Story will be key feature for mobile
2. **Voice Input** - Add speech-to-text (Whisper) later
3. **PDF Generation** - Not yet implemented
4. **Preview page** - May need more field mappings if new fields added
