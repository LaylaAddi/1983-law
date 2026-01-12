# 1983 Law App - Handoff Document

## What This App Does

A web application to help people create Section 1983 civil rights complaints. Users fill out an interview-style form, and the app helps them build their legal document step by step.

---

## Current State (Latest Commit: 58c1764)

The app is functional with the following features complete:

### Core Features Built

1. **User Authentication** (`accounts` app)
   - Email-based login (not username)
   - Registration, login, logout
   - Password recovery
   - User profile with full contact info (name, address, phone, mailing address)
   - **Profile completion required before creating documents**
   - `is_test_user` flag for testing features

2. **Profile Completion Flow** (NEW)
   - After registration → redirect to profile completion page
   - User must provide: name, address, phone
   - Optional: mailing address if different
   - Warning displayed: "This information will appear on your legal documents"
   - Document creation blocked until profile is complete
   - Profile data auto-populates Plaintiff Information section

3. **Document Builder** (`documents` app)
   - Create new case documents (requires complete profile)
   - **Tell Your Story is MANDATORY first step** (blocks section access until done)
   - 10 interview sections (see below)
   - Save progress, come back later
   - Section status tracking (not started, in progress, completed, needs work, N/A)

4. **Document Flow**
   ```
   Complete Profile → Create Document → Tell Your Story (mandatory) → Fill Sections → Preview → PDF
   ```
   - User MUST complete profile before creating any document
   - User MUST tell their story before accessing any section
   - Story is saved to `Document.story_text` field
   - Sections are blocked until `document.has_story()` returns True

5. **Interview Sections** (in order)
   - Plaintiff Information (read-only from profile, attorney info editable)
   - Incident Overview (auto-filled from story, with court lookup)
   - Defendants (add multiple)
   - Incident Narrative
   - Rights Violated (checkboxes for amendments)
   - Witnesses (add multiple)
   - Evidence (add multiple)
   - Damages
   - Prior Complaints
   - Relief Sought (with recommended defaults)

6. **AI Features** (OpenAI GPT-4o-mini)
   - **ChatGPT Rewrite** - Rewrites narrative text in legal format
   - **Rights Violation Analyzer** - Suggests which rights were violated based on narrative
   - **Tell Your Story** - User writes story, AI extracts data for all sections
   - **Parse Story API** - Backend endpoint for AI parsing (`/documents/{id}/parse-story/`)
   - **Auto-apply incident_overview** - Extracted fields automatically saved to database

7. **Helper Features**
   - Federal district court lookup by city/state (auto-lookup on story parse)
   - State dropdowns on all address forms
   - Contextual help tooltips
   - "Use Recommended" button for Relief Sought
   - Test user mode for demo data

---

## Auto-Apply Features (NEW)

### Plaintiff Information
- **Source:** User profile
- **When:** On document creation
- **Fields:** name, address, phone, email
- **User action:** Only needs to select attorney info (if not pro se)
- **Section status:** Auto-marked as complete

### Incident Overview
- **Source:** AI story parsing
- **When:** When user submits their story
- **Fields auto-applied:**
  - `incident_date`
  - `incident_time`
  - `incident_location`
  - `city`
  - `state`
  - `location_type` (inferred from story)
  - `was_recording` (if mentioned)
  - `recording_device` (if mentioned)
  - `federal_district_court` (auto-lookup from city/state)
- **Section status:** Auto-marked as in_progress or completed

---

## User Model Fields (accounts/models.py)

| Field | Purpose |
|-------|---------|
| email | Primary identifier (login) |
| first_name, middle_name, last_name | Legal name |
| street_address, city, state, zip_code | Primary address |
| phone | Contact phone |
| use_different_mailing_address | Boolean flag |
| mailing_street_address, mailing_city, mailing_state, mailing_zip_code | Mailing address (if different) |
| is_test_user | Enable test features |
| has_complete_profile() | Method to check if profile is complete |

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

### Story Parsing Extracts
- incident_overview: date, time, location, city, state, location_type, was_recording, recording_device
- incident_narrative: summary, detailed_narrative, what_were_you_doing, initial_contact, what_was_said, physical_actions, how_it_ended
- defendants: name, badge_number, title, agency, description
- witnesses: name, description, what_they_saw
- evidence: type, description
- damages: physical_injuries, emotional_distress, financial_losses, other_damages
- rights_violated: suggested_violations with amendment and reason
- questions_to_ask: follow-up questions for missing info

### Test Stories Feature
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

# Run migrations (IMPORTANT after pulling new code)
docker-compose exec web python manage.py makemigrations accounts
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
│   ├── models.py       # Custom User model (email login, address, phone, is_test_user)
│   ├── views.py        # Login, register, profile, profile_complete views
│   └── forms.py        # Auth forms, ProfileEditForm, ProfileCompleteForm
│
├── documents/          # Main document builder app
│   ├── models.py       # Document, Section, PlaintiffInfo, etc.
│   ├── views.py        # Section edit, preview, AJAX endpoints, auto-apply logic
│   ├── forms.py        # All section forms + PlaintiffAttorneyForm + US_STATES dropdown
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
│   │   ├── profile.html
│   │   ├── profile_edit.html
│   │   └── profile_complete.html  # NEW - profile completion page
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
| PlaintiffInfo | Plaintiff name, address, attorney info (from profile) |
| IncidentOverview | Date, location, court lookup (auto-filled from story) |
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
- Case law citations (AI could assist - needs research)
- Payment/subscription (DO NOT BUILD - user doesn't want Stripe)
- Video extraction (DO NOT BUILD - user didn't ask for this)

---

## Future Plans

- **Case Law Citations** - AI-assisted relevant case law for each rights violation
- **Mobile App Version** - Tell Your Story will be key feature
- **Voice Input** - Add speech-to-text (Whisper) later

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
docker-compose exec web python manage.py makemigrations
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
