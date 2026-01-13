# 1983 Law App - Handoff Document

## What This App Does

A web application to help people create Section 1983 civil rights complaints. Users fill out an interview-style form, and the app helps them build their legal document step by step.

---

## Current State (Latest Commit: f9dc4b2)

The app is functional with the following features complete:

### Core Features Built

1. **User Authentication** (`accounts` app)
   - Email-based login (not username)
   - Registration, login, logout
   - Password recovery
   - User profile with full contact info (name, address, phone, mailing address)
   - **Profile completion required before creating documents**
   - `is_test_user` flag for testing features

2. **Profile Completion Flow**
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
   - **Case Law Suggestions** - AI selects relevant case law from curated database
   - **Legal Document Generator** - AI writes court-ready federal complaint with case law integrated

7. **Helper Features**
   - Federal district court lookup by city/state (auto-lookup on story parse)
   - State dropdowns on all address forms
   - Contextual help tooltips
   - "Use Recommended" button for Relief Sought
   - Test user mode for demo data
   - **"May not apply" indicator** for sections based on story analysis
   - **Preview Document button** in section edit sidebar

---

## Auto-Apply Features

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
- `documents/services/openai_service.py` - OpenAI API integration (includes `suggest_case_law` method)
- `documents/services/document_generator.py` - Legal document generation
- `documents/test_stories.py` - 20 sample test stories for testing AI parsing
- `documents/management/commands/load_case_law.py` - Management command to populate case law database
- `templates/documents/case_law_list.html` - Case law management UI
- `static/js/tell-story.js` - Tell Your Story frontend
- `static/js/rewrite.js` - Rewrite feature frontend
- `static/js/rights-analyze.js` - Rights analysis frontend
- `static/css/tell-story.css` - Tell Your Story styles

### OpenAI Service Methods
1. `rewrite_text(text, field_name)` - Rewrites text in legal format
2. `analyze_rights_violations(document_data)` - Suggests rights violated
3. `parse_story(story_text)` - Extracts structured data from user's story
4. `suggest_case_law(document_data)` - Suggests relevant case law citations

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
docker-compose exec web python manage.py makemigrations documents
docker-compose exec web python manage.py migrate

# Load case law database (required for case law feature)
docker-compose exec web python manage.py load_case_law

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
│   ├── models.py       # Document, Section, PlaintiffInfo, CaseLaw, etc.
│   ├── views.py        # Section edit, preview, AJAX endpoints, auto-apply logic
│   ├── forms.py        # All section forms + PlaintiffAttorneyForm + US_STATES dropdown
│   ├── help_content.py # Tooltips and help text for each field
│   ├── test_stories.py # 20 sample stories for testing AI
│   ├── urls.py         # URL routing
│   ├── management/
│   │   └── commands/
│   │       └── load_case_law.py  # Populate case law database
│   └── services/
│       ├── court_lookup_service.py
│       ├── openai_service.py      # AI integration
│       └── document_generator.py  # Legal document generation
│
├── templates/
│   ├── base.html
│   ├── accounts/
│   │   ├── profile.html
│   │   ├── profile_edit.html
│   │   └── profile_complete.html
│   └── documents/
│       ├── document_list.html
│       ├── document_detail.html
│       ├── document_preview.html      # Legal document display
│       ├── section_edit.html          # With preview button & may-not-apply indicator
│       ├── tell_your_story.html
│       ├── case_law_list.html         # Case law management
│       └── partials/
│           └── relief_sought_form.html # Redesigned relief form
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
| **CaseLaw** | Curated database of landmark Section 1983 cases |
| **DocumentCaseLaw** | Links case law citations to documents with explanations |

---

## Case Law Citations Feature

### Overview
AI-assisted case law suggestion feature that strengthens Section 1983 complaints with relevant legal precedents.

### How It Works
1. User tells their story or fills out incident narrative
2. User clicks "Get AI Suggestions" on the Case Law page
3. AI analyzes the facts and selects relevant cases from our curated database
4. User reviews suggestions and accepts/edits/rejects each one
5. Accepted citations appear in the document preview

### Database
- **CaseLaw model** - Curated database of ~40 landmark Section 1983 cases
- **DocumentCaseLaw model** - Links cases to documents with AI explanations
- Cases organized by amendment and right category
- All citations are verified and accurate

### Key Cases Included
- **Graham v. Connor** (excessive force standard)
- **Glik v. Cunniffe** (right to record police)
- **Terry v. Ohio** (stop and frisk)
- **Monroe v. Pape** (Section 1983 foundation)
- **Monell v. Dept. of Social Services** (municipal liability)
- And many more...

### URLs
- `/documents/{id}/case-law/` - View and manage citations
- `/documents/{id}/suggest-case-law/` - Get AI suggestions (POST)
- `/documents/{id}/accept-case-law/` - Accept a suggestion (POST)
- `/documents/{id}/case-law/{citation_id}/update/` - Edit explanation (POST)
- `/documents/{id}/case-law/{citation_id}/remove/` - Remove citation (POST)

### Setup Commands (MUST RUN)
```powershell
# Run migrations for new models
docker-compose exec web python manage.py makemigrations documents
docker-compose exec web python manage.py migrate

# Load case law database
docker-compose exec web python manage.py load_case_law
```

---

## Legal Document Generator

### Overview
AI-powered document generation that creates a professionally written Section 1983 federal complaint with case law properly integrated into legal arguments.

### How It Works
1. User fills out document sections (plaintiff info, narrative, rights violated, etc.)
2. User accepts case law citations
3. User visits Preview page (`/documents/{id}/preview/`)
4. System generates complete legal complaint with:
   - Proper caption (court name, parties, case number placeholder)
   - Jurisdiction and venue statement
   - Parties section identifying all plaintiffs and defendants
   - Statement of facts written in professional legal prose
   - **Causes of action with case law woven into legal arguments** (like a lawyer would write)
   - Prayer for relief
   - Jury demand (if requested)
   - Signature block (pro se or attorney)

### Key Features
- **Case Law Integration** - Cases cited inline where they belong, not just listed at the end
- **Professional Legal Prose** - AI writes each section in formal legal style
- **Third Person** - "Plaintiff" not "I"
- **Numbered Paragraphs** - Following federal court conventions
- **Print-Ready** - Document formatted for court filing

### Files
- `documents/services/document_generator.py` - Main generation service
- `documents/views.py` - `document_preview` view and `_collect_document_data` helper
- `templates/documents/document_preview.html` - Legal document display template

### Requirements for Generation
Document must have:
- Plaintiff name (first and last)
- Incident narrative (from story or detailed_narrative)
- At least one constitutional right selected as violated

### URL
- `/documents/{id}/preview/` - View generated legal document
- `/documents/{id}/preview/?generate=false` - View raw data only

---

## Relief Sought Section (Redesigned)

### Smart Defaults
- Pre-selects common relief types
- "Use Recommended" button for one-click defaults
- Calculated suggested amounts based on incident severity

### Form Fields
- Compensatory damages (checkbox + amount)
- Punitive damages (checkbox + amount)
- Declaratory relief
- Injunctive relief
- Attorney's fees
- Jury trial demand
- Other relief (text field)

---

## Section Sidebar Features

### "May Not Apply" Indicator
- Based on AI analysis of story
- Grayed-out badge shows sections that likely don't apply
- Example: "Witnesses" shows "may not apply" if no witnesses mentioned
- User can still access and fill out these sections

### Preview Document Button
- Quick link to document preview from any section
- Opens in new tab

---

## What's NOT Built Yet

- PDF generation of the complaint (HTML output is court-ready for printing)
- E-filing integration
- Payment/subscription (DO NOT BUILD - user doesn't want Stripe)
- Video extraction (DO NOT BUILD - user didn't ask for this)

---

## Future Plans

- **Mobile App Version** - Tell Your Story will be key feature
- **Voice Input** - Add speech-to-text (Whisper) later
- **More Case Law** - Expand database with circuit-specific cases

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

# Load case law (required once)
docker-compose exec web python manage.py load_case_law

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
