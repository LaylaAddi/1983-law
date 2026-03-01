# 1983 Law App - Handoff Document

## What This App Does

A web application to help people create Section 1983 civil rights complaints. Users tell their story, a guided wizard interview extracts details, AI analyzes the case, and the app builds their legal document.

**Production site:** https://www.1983law.org

---

## Current Branch & Deployment

```bash
# Development branch
git fetch origin claude/review-handoff-yKGkf

# To deploy: merge to master and push (Render auto-deploys from master)
git checkout master
git merge origin/claude/review-handoff-yKGkf
git push origin master
# start.sh auto-runs: migrate + seed_ai_prompts + gunicorn
```

---

## Recent Session Work (This Branch)

### Federal District Court in Wizard Step 1
- **Court lookup field** added to bottom of Step 1 (When & Where) with auto-lookup from city/state
- **Auto-populates** when city+state are filled (polling at init + `@change` handlers)
- **URL routing fix** — `lookup-district-court/` moved above `<str:document_slug>/` catch-all in `documents/urls.py` to prevent 404
- **Serializer fixes** — Added `EmptyStringDateField`/`EmptyStringTimeField` to handle empty strings (DRF was rejecting `""` as invalid date/time, causing 400 on step save and silently losing all step 1 data)
- **Missing serializer fields** — Added `address`, `location_type_other`, `was_recording`, `recording_device` to `StepWhenWhereSerializer` (were being silently dropped by DRF)
- **Boolean fix** in `_apply_wizard_to_document()` — Changed `step_1.get('court_district_confirmed')` (falsy for `False`) to `'court_district_confirmed' in step_1`
- **NullBooleanField** removed in DRF 3.14+ — replaced with `BooleanField(allow_null=True, default=None)`
- **Visual states**: orange box when court needed, green when found, header icon changes to checkmark
- **Dark mode** styles for court box, lookup button, form inputs, confirmation labels
- **Confirmation required** — User must check "I confirm this is the correct federal district court" before proceeding to Step 2
- **Guided validation** — Clicking Next without completing court fields shows a prominent warning banner above the Next button explaining exactly what's needed, auto-scrolls to the problem area, and pulses the confirmation checkbox with red animation

### Wizard Hub (Document Detail Page Replacement)
- **Replaced** old 10-section grid document detail page with wizard-centric hub at `/documents/{slug}/`
- **Shows**: wizard progress steps, case summary (after completion), quick actions sidebar
- **Edit links** go to `?step=N` on the wizard — clicking a step row opens the wizard at that step
- **Fixed** wizard init to respect `?step=N` URL parameter (was being overridden by `currentView = 'analysis'` in init)
- Template: `templates/documents/document_detail.html`
- View: `documents/views.py` `document_detail()` — passes `wizard_status`, `wizard_steps`, `case_summary` context

### Navigation Updates
- **Know Your Rights dropdown** added to navbar for all users (Overview, Section 1983, Right to Record, amendments, etc.)
- **Landing page** no longer redirects authenticated users to document list — they can browse the full public site
- **My Documents** and **New Case** remain in nav for authenticated users
- Changes in: `templates/base.html`, `public_pages/views.py`

---

## Architecture

### Tech Stack
- **Backend**: Django 4.2, Python 3.11
- **API**: Django REST Framework + SimpleJWT
- **Frontend**: Bootstrap 5, vanilla JS, Alpine.js (wizard only)
- **Database**: PostgreSQL
- **AI**: OpenAI GPT-4o-mini
- **PDF**: WeasyPrint
- **Payments**: Stripe
- **Deployment**: Docker on Render

### URL Structure
- **Web app**: `/documents/<slug>/...` (Django templates)
- **Wizard page**: `/documents/<slug>/wizard/` (Alpine.js SPA within Django template)
- **Court lookup**: `/documents/lookup-district-court/` (MUST be before `<str:document_slug>/` in urls.py)
- **API**: `/api/v1/wizard/...` (DRF, JSON)
- **Public pages**: `/`, `/rights/...` (accessible to all users including authenticated)
- **Auth**: Session auth (web) + JWT (mobile/API)
- **All URLs use 8-char random slugs** (e.g., `/documents/xK9mR2pL/`)

### Document Flow (Primary — Wizard)
```
Register → Profile → Create Document → Wizard (tell story + 7 steps + analysis) → Build Complaint → Wizard Hub → Final Review → PDF
```
Document creation redirects to wizard. After completion, user lands on the wizard hub page.

### Document Flow (Legacy — old path still accessible)
```
Register → Profile → Create Document → Tell Your Story → Fill Sections → Final Review → PDF
```

---

## Wizard Architecture (Detailed)

### How It Works
1. User enters `/documents/{slug}/wizard/`
2. Django `wizard()` view serves `wizard.html` with session state as JSON context
3. Alpine.js takes over — single-page app with 3 views: Story → Steps → Analysis
4. All data flows through DRF API endpoints (session auth with CSRF)
5. AI processing runs in background threads; frontend polls for completion
6. On "Build My Complaint", API applies all wizard data to real Django models

### API Endpoints
```
POST   /api/v1/wizard/{doc_slug}/start/           → Submit story text, kicks off AI extraction (background thread)
GET    /api/v1/wizard/{session_slug}/status/       → Poll AI extraction progress
GET    /api/v1/wizard/{session_slug}/              → Get full wizard state
PUT    /api/v1/wizard/{session_slug}/step/{1-7}/   → Save step data (validated by step serializer)
POST   /api/v1/wizard/{session_slug}/analyze/      → Run final AI case analysis (background thread)
GET    /api/v1/wizard/{session_slug}/analysis/     → Poll analysis results
POST   /api/v1/wizard/{session_slug}/complete/     → Apply all wizard data to Document models

POST   /api/v1/auth/token/                         → JWT login (for future mobile)
POST   /api/v1/auth/token/refresh/                 → Refresh JWT
```

### Wizard Steps
1. **When & Where** — Date, time, location, city, state, **Federal District Court (auto-lookup + confirmation)**
2. **Who Was Involved** — Defendants (officers/agencies) + witnesses
3. **What Happened** — Narrative breakdown (initial contact, dialogue, actions, ending)
4. **Why It Was Wrong** — Plain-language violation selection → maps to constitutional amendments
5. **How It Affected You** — Physical, emotional, financial damages
6. **Evidence & Proof** — Evidence types, items, YouTube links
7. **Preferences** — Case law opt-in/out

### Key Wizard Files
| File | What It Does |
|------|-------------|
| `documents/views.py` | `wizard()` view + `document_detail()` hub view |
| `documents/api/views.py` | 7 API endpoints + background AI threads + `_apply_wizard_to_document()` |
| `documents/api/serializers.py` | Step serializers with custom `EmptyStringDateField`/`EmptyStringTimeField` |
| `documents/api/urls.py` | API URL routing |
| `templates/documents/wizard.html` | Alpine.js SPA (story → steps → analysis) |
| `templates/documents/document_detail.html` | Wizard hub (replaced old section grid) |
| `documents/models.py` | `WizardSession` model (OneToOne with Document, JSONField storage) |
| `documents/urls.py` | Web URL routing (`lookup-district-court/` at top, before slug catch-all) |

### WizardSession Model
```python
class WizardSession(models.Model):
    document       = OneToOneField(Document, related_name='wizard_session')
    slug           = CharField(max_length=12, unique=True)
    status         = CharField  # not_started|in_progress|analyzing|analyzed|completed|abandoned
    current_step   = PositiveIntegerField(default=1)
    raw_story      = TextField
    ai_extracted   = JSONField  # AI parsed data (pre-fill)
    interview_data = JSONField  # User-confirmed step data
    use_case_law   = BooleanField(default=True)
    ai_analysis    = JSONField  # Final analysis results
    analysis_status = CharField  # pending|processing|completed|failed
    analysis_error = TextField
    created_at / updated_at
```

### Alpine.js Frontend State
```javascript
// Key state variables in wizardApp()
currentView: 'story' | 'steps' | 'analysis'
currentStep: 1-7
stepData: { 1: {...}, 2: {...}, ... 7: {...} }
aiExtracted: { step_1: {...}, step_2: {...} }
analysisData: { violations: [], case_law: [], ... }

// Court lookup state (Step 1)
courtLookupLoading, courtLookupConfidence, courtLookupMessage, _lastCourtLookupKey
step1CityError, step1StateError, step1CourtError, step1BlockedMessage, step1NeedsConfirmation
```

### Step 1 Court Lookup Flow
```
City/state filled → lookupCourt() fires (via @change + init polling)
  → fetch('/documents/lookup-district-court/?city=X&state=Y')
  → CourtLookupService: static lookup first, then GPT fallback
  → Court box turns green, header says "Found"
  → User must check confirmation checkbox
  → validateStep1() blocks nextStep() if court empty or unconfirmed
  → Shows warning banner + auto-scrolls + pulses checkbox
```

### How Wizard Completion Works
**Frontend (`completeWizard()`):**
1. Saves ALL 7 steps via PUT requests
2. Calls `/api/v1/wizard/{session}/complete/`
3. Redirects to document hub on success

**Backend (`_apply_wizard_to_document()`):**
- Step 1 → `IncidentOverview` (date, time, location, city, state, **federal_district_court, use_manual_court, court_district_confirmed**)
- Step 2 → Creates `Defendant` and `Witness` model instances
- Step 3 → `IncidentNarrative` (narrative fields)
- Step 4 → `RightsViolated` via `VIOLATION_MAP`
- Step 5 → `Damages` (physical, emotional, financial)
- Step 6 → Creates `Evidence` instances
- Step 7 → `use_case_law` flag

---

## Full App Features

1. **User Authentication** (`accounts` app) — Email-based login, profile completion required, `is_test_user` flag
2. **Document Builder** (`documents` app) — 10 interview sections with status tracking
3. **AI Features** (OpenAI GPT-4o-mini) — Story parsing, section suggestions, document generation, case analysis, case law, court lookup. **15 prompt types** in database, auto-seeded on deploy.
4. **Video Evidence** (YouTube) — Transcript extraction via Supadata API, speaker attribution, AI evidence suggestions
5. **Final Review** (`/documents/{slug}/final/`) — Auto-generates legal document, inline editing, AI review, PDF download
6. **PDF Generation** (WeasyPrint) — Court caption, Times New Roman, double-spaced, page numbers
7. **Payments** (Stripe) — Per-document purchase or subscription, referral codes, 48-hour draft expiry
8. **Public Pages** — Know Your Rights, Section 1983 explainer, amendment pages, accessible to all users

---

## Key Files (Non-Wizard)

### Models
- `documents/models.py` — Document, Defendant, Witness, Evidence, WizardSession, IncidentOverview, etc.

### Views
- `documents/views.py` — All document views (function-based, ~5400 lines)
- `public_pages/views.py` — Public rights pages (no longer redirects authenticated users)

### Templates
- `templates/base.html` — Base layout with navbar (Know Your Rights dropdown, My Documents, user dropdown)
- `templates/documents/document_detail.html` — Wizard hub (replaced old section grid)
- `templates/documents/wizard.html` — Alpine.js wizard SPA
- `templates/documents/section_edit.html` — Section editing (largest template)
- `templates/documents/final_review.html` — Final review with inline editing
- `templates/documents/final_pdf.html` — PDF template

### Services
- `documents/services/openai_service.py` — OpenAI integration
- `documents/services/document_generator.py` — Legal document generation
- `documents/services/youtube_service.py` — YouTube transcript extraction
- `documents/services/court_lookup_service.py` — Federal court lookup (static + GPT fallback)

---

## Environment Variables

```
OPENAI_API_KEY=sk-...          # Required for AI features
STRIPE_SECRET_KEY=sk_test_...  # Required for payments
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_SINGLE=price_...
STRIPE_PRICE_MONTHLY=price_...
STRIPE_PRICE_ANNUAL=price_...
SECRET_KEY=...
SUPADATA_API_KEY=...           # Required for YouTube transcript extraction
EMAIL_HOST=...
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
```

---

## Known Issues / TODO

### Bugs to Watch
- Court lookup URL **must** be before `<str:document_slug>/` in `documents/urls.py` — Django matches it as a document slug otherwise (was a 404 bug, now fixed)
- DRF serializer empty string handling — custom `EmptyStringDateField`/`EmptyStringTimeField` classes needed because DRF rejects `""` as invalid date/time even with `required=False, allow_null=True`

### Remaining Work
- YouTube URL in wizard Step 6 collected but not wired to video analysis features
- Voice input only works on story input, not individual step fields
- No unit tests for wizard API endpoints
- CKEditor 4 bundled version has security warnings (consider migrating to CKEditor 5)
- Pricing simplification planned ($99 per document, drop subscription tiers) — not started
- Mobile app planned (API layer ready) — not started

---

## Rollback

A git tag `pre-wizard-v1` marks the stable state before wizard changes.
```bash
git reset --hard pre-wizard-v1
git push origin master --force
```

---

## Recent Commit History

```
c99c4e5 Guide user through Step 1 validation with clear prompts and scroll
2f720eb Add Know Your Rights nav dropdown, stop redirecting logged-in users from home
05b8880 Fix wizard step links: don't override ?step=N with analysis view
9e9c35b Highlight court district box green when populated
a39c25b Fix NullBooleanField removed in DRF 3.14+
092b522 Replace document detail with wizard-centric hub + fix court data saving
a0b6c15 Fix court data not saving + improve dark mode + better explanation text
d5d3b62 Fix court lookup 404: move URL route above document_slug catch-all
3272f87 Fix court auto-lookup: replace broken $watch with polling + @change handlers
c733f4e Fix court auto-lookup with $watch on city/state changes
dae19b6 Fix court lookup button visibility and auto-lookup on page load
944b7c6 Add Federal District Court to wizard Step 1 (When & Where)
8fd4b3b Fix Google Scholar research links not opening in new tab
404dbdc Add analysis selection toggles, violation explanations, and case law research links
e0277d3 Fix wizard data flow to document sections, add dark mode for court lookup
```

---

## Testing

**Test wizard (browser):**
1. Register/login, complete profile, create document
2. Go to `/documents/{slug}/wizard/`
3. Enter story text (50+ chars), submit
4. Wait for AI extraction (terminal animation)
5. Confirm city/state → court auto-populates → check confirmation → Next
6. Complete steps 2-7
7. Click "Analyze My Case" on step 7
8. Review violations, case law, preview
9. Click "Build My Complaint"
10. Verify wizard hub shows case summary with court info
11. Click step rows to edit — should open wizard at that step
12. Check navbar: Know Your Rights dropdown visible, Home goes to public landing page
