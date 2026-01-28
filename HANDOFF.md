# 1983 Law App - Handoff Document

## What This App Does

A web application to help people create Section 1983 civil rights complaints. Users fill out an interview-style form, and the app helps them build their legal document step by step.

---

## Current State (January 28, 2026)

The app is fully functional with all core features complete.

### Document Flow
```
Register → Complete Profile → Create Document → Tell Your Story → Fill Sections → Final Review → Download PDF
```

### Key Features

1. **User Authentication** (`accounts` app)
   - Email-based login
   - Profile completion required before creating documents
   - `is_test_user` flag for testing

2. **Document Builder** (`documents` app)
   - 10 interview sections
   - Tell Your Story is MANDATORY first step
   - Section status tracking (not started, in progress, completed, needs work, N/A)

3. **Interview Sections** (in order)
   - Plaintiff Information (from profile)
   - Incident Overview (with court lookup)
   - Defendants (multiple)
   - Incident Narrative
   - Rights Violated
   - Witnesses (multiple)
   - Evidence (multiple)
   - Damages
   - Prior Complaints
   - Relief Sought

4. **AI Features** (OpenAI GPT-4o-mini)
   - Story parsing and auto-fill
   - Per-section suggestions (damages, witnesses, evidence, rights)
   - Legal document generation
   - Document review with issue highlighting
   - **All AI prompts stored in database via seed files**

5. **Final Review Pathway** (`/documents/{id}/final/`) - NEW
   - Auto-generates legal document on page load
   - Inline editing of all sections
   - AI review of actual document text
   - Regenerate individual sections or entire document
   - Download PDF with proper legal formatting
   - **Requires 100% section completion**

6. **PDF Generation**
   - Proper court caption with bordered case box
   - Document title: "COMPLAINT FOR VIOLATION OF CIVIL RIGHTS PURSUANT TO 42 U.S.C. § 1983"
   - Section headers: Jurisdiction, Parties, Facts, Causes of Action, Prayer, Jury Demand
   - Times New Roman, 12pt, double-spaced
   - Page numbers, signature block
   - Draft watermark for unpaid documents

7. **Payments** (Stripe)
   - Per-document purchase or subscription
   - Draft documents expire after 7 days

---

## Tech Stack

- **Backend**: Django 4.2, Python 3.11
- **Frontend**: Bootstrap 5, vanilla JS
- **Database**: PostgreSQL
- **AI**: OpenAI GPT-4o-mini
- **PDF**: WeasyPrint
- **Payments**: Stripe
- **Deployment**: Docker, Nginx

---

## Key Files

### Models
- `documents/models.py` - Document, Defendant, Witness, Evidence, etc.
  - `final_*` fields for editable final document text
  - `has_final_document()` method

### Views
- `documents/views.py` - All document views
  - `final_review` - Main final review page (line ~5180)
  - `generate_final_document` - Generate/regenerate (line ~5210)
  - `save_final_section` - Save inline edits (line ~5230)
  - `ai_review_final` - AI review endpoint (line ~5250)
  - `download_final_pdf` - PDF generation (line ~5270)

### Templates
- `templates/documents/final_review.html` - Final review page with inline editing
- `templates/documents/final_pdf.html` - PDF template with legal formatting
- `templates/documents/document_detail.html` - Document overview page

### Services
- `documents/services/openai_service.py` - OpenAI integration
  - `review_final_document()` - Reviews actual document text
- `documents/services/document_generator.py` - Generates legal document sections

### AI Prompts (Database Seeds)
- `documents/management/commands/seed_ai_prompts.py` - All AI prompts
  - `review_final_document` - Reviews the generated legal document

---

## Recent Changes (January 28, 2026)

1. **Final Review Button** - Only clickable at 100% completion
2. **Removed Finalize button** from document detail page (moved to final review)
3. **PDF Template** - Proper legal document format with court caption
4. **Preview Template** - Matches PDF format for consistency
5. **AI Review** - Reviews actual document text, not raw input data

---

## Running Locally

```bash
docker-compose up --build
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py seed_ai_prompts
```

## Environment Variables

```
OPENAI_API_KEY=sk-...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
DATABASE_URL=postgres://...
SECRET_KEY=...
```

---

## Known Issues / TODO

- None currently blocking

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
