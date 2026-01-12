# 1983 Law App - Handoff Document

## What This App Does

A web application to help people create Section 1983 civil rights complaints. Users fill out an interview-style form, and the app helps them build their legal document step by step.

---

## Current State (Latest Commit: 4b140b8)

The app is functional with the following features complete:

### Core Features Built

1. **User Authentication** (`accounts` app)
   - Email-based login (not username)
   - Registration, login, logout
   - Password recovery
   - User profile with first/middle/last name
   - `is_test_user` flag for testing features

2. **Document Builder** (`documents` app)
   - Create new case documents
   - **Tell Your Story is MANDATORY first step** (blocks section access until done)
   - 10 interview sections (see below)
   - Save progress, come back later
   - Section status tracking (not started, in progress, completed, needs work, N/A)

3. **Document Flow**
   ```
   Create Document → Tell Your Story (mandatory) → Fill Sections → Preview → PDF
   ```
   - User MUST tell their story before accessing any section
   - Story is saved to `Document.story_text` field
   - Sections are blocked until `document.has_story()` returns True

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

5. **AI Features** (OpenAI GPT-4o-mini)
   - **ChatGPT Rewrite** - Rewrites narrative text in legal format
   - **Rights Violation Analyzer** - Suggests which rights were violated based on narrative
   - **Tell Your Story** - User writes story, AI extracts data for all sections
   - **Parse Story API** - Backend endpoint for AI parsing (`/documents/{id}/parse-story/`)

6. **Helper Features**
   - Federal district court lookup by city/state
   - State dropdowns on all address forms
   - Contextual help tooltips
   - "Use Recommended" button for Relief Sought
   - Test user mode for demo data

---

## AI Features Detail

### Files
- `documents/services/openai_service.py` - OpenAI API integration
- `documents/test_stories.py` - 20 sample test stories for testing AI parsing
- `static/js/tell-story.js` - Tell Your Story frontend
- `static/js/rewrite.js` - Rewrite feature frontend
- `static/js/rights-analyze.js` - Rights analysis frontend
- `static/css/tell-story.css` - Tell Your Story styles

### OpenAI Service Methods
1. `rewrite_text(text, field_name)` - Rewrites text in legal format
2. `analyze_rights_violations(document_data)` - Suggests rights violated
3. `parse_story(story_text)` - Extracts structured data from user's story

### Test Stories Feature (NEW)
- 20 sample stories with mixed violations for testing
- Only visible to users with `is_test_user=True`
- Dropdown on Tell Your Story page to select and auto-fill textarea
- Stories cover: 1st, 4th, 5th, 14th amendment violations combined

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
│   ├── models.py       # Custom User model (email login, is_test_user)
│   ├── views.py        # Login, register, profile views
│   └── forms.py        # Auth forms
│
├── documents/          # Main document builder app
│   ├── models.py       # Document, Section, PlaintiffInfo, etc.
│   ├── views.py        # Section edit, preview, AJAX endpoints
│   ├── forms.py        # All section forms + US_STATES dropdown
│   ├── help_content.py # Tooltips and help text for each field
│   ├── test_stories.py # 20 sample stories for testing AI
│   ├── urls.py         # URL routing
│   └── services/
│       ├── court_lookup_service.py
│       └── openai_service.py  # AI integration
│
├── templates/
│   ├── base.html
│   ├── accounts/
│   └── documents/
│       ├── document_list.html
│       ├── document_detail.html
│       ├── document_preview.html
│       ├── section_edit.html
│       └── tell_your_story.html  # AI story parsing page
│
├── static/
│   ├── js/
│   │   ├── tell-story.js
│   │   ├── rewrite.js
│   │   └── rights-analyze.js
│   └── css/
│       └── tell-story.css
│
└── docker-compose.yml
```

---

## Database Models (documents/models.py)

| Model | Purpose |
|-------|---------|
| Document | The main case, has title and owner |
| DocumentSection | Links document to section type + status |
| PlaintiffInfo | Plaintiff name, address, attorney info |
| IncidentOverview | Date, location, court lookup |
| Defendant | Individual officers or agencies (multiple per doc) |
| IncidentNarrative | Detailed story of what happened |
| RightsViolated | Which amendments were violated |
| Witness | People who saw the incident (multiple) |
| Evidence | Videos, documents, etc. (multiple) |
| Damages | Physical, emotional, financial harm |
| PriorComplaints | Previous complaints filed |
| ReliefSought | What the plaintiff wants (money, declaration, etc.) |

---

## What's NOT Built Yet

- PDF generation of the complaint
- E-filing integration
- Auto-save parsed story data to database (currently shows suggestions only)
- Payment/subscription (DO NOT BUILD - user doesn't want Stripe)
- Video extraction (DO NOT BUILD - user didn't ask for this)

---

## Future Plans

- **Mobile App Version** - Tell Your Story will be key feature
- **Voice Input** - Add speech-to-text (Whisper) later
- **Auto-fill from AI** - Make "Apply Selected" actually save to database

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
```

---

## Environment Variables Needed

```
OPENAI_API_KEY=sk-...  # Required for AI features
```
