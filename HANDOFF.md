# 1983 Law App - Handoff Document

## What This App Does

A web application to help people create Section 1983 civil rights complaints. Users are guided through a step-by-step wizard interview, AI analyzes their case, and the app builds their legal document.

---

## Current State (February 2, 2026)

The app is fully functional. A guided wizard API layer has been added for the new interview flow. URLs now use opaque slugs instead of integer IDs.

### Document Flow (Current)
```
Register → Complete Profile → Create Document → Tell Your Story → Fill Sections → Final Review → Download PDF
```

### Document Flow (New Wizard - In Progress)
```
Register → Profile → Create Document → Tell Story → 7-Step Guided Interview → AI Case Analysis → Build Complaint → Final Review → PDF
```

---

## Architecture

### Tech Stack
- **Backend**: Django 4.2, Python 3.11
- **API**: Django REST Framework + SimpleJWT (new)
- **Frontend**: Bootstrap 5, vanilla JS (Alpine.js planned for wizard UI)
- **Database**: PostgreSQL
- **AI**: OpenAI GPT-4o-mini
- **PDF**: WeasyPrint
- **Payments**: Stripe
- **Deployment**: Docker on Render

### URL Structure
- **Web app**: `/documents/<slug>/...` (Django templates)
- **API**: `/api/v1/wizard/...` (DRF, JSON)
- **Auth**: Session auth (web) + JWT (mobile/API)
- **All URLs use 8-char random slugs** (e.g., `/documents/xK9mR2pL/`)

---

## Key Features

1. **User Authentication** (`accounts` app)
   - Email-based login (custom User model)
   - Profile completion required before creating documents
   - `is_test_user` flag for testing

2. **Document Builder** (`documents` app)
   - 10 interview sections with status tracking
   - Tell Your Story is mandatory first step
   - AI-powered auto-fill from story text

3. **Guided Wizard** (`documents/api/`) — NEW
   - 7-step interview with AI pre-fill
   - Case analysis with violations, case law, document preview
   - Same API serves web and future mobile app
   - See "Wizard Implementation Plan" section below

4. **AI Features** (OpenAI GPT-4o-mini)
   - Story parsing and auto-fill
   - Per-section suggestions
   - Legal document generation
   - Document review with issue highlighting
   - Case analysis with violation strength ratings
   - Case law suggestions (opt-in)
   - **All AI prompts stored in database via seed files**

5. **Video Evidence** (YouTube)
   - YouTube transcript extraction via Supadata API
   - Speaker attribution (plaintiff, defendants, witnesses)
   - AI-powered evidence suggestions from transcripts
   - Applied suggestions tracking with duplicate detection

6. **Final Review Pathway** (`/documents/{slug}/final/`)
   - Auto-generates legal document on page load
   - Inline editing of all sections
   - AI review of actual document text
   - Download PDF with proper legal formatting
   - Requires 100% section completion

7. **PDF Generation** (WeasyPrint)
   - Court caption: "UNITED STATES DISTRICT COURT" / "{DISTRICT} DISTRICT OF {STATE}"
   - Times New Roman, 12pt, double-spaced
   - Page numbers, signature block, draft watermark

8. **Payments** (Stripe)
   - Per-document purchase or subscription
   - Referral/promo code system
   - Draft documents expire after 48 hours

---

## Wizard Implementation Plan

### Overview
Replace the current "dump everything at once" flow with a guided 7-step interview. The user tells their story, AI extracts details, then the user confirms/edits each section one at a time. After all steps, AI provides a case analysis with potential violations, case law, and a document preview.

### Phase 1: API Foundation ✅ COMPLETE
- Django REST Framework + SimpleJWT installed
- `WizardSession` model with JSONField storage
- 7 API endpoints for wizard flow
- JWT auth endpoints for future mobile app
- Step serializers with validation

### Phase 2: Web Frontend (NEXT)
- Single Django template with Alpine.js stepper
- Terminal animation during AI extraction
- Pre-filled forms with "AI suggested" badges
- Step-by-step navigation (back/next/skip)
- Voice input via Web Speech API (progressive enhancement)

### Phase 3: Analysis Screen
- Violations with strength ratings (strong/moderate/worth including)
- Case law references (opt-in, with verification disclaimer)
- Document preview (styled HTML, not full PDF)
- "Build My Complaint" button → applies all data

### Phase 4: Mobile Readiness
- API already supports JWT auth
- Step-by-step flow maps to mobile screens
- React Native or Flutter frontend
- Native speech-to-text replaces Web Speech API

### Wizard Steps
1. **When & Where** — Date, time, location, city, state
2. **Who Was Involved** — Defendants (officers/agencies) + witnesses
3. **What Happened** — Narrative breakdown (initial contact, dialogue, actions, ending)
4. **Why It Was Wrong** — Plain-language violation selection with amendment mapping
5. **How It Affected You** — Physical, emotional, financial damages
6. **Evidence & Proof** — Evidence types, items, YouTube links
7. **Preferences** — Case law opt-in/out

### API Endpoints
```
POST   /api/v1/wizard/{doc_slug}/start/           → Submit story, AI extracts
GET    /api/v1/wizard/{session_slug}/status/       → Poll extraction progress
GET    /api/v1/wizard/{session_slug}/              → Get full wizard state
PUT    /api/v1/wizard/{session_slug}/step/{1-7}/   → Save step data
POST   /api/v1/wizard/{session_slug}/analyze/      → Run case analysis
GET    /api/v1/wizard/{session_slug}/analysis/     → Poll analysis results
POST   /api/v1/wizard/{session_slug}/complete/     → Apply to document models

POST   /api/v1/auth/token/                         → JWT login
POST   /api/v1/auth/token/refresh/                 → Refresh JWT
```

---

## Key Files

### Models
- `documents/models.py` — Document, Defendant, Witness, Evidence, WizardSession, etc.
  - All URL-exposed models have `slug` field (8-char random)
  - `WizardSession` — OneToOne with Document, tracks wizard progress
  - `final_*` fields for editable final document text

### Views
- `documents/views.py` (~5400 lines) — All document views (function-based)
- `documents/api/views.py` — Wizard API endpoints (DRF)
- `documents/api/serializers.py` — Step serializers with validation
- `documents/api/urls.py` — API URL routing

### Templates
- `templates/documents/tell_your_story.html` — Current story entry
- `templates/documents/section_edit.html` — Section editing (largest template)
- `templates/documents/final_review.html` — Final review with inline editing
- `templates/documents/final_pdf.html` — PDF template
- `templates/documents/video_analysis.html` — YouTube video analysis
- `templates/documents/document_detail.html` — Document overview hub
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

## Recent Changes

### Session 4 Updates (February 2, 2026)

1. **URL Masking with Short Random Slugs** — Replaced all integer IDs in URLs with 8-char alphanumeric slugs across 20 files (models, URLs, views, templates, JS). Admin/referral routes kept with integer IDs.

2. **Wizard API Foundation** — Added DRF + JWT, WizardSession model, 7 API endpoints, step serializers. Phase 1 of guided interview wizard.

3. **Court Caption Fix** — PDF now shows "UNITED STATES DISTRICT COURT" / "{DISTRICT} DISTRICT OF {STATE}" instead of redundant format.

4. **AI Uses Display** — Profile page shows remaining AI uses per paid document and subscription with color-coded badges.

5. **Video Evidence Improvements** — Mandatory date/time/location before AI analysis, applied suggestions tracking with "Previously Applied" history, duplicate detection, fixed damages BooleanField bug.

6. **Slug Excluded from Forms** — Defendant, Witness, and Evidence forms properly exclude the auto-generated slug field.

### Session 3 Updates (January 29, 2026)

1. Fixed Final Review edit button accessibility
2. Removed redundant AI assistant from Rights Violated section
3. Improved PDF page utilization (jury demand + signature together)
4. Fixed AI generating fake timestamps
5. Added generate_facts prompt to seed file
6. YouTube for paid documents (not just subscribers)
7. Fixed profile display for paid documents
8. Dark mode fixes for profile page

### Session 2 Updates (January 28, 2026)

1. Smart regenerate detection on final review
2. Terminal animation for regeneration
3. Fixed subscription display
4. Fixed dark mode table styling
5. Fixed pricing page flow
6. Removed 3-document pack
7. Fixed analyze story evidence button
8. Document ID through pricing flow

---

## Running Locally

```bash
docker-compose up --build
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py seed_ai_prompts
```

## Rollback

A git tag `pre-wizard-v1` marks the stable state before wizard implementation.
```bash
git reset --hard pre-wizard-v1
git push origin master --force
```

## Environment Variables

```
OPENAI_API_KEY=sk-...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_SINGLE=price_...
STRIPE_PRICE_MONTHLY=price_...
STRIPE_PRICE_ANNUAL=price_...
DATABASE_URL=postgres://...
SECRET_KEY=...
SUPADATA_API_KEY=...
EMAIL_HOST=...
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
```

---

## Known Issues / TODO

- CKEditor 4 bundled version has security warnings (consider migrating to CKEditor 5)
- Migration numbering: if server has a different `0008`, run `python manage.py makemigrations --merge`
- Wizard web frontend (Phase 2) not yet built
- Pricing simplification planned ($99 per document, drop subscription tiers)
- Mobile app planned (API layer ready)

---

## Testing

Test user: Set `is_test_user=True` in admin for demo data features.

Test document flow:
1. Register/login
2. Complete profile
3. Create document
4. Tell your story
5. Complete all sections (or mark N/A)
6. Click "Final Review" (only enabled at 100%)
7. Review/edit document
8. Download PDF

Test wizard API:
```bash
# Get JWT token
curl -X POST /api/v1/auth/token/ -d '{"email":"user@test.com","password":"pass"}'

# Start wizard
curl -X POST /api/v1/wizard/{doc_slug}/start/ -H "Authorization: Bearer {token}" -d '{"story":"..."}'

# Save step
curl -X PUT /api/v1/wizard/{session_slug}/step/1/ -H "Authorization: Bearer {token}" -d '{"incident_date":"2024-03-15",...}'
```
