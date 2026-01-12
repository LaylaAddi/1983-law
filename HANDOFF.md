# 1983 Law App - Handoff Document

## What This App Does

A web application to help people create Section 1983 civil rights complaints. Users fill out an interview-style form, and the app helps them build their legal document step by step.

---

## Current State (Latest Commit: b874513)

The app is functional with the following features complete:

### Core Features Built

1. **User Authentication** (`accounts` app)
   - Email-based login (not username)
   - Registration, login, logout
   - Password recovery
   - User profile with first/middle/last name

2. **Document Builder** (`documents` app)
   - Create new case documents
   - 10 interview sections (see below)
   - Save progress, come back later
   - Section status tracking (not started, in progress, completed, needs work, N/A)

3. **Interview Sections** (in order)
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

4. **Helper Features**
   - Federal district court lookup by city/state
   - State dropdowns on all address forms
   - Contextual help tooltips
   - "Use Recommended" button for Relief Sought
   - Test user mode for demo data

---

## Tech Stack

- **Backend:** Django 4.2, Python 3.11
- **Database:** PostgreSQL (via Docker)
- **Frontend:** Bootstrap 5, vanilla JavaScript
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
│   ├── models.py       # Custom User model (email login)
│   ├── views.py        # Login, register, profile views
│   └── forms.py        # Auth forms
│
├── documents/          # Main document builder app
│   ├── models.py       # Document, Section, PlaintiffInfo, etc.
│   ├── views.py        # Section edit, preview, AJAX endpoints
│   ├── forms.py        # All section forms + US_STATES dropdown
│   ├── help_content.py # Tooltips and help text for each field
│   ├── urls.py         # URL routing
│   └── services/       # Court lookup service
│       └── court_lookup_service.py
│
├── templates/
│   ├── base.html                    # Base template
│   ├── accounts/                    # Auth templates
│   └── documents/
│       ├── document_list.html       # User's documents
│       ├── document_detail.html     # Single document overview
│       ├── document_preview.html    # Preview with edit modals
│       └── section_edit.html        # Interview form (main form page)
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

## Recent Changes (This Session)

1. **Attorney Representation** - Checkbox to add attorney info when plaintiff has a lawyer
2. **Court Lookup** - Enter city/state, click button, auto-fills federal district court
3. **State Dropdowns** - All state fields now use dropdown instead of text input
4. **Help Tooltips** - Question mark icons with explanations
5. **Multi-item Guidance** - Info box explaining "add multiple entries" for defendants/witnesses/evidence

---

## What's NOT Built Yet

- PDF generation of the complaint
- E-filing integration
- Payment/subscription (DO NOT BUILD - user doesn't want Stripe)
- Video extraction (DO NOT BUILD - user didn't ask for this)

---

## Instructions for Next Claude Session

**IMPORTANT:**
- Do NOT start building features automatically
- Ask what the user wants to work on
- Go step by step - explain what you plan to do BEFORE doing it
- Get approval before writing code

**To continue work:**
1. User will tell you what feature they want
2. You explain the plan
3. User approves
4. You implement
5. User tests
6. Repeat

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
```
