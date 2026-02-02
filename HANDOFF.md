# 1983 Law App - Handoff Document

## What This App Does

A web application to help people create Section 1983 civil rights complaints. Users tell their story, a guided wizard interview extracts details, AI analyzes the case, and the app builds their legal document.

---

## YOUR TASK: Continue Wizard Development (Phase 3)

### What's Done
- **Phase 1 (API Foundation)** ✅ — DRF + JWT, WizardSession model, 7 API endpoints, step serializers
- **Phase 2 (Web Frontend)** ✅ — Alpine.js single-page wizard template with 7-step forms, AI pre-fill, voice input, terminal animation, analysis view

### What's Next: Phase 3

**1. Link wizard into the document flow**
The wizard template exists at `/documents/{slug}/wizard/` but NOTHING links to it yet. You need to:
- Add a "Start Guided Interview" button on the **document detail page** (`templates/documents/document_detail.html`) OR after Tell Your Story (`templates/documents/tell_your_story.html`)
- The wizard URL name is `documents:wizard` with `document_slug` param
- Consider making it the primary path after document creation

**2. Test the full wizard end-to-end**
The frontend and API have never been tested together in a browser. Things to verify:
- Story submission → AI extraction → step pre-fill
- Step editing, saving, navigation (back/next)
- Case analysis → violations + case law display
- "Build My Complaint" → applies wizard data to document models
- Error handling (AI timeouts, network failures)

**3. Polish the analysis screen**
- Violations with strength ratings (strong/moderate/worth including)
- Case law references (if opted in, with verification disclaimer)
- Document preview (styled HTML)
- "Build My Complaint" button applies all data and redirects

**4. Missing integration points**
- Wizard completion should redirect to document detail (currently coded, needs testing)
- YouTube URL field exists in Step 6 but video analysis integration is not wired
- Voice input only works on story textarea (Web Speech API)

### Future phases (not yet)
- **Phase 4: Mobile** — API already supports JWT auth, mobile app planned but not started
- **Pricing simplification** — $99 per document, drop subscription tiers (mentioned but not started)

---

## Local Docker Setup

```bash
# Pull latest code and merge this branch
git fetch origin claude/review-handoff-merge-MdiXj
git checkout master
git merge origin/claude/review-handoff-merge-MdiXj

# Build and start containers (auto-runs migrate + seed_ai_prompts)
docker-compose up --build

# App runs at http://localhost:8000
```

**Manual seed (if needed):**
```bash
docker-compose exec web python manage.py seed_ai_prompts
```

**Environment variables** — add to `docker-compose.yml` under `web.environment` or use `.env`:
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

**Deploying to Render (production):**
```bash
# Render auto-deploys from master. To merge latest changes and deploy:
git fetch origin claude/review-handoff-merge-MdiXj
git checkout master
git merge origin/claude/review-handoff-merge-MdiXj
git push origin master
# start.sh auto-runs: migrate + seed_ai_prompts + gunicorn
```

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
- **API**: `/api/v1/wizard/...` (DRF, JSON)
- **Auth**: Session auth (web) + JWT (mobile/API)
- **All URLs use 8-char random slugs** (e.g., `/documents/xK9mR2pL/`)

### Document Flow (Current — old path still works)
```
Register → Profile → Create Document → Tell Your Story → Fill Sections → Final Review → PDF
```

### Document Flow (New Wizard — needs linking)
```
Register → Profile → Create Document → Wizard (tell story + 7 steps + analysis) → Build Complaint → Final Review → PDF
```

---

## Wizard Architecture (Detailed)

### How It Works
1. User enters `/documents/{slug}/wizard/`
2. Django `wizard()` view (views.py:2390) serves `wizard.html` with session state as JSON context
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
1. **When & Where** — Date, time, location, city, state
2. **Who Was Involved** — Defendants (officers/agencies) + witnesses
3. **What Happened** — Narrative breakdown (initial contact, dialogue, actions, ending)
4. **Why It Was Wrong** — Plain-language violation selection → maps to constitutional amendments
5. **How It Affected You** — Physical, emotional, financial damages
6. **Evidence & Proof** — Evidence types, items, YouTube links
7. **Preferences** — Case law opt-in/out

### Key Wizard Files
| File | What It Does |
|------|-------------|
| `documents/views.py:2390` | `wizard()` — Django view, serves template with session JSON |
| `documents/api/views.py` | 7 API endpoints + background AI threads + `_apply_wizard_to_document()` |
| `documents/api/serializers.py` | 11 serializers — one per step + start + session + nested entries |
| `documents/api/urls.py` | API URL routing (9 endpoints + 2 JWT) |
| `templates/documents/wizard.html` | ~600-line Alpine.js SPA (story → steps → analysis) |
| `documents/models.py:1279` | `WizardSession` model (OneToOne with Document, JSONField storage) |
| `documents/migrations/0009_add_wizard_session.py` | Creates WizardSession table |

### WizardSession Model
```python
class WizardSession(models.Model):
    document       = OneToOneField(Document, related_name='wizard_session')
    slug           = CharField(max_length=12, unique=True)     # URL identifier
    status         = CharField  # not_started|in_progress|analyzing|analyzed|completed|abandoned
    current_step   = PositiveIntegerField(default=1)
    raw_story      = TextField                                  # User's original story
    ai_extracted   = JSONField                                  # AI parsed data (pre-fill)
    interview_data = JSONField                                  # User-confirmed step data
    use_case_law   = BooleanField(default=True)
    ai_analysis    = JSONField                                  # Final analysis results
    analysis_status = CharField  # pending|processing|completed|failed
    analysis_error = TextField
    created_at / updated_at
```
Methods: `progress_percent`, `is_complete`, `get_step_data(n)`, `set_step_data(n, data)`

### Alpine.js Frontend State
```javascript
// Key state variables in wizardApp()
currentView: 'story' | 'steps' | 'analysis'
currentStep: 1-7
stepData: { 1: {...}, 2: {...}, ... 7: {...} }  // User form data
aiExtracted: { step_1: {...}, step_2: {...} }    // AI suggestions
analysisData: { violations: [], case_law: [], ... }
```

### How Wizard Completion Works (`_apply_wizard_to_document()` in api/views.py)
Maps wizard JSON → real models:
- Step 1 (when/where) → `Document.incident_date/time/location/city/state` + `IncidentOverview`
- Step 2 (who) → Creates `Defendant` and `Witness` model instances
- Step 3 (what) → `DocumentSection(section_type='detailed_narrative')` content
- Step 4 (why) → `RightsViolated` model fields via `VIOLATION_MAP`
- Step 5 (impact) → `DamagesSought` model fields
- Step 6 (evidence) → Creates `Evidence` model instances
- Step 7 (preferences) → `use_case_law` flag

---

## Full App Features

1. **User Authentication** (`accounts` app)
   - Email-based login (custom User model)
   - Profile completion required before creating documents
   - `is_test_user` flag for demo data features

2. **Document Builder** (`documents` app)
   - 10 interview sections with status tracking
   - Tell Your Story is mandatory first step (old flow)
   - AI-powered auto-fill from story text

3. **AI Features** (OpenAI GPT-4o-mini)
   - Story parsing and auto-fill
   - Per-section suggestions
   - Legal document generation
   - Document review with issue highlighting
   - Case analysis with violation strength ratings
   - Case law suggestions (opt-in)
   - **All AI prompts stored in database** — single source of truth is `seed_ai_prompts` management command
   - **15 prompt types** seeded: parse_story, analyze_rights, suggest_relief, suggest_damages, suggest_witnesses, suggest_evidence, suggest_rights_violated, find_law_enforcement, identify_officer_agency, lookup_federal_court, review_document, rewrite_section, generate_facts, review_final_document, wizard_analyze_case
   - Prompts auto-seed on deploy (start.sh) and local Docker startup (docker-compose.yml)

4. **Video Evidence** (YouTube)
   - YouTube transcript extraction via Supadata API
   - Speaker attribution (plaintiff, defendants, witnesses)
   - AI-powered evidence suggestions from transcripts
   - Applied suggestions tracking with duplicate detection

5. **Final Review Pathway** (`/documents/{slug}/final/`)
   - Auto-generates legal document on page load
   - Inline editing of all sections
   - AI review of actual document text
   - Download PDF with proper legal formatting
   - Requires 100% section completion

6. **PDF Generation** (WeasyPrint)
   - Court caption: "UNITED STATES DISTRICT COURT" / "{DISTRICT} DISTRICT OF {STATE}"
   - Times New Roman, 12pt, double-spaced
   - Page numbers, signature block, draft watermark

7. **Payments** (Stripe)
   - Per-document purchase or subscription
   - Referral/promo code system
   - Draft documents expire after 48 hours

---

## Key Files (Non-Wizard)

### Models
- `documents/models.py` — Document, Defendant, Witness, Evidence, WizardSession, and more
  - All URL-exposed models have `slug` field (8-char random)
  - `final_*` fields on Document for editable final document text

### Views
- `documents/views.py` (~5400 lines) — All document views (function-based)

### Templates
- `templates/documents/document_detail.html` — Document overview hub
- `templates/documents/tell_your_story.html` — Current story entry (old flow)
- `templates/documents/section_edit.html` — Section editing (largest template)
- `templates/documents/final_review.html` — Final review with inline editing
- `templates/documents/final_pdf.html` — PDF template
- `templates/documents/video_analysis.html` — YouTube video analysis
- `templates/documents/document_review.html` — Document review

### Services
- `documents/services/openai_service.py` — OpenAI integration
- `documents/services/document_generator.py` — Legal document generation
- `documents/services/youtube_service.py` — YouTube transcript extraction
- `documents/services/court_lookup_service.py` — Federal court lookup

### Migrations
- `0007_document_applied_video_suggestions.py` — Video suggestion tracking
- `0008_add_slugs_to_models.py` — Slug fields for all URL-exposed models
- `0009_add_wizard_session.py` — WizardSession model

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
0a331e3 Add wizard web frontend with Alpine.js stepper UI          ← Phase 2
247469f Update HANDOFF.md with wizard plan, slug URLs, session 4 changes
5bc5d74 Add wizard API foundation with DRF, JWT auth, WizardSession model  ← Phase 1
87329cd Exclude slug field from Defendant, Witness, and Evidence forms
d4f0bf2 Replace integer IDs with short random slugs in all URLs
11e4ec2 Add duplicate detection for video evidence suggestions
3bf012a Fix damages apply bug - was writing to BooleanField instead of TextField
```

---

## Known Issues / TODO

- CKEditor 4 bundled version has security warnings (consider migrating to CKEditor 5)
- Migration numbering: if server has a different `0008`/`0009`, run `python manage.py makemigrations --merge`
- Wizard not linked from any page yet (accessible only via direct URL)
- YouTube URL in wizard Step 6 collected but not wired to video analysis features
- Voice input only works on story input, not individual step fields
- Pricing simplification planned ($99 per document, drop subscription tiers) — not started
- Mobile app planned (API layer ready) — not started
- No unit tests for wizard API endpoints

---

## Testing

Test user: Set `is_test_user=True` in admin for demo data features.

**Test wizard (browser):**
1. Register/login, complete profile, create document
2. Go to `/documents/{slug}/wizard/`
3. Enter story text (50+ chars), submit
4. Wait for AI extraction (terminal animation)
5. Confirm/edit each of the 7 steps
6. Click "Analyze My Case" on step 7
7. Review violations, case law, preview
8. Click "Build My Complaint"
9. Verify document detail page has all data populated

**Test wizard API (curl):**
```bash
# Get JWT token
curl -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@test.com","password":"pass"}'

# Start wizard (use document slug)
curl -X POST http://localhost:8000/api/v1/wizard/{doc_slug}/start/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"story":"On March 15, 2024, I was pulled over by Officer Smith..."}'

# Poll extraction status (use session slug from start response)
curl http://localhost:8000/api/v1/wizard/{session_slug}/status/ \
  -H "Authorization: Bearer {token}"

# Save a step
curl -X PUT http://localhost:8000/api/v1/wizard/{session_slug}/step/1/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"incident_date":"2024-03-15","incident_time":"14:30","incident_location":"Main St","city":"Denver","state":"CO"}'

# Run analysis (after completing steps)
curl -X POST http://localhost:8000/api/v1/wizard/{session_slug}/analyze/ \
  -H "Authorization: Bearer {token}"

# Complete wizard (apply to document)
curl -X POST http://localhost:8000/api/v1/wizard/{session_slug}/complete/ \
  -H "Authorization: Bearer {token}"
```
