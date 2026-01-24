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
   - **Per-Section AI Suggestions** (NEW) - Each section has "Analyze Story & Suggest" button:
     - **Damages**: Identifies physical, emotional, economic, constitutional damages
     - **Witnesses**: Identifies people mentioned who could be witnesses
     - **Evidence**: Distinguishes between evidence user HAS vs. evidence to OBTAIN (see below)
     - **Rights Violated**: Identifies constitutional violations with strength assessment
   - **Context-aware Rights Section** - Shows different messages based on section status
   - **Rights Section First-Time Guide** - Dismissible guide explaining how to use AI suggestions and "Copy to Details" feature
   - **AI Document Review** (NEW) - Comprehensive review of the complete document:
     - Legal strength analysis
     - Clarity and readability suggestions
     - Completeness check for required elements
     - Inline highlighting of issues (critical=red, warning=yellow, suggestion=blue)
     - Click issues in sidebar to scroll to problem area

7. **Document Completion Validation** (NEW)
   - Checkout blocked until all sections complete or marked N/A
   - Defendants must have addresses (for serving legal documents)
   - Federal district court must be looked up AND confirmed
   - Clear error messages showing what's missing

8. **Court District Requirement** (NEW)
   - Highlighted orange box around court district fields
   - Mandatory confirmation checkbox: "I confirm this is the correct federal district court"
   - Form cannot submit without court lookup and confirmation
   - Single-district states (Nevada, Idaho, etc.) auto-return the only court

9. **Helper Features**
   - Federal district court lookup by city/state (auto-lookup on story parse)
   - State dropdowns on all address forms
   - Contextual help tooltips
   - "Use Recommended" button for Relief Sought
   - Test user mode for demo data

8. **Navigation & UX Improvements**
   - **Back to Document buttons** on all section edit pages and Tell Your Story page
   - **Unsaved changes warning** - Browser warns if user tries to navigate away with unsaved edits
   - **Story status indicator** - Document detail page shows "Story Saved" with "Update Story" button when story exists, otherwise "Quick Start with AI" with "Tell Your Story" button
   - **"Et al." in case caption** - When multiple defendants, shows first defendant + "et al." (full list in PARTIES section)

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
  - `incident_date` (**REQUIRED** - form validation enforces this)
  - `incident_time` (**REQUIRED** - form validation enforces this, AM/PM must be specified)
  - `incident_location`
  - `city`
  - `state`
  - `location_type` (inferred from story)
  - `was_recording` (if mentioned)
  - `recording_device` (if mentioned)
  - `federal_district_court` (auto-lookup from city/state)
- **Section status:** Auto-marked as in_progress or completed
- **Note:** If date/time not in story, AI ALWAYS asks for them in follow-up questions

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

### Profile Page - My Plan Section (NEW)
The profile page now shows subscription/purchase status with:
- **Active subscription**: Plan type, AI uses this period, renewal date, manage link
- **Document packs**: Table showing packs with remaining credits
- **Free trial**: Shows remaining free AI uses with upgrade prompt
- **No plan**: Shows prompt to view pricing
- **Purchase history**: Table of paid/finalized documents with amounts

### Document Creation Soft Gate (NEW)
When a user has exhausted all free options (no subscription, no pack credits, no free AI remaining), attempting to create a document shows an interstitial page with:
- Pricing options for subscriptions and one-time purchases
- "Continue with limited access" button (sets session flag to bypass)
- Feature highlights (AI writing, court-ready PDF, rights analysis)

**Files:**
- `templates/documents/purchase_required.html` - Interstitial template
- `documents/views.py` - `document_create` checks `user.needs_purchase_prompt()`
- `accounts/models.py` - `needs_purchase_prompt()` and `get_access_summary()` methods

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
| has_active_subscription() | Method: returns True if user has active subscription |
| get_document_credits() | Method: returns total remaining document credits from packs |
| needs_purchase_prompt() | Method: returns True if user should see purchase interstitial |
| get_access_summary() | Method: returns dict with subscription, credits, free AI status |

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

### Database-Editable AI Prompts (NEW)
AI prompts can now be edited via admin without code changes.

**Admin URL:** `/admin/documents/aiprompt/`

**Prompt Types:**
| Type | Title | Purpose |
|------|-------|---------|
| `find_law_enforcement` | Find Law Enforcement Agency | Identifies correct police/sheriff |
| `parse_story` | Parse User Story | Analyzes "Tell Your Story" input |
| `analyze_rights` | Analyze Constitutional Rights | Identifies rights violations |
| `suggest_relief` | Suggest Legal Relief | Recommends damages/injunctions |
| `suggest_damages` | Suggest Damages from Story | Per-section AI: identifies damages |
| `suggest_witnesses` | Suggest Witnesses from Story | Per-section AI: identifies witnesses |
| `suggest_evidence` | Suggest Evidence from Story | Per-section AI: separates evidence user HAS vs. evidence to OBTAIN |
| `suggest_rights_violated` | Suggest Rights Violations | Per-section AI: identifies constitutional violations |
| `identify_officer_agency` | Identify Agency for Officer | Identifies agency when "Find Agency & Address" is clicked with empty agency field |
| `lookup_federal_court` | Lookup Federal District Court | Uses GPT web search to find federal court for locations not in static database |

**Each Prompt Has:**
- **Title** - Human-readable name
- **Description** - What it does and when called
- **System Message** - AI persona/behavior
- **Prompt Template** - Main prompt with `{variable}` placeholders
- **Available Variables** - List of placeholders (e.g., city, state, story_text)
- **Model Name** - OpenAI model (default: gpt-4o-mini)
- **Temperature** - 0.0 = consistent, 1.0 = creative
- **Max Tokens** - Response length limit
- **Is Active** - Disable to fall back to hardcoded
- **Version** - Auto-increments on edit
- **Last Edited By** - Audit trail

**How to Edit Prompts:**

| Method | When to Use | Steps |
|--------|-------------|-------|
| **Admin (Recommended)** | Routine edits | Go to admin → AI Prompts → Edit → Save. No deploy needed! |
| **Seed Command** | Initial setup or reset to defaults | Run `python manage.py seed_ai_prompts` |

**Workflow for Editing:**
1. Edit prompt directly in admin at `/admin/documents/aiprompt/`
2. Changes take effect immediately (no deploy needed)
3. Update backup file in `documents/prompts/` to keep in sync (optional but recommended)

**Initial Setup (new deployments only):**
```bash
python manage.py migrate
python manage.py seed_ai_prompts
```

**Backup Files:**
- `documents/prompts/` - Markdown copies of each prompt for reference/disaster recovery
- Copy-paste from these files into admin if database is wiped
- Update these files when you edit prompts in admin (for version control)

**Files:**
- `documents/models.py` - AIPrompt model
- `documents/admin.py` - Admin interface with monospace text areas
- `documents/management/commands/seed_ai_prompts.py` - Initial prompt seeding (run once)
- `documents/prompts/*.md` - Backup copies for reference
- `documents/migrations/0018_aiprompt.py` - Migration

### OpenAI Service Methods
1. `analyze_rights_violations(document_data)` - Suggests rights violated
2. `parse_story(story_text)` - Extracts structured data from user's story
3. `find_law_enforcement_agency(city, state)` - Identifies correct police/sheriff jurisdiction
4. `_verify_inferred_agencies(parsed_result)` - Post-processes to correct small town agencies
5. `lookup_federal_court(city, state)` - Uses GPT web search to find federal district court
6. `review_document(document_data)` - Comprehensive AI review of the complete document

### AI Document Review (ENHANCED)
Comprehensive AI review of Section 1983 complaints on the Review & Edit page.

**How It Works:**
1. User clicks "AI Review" button on `/documents/{id}/review/`
2. Terminal-style animation shows in document panel during analysis
3. All document data is sent to GPT for analysis
4. AI returns structured feedback with issues by section
5. Issues are highlighted inline with severity colors
6. User clicks issue in sidebar to scroll to problem area

**What AI Reviews (Priority Order):**
1. **Cross-Document Consistency** - Does time/date/location/names match across ALL sections?
2. **Missing Required Info** - Date, time with AM/PM, location, defendants, rights, damages
3. **Formatting Issues** - Third person writing, placeholder text like "[insert]"

**Does NOT flag:**
- Legal strategy opinions (e.g., "claims may be weak")
- Suggestions to add more evidence
- Information not required for filing

**Overall Assessment:**
- **Ready** (green) - Document is ready for filing
- **Needs Fixes** (yellow) - Has issues to address
- **Has Errors** (red) - Has critical errors

**Issue Severities:**
- **Error** (red) - Must fix before filing
- **Warning** (yellow) - Should address
- **Suggestion** (blue) - Nice to have improvements

**Files:**
- `documents/views.py` - `ai_review_document` endpoint
- `documents/services/openai_service.py` - `review_document()` method
- `documents/management/commands/seed_ai_prompts.py` - `review_document` prompt
- `templates/documents/document_review.html` - UI with highlights and sidebar

**API Endpoints:**
- `/documents/{id}/ai-review/` (POST) - Run comprehensive review
- `/documents/{id}/generate-fix/` (POST) - Generate AI fix for an issue
- `/documents/{id}/apply-fix/` (POST) - Apply fix to database

### Step-Through Fix Mode (NEW)
After AI review, users can step through issues one-by-one and apply AI-generated fixes.

**How It Works:**
1. After AI Review, click "Fix Issues Step-by-Step"
2. For each issue:
   - View the issue description and suggestion
   - Click "Generate AI Fix" to get rewritten content
   - See word-level diff (red=removed, green=added)
   - Apply the fix or skip to next issue
3. Final comparison shows all changes applied/skipped
4. Page reloads to show updated document
5. Can run AI Review again to verify fixes

**Word-Level Diff Algorithm:**
- Uses LCS (Longest Common Subsequence) algorithm
- Shows removed words with red strikethrough
- Shows added words with green highlight
- Unchanged words shown in gray

**Time Format Conversion:**
- AI suggests times in "09:30 AM" format
- Django TimeField requires "HH:MM:SS" format
- `_convert_time_format()` helper automatically converts AM/PM times to 24-hour format

**Date Format Conversion:**
- AI suggests dates in "August 24, 2025" format
- Django DateField requires "YYYY-MM-DD" format
- `_convert_date_format()` helper automatically converts various date formats to ISO format

**Files:**
- `documents/views.py` - `generate_fix`, `apply_fix`, `_get_section_content`, `_convert_time_format` functions
- `documents/services/openai_service.py` - `rewrite_section()` method
- `documents/management/commands/seed_ai_prompts.py` - `rewrite_section` prompt
- `templates/documents/document_review.html` - Step-through UI and diff display

**Note:** Requires `python manage.py seed_ai_prompts` after deploying to add the new prompts.

### Federal Court Lookup (NEW)
Automatically finds the correct federal district court for any US location.

**How It Works:**
1. Static lookup tries first (instant, free) - checks city against known database
2. If city not found → GPT with web search finds the correct court
3. Result auto-fills the "Federal Court" field in Incident Overview

**Files:**
- `documents/services/court_lookup_service.py` - Main lookup service with GPT fallback
- `documents/services/openai_service.py` - `lookup_federal_court()` method
- `documents/prompts/lookup_federal_court.md` - Prompt backup
- `documents/services/court_data/states/` - Static lookup databases per state

**Benefits:**
- Works for small towns, rural areas, unincorporated communities
- No maintenance needed for static city lists
- Always returns a result (never "court not found")
- Results are accurate via web search

**Note:** Requires `python manage.py seed_ai_prompts` after deploying to add the new prompt.

### Story Parsing Extracts
- incident_overview: date, time, location, city, state, location_type, was_recording, recording_device
- incident_narrative: summary, detailed_narrative, what_were_you_doing, initial_contact, what_was_said, physical_actions, how_it_ended
- defendants: name, badge_number, title, agency, agency_inferred, description
- witnesses: name, description, what_they_saw
- evidence: type, description (includes deleted/seized recordings, potential body cam footage)
- damages: physical_injuries, emotional_distress (including lost memories/photos), financial_losses, other_damages (destroyed data)
- rights_violated: suggested_violations with amendment and reason
- questions_to_ask: follow-up questions for missing info (**ALWAYS asks for date/time if missing, ALWAYS asks AM/PM if time is ambiguous** - these are mandatory for legal filings)

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

### Progress Indicator During Analysis (Terminal Style)
When user clicks "Analyze My Story" OR "Analyze My Case" (Rights Violated section), shows a modern terminal/CLI-themed progress display:
- macOS-style terminal window with close/minimize/maximize buttons
- Dark background (#1e1e1e) with monospace font
- Dynamic bash-like commands that incorporate the user's story content
- Commands extract and display real info from the story (dates, names, locations, actions)
- Example commands: `grep -i "officer" story.txt`, `lookup-agency --city="Tampa"`
- Progress bar at bottom with percentage
- Spinner animation while waiting for AI response
- Green checkmark and "Analysis complete" when done
- Commands scroll like a real terminal output

**Rights Analysis Terminal** (`rights-analyze.js` + `rights-analyze.css`)
- Same terminal styling but purple theme (#c586c0)
- Commands specific to constitutional analysis:
  - `load-narrative --from=incident_narrative`
  - `check-first-amendment --speech --press --assembly`
  - `analyze-force --usc=42-1983 --graham-v-connor`

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

### Smart Law Enforcement Agency Detection (NEW)
The AI now intelligently detects when a location doesn't have its own police department and suggests the correct jurisdiction.

**Problem solved:**
- Small towns like "Zama, Mississippi" don't have local police
- AI was incorrectly suggesting "Zama Police Department"
- Now correctly identifies County Sheriff jurisdiction

**How it works:**
1. When parsing a story OR suggesting agencies, AI first checks if the location has local police
2. Uses `find_law_enforcement_agency()` method to determine:
   - Is this a major city (population >10,000) with its own police?
   - Or a small town/unincorporated area served by County Sheriff?
   - What county is this location in?
3. For small towns: Suggests County Sheriff instead of inventing a police department
4. Shows prominent **VERIFICATION REQUIRED** warning

**Example (Zama, Mississippi):**
- Location type: Unincorporated community
- County: Attala
- AI suggests: "Attala County Sheriff's Office" (NOT "Zama Police Department")
- Warning displayed: "This location does not have its own police department"

**Files involved:**
- `documents/services/openai_service.py` - `find_law_enforcement_agency()`, `_verify_inferred_agencies()`
- `templates/documents/section_edit.html` - Verification warning display

### Agency Suggestion Feature (Defendant Form)
In the Government Defendants section, users can click "Suggest Agency" to get AI-powered agency name AND address suggestions.

**How it works:**
1. User enters city/state in Incident Overview (or inferred from story)
2. User adds a defendant in Government Defendants section
3. User clicks "Suggest Agency" button
4. **AI first checks if location has local police** (see Smart Law Enforcement above)
5. AI suggests official agency names AND headquarters addresses based on verified jurisdiction
6. User clicks "Use" to accept a suggestion (auto-fills both agency AND address fields)

**Address Lookup:**
- AI provides the agency's official headquarters address for service of process
- Address is displayed with a location icon in the suggestion
- Both agency name and address are auto-filled when user clicks "Use"
- Warning always displayed: "Please verify the address before filing legal documents"
- Addresses are from AI's knowledge base and should be verified before filing
- **Works for both agency defendants (uses "name" field) and individual officers (uses "agency_name" field)**

**API Endpoint:** `/documents/{id}/suggest-agency/`
- Method: POST
- Payload: `{city, state, defendant_name, title, description}`
- Returns: List of agency suggestions with confidence levels AND addresses

**Defendant model fields:**
- `agency_inferred` (BooleanField, default=False)
  - Set to True when agency comes from AI (story parsing or suggestion)
  - Cleared to False when user manually saves/edits the defendant OR accepts via verification modal
- `address_verified` (BooleanField, default=False)
  - Set to True when user confirms they verified the address is correct
  - Required before accepting an AI-suggested defendant

**Address Verification Requirement (IMPORTANT):**
When AI suggests defendants, users MUST verify the service address before accepting:

1. **Warning Display:** AI-suggested defendants show "you must verify the address before accepting"
2. **"Verify & Accept" Button:** Opens a verification modal (replaces simple "Accept" button)
3. **Verification Modal includes:**
   - Warning about proper service requirements
   - Current address displayed prominently
   - Instructions to use "Find Agency & Address" to search
   - **REQUIRED checkbox:** "I confirm that I have verified the address is correct for serving legal documents to this defendant."
   - Accept button is DISABLED until checkbox is checked
4. **On Accept:** Both `agency_inferred=False` and `address_verified=True` are set

**Edit Defendant Page:**
- Shows red alert banner: "Address Verification Required" for AI-suggested defendants
- Step-by-step instructions to verify address
- "Find Agency & Address" button to search for agency and official address

**Document Detail Warning:**
When defendants have `agency_inferred=True`, the Government Defendants section card shows:
- Blue info alert: "AI-Suggested Agencies: X defendants have AI-inferred agencies that should be reviewed for accuracy."

**Editing Existing Defendants:**
- Defendants list shows "Edit" button for each defendant
- Shows AI-suggested warning badge for defendants with agency_inferred=True
- Displays the agency name inline for each defendant
- Edit page at `/documents/{id}/defendant/{defendant_id}/edit/`
- Edit page has Save/Cancel and **Find Agency & Address** buttons

**Find Agency & Address Feature (Enhanced - Web Search):**
- "Find Agency & Address" button on edit defendant page
- Uses OpenAI web search to find official agency headquarters address
- **NEW:** If agency name is missing for individual officers, AI identifies the likely agency based on:
  - Officer's title/rank (e.g., "Deputy" → County Sheriff, "Trooper" → State Highway Patrol)
  - Incident location (city/state from Incident Overview)
  - Officer description
- Shows results with separate "Use" buttons for agency and address
- "Use All Information" button to apply both at once
- AI-suggested agencies show warning badge
- API endpoint: `/documents/{id}/lookup-address/`

**Files involved:**
- `documents/services/openai_service.py` - `suggest_agency()`, `lookup_agency_address()`, and `_identify_agency_for_officer()` methods
- `documents/views.py` - `suggest_agency`, `edit_defendant`, `lookup_address`, and `accept_defendant_agency` view endpoints
- `documents/urls.py` - Routes for suggest-agency, edit-defendant, lookup-address, and accept-defendant-agency
- `templates/documents/section_edit.html` - Verification modal with checkbox for AI-suggested defendants
- `templates/documents/edit_defendant.html` - Edit defendant form with Find Agency & Address button and verification warning
- `templates/documents/document_detail.html` - Warning for defendants needing review
- `documents/forms.py` - DefendantForm clears agency_inferred on save
- `documents/models.py` - Defendant.agency_inferred and address_verified fields
- `documents/migrations/0013_defendant_agency_inferred.py` - Migration for agency_inferred field
- `documents/migrations/0017_defendant_address_verified.py` - Migration for address_verified field
- `documents/prompts/identify_officer_agency.md` - Backup of agency identification prompt
- `documents/management/commands/seed_ai_prompts.py` - Seeds `identify_officer_agency` prompt to database

### Evidence Categorization Feature (NEW)
The Evidence section AI suggestion now **separates evidence into two categories** to prevent users from adding evidence they don't actually have.

**Two Categories:**
1. **Evidence You Have** (green section with "Add" buttons)
   - ONLY includes evidence explicitly mentioned as in user's possession
   - User must have stated "I recorded...", "I have photos...", etc.
   - These can be added to the case with one click

2. **Evidence to Obtain** (blue/gray informational section, NO add buttons)
   - Evidence that likely exists but user needs to request
   - Body camera footage, police reports, 911 recordings, surveillance footage
   - Shows how to obtain each item (FOIA, subpoena, etc.)
   - Informational only - cannot be added until user actually obtains it

**Why This Matters:**
- Legal documents should only list evidence the plaintiff actually possesses
- Prevents users from accidentally claiming they have evidence they don't
- Still provides helpful guidance on what evidence to pursue

**Files involved:**
- `documents/management/commands/seed_ai_prompts.py` - Updated `suggest_evidence` prompt
- `documents/prompts/suggest_evidence.md` - Backup of the prompt
- `templates/documents/section_edit.html` - JavaScript to render two sections

### Evidence Auto-Extraction from Story (NEW)
Evidence is now **automatically extracted** with full details during "Tell Your Story" parsing.

**Fields Extracted:**
| Field | Description |
|-------|-------------|
| `evidence_type` | video, audio, photo, document, body_cam, dash_cam, surveillance, other |
| `title` | Brief title like "My cell phone recording" |
| `description` | What the evidence shows |
| `date_created` | Uses incident date if captured during incident |
| `is_in_possession` | True for user's recordings, false for body cam/dash cam |
| `needs_subpoena` | True for police-held evidence |
| `notes` | Additional details |

**How It Works:**
1. User tells their story mentioning evidence (e.g., "I was recording on my phone")
2. AI extracts evidence with all fields populated
3. Evidence records are auto-created in database
4. Users can edit any evidence to refine details (add AM/PM to times, correct dates, etc.)

**Files involved:**
- `documents/management/commands/seed_ai_prompts.py` - Updated `parse_story` prompt with evidence structure
- `documents/prompts/parse_story.md` - Backup of the prompt
- `documents/views.py` - `apply_story_fields` handles all evidence fields

**Note:** Requires `python manage.py seed_ai_prompts` after deploying.

### Edit Evidence Feature (NEW)
Evidence items now have Edit buttons for refining details after auto-extraction.

**Features:**
- Edit button on each evidence item in the list
- Edit page at `/documents/{id}/evidence/{evidence_id}/edit/`
- Form sections: Evidence Details, When & Where, Status, Notes
- Works for both server-rendered and dynamically added items
- **"Use Incident Location" button** - When editing evidence, shows button to auto-fill location from incident overview

**Files involved:**
- `documents/views.py` - `edit_evidence` view (passes incident_location to template)
- `documents/urls.py` - Route for edit_evidence
- `templates/documents/edit_evidence.html` - Edit form template with "Use Incident Location" button
- `templates/documents/section_edit.html` - Edit button in list

### Evidence Location Defaults (NEW)
Evidence location (`location_obtained`) now defaults to the incident location for evidence in possession.

**When Location is Auto-Filled:**
1. **Story Parsing** - When AI extracts evidence from "Tell Your Story", evidence items marked as `is_in_possession=True` with no explicit location get the incident location
2. **Manual Adding** - When adding evidence via section edit page, if `is_in_possession=True` and location is blank, defaults to incident location
3. **Editing** - "Use Incident Location" button allows one-click filling of the incident location

**Location Format:**
Combines available fields from Incident Overview: `incident_location, city, state`
Example: "Downtown parking lot, Tampa, FL"

**Why This Matters:**
- Evidence captured during the incident (personal recordings) logically happened at the incident location
- Saves user time and ensures consistency
- Location remains editable for evidence obtained elsewhere

**Files involved:**
- `documents/views.py` - `apply_story_fields` and `add_multiple_item` views

### Duplicate Filtering for AI Suggestions (NEW)
AI suggestions now filter out items that already exist in the user's list.

**Sections with duplicate filtering:**
- **Evidence** - Word-based matching (>70% of significant words must match)
- **Witnesses** - Name matching (partial match detection)
- **Damages** - Form field content detection

**Features:**
- Items already in list are not shown in suggestions
- Items added during session are tracked to prevent re-adding
- Shows "All suggested items already added" when everything filtered
- Prevents exact duplicates and near-duplicates

**Damage Auto-Fill:**
- "Use" buttons on damage suggestions auto-fill form fields
- Auto-checks corresponding checkbox (emotional distress, property damage, etc.)
- Appends content if field already has text
- Highlights filled field and scrolls to it

**Files involved:**
- `templates/documents/section_edit.html` - `suggestionExists()`, `getExistingItems()`, `useDamageSuggestion()` functions

### Dynamic List Updates (NEW)
When adding items from AI suggestions, items appear immediately at the top of the list without page refresh.

**Features:**
- List container always rendered (hidden when empty, shown when items added)
- New items have "Just Added" badge and green highlight
- Auto-scroll to show newly added item
- Edit and Delete buttons work immediately
- Counter in header updates automatically

**Fixed Issue:** Previously items wouldn't appear if the list was initially empty because the container didn't exist in the DOM.

**Files involved:**
- `templates/documents/section_edit.html` - Container always rendered with `d-none` class when empty, `addItemToList()` function
- `documents/views.py` - `add_multiple_item` returns JSON with item_id for AJAX requests

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
# Note: Subscription models added - run migrations for accounts and documents
docker-compose exec web python manage.py makemigrations accounts documents
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
│   ├── models.py       # Custom User model, Subscription, DocumentPack, SubscriptionReferral
│   ├── views.py        # Login, register, profile, pricing, subscription views
│   ├── urls.py         # Auth + subscription URLs
│   ├── admin.py        # User, Subscription, DocumentPack, SubscriptionReferral admin
│   └── forms.py        # Auth forms, ProfileEditForm, ProfileCompleteForm
│
├── common/             # Shared utilities across apps
│   └── constants.py    # US_STATES list and other shared constants
│
├── documents/          # Main document builder app
│   ├── models.py       # Document, Section, PlaintiffInfo, etc.
│   ├── views.py        # Section edit, preview, AJAX endpoints, auto-apply logic
│   ├── forms.py        # All section forms + PlaintiffAttorneyForm
│   ├── help_content.py # Tooltips and help text for each field
│   ├── test_stories.py # 20 sample stories for testing AI
│   ├── urls.py         # URL routing
│   └── services/
│       ├── court_lookup_service.py
│       ├── openai_service.py  # AI integration
│       └── document_generator.py  # Legal document generation
│
├── templates/
│   ├── base.html
│   ├── accounts/
│   │   ├── profile.html
│   │   ├── profile_edit.html
│   │   ├── profile_complete.html  # Profile completion page
│   │   ├── pricing.html           # Pricing page (subscriptions + one-time)
│   │   └── subscription_manage.html  # Subscription management
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
├── config/
│   ├── settings.py     # Django settings with pricing config
│   ├── urls.py         # Main URL routing
│   └── sitemaps.py     # XML sitemap definitions
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
| Evidence | Videos, documents, etc. (multiple) - with auto-extraction from story |
| Damages | Physical, emotional, financial harm |
| PriorComplaints | Previous complaints filed |
| ReliefSought | What the plaintiff wants (money, declaration, etc.) |

---

## Legal Document Preview (Template-Based)

### Overview
The document preview displays saved data formatted as a professional Section 1983 federal complaint using Django templates - no AI generation required at preview time.

### How It Works
1. User fills out document sections (plaintiff info, narrative, rights violated, etc.)
2. User visits Preview page (`/documents/{id}/preview/`)
3. Django template formats saved database data as a legal complaint:
   - Proper caption (court name, parties, case number placeholder)
   - Jurisdiction and venue statement
   - Parties section identifying all plaintiffs and defendants
   - Statement of facts using saved narrative and damages
   - Causes of action for each selected amendment
   - Prayer for relief based on relief_sought selections
   - Jury demand (if requested)
   - Signature block (pro se or attorney)

### Key Features
- **Instant Loading** - No AI API calls, just database reads and template rendering
- **Third Person** - "Plaintiff" not "I"
- **Numbered Paragraphs** - Following federal court conventions
- **Print-Ready** - Document formatted for court filing
- **Proper Caption Format** - Includes:
  - Individual defendants with title and agency
  - "individually and in official capacity" language
  - Proper formatting for government entities
- **Amendment-Specific Causes of Action** - Each cause of action includes:
  - List of specific violations (e.g., "Conducting an unreasonable search")
  - Details from rights_violated explanations (shown in italic detail box)
  - Proper legal language for that amendment
- **Dynamic Paragraph Numbering** - Adjusts based on number of defendants and facts

### Files
- `documents/views.py` - `document_preview` view and `_collect_document_data` helper
- `templates/documents/document_preview.html` - Legal document display template (Django template logic)

### Requirements for Display
Document must have:
- Plaintiff name (first and last)
- Incident narrative (from story or detailed_narrative)
- At least one constitutional right selected as violated

If requirements not met, shows "More Information Needed" with links to complete sections.

### URL
- `/documents/{id}/preview/` - View formatted legal document

### Note on Caching Fields
The Document model still has `generated_complaint` and `generated_at` fields from a previous AI-caching implementation. These are no longer used for preview (template-based now) but remain for potential future use in PDF generation.

---

## Payment System (ENHANCED)

### Overview
Hybrid pricing model with both pay-per-document purchases and subscription plans. Stripe integration for all payments, promo/referral codes, and document lifecycle management.

### Pricing - One-Time Purchases
| Item | Price | AI Budget |
|------|-------|-----------|
| Single Document | $49.00 | $5 per document |
| 3-Document Pack | $99.00 ($33/each) | $5 per document |
| With promo code | 25% off | Same |

### Pricing - Subscriptions
| Plan | Price | AI Uses | Benefits |
|------|-------|---------|----------|
| Monthly Pro | $29/month | 50/month | Unlimited documents |
| Annual Pro | $249/year (~$20.75/mo) | Unlimited | Save $99 + 2 months free |

### Referral Payouts (by purchase type)
| Purchase Type | Referral Payout |
|---------------|-----------------|
| Single Document | $10.00 |
| 3-Document Pack | $15.00 |
| Monthly Subscription | $10.00 (first payment only) |
| Annual Subscription | $40.00 (first payment only) |

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

### Edit Lock for Finalized/Expired Documents
Views check `document.can_edit()` before allowing edits:
- `section_edit` - Redirects with message if document is finalized or expired
- `tell_your_story` - Redirects with message if document is finalized or expired
- `document_review` - Redirects finalized documents to `document_preview` (read-only)
- `document_preview` - Renders preview for finalized documents, redirects others to review
- `document_detail.html` - Hides Review & Edit button for finalized documents
- `document_preview.html` - Hides Review & Edit button for finalized documents

### Generate PDF Button (Payment-Aware)
The Generate PDF button on document detail page adapts based on payment status:
| Status | Button Text | Action |
|--------|-------------|--------|
| draft/expired (100% complete) | "Pay & Generate PDF" | Goes to checkout |
| draft/expired (incomplete) | "Generate PDF" (disabled) | Shows "Complete all sections first" |
| paid (100% complete) | "Finalize & Generate PDF" | Goes to finalize page |
| paid (incomplete) | "Generate PDF" (disabled) | Shows "Complete all sections first" |
| finalized | "Download PDF" | Downloads PDF directly |

### Key Features
1. **User-Level AI Tracking** - Free AI uses tracked across ALL user documents (prevents abuse)
2. **AI Limit Enforcement** - All 7 AI endpoints check limits BEFORE making API calls and record usage AFTER success
3. **Dynamic AI Usage Banner** - Status banner updates in real-time after each AI call (no page refresh needed)
4. **Admin Unlimited Access** - `is_staff` or `is_superuser` users bypass all limits
5. **Promo Codes** - Users create their own referral code, earn $15 per use
6. **Stripe Checkout** - Secure payment with promo code validation
7. **Document Finalization** - Confirmation required before locking document
8. **Status Banner** - Shows time remaining, AI usage, and action buttons on all document pages
9. **Checkout When AI Exhausted** - Users who hit AI limit can still proceed to checkout (bypasses section completion validation)

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
| **Subscription** | User subscription (monthly/annual) with Stripe sync |
| **DocumentPack** | One-time document pack purchases |
| **SubscriptionReferral** | Tracks referral earnings from subscriptions |

### Subscription Model Fields
| Field | Purpose |
|-------|---------|
| user | OneToOne link to User |
| plan | 'monthly' or 'annual' |
| status | 'active', 'past_due', 'canceled', 'incomplete', 'incomplete_expired' |
| stripe_subscription_id | Stripe subscription ID |
| stripe_customer_id | Stripe customer ID |
| current_period_start | Billing period start |
| current_period_end | Billing period end |
| cancel_at_period_end | Whether scheduled to cancel |
| ai_uses_this_period | Monthly AI usage counter |
| ai_period_reset_at | When AI uses reset (monthly) |
| promo_code_used | FK to PromoCode (for referral tracking) |

### DocumentPack Model Fields
| Field | Purpose |
|-------|---------|
| user | FK to User |
| pack_type | 'single' or '3pack' |
| documents_included | Number of docs in pack |
| documents_used | How many used |
| amount_paid | Price paid |
| stripe_payment_id | Stripe Payment Intent ID |
| ai_budget_per_document | $5 per document |

### SubscriptionReferral Model Fields
| Field | Purpose |
|-------|---------|
| promo_code | FK to PromoCode |
| subscription | FK to Subscription |
| subscriber | FK to User |
| plan_type | 'monthly' or 'annual' |
| first_payment_amount | Amount of first payment |
| referral_amount | Payout amount for this referral |
| payout_status | 'pending' or 'paid' |
| payout_date | When paid out |
| payout_reference | Payment reference number |

### User Model Additions
- `has_unlimited_access()` - Check if admin/staff
- `get_total_free_ai_uses()` - AI uses across all documents
- `can_use_free_ai()` - Check user-level AI limit
- `get_free_ai_remaining()` - Remaining free AI count
- `get_total_referral_earnings()` - Total earnings from all codes
- `get_pending_referral_earnings()` - Pending (unpaid) earnings
- `get_paid_referral_earnings()` - Already paid earnings

### AI Limit Enforcement (IMPORTANT)
All 7 AI endpoints now enforce limits BEFORE making OpenAI API calls:

| Endpoint | URL | Feature |
|----------|-----|---------|
| `parse_story` | `/documents/{id}/parse-story/` | Tell Your Story analysis |
| `analyze_rights` | `/documents/{id}/analyze-rights/` | Rights Violated analysis |
| `suggest_section_content` | `/documents/{id}/suggest-section-content/` | Damages/Evidence/Witnesses suggestions |
| `ai_review_document` | `/documents/{id}/ai-review/` | Document review |
| `generate_fix` | `/documents/{id}/generate-fix/` | Generate AI fix for issues |
| `suggest_agency` | `/documents/{id}/suggest-agency/` | Suggest agency for defendants |
| `lookup_address` | `/documents/{id}/lookup-address/` | Lookup agency address |

**How It Works:**
1. Each endpoint calls `document.can_use_ai()` BEFORE making any API calls
2. If limit reached, returns `{success: false, limit_reached: true, error: "...upgrade message..."}`
3. Frontend shows upgrade prompt with button linking to checkout
4. On success, endpoint calls `document.record_ai_usage()` to increment counter
5. Response includes `ai_usage_display` for dynamic banner update

**JavaScript Updates:**
- All JS files have `showLimitReachedError()` function with upgrade button
- All JS files have `updateAIUsageBanner()` function to update status banner
- Banner updates without page refresh after each AI call

**Files Modified:**
- `documents/views.py` - Added limit checks to all 7 endpoints + `get_ai_usage_info()` helper
- `static/js/tell-story.js` - Added limit handling and banner update
- `static/js/rights-analyze.js` - Added limit handling and banner update
- `templates/documents/section_edit.html` - Added limit handling and banner update
- `templates/documents/document_review.html` - Added limit handling and banner update
- `templates/documents/edit_defendant.html` - Added limit handling
- `templates/documents/partials/status_banner.html` - Added `id="aiUsageDisplay"` for JS targeting

**Testing AI Limits:**
```python
# In Django shell - reset a user's AI usage
from accounts.models import User
u = User.objects.get(email='user@email.com')
for doc in u.documents.filter(payment_status='draft'):
    doc.ai_generations_used = 0
    doc.save()
```

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

### URLs (Subscriptions)
- `/accounts/pricing/` - Pricing page (subscriptions + one-time)
- `/accounts/subscribe/<plan>/` - Start subscription checkout (monthly/annual)
- `/accounts/subscription/success/` - Subscription success handler
- `/accounts/subscription/manage/` - Manage/cancel subscription
- `/accounts/subscription/webhook/` - Stripe subscription webhook

### Admin Features
- View all documents with payment status
- PromoCode admin with usage stats
- PromoCodeUsage admin with payout tracking
- PayoutRequest admin for processing payouts
- Bulk action: "Mark as paid" for referral payouts
- Custom admin referral dashboard at `/documents/admin/referrals/`
- **Subscription admin** with plan, status, AI usage, Stripe IDs
- **DocumentPack admin** with documents remaining count
- **SubscriptionReferral admin** with bulk "Mark as paid" action

### Environment Variables
```env
STRIPE_PUBLIC_KEY=pk_test_xxx
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx  # Optional for local testing

# Stripe Price IDs (from Stripe Dashboard → Products)
STRIPE_PRICE_SINGLE=price_xxx    # Single document ($49)
STRIPE_PRICE_3PACK=price_xxx     # 3-document pack ($99)
STRIPE_PRICE_MONTHLY=price_xxx   # Monthly subscription ($29/mo)
STRIPE_PRICE_ANNUAL=price_xxx    # Annual subscription ($249/yr)
```

### Settings (config/settings.py)
```python
# One-Time Purchases
DOCUMENT_PRICE_SINGLE = 49.00
DOCUMENT_PRICE_3PACK = 99.00

# Subscriptions
SUBSCRIPTION_PRICE_MONTHLY = 29.00
SUBSCRIPTION_PRICE_ANNUAL = 249.00
SUBSCRIPTION_MONTHLY_AI_USES = 50
SUBSCRIPTION_ANNUAL_AI_USES = 999999  # Effectively unlimited

# Referral Payouts (by type)
REFERRAL_PAYOUT_SINGLE = 10.00
REFERRAL_PAYOUT_3PACK = 15.00
REFERRAL_PAYOUT_MONTHLY = 10.00
REFERRAL_PAYOUT_ANNUAL = 40.00

# Other settings
PROMO_DISCOUNT_PERCENT = 25
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
- `templates/accounts/pricing.html` - Pricing page (subscriptions + one-time)
- `templates/accounts/subscription_manage.html` - Subscription management

### Checkout Flow (One-Time Purchase)
1. User clicks "Upgrade Now" in status banner
2. Enter promo code OR check "I confirm I do not have a promo code"
3. Redirected to Stripe Checkout
4. On success → document marked as `paid`
5. User has 45 days to edit and use AI ($5 budget)
6. User clicks "Finalize & Download PDF"
7. Confirmation modal with checkbox
8. Document marked as `finalized`, PDF available (no watermark)

### Subscription Flow
1. User visits `/accounts/pricing/`
2. Selects Monthly Pro ($29/mo) or Annual Pro ($249/yr)
3. Can enter promo code during checkout (25% off first payment)
4. Redirected to Stripe Checkout (subscription mode)
5. On success → Subscription created in database
6. User has unlimited documents while subscription is active
7. AI usage tracked per billing period (50/mo for monthly, unlimited for annual)
8. User can manage/cancel at `/accounts/subscription/manage/`

### Subscription Management
**Active subscribers can:**
- View current plan and billing date
- See AI usage for current period
- Cancel subscription (access continues until period end)
- Reactivate if cancellation pending

**Subscription states:**
| Status | Meaning |
|--------|---------|
| active | Subscription is current and paid |
| past_due | Payment failed, awaiting retry |
| canceled | Subscription ended |
| incomplete | Initial payment pending |

**AI Usage Reset:**
- Monthly plans: AI counter resets at `current_period_start`
- Annual plans: Unlimited AI (no tracking needed)

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

### Migration Best Practices (IMPORTANT)
**Migrations should be committed to git, NOT auto-generated in production.**

The `build.sh` script previously ran `makemigrations` on every deploy, which caused ghost migrations and database inconsistencies. This has been fixed - `build.sh` now only runs `migrate`.

**If you get migration conflicts:**
1. Never run `makemigrations` on production
2. Create migrations locally, test them, commit them
3. If ghost migrations exist in the database, use `--fake` to skip them:
   ```bash
   python manage.py migrate documents 0001 --fake
   python manage.py migrate
   ```

### Squashed Migrations (January 2026)
All migrations have been squashed into single `0001_initial.py` files for both `accounts` and `documents` apps. This eliminates all previous migration conflicts and ghost migrations.

**Current migration files:**
- `accounts/migrations/0001_initial.py` - All accounts models
- `documents/migrations/0001_initial.py` - All documents models

**If setting up a new server or resetting migrations:**
```bash
# Clear migration history
python manage.py migrate accounts zero --fake
python manage.py migrate documents zero --fake

# Apply new initial migrations (tables already exist)
python manage.py migrate --fake-initial

# Verify
python manage.py showmigrations
```

**Files involved:**
- `build.sh` - Only runs `migrate`, NOT `makemigrations`
- `documents/migrations/0001_initial.py` - Single squashed migration
- `accounts/migrations/0001_initial.py` - Single squashed migration

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

**Document Checkout Webhook:**
1. Go to https://dashboard.stripe.com/webhooks
2. Click "Add endpoint"
3. URL: `https://one983-law.onrender.com/documents/webhook/stripe/`
4. Select event: `checkout.session.completed`
5. Copy signing secret → Add as `STRIPE_WEBHOOK_SECRET` on Render

**Subscription Webhook (NEW):**
1. Add another endpoint for subscriptions
2. URL: `https://one983-law.onrender.com/accounts/subscription/webhook/`
3. Select events:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
4. Use same `STRIPE_WEBHOOK_SECRET` or create separate one

---

## Legal Pages & Compliance

### Overview
The app includes comprehensive legal pages (Terms of Service, Privacy Policy, Legal Disclaimer, Cookie Policy) with:
- Dynamic company info from database settings
- Rich text editing via CKEditor in admin
- Registration requires agreeing to Terms and Privacy Policy

### Legal Page URLs
| URL | Document |
|-----|----------|
| `/legal/terms/` | Terms of Service |
| `/legal/privacy/` | Privacy Policy |
| `/legal/disclaimer/` | Legal Disclaimer |
| `/legal/cookies/` | Cookie Policy |

### Site Settings (Admin Editable)
Located at `/admin/accounts/sitesettings/`:

| Setting | Default | Purpose |
|---------|---------|---------|
| company_name | 1983law.org | Legal company/org name |
| company_type | (blank) | LLC, Non-Profit, etc. |
| company_state | New York | State of incorporation |
| company_address | (blank) | Physical address (CAN-SPAM) |
| contact_email | contact@1983law.org | Privacy/legal inquiries |
| website_url | https://www.1983law.org | Primary website |
| minimum_age | 18 | Age requirement |
| governing_law_state | New York | TOS governing law |
| has_attorneys | False | Toggle if attorneys involved |
| attorney_states | (blank) | States where licensed |
| payment_processor | Stripe | Payment processor name |
| refund_policy_days | 0 | Days for refunds (0=no refunds) |
| uses_google_analytics | True | For Privacy Policy disclosure |
| uses_openai | True | For Privacy Policy disclosure |
| hosting_provider | Render | Hosting provider name |
| terms_effective_date | (blank) | TOS effective date |
| privacy_effective_date | (blank) | Privacy effective date |
| footer_address | 123 Liberty Avenue... | Address for footer (fake default) |
| footer_phone | 585-204-7416 | Phone for footer |
| footer_email | info@1983law.org | Email for footer |
| show_footer_contact | True | Master toggle for contact section |
| show_footer_address | False | Toggle for address display |
| show_footer_phone | True | Toggle for phone display |
| show_footer_email | True | Toggle for email display |

### Footer Contact Information (NEW)
The website footer displays contact information with individual show/hide toggles.

**Features:**
- Master toggle (`show_footer_contact`) to show/hide entire contact section
- Individual toggles for address, phone, and email
- Address hidden by default (fake placeholder address)
- Phone and email visible by default
- Icons for each contact type (geo-alt, telephone, envelope)
- Clickable phone (tel:) and email (mailto:) links

**Admin Location:** `/admin/accounts/sitesettings/` → "Footer Contact Information" fieldset

**Files:**
- `accounts/models.py` - SiteSettings model with footer fields
- `accounts/admin.py` - Admin fieldset for footer contact
- `config/context_processors.py` - Makes site_settings available in templates
- `templates/base.html` - Footer display with conditional rendering
- `accounts/migrations/0002_footer_contact_info.py` - Migration

### Legal Documents (Full Content Editing)
Located at `/admin/accounts/legaldocument/`:

- Each document type (terms, privacy, disclaimer, cookies) can have fully customized content
- Rich text editor (CKEditor) with:
  - Bold, italic, underline, strikethrough
  - Numbered and bullet lists
  - Headers (H2-H6)
  - Links and tables
  - Pre-built styles: Alert boxes (warning, info, danger), Cards
- If no database document exists, falls back to template version
- Templates still use dynamic company info from SiteSettings

### Registration Agreement
Users must check two required checkboxes during registration:
1. "I agree to the Terms of Service" (links to `/legal/terms/`)
2. "I agree to the Privacy Policy" (links to `/legal/privacy/`)

Both are required to create an account.

### Terms Agreement Tracking (NEW)
Admin can see which users agreed to terms and when.

**User Model Fields:**
| Field | Purpose |
|-------|---------|
| `agreed_to_terms` | Boolean - did user agree to Terms of Service |
| `agreed_to_privacy` | Boolean - did user agree to Privacy Policy |
| `terms_agreed_at` | Timestamp when user agreed |
| `terms_agreed_ip` | IP address when terms were agreed (for audit) |

**Admin View:**
- User list shows "Agreed to terms" and "Terms agreed at" columns
- Filter users by "Agreed to terms" and "Agreed to privacy"
- User detail page has "Terms Agreement" section (read-only timestamp/IP)

**Migration:** `accounts/migrations/0007_user_terms_agreement.py`

### Footer Links
All pages include footer links to:
- Terms of Service
- Privacy Policy
- Legal Disclaimer
- Cookie Policy

### Database Models
| Model | Location | Purpose |
|-------|----------|---------|
| SiteSettings | accounts/models.py | Singleton for company info (one instance) |
| LegalDocument | accounts/models.py | Editable legal document content |

### Key Files
- `accounts/models.py` - SiteSettings and LegalDocument models
- `accounts/views.py` - Legal page views with fallback logic
- `accounts/legal_urls.py` - Legal URL routes
- `accounts/admin.py` - Admin config with CKEditor
- `accounts/forms.py` - Registration form with agreement checkboxes
- `templates/legal/terms.html` - Default Terms template
- `templates/legal/privacy.html` - Default Privacy template
- `templates/legal/disclaimer.html` - Default Disclaimer template
- `templates/legal/cookies.html` - Default Cookie Policy template
- `templates/legal/document_base.html` - Database content renderer
- `templates/accounts/register.html` - Registration with checkboxes
- `templates/base.html` - Footer with legal links
- `config/settings.py` - CKEditor configuration
- `requirements.txt` - django-ckeditor>=6.5

### Adding Attorney Information Later
When attorneys become involved:
1. Go to `/admin/accounts/sitesettings/`
2. Check "Has attorneys"
3. Enter states in "Attorney states" (comma-separated)
4. Legal Disclaimer automatically shows attorney information

---

## Public Pages & Landing Page (NEW)

### Overview
The app now has a public-facing landing page with civil rights information, American flag themed design, and SEO optimization.

### Color Scheme (American Flag Theme)
| Color | Hex | Usage |
|-------|-----|-------|
| Patriot Blue | `#002868` | Primary - headers, buttons, links |
| Patriot Red | `#BF0A30` | Accent - CTAs, alerts, emphasis |
| White | `#FFFFFF` | Backgrounds |
| Cream | `#F8F9FA` | Alternate section backgrounds |
| Light Blue | `#E8EEF5` | Card backgrounds, highlights |

### Landing Page Sections
1. **Hero** - "Know Your Rights. Protect Your Freedom." with CTAs
2. **Stats Bar** - 42 U.S.C., 1871, 150+ years, "You Have Rights"
3. **Know Your Rights** - 4 amendment cards (1st, 4th, 5th, 14th)
4. **Featured Articles** - 4 article cards (from CMS)
5. **News Widget** - 5 sample items (placeholder for News API)
6. **Resources** - Links to ACLU, EFF, Flex Your Rights, Cornell Law
7. **What is Section 1983** - Educational explainer
8. **CTA Section** - Red banner with action button

### User Routing
- **Anonymous users**: See landing page with civil rights info
- **Authenticated users**: Automatically redirected to `/documents/` (document list)

### Animated American Flag (Footer)
The footer includes a subtle animated American flag with waving effect.

**Features:**
- SVG flag with accurate stars and stripes
- CSS animation creates waving motion
- Shine/ripple effect overlay
- Speeds up on hover
- Text: "Protecting American Freedoms"

**CSS Classes:**
- `.flag-container` - Contains the SVG flag
- `.footer-flag` - Wrapper with text
- `@keyframes flag-wave` - Waving animation
- `@keyframes flag-shine` - Shine overlay effect

**Files:**
- `templates/base.html` - SVG flag markup in footer
- `static/css/app-theme.css` - Animation CSS (lines 429-505)

### Files
| File | Purpose |
|------|---------|
| `public_pages/__init__.py` | App init |
| `public_pages/apps.py` | App config |
| `public_pages/views.py` | Landing page view with redirect logic |
| `public_pages/urls.py` | URL routing (name='home') |
| `public_pages/models.py` | CMS models (CivilRightsPage, PageSection) |
| `public_pages/admin.py` | Admin config for CMS |
| `static/css/public-pages.css` | Landing page specific styles |
| `static/css/app-theme.css` | App-wide patriot theme + flag animation |
| `templates/public_pages/landing.html` | Landing page template |
| `templates/public_pages/cms_page.html` | CMS page template |

---

## Section-Based CMS (NEW)

### Overview
A flexible CMS system for creating civil rights content pages with multiple section types.

### CivilRightsPage Model
Each page has:
| Field | Purpose |
|-------|---------|
| `title` | Page title |
| `slug` | URL slug (unique) |
| `hero_title` | Override title for hero section |
| `hero_subtitle` | Subtitle in hero |
| `meta_description` | SEO description (max 160 chars) |
| `meta_keywords` | SEO keywords (comma-separated) |
| `is_published` | Show/hide page |
| `is_featured` | Show on homepage |
| `order` | Sort order |
| `show_in_nav` | Include in navigation |
| `nav_title` | Short nav title |
| `category` | rights, legal, action, resources, auditors |
| `icon` | Bootstrap icon class |

### PageSection Model
Each page can have multiple sections:

**Section Types:**
| Type | Description |
|------|-------------|
| `hero` | Hero section with title, subtitle, CTAs |
| `content` | Rich text content (CKEditor) |
| `cards` | Card grid layout |
| `rights_cards` | Cards with amendment badge |
| `article_cards` | Cards with category badge |
| `quote` | Blockquote with source |
| `cta` | Call to action banner |
| `resources` | Resource links list |
| `stats` | Statistics row |
| `two_column` | Two column layout |
| `checklist` | Do/Don't checklist |
| `alert` | Notice/alert box |
| `accordion` | FAQ accordion |

**Common Section Fields:**
- `title`, `subtitle` - Section headings
- `content` - Rich text (CKEditor)
- `content_secondary` - For two-column layouts
- `data` - JSON for structured content (cards, resources, etc.)
- `background` - light, cream, blue, dark
- `css_class` - Additional CSS classes
- `cta_text`, `cta_url`, `cta_icon` - CTA button
- `order`, `is_visible` - Display control

### Admin Interface
- **Page list:** Shows published status, category, featured
- **Inline sections:** Add/edit sections directly on page edit
- **Rich text editor:** CKEditor for content fields
- **JSON editor:** For structured data (cards, resources)

### URLs
| URL | Purpose |
|-----|---------|
| `/rights/<slug>/` | View CMS page |
| `/admin/public_pages/civilrightspage/` | Manage pages |

### Pre-built Content Pages
The following pages are created with comprehensive content:

1. **First Amendment** (`/rights/first-amendment/`)
   - Right to record police
   - Free speech, press, assembly protections
   - Real case examples

2. **Fourth Amendment** (`/rights/fourth-amendment/`)
   - Unreasonable search and seizure
   - Warrant requirements
   - Stop and frisk rules

3. **Fifth Amendment** (`/rights/fifth-amendment/`)
   - Right to remain silent
   - Miranda rights
   - Self-incrimination protection

4. **Fourteenth Amendment** (`/rights/fourteenth-amendment/`)
   - Due process
   - Equal protection
   - Incorporation doctrine

### Migration Required
After pulling code, create and run migrations:
```bash
docker-compose exec web python manage.py makemigrations public_pages
docker-compose exec web python manage.py migrate
```

### Future: News API Integration
The landing page has placeholder news items. Planned additions:
- NewsAPI.org integration for civil rights news
- NewsItem model for caching
- Management command for daily fetch

---

## App-Wide Theme & Navbar (NEW)

### Navbar Features
- **Gradient background**: Navy blue gradient
- **Brand icon**: Shield with check in white box
- **User avatar**: Circle with first initial
- **Pill-shaped buttons**: Login (outline), Get Started (red)
- **Authenticated nav**: My Documents, New Case links
- **User dropdown**: Email display, organized sections, admin links
- **Mobile-responsive**: Collapsible with proper styling

### Footer Features
- **Multi-column layout**: About, Resources, Legal, Get Started
- **Gradient background**: Matching navbar
- **CTA button**: "Create Free Account" for anonymous users
- **Legal disclaimer**: Standard not-legal-advice notice

### CSS Files
| File | Purpose |
|------|---------|
| `static/css/app-theme.css` | App-wide theme (navbar, footer, buttons, cards, forms, dark theme) |
| `static/css/public-pages.css` | Landing page specific (hero, sections, widgets) |

---

## Hero Section Flag Background (NEW)

### Overview
The landing page hero section features a subtle transparent American flag positioned on the right side with a gradient overlay to ensure text readability.

### Features
- SVG American flag embedded as CSS background-image (data URI)
- Positioned on right side at 8% opacity
- Gradient overlay fades from solid blue on left to transparent on right
- Text remains fully readable against the gradient
- Responsive - flag scales with section

### CSS Implementation
Located in `static/css/public-pages.css`:

**`.hero-section::before`** - The flag background
- SVG data URI with stars and stripes
- 55% width, 120% height
- 8% opacity
- Positioned right side, vertically centered
- `z-index: 1`

**`.hero-section::after`** - Gradient overlay
- Linear gradient from solid patriot-blue to transparent
- Ensures left-side text is always readable
- `z-index: 2`

**`.hero-section .container`** - Content layer
- `position: relative`
- `z-index: 3` - Ensures text/buttons appear above overlays

### Z-Index Layering (Important!)
The hero section uses z-index layering to keep content visible:
```
z-index: 1  →  ::before (flag background)
z-index: 2  →  ::after (gradient overlay)
z-index: 3  →  .container (text, buttons)
```
Without this, the gradient overlay would fade the text and buttons.

---

## Dark Theme Toggle (NEW)

### Overview
A moon/sun toggle button in the navbar allows users to switch between light and dark modes. The preference is saved to localStorage and persists across visits.

### Features
- **Toggle button**: Moon icon (light mode) / Sun icon (dark mode)
- **localStorage persistence**: Saves preference as `1983law_theme`
- **System preference detection**: Auto-detects `prefers-color-scheme: dark`
- **Instant apply**: No flash of wrong theme on page load
- **System change listener**: Updates if user changes OS theme (unless manually set)

### Toggle Button Styling
- Circular button (38px) in navbar
- Semi-transparent background
- Rotates 15° on hover
- Located next to login buttons (for all users)

### Dark Theme Color Scheme
| Variable | Value | Usage |
|----------|-------|-------|
| `--dark-bg` | `#1a1a2e` | Main background |
| `--dark-bg-secondary` | `#16213e` | Cards, modals |
| `--dark-bg-card` | `#0f3460` | Headers, accents |
| `--dark-text` | `#e4e4e4` | Primary text |
| `--dark-text-muted` | `#a0a0a0` | Secondary text |
| `--dark-border` | `#2d3748` | Borders |

### Components Styled for Dark Mode
- Navbar & footer (darker gradients)
- Cards, modals, accordions
- Forms (inputs, selects, labels)
- Tables (headers, rows, hover states)
- Alerts (info, success, warning, danger)
- Public page sections (rights cards, news widget, resources)
- Auth pages (login, register cards)
- Dropdowns, pagination, tooltips
- Code blocks, scrollbars

### Files
| File | Purpose |
|------|---------|
| `templates/base.html` | Toggle button HTML + JavaScript |
| `static/css/app-theme.css` | Theme toggle button + all dark theme styles |

### JavaScript (in base.html)
```javascript
// Key functions:
getPreferredTheme()  // Check localStorage or system preference
setTheme(theme)      // Apply theme + save to localStorage
updateIcon(theme)    // Switch moon/sun icon
toggleTheme()        // Switch between light/dark
```

### Testing Dark Mode
1. Click the moon icon in navbar to switch to dark mode
2. Icon changes to sun
3. Refresh page - dark mode persists
4. Clear localStorage or click sun to return to light mode

---

## Navbar Brand & Logo (NEW)

### Overview
The navbar features a custom judge's gavel logo with patriot gradient colors and serif font branding.

### Logo Design
- **Icon**: Judge's gavel with sound block (SVG)
- **Background**: Patriot gradient (blue → red → dark blue)
- **Gavel**: White silhouette on gradient
- **Shape**: Rounded square (4px radius)

### Brand Text
- **Font**: Playfair Display (Google Fonts) - law/legal style serif
- **Color**: White
- **Fallbacks**: Georgia, Times New Roman, serif

### Gradient Colors
```css
linearGradient (135° diagonal):
  0%   - #002868 (Patriot Blue)
  50%  - #BF0A30 (Patriot Red)
  100% - #001a4d (Dark Blue)
```

### Files
| File | Purpose |
|------|---------|
| `static/gavel-icon.svg` | 32x32 navbar logo icon |
| `static/gavel-logo.svg` | Full-size gavel logo (for other uses) |
| `static/favicon.svg` | Browser tab icon (same as gavel-icon) |
| `templates/base.html` | Navbar brand markup + Google Fonts link |
| `static/css/app-theme.css` | Brand icon and text styling |

### Gavel SVG Structure
The gavel SVG uses the original detailed court gavel paths:
- Gavel head with decorative grooves
- Handle with end knob
- Sound block (base)
- Scaled to fit 32x32 with `transform="translate(1, 0) scale(0.02)"`

### CSS Classes
```css
.navbar-brand .brand-icon      /* Container for gavel icon */
.navbar-brand .brand-icon img  /* The SVG image */
.navbar-brand .brand-text      /* "1983 Law" text with Playfair Display */
```

---

## SEO Optimization (NEW)

### Meta Tags (in base.html)
- `<title>` - Dynamic with blocks
- `<meta name="description">` - Customizable per page
- `<meta name="keywords">` - Customizable per page
- `<meta name="robots">` - index, follow
- `<link rel="canonical">` - Auto-generated from request URL

### Open Graph (Social Sharing)
- `og:type`, `og:title`, `og:description`, `og:site_name`, `og:image`
- All customizable via template blocks

### Twitter Cards
- `twitter:card`, `twitter:title`, `twitter:description`
- All customizable via template blocks

### Structured Data (JSON-LD)
- WebSite schema with search action
- Customizable via `{% block structured_data %}`

### Template Blocks for SEO
```django
{% block meta_description %}Custom description{% endblock %}
{% block meta_keywords %}custom, keywords{% endblock %}
{% block og_title %}Custom OG Title{% endblock %}
{% block og_description %}Custom OG description{% endblock %}
{% block structured_data %}<!-- Additional JSON-LD -->{% endblock %}
```

### XML Sitemap (ENHANCED)
An XML sitemap helps search engines discover and index all public pages.

**URLs:**
| URL | Purpose |
|-----|---------|
| `/sitemap.xml` | XML sitemap for search engines |
| `/robots.txt` | Crawler directives pointing to sitemap |

**What's Included:**
- Home page
- Pricing page (`/accounts/pricing/`)
- Legal pages (Terms, Privacy, Disclaimer, Cookies)
- Know Your Rights educational pages:
  - Know Your Rights landing
  - Right to Record
  - Section 1983
  - What to Do if Rights Violated
  - First Amendment Auditors
  - Fourth Amendment
  - Fifth Amendment
- CMS pages (CivilRightsPage with `is_published=True`)

**What's Excluded:**
- Admin URLs (dynamic path for security)
- User accounts/profile pages
- Document builder pages (require authentication)

**Files:**
- `config/sitemaps.py` - Sitemap definitions (StaticViewSitemap, KnowYourRightsSitemap, CivilRightsPageSitemap)
- `config/urls.py` - Sitemap URL configuration
- `public_pages/views.py` - robots.txt view
- `config/settings.py` - `django.contrib.sites` and `django.contrib.sitemaps` added

**After Deployment:**
Submit sitemap to Google Search Console:
1. Go to https://search.google.com/search-console
2. Add property for 1983law.org
3. Submit sitemap URL: `https://1983law.org/sitemap.xml`

---

## What's NOT Built Yet

- E-filing integration
- Video extraction
- **News API integration** (placeholder content on landing page)
- **CMS for article management** (planned)

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
Finalized documents can be downloaded as professionally formatted PDF files using WeasyPrint. PDF generation runs in the background with real-time progress updates.

### How It Works (Background Processing)
1. User finalizes their document (after payment)
2. "Download PDF" button appears on the preview page and status banner
3. User clicks button → Modal opens with progress indicator
4. Server starts background PDF generation thread (returns immediately)
5. Frontend polls status endpoint every 2 seconds
6. Modal shows progress stages:
   - "Collecting document data..."
   - "Generating legal document..."
   - "Creating PDF file..."
   - "PDF ready! Starting download..."
7. When complete, PDF auto-downloads and modal closes
8. On error, modal shows error message with "Try Again" button

### Why Background Processing?
PDF generation can take 10-30 seconds depending on document size. Background processing with polling:
- Prevents browser timeouts
- Keeps users informed of progress
- Allows retry on failure
- Same pattern used for story analysis

### Database Fields (Document model)
| Field | Purpose |
|-------|---------|
| `pdf_status` | idle/processing/completed/failed |
| `pdf_progress_stage` | Current stage for progress display |
| `pdf_error` | Error message if generation failed |
| `pdf_started_at` | Timestamp to detect stale jobs |
| `pdf_file_path` | Temp file path to generated PDF |

### PDF Formatting (Page Breaks)
CSS page-break controls prevent awkward formatting:
- **Section headers**: `page-break-after: avoid` - headers won't be orphaned at bottom of pages
- **Signature block**: `page-break-inside: avoid` - keeps signature together on one page
- **Paragraphs**: `orphans: 3; widows: 3` - minimum 3 lines at page breaks
- **Causes of action**: `page-break-inside: avoid` - tries to keep each cause together
- **Prayer for relief**: `page-break-inside: avoid` - keeps prayer section together

### Requirements
- Document must be in `finalized` status
- Document must have minimum required data (plaintiff name, narrative, rights violated)

### Files
- `templates/documents/document_pdf.html` - Print-optimized PDF template with page-break CSS
- `templates/documents/document_preview.html` - Download button
- `templates/documents/partials/status_banner.html` - Status banner with modal + JS for progress
- `documents/views.py` - `start_pdf_generation`, `pdf_generation_status`, `download_pdf` views
- `documents/migrations/0016_pdf_generation_status.py` - Migration for new fields

### URLs
| URL | Method | Purpose |
|-----|--------|---------|
| `/documents/{id}/generate-pdf/` | POST | Start background PDF generation |
| `/documents/{id}/generate-pdf/status/` | GET | Poll for generation status |
| `/documents/{id}/download-pdf/` | GET | Download the generated PDF file |

---

## Future Plans

### Speech-to-Text for Tell Your Story (Priority Feature)
The main mobile feature request is to allow users to record their story by speaking instead of typing.

**Planned Implementation:**
- Add a microphone button to the Tell Your Story textarea
- Use **Web Speech API** (browser built-in, free) - NOT OpenAI Whisper
- Real-time transcription as user speaks
- Works on Chrome, Edge, Safari (desktop + mobile)
- No server costs - all processing in browser

**Why Web Speech API:**
- Free (no API costs)
- Real-time (shows words as user speaks)
- Works on mobile browsers
- Good accuracy for conversational speech
- Privacy - audio processed locally

**Files to modify:**
- `static/js/tell-story.js` - Add speech recognition logic
- `templates/documents/tell_your_story.html` - Add microphone button UI

**User Flow:**
1. User clicks microphone button
2. Browser asks for microphone permission
3. User speaks their story
4. Text appears in real-time in textarea
5. User can edit, then analyze as usual

### Mobile App Version
- Tell Your Story with voice input will be key feature
- Options: PWA (Progressive Web App), Capacitor wrapper, or wrapper services
- PWA is simplest (add to home screen, works offline)

### News API Integration (NEXT PRIORITY)
Landing page has placeholder news items. Need to integrate real news.

**Planned Implementation:**
- NewsAPI.org integration for civil rights news
- Search queries: "civil rights", "police accountability", "Section 1983"
- Django management command to fetch/cache news daily
- NewsItem model for storage
- Display latest 5 on landing page, full archive at /news/

**Files to create:**
- `public_pages/models.py` - NewsItem model
- `public_pages/management/commands/fetch_news.py` - Fetch command
- Add cron job or Celery task for daily fetch

### CMS for Articles (Planned)
Landing page has placeholder articles. Need editable content.

**Planned Implementation:**
- CivilRightsArticle model with CKEditor
- Admin-editable articles
- Category system (Know Your Rights, Legal Basics, Take Action)
- Featured flag for homepage display
- URL: `/rights/<slug>/` for individual articles

### User Purchase System / Membership (IMPLEMENTED)
Hybrid pricing model with subscriptions and one-time purchases is now live.

**Current options:**
- Single Document: $49 (one-time)
- 3-Document Pack: $99 (one-time, saves $48)
- Monthly Pro: $29/month (unlimited docs, 50 AI/month)
- Annual Pro: $249/year (unlimited docs, unlimited AI)

**Potential future enhancements:**
- Different pricing for different case types
- Non-profit/reduced pricing options

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

### Redirect Loop for Finalized Documents (RESOLVED)
Clicking "Download PDF" on a finalized document was causing a blank page.

**Root cause:** `document_preview` was unconditionally redirecting to `document_review`, while `document_review` redirected finalized documents back to `document_preview`, creating an infinite redirect loop.

**Solution:** Updated `document_preview` to actually render the preview template for finalized documents instead of always redirecting. Now:
- Non-finalized documents: `document_preview` → redirect to `document_review`
- Finalized documents: `document_preview` → render preview template (read-only)
- Finalized documents visiting `document_review`: redirect to `document_preview`

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

### Subscription Migration Conflict (RESOLVED)
Subscription tables were created on server via auto-generated migration but a manually created migration file caused conflicts on deploy.

**Root cause:** `makemigrations` was run on the server, creating `0003_subscription_alter_user_groups_subscriptionreferral_and_more.py`. A manually created migration file `0003_subscription_documentpack_subscriptionreferral.py` conflicted with it.

**Solution:**
1. Deleted the manually created migration file
2. Ran `python manage.py migrate accounts 0003 --fake` on server to mark existing migration as applied
3. Deploy succeeded

**Lesson:** Never run `makemigrations` on production. Always create migrations locally, test them, commit them, then deploy.

### Subscription Success AttributeError (RESOLVED)
Users completing subscription checkout were getting 500 error: `AttributeError: current_period_start`

**Root cause:** The Stripe subscription object may not have `current_period_start` or `current_period_end` fields directly accessible for all subscription states. The code was using direct attribute access (`stripe_sub.current_period_start`) which fails if the field doesn't exist.

**Solution:** Changed to use `.get()` method for safe access:
```python
# Before (broken):
'current_period_start': _timestamp_to_datetime(stripe_sub.current_period_start),

# After (fixed):
period_start = stripe_sub.get('current_period_start')
if period_start:
    defaults['current_period_start'] = _timestamp_to_datetime(period_start)
```

**Files modified:**
- `accounts/views.py` - Both `subscription_success` and `subscription_webhook` views updated
- Added debug logging to help troubleshoot future subscription issues

### Subscribers Blocked by Free AI Limit (RESOLVED)
Users with active subscriptions were seeing "AI Limit Reached - You have used all 3 free AI analyses" and being blocked from using AI features.

**Root cause:** The `Document.can_use_ai()` method only checked admin access, free tier, and paid document status - it never checked if the user had an active subscription.

**Solution:** Updated three methods in `documents/models.py`:
1. `can_use_ai()` - Now checks `user.can_use_subscription_ai()` before falling back to free tier
2. `get_ai_usage_display()` - Shows subscription AI remaining (e.g., "AI: 50 uses remaining this month (Pro)")
3. `record_ai_usage()` - Records usage on subscription instead of document for subscribers

**Files modified:**
- `documents/models.py` - All three methods updated

### Subscribers Seeing Upgrade Prompts (RESOLVED)
Subscribers were still seeing "Upgrade Now - $79" in the status banner even with active subscriptions.

**Root cause:** The status banner template always showed upgrade buttons for draft/expired documents regardless of subscription status.

**Solution:** Updated `templates/documents/partials/status_banner.html`:
- Hide "Upgrade Now" button for subscribers
- Show "PRO - Draft Document" instead of "DRAFT - X hours remaining"
- Hide "Unlock Now" button for subscribers on expired docs

### Dark Mode Text Readability in Document Builder (RESOLVED)
Text in AI results, accordions, and various document builder elements was hard to read in dark mode.

**Solution:** Added comprehensive dark mode styles to `static/css/app-theme.css`:
- Field items and field values in AI results
- bg-light backgrounds
- Card headers with colored backgrounds (success, warning, info, etc.)
- Results panel and questions section
- Section edit page elements (defendants, witnesses, evidence cards)
- Document detail and review pages
- Accordion buttons and arrows
- Various text elements, badges, borders, and list items

---

## Instructions for Next Claude Session

**IMPORTANT:**
- Do NOT start building features automatically
- Ask what the user wants to work on
- Go step by step - explain what you plan to do BEFORE doing it
- Get approval before writing code
- **ALWAYS update this HANDOFF.md after ANY change** (features, bug fixes, removals, etc.)
- **Always provide git pull and merge commands at the end of a session**

**To continue work:**
1. User will tell you what feature they want
2. You explain the plan
3. User approves
4. You implement
5. User tests
6. **Update HANDOFF.md** (document what changed - this is mandatory for every change)
7. Provide merge commands (see below)
8. Repeat

**After completing work - provide these merge commands:**

*Note: User deploys from local machine. Branches created by Claude exist only on remote until fetched.*

```bash
# Fetch the remote branch
git fetch origin <branch-name>

# Switch to master and merge (use origin/ prefix for remote branch)
git checkout master
git pull origin master
git merge origin/<branch-name>

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

# Run migrations (migrations should already be committed to git)
docker-compose run web python manage.py migrate

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

# Stripe Price IDs (Required for subscriptions)
# Create these products in Stripe Dashboard → Products
STRIPE_PRICE_SINGLE=price_xxx  # Single document ($49)
STRIPE_PRICE_3PACK=price_xxx   # 3-document pack ($99)
STRIPE_PRICE_MONTHLY=price_xxx # Monthly subscription ($29/mo recurring)
STRIPE_PRICE_ANNUAL=price_xxx  # Annual subscription ($249/yr recurring)

# Optional (Branding)
APP_NAME=1983law.com           # Shown in DRAFT watermark and footer
HEADER_APP_NAME=1983 Law       # Shown in navbar and page titles

# Security (Optional)
ADMIN_URL=manage-x7k9m2/       # Custom admin URL path (default: manage-x7k9m2/)
                                # Rotate periodically for security
                                # Must end with /
```

### Admin URL Security
The Django admin is NOT at `/admin/` by default. It uses a randomized path to prevent brute force attacks.

**Default:** `/manage-x7k9m2/`

**To rotate the admin URL:**
1. Generate a new random path (e.g., `backend-abc123/`)
2. Set `ADMIN_URL=backend-abc123/` in Render environment variables
3. Redeploy

**Note:** All admin links in the app use Django's `{% url 'admin:index' %}` so they automatically update when the path changes.
