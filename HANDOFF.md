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
   - **Rights Violation Analyzer** - Suggests which rights were violated based on narrative
   - **Tell Your Story** - User writes story, AI extracts data for all sections
   - **Parse Story API** - Backend endpoint for AI parsing (`/documents/{id}/parse-story/`)
   - **Auto-apply incident_overview** - Extracted fields automatically saved to database
   - **Legal Document Generator** - AI writes court-ready federal complaint

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

## Authentication System

### Features
- Email-based login (no usernames)
- User registration with email verification
- Password reset via email
- Password change for logged-in users
- Profile management

### URLs (accounts app)
| URL | Purpose |
|-----|---------|
| `/accounts/login/` | Login page |
| `/accounts/logout/` | Logout |
| `/accounts/register/` | New user registration |
| `/accounts/password-reset/` | Request password reset email |
| `/accounts/password-reset/done/` | "Email sent" confirmation |
| `/accounts/password-reset/<uid>/<token>/` | Set new password (from email link) |
| `/accounts/password-reset/complete/` | "Password changed" confirmation |
| `/accounts/password-change/` | Change password (logged in) |
| `/accounts/profile/` | View profile |
| `/accounts/profile/edit/` | Edit profile |

### Email Configuration
Password reset and payout notifications require SMTP email. See Environment Variables section for Namecheap Private Email setup.

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
- `documents/services/openai_service.py` - OpenAI API integration
- `documents/test_stories.py` - 20 sample test stories for testing AI parsing
- `static/js/tell-story.js` - Tell Your Story frontend
- `static/js/rights-analyze.js` - Rights analysis frontend
- `static/css/tell-story.css` - Tell Your Story styles

### OpenAI Service Methods
1. `analyze_rights_violations(document_data)` - Suggests rights violated
2. `parse_story(story_text)` - Extracts structured data from user's story

### Story Parsing Extracts
- incident_overview: date, time, location, city, state, location_type, was_recording, recording_device
- incident_narrative: summary, detailed_narrative, what_were_you_doing, initial_contact, what_was_said, physical_actions, how_it_ended
- defendants: name, badge_number, title, agency, agency_inferred, description
- witnesses: name, description, what_they_saw
- evidence: type, description (includes deleted/seized recordings, potential body cam footage)
- damages: physical_injuries, emotional_distress (including lost memories/photos), financial_losses, other_damages (destroyed data)
- rights_violated: suggested_violations with amendment and reason
- questions_to_ask: follow-up questions for ONLY missing info (skips info already in story)

### Relief Suggestions (Separate AI Prompt)
After story parsing completes, a second AI call analyzes the extracted data and recommends relief:
- `suggest_relief(extracted_data)` in `openai_service.py`
- Returns recommendations for each relief type with case-specific reasoning
- Displayed in "Relief Sought" accordion section during analysis
- Saved to database when user clicks "Continue to Document"

Relief types analyzed:
- Compensatory Damages (based on damages suffered)
- Punitive Damages (if willful/malicious conduct)
- Declaratory Relief (with suggested declaration text)
- Injunctive Relief (with suggested policy changes)
- Attorney's Fees (always recommended per 42 U.S.C. § 1988)
- Jury Trial (usually recommended)

### Progress Indicator During Analysis (Tech Style)
When user clicks "Analyze My Story", shows a cool tech-themed progress display:
- Dark background with glowing green/cyan accents
- Large percentage counter (0% → 100%)
- Animated progress bar
- 8 steps with status: WAITING → ANALYZING... → COMPLETE
- Pulsing/glowing effects on active steps
- Scanline animation across top
- Grid overlay for tech aesthetic
- All steps turn green with checkmarks when complete

### Story Persistence on Revisit
When users revisit the Tell Your Story page after completing analysis:
- Textarea is pre-filled with their saved story
- Green notice explains they can edit and re-analyze
- No limits on re-analysis (users often remember more details later)
- Re-analyzing updates document sections with new information

### Background Processing with Polling
Story analysis now runs in a background thread to prevent timeouts:

**How it works:**
1. User clicks "Analyze My Story" → POST to `/parse-story/`
2. Server starts background thread, returns `{status: "processing"}` immediately
3. Frontend polls `/parse-story/status/` every 3 seconds
4. When background processing completes, status endpoint returns results
5. Frontend displays results

**Database fields added to Document model:**
- `parsing_status`: 'idle', 'processing', 'completed', 'failed'
- `parsing_result`: JSONField storing parsed sections
- `parsing_error`: Error message if failed
- `parsing_started_at`: Timestamp for detecting stale jobs

**Benefits:**
- No more Gunicorn worker timeouts (was 30s, now irrelevant)
- User stays on page with progress animation
- More reliable for slow OpenAI responses

### AI Extraction Improvements (Recent)
1. **Inference from Context** - AI extracts info that can be reasonably inferred (e.g., "city hall in Oklahoma City" → city="Oklahoma City", state="OK", location_type="government building")
2. **Smart Follow-up Questions** - Only asks about truly missing info, skips questions about info already in story
3. **Evidence Capture** - Includes recordings even if deleted/seized, potential body cam footage
4. **Emotional Distress** - Captures loss of irreplaceable memories/photos
5. **No Redundant Questions** - Won't ask about location if story mentions where it happened

### Agency Inference Feature (Story Parsing)
When a user mentions a location (city/state) but not a specific agency, the AI will infer the likely agency:
- Police officer in Tampa, FL → "Tampa Police Department"
- Deputy in Orange County → "Orange County Sheriff's Office"
- State trooper → "[State] Highway Patrol"

The `agency_inferred` flag indicates when the agency was AI-suggested vs explicitly stated.
UI shows a yellow warning: "AI suggested - please verify this is correct"

### Agency Suggestion Feature (Defendant Form)
In the Government Defendants section, users can click "Suggest Agency" to get AI-powered agency name AND address suggestions.

**How it works:**
1. User enters city/state in Incident Overview (or inferred from story)
2. User adds a defendant in Government Defendants section
3. User clicks "Suggest Agency" button
4. AI suggests official agency names AND headquarters addresses based on location context
5. User clicks "Use" to accept a suggestion (auto-fills both agency AND address fields)

**Address Lookup:**
- AI provides the agency's official headquarters address for service of process
- Address is displayed with a location icon in the suggestion
- Both agency name and address are auto-filled when user clicks "Use"
- Warning always displayed: "Please verify the address before filing legal documents"
- Addresses are from AI's knowledge base and should be verified before filing

**API Endpoint:** `/documents/{id}/suggest-agency/`
- Method: POST
- Payload: `{city, state, defendant_name, title, description}`
- Returns: List of agency suggestions with confidence levels AND addresses

**Defendant model field:**
- `agency_inferred` (BooleanField, default=False)
- Set to True when agency comes from AI (story parsing or suggestion)
- Cleared to False when user manually saves/edits the defendant

**Document Detail Warning:**
When defendants have `agency_inferred=True`, the Government Defendants section card shows:
- Blue info alert: "AI-Suggested Agencies: X defendants have AI-inferred agencies that should be reviewed for accuracy."

**Editing Existing Defendants:**
- Defendants list shows "Edit" button for each defendant
- Shows AI-suggested warning badge for defendants with agency_inferred=True
- Displays the agency name inline for each defendant
- Edit page at `/documents/{id}/defendant/{defendant_id}/edit/`
- Edit page has Save/Cancel buttons only (no Suggest Agency - users editing already know what to change)

**Files involved:**
- `documents/services/openai_service.py` - `suggest_agency()` method
- `documents/views.py` - `suggest_agency` and `edit_defendant` view endpoints
- `documents/urls.py` - Routes for suggest-agency and edit-defendant
- `templates/documents/section_edit.html` - Suggest Agency button, Edit button for existing defendants
- `templates/documents/edit_defendant.html` - Edit defendant form with Suggest Agency
- `templates/documents/document_detail.html` - Warning for defendants needing review
- `documents/forms.py` - DefendantForm clears agency_inferred on save
- `documents/models.py` - Defendant.agency_inferred field
- `documents/migrations/0013_defendant_agency_inferred.py` - Migration for new field

### Witness Enhancement Feature (NEW)
The Witnesses section now includes enhanced fields for tracking evidence captured by witnesses and their prior interactions with defendants.

**Enhanced Witness Fields:**
| Field | Purpose |
|-------|---------|
| `has_evidence` | Boolean - did witness capture video/photo evidence? |
| `evidence_description` | Text - what they recorded (video, photos, audio) |
| `prior_interactions` | Text - any prior interactions with defendant(s) |
| `additional_notes` | Text - other relevant witness information |

**Edit Witness Feature:**
- Each witness in the list shows an "Edit" button
- Edit page at `/documents/{id}/witness/{witness_id}/edit/`
- Form organized into collapsible sections (basic info, what they witnessed, evidence, prior interactions)
- Visual indicators in witness list show evidence badge and prior interactions indicator

**Document Generation Integration:**
- Witness evidence data is passed to the AI document generator
- Statement of Facts now includes witness-captured evidence (video, photos, audio)
- Prior interactions with defendants can establish pattern or motive
- AI writes appropriate paragraphs about recordings and witness observations

**Files involved:**
- `documents/models.py` - Enhanced Witness model with new fields
- `documents/forms.py` - WitnessForm with new field widgets
- `documents/views.py` - `edit_witness` view, `_collect_document_data` includes witnesses
- `documents/urls.py` - Route for edit_witness
- `documents/services/document_generator.py` - `_generate_facts` incorporates witness evidence
- `templates/documents/section_edit.html` - Edit button, evidence badges
- `templates/documents/edit_witness.html` - Full edit form for witnesses
- `documents/migrations/0014_witness_enhanced_fields.py` - Migration for new fields

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
| Witness | People who saw the incident (multiple) - with enhanced evidence fields |
| Evidence | Videos, documents, etc. (multiple) |
| Damages | Physical, emotional, financial harm |
| PriorComplaints | Previous complaints filed |
| ReliefSought | What the plaintiff wants (money, declaration, etc.) |

---

## Legal Document Generator

### Overview
AI-powered document generation that creates a professionally written Section 1983 federal complaint.

### How It Works
1. User fills out document sections (plaintiff info, narrative, rights violated, etc.)
2. User visits Preview page (`/documents/{id}/preview/`)
3. System generates complete legal complaint with:
   - Proper caption (court name, parties, case number placeholder)
   - Jurisdiction and venue statement
   - Parties section identifying all plaintiffs and defendants
   - Statement of facts written in professional legal prose
   - Causes of action with legal arguments
   - Prayer for relief
   - Jury demand (if requested)
   - Signature block (pro se or attorney)

### Key Features
- **Professional Legal Prose** - AI writes each section in formal legal style
- **Third Person** - "Plaintiff" not "I"
- **Numbered Paragraphs** - Following federal court conventions
- **Print-Ready** - Document formatted for court filing
- **Proper Caption Format** - Includes:
  - Individual defendants with title (e.g., "OFFICER JOHN DOE")
  - "individually and in official capacity" language
  - Agency name (e.g., "TAMPA POLICE DEPARTMENT")
  - "et al." when more than 2 defendants
- **Missing Agency Warning** - Individual defendants without agency shown in red with warning

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
| Default referral payout | $5.00 per use (customizable per code) |

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
| PromoCode | User's referral codes (multiple per user) |
| PromoCodeUsage | Tracks each promo use for payouts |
| PayoutRequest | User payout requests with status tracking |

### User Model Additions
- `has_unlimited_access()` - Check if admin/staff
- `get_total_free_ai_uses()` - AI uses across all documents
- `can_use_free_ai()` - Check user-level AI limit
- `get_free_ai_remaining()` - Remaining free AI count
- `get_total_referral_earnings()` - Total earnings from all codes
- `get_pending_referral_earnings()` - Pending (unpaid) earnings
- `get_paid_referral_earnings()` - Already paid earnings

### URLs (Payment)
- `/documents/{id}/checkout/` - Checkout page with promo code
- `/documents/{id}/checkout/success/` - Payment success handler
- `/documents/{id}/checkout/cancel/` - Payment cancelled
- `/documents/webhook/stripe/` - Stripe webhook endpoint
- `/documents/{id}/finalize/` - Document finalization confirmation
- `/documents/my-referral-code/` - Referral dashboard (multiple codes)
- `/documents/validate-promo-code/` - AJAX promo validation
- `/documents/promo-code/{id}/toggle/` - Activate/deactivate a code
- `/documents/request-payout/` - Request payout for pending earnings
- `/documents/admin/referrals/` - Admin referral management dashboard
- `/documents/admin/referrals/code/{id}/edit/` - Edit promo code rate (admin only)

### Admin Features
- View all documents with payment status
- PromoCode admin with usage stats
- PromoCodeUsage admin with payout tracking
- PayoutRequest admin for processing payouts
- Bulk action: "Mark as paid" for referral payouts
- Custom admin referral dashboard at `/documents/admin/referrals/`

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
REFERRAL_PAYOUT = 5.00  # Default, but each PromoCode has its own referral_amount
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
- `templates/documents/my_referral_code.html` - Referral dashboard (multiple codes)
- `templates/documents/request_payout.html` - Payout request form
- `templates/documents/admin_referrals.html` - Admin referral management
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

## Referral System (Enhanced)

### Overview
Users can create multiple referral codes, track referrals, and request payouts. Admin manages all payouts manually via Stripe dashboard then updates the database. **Each promo code has a custom referral rate** (default $5, admin can edit).

### User Features
1. **Multiple Codes** - Create unlimited referral codes with optional names
2. **Custom Rates** - Each code has its own referral rate (shown in "Rate" column)
3. **Referral Dashboard** - See all codes, usage stats, earnings breakdown
4. **Referral History** - View who used your codes, when, and payout status
5. **Payout Requests** - Request payout when pending balance >= $15

### Admin Features
1. **Admin Referral Dashboard** (`/documents/admin/referrals/`)
   - Summary stats (total referrals, pending payouts, total paid)
   - All promo codes with owner, rate, and usage count
   - **Edit button** to change referral rate per code
   - Recent referral activity
   - Payout request queue with processing actions

2. **Custom Referral Rates**
   - Default rate is $5.00 for new codes
   - Admin can edit any code's rate via pencil icon in admin panel
   - When code is used, the code's `referral_amount` is applied (not global setting)

3. **Payout Processing Workflow**
   - User requests payout → Admin sees request with payment details
   - Admin pays manually via Stripe/PayPal/Venmo/etc.
   - Admin marks request as "Completed" with reference number
   - System auto-marks all pending usages as paid

4. **Email Notifications**
   - When user requests payout, admin receives email notification
   - Configure `ADMIN_EMAIL` in settings

### Database Models
| Model | Purpose |
|-------|---------|
| PromoCode | Multiple per user, tracks times_used and total_earned |
| PromoCode.name | Optional friendly name for the code |
| PromoCode.referral_amount | Custom rate per code (default $5.00) |
| PromoCodeUsage | Each code use with payout_status (pending/paid) |
| PayoutRequest | User payout requests with status and payment tracking |

### Settings
```python
ADMIN_EMAIL = 'admin@1983law.com'  # Receives payout request notifications
DEFAULT_FROM_EMAIL = 'noreply@1983law.com'
```

### Payout Flow
1. User creates referral codes at `/documents/my-referral-code/`
2. Others use code at checkout → User earns $15 per use
3. When pending >= $15, user clicks "Request Payout"
4. User enters payment method (PayPal, Venmo, Zelle, etc.)
5. Admin receives email notification
6. Admin visits `/documents/admin/referrals/`
7. Admin pays user via Stripe dashboard or other method
8. Admin enters payment reference and marks as "Completed"
9. User's pending earnings reset, history shows "Paid"

---

## Deployment (Render.com)

### Live URL
- **Production**: https://one983-law.onrender.com
- **Custom Domains**: 1983law.org, www.1983law.org

### Render Configuration
The app uses Docker deployment on Render with these files:
- `Dockerfile` - Python 3.11 slim image with gunicorn
- `start.sh` - Startup script that runs migrations then starts gunicorn
- `render.yaml` - Blueprint configuration (optional, can configure via dashboard)

### IMPORTANT: Pre-Deploy Command
Set this in Render Dashboard → Settings → **Pre-Deploy Command**:
```
python manage.py migrate
```
This ensures migrations run automatically on every deploy.

### Key Files for Deployment
| File | Purpose |
|------|---------|
| `Dockerfile` | Container build instructions |
| `start.sh` | Runs migrations + starts gunicorn on $PORT |
| `build.sh` | Alternative build script (for native Python runtime) |
| `requirements.txt` | Python dependencies |

### Migration Troubleshooting
If you get 500 errors after deploy, check if tables are missing:

1. Go to Render Dashboard → Shell
2. Run: `python manage.py shell`
3. Test:
```python
from documents.models import PayoutRequest
PayoutRequest.objects.count()
```
4. If you get "table does not exist" error, create it manually:
```python
from django.db import connection
cursor = connection.cursor()
cursor.execute("CREATE TABLE documents_payoutrequest (...)")
```

**Why this happens:** If migrations were "faked" previously (marked as applied but tables not created), new deploys won't recreate them. Always commit migration files BEFORE running them on production.

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

**Email (Namecheap Private Email):**
- `EMAIL_HOST` - `mail.privateemail.com`
- `EMAIL_PORT` - `465` (SSL) or `587` (TLS)
- `EMAIL_USE_SSL` - `1` (if using port 465)
- `EMAIL_USE_TLS` - `0` (set to `1` if using port 587)
- `EMAIL_HOST_USER` - Your email address (e.g., `noreply@1983law.com`)
- `EMAIL_HOST_PASSWORD` - Email account password
- `DEFAULT_FROM_EMAIL` - Same as EMAIL_HOST_USER (e.g., `noreply@1983law.com`)
- `ADMIN_EMAIL` - Where payout notifications go (e.g., `admin@1983law.com`)

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

- E-filing integration
- Video extraction

---

## OpenAI Capabilities Available (for future features)

The OpenAI API has these capabilities that could enhance the app:

| Capability | Potential Use |
|------------|---------------|
| ✅ Chat Completions | Currently used for story parsing and relief suggestions |
| 🔍 Web Search | Look up actual agency addresses, court info, relevant case law |
| 🖼️ Images | Analyze uploaded evidence photos |
| 🎤 Audio Transcriptions | Let users speak their story instead of typing (accessibility) |
| 📁 File Search | Search through legal documents or templates |
| 🧮 Code Interpreter | Process uploaded documents |

**Most useful additions:**
1. **Web Search** - Find real agency addresses instead of inferring
2. **Audio Transcriptions** - Voice-to-text for telling the story

---

## PDF Download Feature

### Overview
Finalized documents can be downloaded as professionally formatted PDF files using WeasyPrint.

### How It Works
1. User finalizes their document (after payment)
2. "Download PDF" button appears on the preview page
3. Server generates PDF from the legal document template
4. PDF downloads to user's machine

### Requirements
- Document must be in `finalized` status
- Document must have minimum required data (plaintiff name, narrative, rights violated)

### Files
- `templates/documents/document_pdf.html` - Print-optimized PDF template
- `documents/views.py` - `download_pdf` view function

### URL
- `/documents/{id}/download-pdf/` - Download PDF endpoint

---

## Future Plans

- **Mobile App Version** - Tell Your Story will be key feature
- **Voice Input** - Add speech-to-text (Whisper) later

---

## Known Issues / Debugging

### "Network error" on Story Analysis (FULLY RESOLVED)
Users were seeing "Network error. Please try again." when clicking "Analyze My Story" on production.

**Root cause:** Gunicorn default worker timeout is 30 seconds. The OpenAI API calls for story parsing can take longer, causing Gunicorn to kill the worker and return a 500 error.

**Solution:** Implemented background processing with polling:
1. POST to `/parse-story/` returns immediately with `{status: "processing"}`
2. OpenAI calls run in background thread
3. Frontend polls `/parse-story/status/` every 3 seconds
4. Results stored in database, returned when ready

This completely eliminates timeout issues regardless of how long OpenAI takes.

### Relief Sought Not Saving (Needs Investigation)
The relief_sought section may not be saving properly when user clicks "Continue to Document".

**Debug steps:**
1. Open browser DevTools (F12) → Console tab
2. Click "Analyze My Story" and wait for results
3. Check if Relief Sought section appears in the accordion
4. Click "Continue to Document"
5. Look in console for:
   - `Relief fields to apply:` - Shows what's being sent
   - `Some sections had errors:` - Shows if there were save errors

**Possible causes:**
- DocumentSection for relief_sought may not exist
- Boolean value handling in Python
- Check `apply_story_fields` view in `documents/views.py` around line 1374

---

## Instructions for Next Claude Session

**IMPORTANT:**
- Do NOT start building features automatically
- Ask what the user wants to work on
- Go step by step - explain what you plan to do BEFORE doing it
- Get approval before writing code
- Update this HANDOFF.md after completing features
- **Always provide git pull and merge commands at the end of a session**

**To continue work:**
1. User will tell you what feature they want
2. You explain the plan
3. User approves
4. You implement
5. User tests
6. Update HANDOFF.md
7. Provide merge commands (see below)
8. Repeat

**After completing work - provide these merge commands:**
```bash
# Pull the changes
git fetch origin <branch-name>

# Switch to master and merge
git checkout master
git pull origin master
git merge <branch-name>

# Push merged master
git push origin master
```

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
