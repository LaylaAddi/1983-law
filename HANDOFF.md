# 1983 Law App - Handoff Document

## What This App Does

A web application to help people create Section 1983 civil rights complaints. Users fill out an interview-style form, and the app helps them build their legal document step by step.

---

## Current State (Latest Commit: see git log)

The app is functional with the following features complete:

### Core Features Built

1. **User Authentication** (`accounts` app)
   - Email-based login (not username)
   - Registration requires only email and password (no name fields)
   - Name and address collected via Profile Completion before creating documents
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
   - **Case Law Suggestions** - AI selects relevant case law from curated database
   - **Legal Document Generator (NEW)** - AI writes court-ready federal complaint with case law integrated

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
| is_test_user | Enable test features (NOT admin access) |
| is_staff | Django staff status (grants unlimited AI access) |
| is_superuser | Django superuser status (grants unlimited AI access) |
| has_complete_profile() | Method to check if profile is complete |
| has_unlimited_access() | Method: returns True if is_staff OR is_superuser |

---

## User Permission Types (IMPORTANT)

There are three separate permission flags - they serve different purposes:

| Flag | What It Does | AI Limits | Payment Required |
|------|--------------|-----------|------------------|
| `is_test_user` | Test stories dropdown, fill test data button | **Normal limits apply** | **Yes** |
| `is_staff` | Django admin panel + unlimited AI | **Unlimited** | **No** |
| `is_superuser` | Full Django admin + unlimited AI | **Unlimited** | **No** |

### Common Configurations

| User Type | is_test_user | is_staff | is_superuser |
|-----------|--------------|----------|--------------|
| Regular user | False | False | False |
| Tester (limited) | True | False | False |
| Staff tester (full) | True | True | False |
| Site admin | True | True | True |

### Key Code Locations
- `is_test_user` check: `documents/views.py` lines 513, 1081
- `has_unlimited_access()`: `accounts/models.py` line 112
- AI limit bypass: `accounts/models.py` lines 126, 132 and `documents/models.py` line 143

### Setting Up a Full Test User
```python
# In Django shell
from accounts.models import User
u = User.objects.get(email='your@email.com')
u.is_test_user = True   # Test features (stories, sample data)
u.is_staff = True       # Unlimited AI access
u.save()
```

---

## AI Features Detail

### Files
- `documents/services/openai_service.py` - OpenAI API integration (includes `suggest_case_law` method)
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
│       ├── openai_service.py  # AI integration
│       └── document_generator.py  # Legal document generation (NEW)
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
| CaseLaw | Curated database of landmark Section 1983 cases (NEW) |
| DocumentCaseLaw | Links case law citations to documents with explanations (NEW) |

---

## Case Law Citations (NEW)

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

## Legal Document Generator (NEW)

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

## Payment System (NEW)

### Overview
Pay-per-document model with Stripe integration, promo/referral codes, and document lifecycle management.

### Pricing
| Item | Price |
|------|-------|
| Base price | $79.00 |
| With promo code | $59.25 (25% off) |
| Referral payout | $15.00 per use |

### Document Lifecycle
```
DRAFT (free) → EXPIRED or PAID → FINALIZED
```

| Status | Can Edit | AI Access | Expiry | PDF |
|--------|----------|-----------|--------|-----|
| draft | Yes | 3 free (user-level) | 48 hours | No |
| expired | No | No | Pay to unlock | No |
| paid | Yes | $5 budget | 45 days | No |
| finalized | No | No | Never | Yes |

### Key Features
1. **User-Level AI Tracking** - Free AI uses tracked across ALL user documents (prevents abuse)
2. **Admin Unlimited Access** - `is_staff` or `is_superuser` users bypass all limits
3. **Promo Codes** - Users create their own referral code, earn $15 per use
4. **Stripe Checkout** - Secure payment with promo code validation
5. **Document Finalization** - Confirmation required before locking document
6. **Status Banner** - Shows time remaining, AI usage, and action buttons on all document pages

### Database Models
| Model | Purpose |
|-------|---------|
| Document.payment_status | draft/expired/paid/finalized |
| Document.stripe_payment_id | Stripe Payment Intent ID |
| Document.promo_code_used | FK to PromoCode |
| Document.amount_paid | Decimal amount |
| Document.paid_at | Payment timestamp |
| Document.finalized_at | Finalization timestamp |
| Document.ai_generations_used | Free tier counter |
| Document.ai_cost_used | Paid tier cost tracking |
| PromoCode | User's referral code with stats |
| PromoCodeUsage | Tracks each promo use for payouts |

### User Model Additions
- `has_unlimited_access()` - Check if admin/staff
- `get_total_free_ai_uses()` - AI uses across all documents
- `can_use_free_ai()` - Check user-level AI limit
- `get_free_ai_remaining()` - Remaining free AI count

### URLs (Payment)
- `/documents/{id}/checkout/` - Checkout page with promo code
- `/documents/{id}/checkout/success/` - Payment success handler
- `/documents/{id}/checkout/cancel/` - Payment cancelled
- `/documents/webhook/stripe/` - Stripe webhook endpoint
- `/documents/{id}/finalize/` - Document finalization confirmation
- `/documents/my-referral-code/` - Create/view referral code
- `/documents/validate-promo-code/` - AJAX promo validation

### Admin Features
- View all documents with payment status
- PromoCode admin with usage stats
- PromoCodeUsage admin with payout tracking
- Bulk action: "Mark as paid" for referral payouts

### Environment Variables
```env
STRIPE_PUBLIC_KEY=pk_test_xxx
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx  # Optional for local testing
```

### Settings (config/settings.py)
```python
DOCUMENT_PRICE = 79.00
PROMO_DISCOUNT_PERCENT = 25
REFERRAL_PAYOUT = 15.00
FREE_AI_GENERATIONS = 3
DRAFT_EXPIRY_HOURS = 48
PAID_AI_BUDGET = 5.00
PAID_EXPIRY_DAYS = 45
APP_NAME = '1983law.com'  # Shown in DRAFT watermark and footer
HEADER_APP_NAME = '1983 Law'  # Shown in navbar and page titles
```

### Templates Added
- `templates/documents/checkout.html` - Checkout page
- `templates/documents/finalize.html` - Finalization confirmation
- `templates/documents/my_referral_code.html` - Referral code management
- `templates/documents/partials/status_banner.html` - Status display partial

### Checkout Flow
1. User clicks "Upgrade Now" in status banner
2. Enter promo code OR check "I confirm I do not have a promo code"
3. Redirected to Stripe Checkout
4. On success → document marked as `paid`
5. User has 45 days to edit and use AI ($5 budget)
6. User clicks "Finalize & Download PDF"
7. Confirmation modal with checkbox
8. Document marked as `finalized`, PDF available (no watermark)

### Testing Without Webhook
- Checkout flow works without webhook (success page handles verification)
- Use test card: `4242 4242 4242 4242`, any future date, any CVC
- For webhook testing, install Stripe CLI:
  ```powershell
  stripe listen --forward-to localhost:8000/documents/webhook/stripe/
  ```

---

## Deployment (Render.com)

### Live URL
- **Production**: https://one983-law.onrender.com
- **Custom Domain**: 1983law.org (when DNS propagates)

### Render Configuration
The app uses Docker deployment on Render with these files:
- `Dockerfile` - Python 3.11 slim image with gunicorn
- `start.sh` - Startup script that runs migrations then starts gunicorn
- `render.yaml` - Blueprint configuration (optional, can configure via dashboard)

### Key Files for Deployment
| File | Purpose |
|------|---------|
| `Dockerfile` | Container build instructions |
| `start.sh` | Runs migrations + starts gunicorn on $PORT |
| `build.sh` | Alternative build script (for native Python runtime) |
| `requirements.txt` | Python dependencies |

### Environment Variables on Render
Set these in Render Dashboard → Environment:
- `DATABASE_URL` - Auto-set if using Render Postgres
- `SECRET_KEY` - Auto-generated or set manually
- `DEBUG` - Set to `0` for production
- `ALLOWED_HOSTS` - `.onrender.com,1983law.org,www.1983law.org`
- `OPENAI_API_KEY` - Your OpenAI API key
- `STRIPE_PUBLIC_KEY` - Stripe publishable key
- `STRIPE_SECRET_KEY` - Stripe secret key
- `STRIPE_WEBHOOK_SECRET` - From Stripe webhook settings
- `APP_NAME` - `1983law.org` (footer/watermark)
- `HEADER_APP_NAME` - `1983 Law` (navbar/titles)

### Creating Admin User on Render
1. Go to Render Dashboard → Your Service → Shell tab
2. Run: `python manage.py createsuperuser`
3. Enter email and password
4. Admin URL: `https://one983-law.onrender.com/admin/`

### Stripe Webhook Setup (Production)
1. Go to https://dashboard.stripe.com/webhooks
2. Click "Add endpoint"
3. URL: `https://one983-law.onrender.com/documents/webhook/stripe/`
4. Select event: `checkout.session.completed`
5. Copy signing secret → Add as `STRIPE_WEBHOOK_SECRET` on Render

---

## What's NOT Built Yet

- Server-side PDF generation (using browser Print to PDF for now)
- E-filing integration
- Video extraction

---

## Future Plans

- **Mobile App Version** - Tell Your Story will be key feature
- **Voice Input** - Add speech-to-text (Whisper) later
- **More Case Law** - Expand database with circuit-specific cases
- **Server-side PDF** - WeasyPrint or similar for direct download

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

```env
# Required
OPENAI_API_KEY=sk-...          # Required for AI features

# Stripe (Required for payments)
STRIPE_PUBLIC_KEY=pk_test_...  # Stripe publishable key
STRIPE_SECRET_KEY=sk_test_...  # Stripe secret key
STRIPE_WEBHOOK_SECRET=whsec_...# Stripe webhook secret (optional for local)

# Optional (Branding)
APP_NAME=1983law.com           # Shown in DRAFT watermark and footer
HEADER_APP_NAME=1983 Law       # Shown in navbar and page titles
```
