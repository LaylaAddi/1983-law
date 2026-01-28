# AI Prompt Backups

These files are backup copies of the AI prompts stored in the database.

**To edit prompts:** Go to Admin → AI Prompts (or `/admin/documents/aiprompt/`)

**These files are for:**
- Reference/documentation
- Backup in case database is wiped
- Copy-paste source for admin edits
- Version control of prompt changes

**Files:**
- `find_law_enforcement.md` - Identifies correct police/sheriff jurisdiction
- `parse_story.md` - Main "Tell Your Story" analysis prompt
- `analyze_rights.md` - Constitutional rights violation analysis
- `suggest_relief.md` - Legal relief recommendations
- `suggest_evidence.md` - Evidence suggestion from story
- `lookup_federal_court.md` - Federal court lookup
- `identify_officer_agency.md` - Agency identification for officers
- `review_final_document.md` - AI review of generated document text (Final Review page)

**After editing in admin, update these files to keep them in sync.**

**To seed prompts into database:** `python manage.py seed_ai_prompts`
