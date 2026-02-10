import threading
import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from documents.models import (
    Document, WizardSession, DocumentSection,
    IncidentOverview, IncidentNarrative, Defendant, Witness, Evidence,
    RightsViolated, Damages, ReliefSought,
)
from .serializers import (
    WizardStartSerializer, WizardSessionSerializer,
    STEP_SERIALIZERS, STEP_META,
)

logger = logging.getLogger(__name__)

# --- Step 4 violation key → amendment mapping ---
VIOLATION_MAP = {
    'searched_without_warrant': {'amendment': 'fourth', 'sub': 'fourth_amendment_search'},
    'arrested_no_cause': {'amendment': 'fourth', 'sub': 'fourth_amendment_arrest'},
    'excessive_force': {'amendment': 'fourth', 'sub': 'fourth_amendment_force'},
    'unlawful_seizure': {'amendment': 'fourth', 'sub': 'fourth_amendment_seizure'},
    'punished_for_speech': {'amendment': 'first', 'sub': 'first_amendment_speech'},
    'punished_for_recording': {'amendment': 'first', 'sub': 'first_amendment_press'},
    'punished_for_assembly': {'amendment': 'first', 'sub': 'first_amendment_assembly'},
    'racial_discrimination': {'amendment': 'fourteenth', 'sub': 'fourteenth_amendment_equal_protection'},
    'gender_discrimination': {'amendment': 'fourteenth', 'sub': 'fourteenth_amendment_equal_protection'},
    'denied_due_process': {'amendment': 'fourteenth', 'sub': 'fourteenth_amendment_due_process'},
    'forced_statements': {'amendment': 'fifth', 'sub': 'fifth_amendment_self_incrimination'},
    'denied_medical_care': {'amendment': 'fourteenth', 'sub': 'fourteenth_amendment_due_process'},
    'retaliation': {'amendment': 'first', 'sub': 'first_amendment_petition'},
}


def _map_ai_violation_to_field(amendment_key, violation_type):
    """Map an AI analysis violation type string to a RightsViolated model sub-field."""
    vt = violation_type.lower()
    mappings = {
        'fourth': {
            'force': 'fourth_amendment_force',
            'excessive': 'fourth_amendment_force',
            'search': 'fourth_amendment_search',
            'seizure': 'fourth_amendment_seizure',
            'arrest': 'fourth_amendment_arrest',
            'false arrest': 'fourth_amendment_arrest',
            'probable cause': 'fourth_amendment_arrest',
        },
        'first': {
            'speech': 'first_amendment_speech',
            'expression': 'first_amendment_speech',
            'press': 'first_amendment_press',
            'record': 'first_amendment_press',
            'film': 'first_amendment_press',
            'assembl': 'first_amendment_assembly',
            'protest': 'first_amendment_assembly',
            'petition': 'first_amendment_petition',
            'retaliat': 'first_amendment_petition',
            'complaint': 'first_amendment_petition',
        },
        'fifth': {
            'self-incrimination': 'fifth_amendment_self_incrimination',
            'miranda': 'fifth_amendment_self_incrimination',
            'forced statement': 'fifth_amendment_self_incrimination',
            'coerce': 'fifth_amendment_self_incrimination',
            'due process': 'fifth_amendment_due_process',
        },
        'fourteenth': {
            'equal protection': 'fourteenth_amendment_equal_protection',
            'discrimination': 'fourteenth_amendment_equal_protection',
            'racial': 'fourteenth_amendment_equal_protection',
            'profil': 'fourteenth_amendment_equal_protection',
            'due process': 'fourteenth_amendment_due_process',
            'medical': 'fourteenth_amendment_due_process',
            'deliberate indifference': 'fourteenth_amendment_due_process',
        },
    }
    amendment_map = mappings.get(amendment_key, {})
    for keyword, field in amendment_map.items():
        if keyword in vt:
            return field
    return None


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def wizard_start(request, document_slug):
    """Start a wizard session: accept raw story, kick off AI extraction."""
    document = get_object_or_404(Document, slug=document_slug, user=request.user)

    serializer = WizardStartSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    story = serializer.validated_data['story']

    # Create or reset wizard session
    session, created = WizardSession.objects.get_or_create(
        document=document,
        defaults={
            'raw_story': story,
            'status': 'in_progress',
        }
    )

    if not created:
        session.raw_story = story
        session.status = 'in_progress'
        session.current_step = 1
        session.interview_data = {}
        session.ai_extracted = {}
        session.ai_analysis = {}
        session.analysis_status = 'pending'
        session.analysis_error = ''
        session.save()

    # Also save story to the document
    document.story_text = story
    document.save(update_fields=['story_text'])

    # Kick off AI extraction in background thread
    thread = threading.Thread(
        target=_extract_story_background,
        args=(session.id, story),
        daemon=True
    )
    thread.start()

    return Response({
        'session_slug': session.slug,
        'status': 'processing',
        'message': 'Story received. AI is extracting details...',
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def wizard_status(request, session_slug):
    """Poll for AI extraction status and get full wizard state."""
    session = get_object_or_404(
        WizardSession,
        slug=session_slug,
        document__user=request.user
    )

    # If AI extraction is done, return the full session with pre-filled data
    if session.ai_extracted:
        return Response(WizardSessionSerializer(session).data)

    # Still processing
    return Response({
        'slug': session.slug,
        'status': session.status,
        'message': 'AI is still extracting details from your story...',
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def wizard_get(request, session_slug):
    """Get the full current wizard state."""
    session = get_object_or_404(
        WizardSession,
        slug=session_slug,
        document__user=request.user
    )
    return Response(WizardSessionSerializer(session).data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def wizard_save_step(request, session_slug, step_number):
    """Save user-confirmed data for a specific wizard step."""
    if step_number < 1 or step_number > WizardSession.TOTAL_STEPS:
        return Response(
            {'error': f'Step must be between 1 and {WizardSession.TOTAL_STEPS}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    session = get_object_or_404(
        WizardSession,
        slug=session_slug,
        document__user=request.user
    )

    # Validate with the appropriate step serializer
    SerializerClass = STEP_SERIALIZERS[step_number]
    serializer = SerializerClass(data=request.data)
    serializer.is_valid(raise_exception=True)

    # Save step data
    session.set_step_data(step_number, serializer.validated_data)

    # If step 7, capture the case law preference
    if step_number == 7:
        session.use_case_law = serializer.validated_data.get('use_case_law', True)
        session.save(update_fields=['use_case_law'])

    return Response({
        'step': step_number,
        'saved': True,
        'current_step': session.current_step,
        'progress_percent': session.progress_percent,
        'next_step': min(step_number + 1, WizardSession.TOTAL_STEPS + 1),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def wizard_analyze(request, session_slug):
    """Run the final AI analysis: violations, case law, document preview."""
    session = get_object_or_404(
        WizardSession,
        slug=session_slug,
        document__user=request.user
    )

    # Check the user can use AI
    document = session.document
    if not document.can_use_ai():
        return Response(
            {'error': 'AI usage limit reached. Please upgrade to continue.'},
            status=status.HTTP_403_FORBIDDEN
        )

    session.status = 'analyzing'
    session.analysis_status = 'processing'
    session.save(update_fields=['status', 'analysis_status'])

    # Run analysis in background
    thread = threading.Thread(
        target=_analyze_case_background,
        args=(session.id,),
        daemon=True
    )
    thread.start()

    return Response({
        'status': 'processing',
        'message': 'Analyzing your case. This may take a moment...',
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def wizard_analysis_status(request, session_slug):
    """Poll for analysis results."""
    session = get_object_or_404(
        WizardSession,
        slug=session_slug,
        document__user=request.user
    )

    if session.analysis_status == 'completed':
        return Response({
            'status': 'completed',
            'analysis': session.ai_analysis,
        })
    elif session.analysis_status == 'failed':
        return Response({
            'status': 'failed',
            'error': session.analysis_error,
        })
    else:
        return Response({
            'status': 'processing',
            'message': 'Still analyzing...',
        })


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def wizard_analysis_selections(request, session_slug):
    """Save user's include/exclude selections on analysis violations and case law."""
    session = get_object_or_404(
        WizardSession,
        slug=session_slug,
        document__user=request.user
    )

    analysis = session.ai_analysis
    if not analysis:
        return Response(
            {'error': 'No analysis data found.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    violations_selections = request.data.get('violations', [])
    case_law_selections = request.data.get('case_law', [])

    # Update violation included flags
    violations = analysis.get('violations', [])
    for sel in violations_selections:
        idx = sel.get('index')
        if isinstance(idx, int) and 0 <= idx < len(violations):
            violations[idx]['included'] = sel.get('included', True)

    # Update case law included flags
    case_law = analysis.get('case_law', [])
    for sel in case_law_selections:
        idx = sel.get('index')
        if isinstance(idx, int) and 0 <= idx < len(case_law):
            case_law[idx]['included'] = sel.get('included', True)

    session.ai_analysis = analysis
    session.save(update_fields=['ai_analysis'])

    return Response({'saved': True})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def wizard_complete(request, session_slug):
    """Apply all wizard data to the real document models."""
    session = get_object_or_404(
        WizardSession,
        slug=session_slug,
        document__user=request.user
    )

    if session.status == 'completed':
        return Response({
            'already_completed': True,
            'document_slug': session.document.slug,
        })

    document = session.document
    errors = []

    try:
        _apply_wizard_to_document(session, document, errors)
        session.status = 'completed'
        session.save(update_fields=['status'])
    except Exception as e:
        logger.exception(f"Error completing wizard session {session.slug}")
        return Response(
            {'error': str(e), 'partial_errors': errors},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return Response({
        'success': True,
        'document_slug': document.slug,
        'errors': errors,
    })


# =============================================================================
# Background processing functions
# =============================================================================

import re


def _convert_to_24h(time_str):
    """Convert AI time strings like '2:00 PM', '2pm', '14:00' to 'HH:MM' for HTML time input."""
    if not time_str:
        return ''
    time_str = time_str.strip()

    # Already in HH:MM 24-hour format?
    match = re.match(r'^(\d{1,2}):(\d{2})$', time_str)
    if match:
        h, m = int(match.group(1)), int(match.group(2))
        if 0 <= h <= 23 and 0 <= m <= 59:
            return f'{h:02d}:{m:02d}'

    # Patterns like "2:00 PM", "2:30PM", "2:00 pm", "11:15 AM"
    match = re.match(r'^(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)$', time_str)
    if match:
        h, m, ampm = int(match.group(1)), int(match.group(2)), match.group(3).upper()
        if ampm == 'PM' and h != 12:
            h += 12
        elif ampm == 'AM' and h == 12:
            h = 0
        return f'{h:02d}:{m:02d}'

    # Patterns like "2 PM", "2pm", "11 AM", "3PM"
    match = re.match(r'^(\d{1,2})\s*(am|pm|AM|PM)$', time_str)
    if match:
        h, ampm = int(match.group(1)), match.group(2).upper()
        if ampm == 'PM' and h != 12:
            h += 12
        elif ampm == 'AM' and h == 12:
            h = 0
        return f'{h:02d}:00'

    # Couldn't parse — return empty so the field stays blank rather than showing garbage
    return ''


def _extract_story_background(session_id, story_text):
    """Background thread: parse story with AI and populate ai_extracted."""
    try:
        from documents.services.openai_service import OpenAIService

        session = WizardSession.objects.get(id=session_id)
        document = session.document

        # Use existing OpenAI parse_story service
        ai_service = OpenAIService()
        result = ai_service.parse_story(story_text)

        if not result or not result.get('success'):
            session.ai_extracted = {'error': result.get('error', 'AI parsing failed') if result else 'No response from AI'}
            session.save(update_fields=['ai_extracted'])
            return

        # parse_story returns {'success': True, 'sections': {...}}
        # The actual data (incident_overview, defendants, etc.) is inside 'sections'
        sections = result.get('sections', {})

        # Map AI extraction to wizard step structure
        ai_steps = {}

        # Step 1: When & Where
        overview = sections.get('incident_overview', {})
        if overview:
            # Convert AI time format (e.g., "2:00 PM") to HTML time input format ("14:00")
            raw_time = overview.get('incident_time', '') or ''
            incident_time = _convert_to_24h(raw_time)

            ai_steps['step_1'] = {
                'incident_date': overview.get('incident_date', '') or '',
                'incident_time': incident_time,
                'incident_location': overview.get('incident_location', '') or '',
                'address': overview.get('address', '') or '',
                'city': overview.get('city', '') or '',
                'state': overview.get('state', '') or '',
                'location_type': overview.get('location_type', '') or '',
                'location_type_other': overview.get('location_type_other', '') or '',
                'was_recording': overview.get('was_recording'),
                'recording_device': overview.get('recording_device', '') or '',
            }

        # Step 2: Who — field names now match wizard directly
        # (prompt returns title_rank, agency_name, defendant_type)
        defendants = sections.get('defendants', [])
        witnesses = sections.get('witnesses', [])
        if defendants or witnesses:
            # Normalize defendant fields (handle old prompt format gracefully)
            normalized_defendants = []
            for d in defendants:
                normalized_defendants.append({
                    'name': d.get('name', '') or '',
                    'badge_number': d.get('badge_number', '') or '',
                    'title_rank': d.get('title_rank', '') or d.get('title', '') or '',
                    'agency_name': d.get('agency_name', '') or d.get('agency', '') or '',
                    'defendant_type': d.get('defendant_type', 'individual') or 'individual',
                    'description': d.get('description', '') or '',
                    'agency_inferred': d.get('agency_inferred', False),
                })

            # Normalize witness fields
            normalized_witnesses = []
            for w in witnesses:
                normalized_witnesses.append({
                    'name': w.get('name', '') or '',
                    'description': w.get('description', '') or '',
                    'what_they_saw': w.get('what_they_saw', '') or '',
                    'was_recording': w.get('was_recording'),
                    'recording_device': w.get('recording_device', '') or '',
                })

            ai_steps['step_2'] = {
                'defendants': normalized_defendants,
                'witnesses': normalized_witnesses,
            }

        # Step 3: What happened
        narrative = sections.get('incident_narrative', {})
        if narrative:
            ai_steps['step_3'] = {
                'summary': narrative.get('summary', '') or '',
                'detailed_narrative': narrative.get('detailed_narrative', '') or '',
                'what_were_you_doing': narrative.get('what_were_you_doing', '') or '',
                'initial_contact': narrative.get('initial_contact', '') or '',
                'what_was_said': narrative.get('what_was_said', '') or '',
                'physical_actions': narrative.get('physical_actions', '') or '',
                'how_it_ended': narrative.get('how_it_ended', '') or '',
            }

        # Step 4: Why (from rights_violated)
        rights = sections.get('rights_violated', {})
        violations = rights.get('suggested_violations', [])
        if violations:
            # Map AI violation suggestions to our plain-language keys
            selections = []
            for v in violations:
                right = v.get('right', '').lower()
                # Check multiple keywords per category for better matching
                if 'search' in right and 'warrant' not in right:
                    selections.append('searched_without_warrant')
                if 'unreasonable search' in right or 'illegal search' in right or 'warrantless search' in right:
                    selections.append('searched_without_warrant')
                if 'arrest' in right or 'detention' in right or 'detain' in right:
                    selections.append('arrested_no_cause')
                if 'force' in right or 'brutal' in right or 'assault' in right or 'taser' in right or 'pepper spray' in right:
                    selections.append('excessive_force')
                if 'seizure' in right or 'property' in right or 'confiscat' in right:
                    selections.append('unlawful_seizure')
                if 'speech' in right or 'recording' in right or 'film' in right or 'press' in right:
                    selections.append('punished_for_speech')
                if 'recording' in right or 'film' in right or 'photograph' in right:
                    selections.append('punished_for_recording')
                if 'assembl' in right or 'protest' in right or 'gather' in right:
                    selections.append('punished_for_assembly')
                if 'racial' in right or 'race' in right or 'profil' in right:
                    selections.append('racial_discrimination')
                if 'gender' in right or 'sex' in right:
                    selections.append('gender_discrimination')
                if 'due process' in right:
                    selections.append('denied_due_process')
                if 'self-incrimination' in right or 'miranda' in right or 'fifth' in right or 'forced statement' in right:
                    selections.append('forced_statements')
                if 'medical' in right or 'deliberate indifference' in right:
                    selections.append('denied_medical_care')
                if 'retaliat' in right:
                    selections.append('retaliation')
            ai_steps['step_4'] = {
                'selections': list(set(selections)),
                'ai_violations': violations,  # Keep the full AI output for reference
            }

        # Step 5: Impact
        damages = sections.get('damages', {})
        if damages:
            ai_steps['step_5'] = {
                'physical_injuries': damages.get('physical_injuries', '') or '',
                'medical_treatment': damages.get('medical_treatment', '') or '',
                'emotional_distress': damages.get('emotional_distress', '') or '',
                'financial_losses': damages.get('financial_losses', '') or '',
                'lost_wages': damages.get('lost_wages', '') or '',
                'ongoing_effects': damages.get('ongoing_effects', '') or damages.get('other_damages', '') or '',
            }

        # Step 6: Evidence
        evidence = sections.get('evidence', [])
        if evidence:
            ai_steps['step_6'] = {
                'items': evidence,
                'evidence_types': list(set(
                    e.get('evidence_type', '') or e.get('type', '')
                    for e in evidence
                    if e.get('evidence_type') or e.get('type')
                )),
            }

        session.ai_extracted = ai_steps
        session.save(update_fields=['ai_extracted'])

        # Record AI usage
        document.record_ai_usage()

    except Exception as e:
        logger.exception(f"Error extracting story for wizard session {session_id}")
        try:
            session = WizardSession.objects.get(id=session_id)
            session.ai_extracted = {'error': str(e)}
            session.save(update_fields=['ai_extracted'])
        except Exception:
            pass


def _analyze_case_background(session_id):
    """Background thread: run final case analysis with AI."""
    try:
        from documents.services.openai_service import OpenAIService

        session = WizardSession.objects.get(id=session_id)
        document = session.document
        ai_service = OpenAIService()

        # Collect all interview data into a single narrative
        interview = session.interview_data
        case_summary = _build_case_summary(interview, session.raw_story)

        # Fetch the wizard analysis prompt from the database
        from documents.models import AIPrompt
        prompt = AIPrompt.objects.filter(
            prompt_type='wizard_analyze_case',
            is_active=True,
        ).first()

        if not prompt:
            raise ValueError(
                "AI prompt 'wizard_analyze_case' not found or inactive. "
                "Run 'python manage.py seed_ai_prompts' to populate prompts."
            )

        system_message = prompt.system_message

        # Conditionally add case law instructions if user opted in
        use_case_law = session.use_case_law
        if use_case_law:
            system_message += (
                "\n2. 'case_law': An array of relevant cases. For each:\n"
                "   - 'case_name': Full case citation (e.g., 'Graham v. Connor, 490 U.S. 386 (1989)')\n"
                "   - 'relevance': One sentence on why this case applies\n"
                "   - 'key_holding': The key legal principle from this case\n"
                "   Only include well-established, widely-cited Section 1983 cases. "
                "   Do NOT fabricate citations.\n"
            )

        response = ai_service.client.chat.completions.create(
            model=prompt.model_name,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": case_summary},
            ],
            response_format={"type": "json_object"},
            temperature=prompt.temperature,
            max_tokens=prompt.max_tokens,
        )

        import json
        analysis = json.loads(response.choices[0].message.content)

        session.ai_analysis = analysis
        session.analysis_status = 'completed'
        session.status = 'analyzed'
        session.save(update_fields=['ai_analysis', 'analysis_status', 'status'])

        # Record AI usage
        document.record_ai_usage()

    except Exception as e:
        logger.exception(f"Error analyzing case for wizard session {session_id}")
        try:
            session = WizardSession.objects.get(id=session_id)
            session.analysis_status = 'failed'
            session.analysis_error = str(e)
            session.save(update_fields=['analysis_status', 'analysis_error'])
        except Exception:
            pass


def _build_case_summary(interview_data, raw_story):
    """Build a comprehensive case summary from interview data for AI analysis."""
    parts = []

    parts.append(f"ORIGINAL STORY:\n{raw_story}\n")

    step_1 = interview_data.get('step_1', {})
    if step_1:
        parts.append("INCIDENT DETAILS:")
        if step_1.get('incident_date'):
            parts.append(f"  Date: {step_1['incident_date']}")
        if step_1.get('incident_time'):
            parts.append(f"  Time: {step_1['incident_time']}")
        if step_1.get('incident_location'):
            parts.append(f"  Location: {step_1['incident_location']}")
        if step_1.get('city'):
            parts.append(f"  City/State: {step_1.get('city', '')}, {step_1.get('state', '')}")
        parts.append("")

    step_2 = interview_data.get('step_2', {})
    if step_2:
        defendants = step_2.get('defendants', [])
        if defendants:
            parts.append("DEFENDANTS:")
            for d in defendants:
                name = d.get('name', 'Unknown')
                agency = d.get('agency_name', d.get('agency', ''))
                parts.append(f"  - {name} ({agency})" if agency else f"  - {name}")
            parts.append("")

    step_3 = interview_data.get('step_3', {})
    if step_3:
        parts.append("NARRATIVE:")
        if step_3.get('detailed_narrative'):
            parts.append(f"  {step_3['detailed_narrative']}")
        elif step_3.get('summary'):
            parts.append(f"  {step_3['summary']}")
        parts.append("")

    step_4 = interview_data.get('step_4', {})
    if step_4:
        selections = step_4.get('selections', [])
        if selections:
            parts.append("USER-IDENTIFIED VIOLATIONS:")
            for s in selections:
                parts.append(f"  - {s.replace('_', ' ').title()}")
        if step_4.get('additional_text'):
            parts.append(f"  Additional: {step_4['additional_text']}")
        parts.append("")

    step_5 = interview_data.get('step_5', {})
    if step_5:
        parts.append("DAMAGES:")
        for key in ['physical_injuries', 'emotional_distress', 'financial_losses',
                     'medical_treatment', 'lost_wages', 'ongoing_effects']:
            if step_5.get(key):
                parts.append(f"  {key.replace('_', ' ').title()}: {step_5[key]}")
        parts.append("")

    step_6 = interview_data.get('step_6', {})
    if step_6:
        types = step_6.get('evidence_types', [])
        if types:
            parts.append(f"EVIDENCE AVAILABLE: {', '.join(types)}")
        items = step_6.get('items', [])
        for item in items:
            if item.get('description'):
                parts.append(f"  - {item.get('title', '')}: {item['description']}")
        parts.append("")

    return '\n'.join(parts)


def _apply_wizard_to_document(session, document, errors):
    """Apply all wizard interview data to the real document models."""
    interview = session.interview_data

    # Ensure all sections exist
    _ensure_sections_exist(document)

    # Step 1: When & Where → IncidentOverview
    step_1 = interview.get('step_1', {})
    if step_1:
        try:
            section = document.sections.get(section_type='incident_overview')
            overview, _ = IncidentOverview.objects.get_or_create(section=section)

            if step_1.get('incident_date'):
                try:
                    from datetime import date
                    if isinstance(step_1['incident_date'], str):
                        overview.incident_date = date.fromisoformat(step_1['incident_date'])
                    else:
                        overview.incident_date = step_1['incident_date']
                except (ValueError, TypeError):
                    pass

            if step_1.get('incident_time'):
                try:
                    from datetime import time
                    if isinstance(step_1['incident_time'], str):
                        overview.incident_time = time.fromisoformat(step_1['incident_time'])
                    else:
                        overview.incident_time = step_1['incident_time']
                except (ValueError, TypeError):
                    pass

            for field in ['incident_location', 'city', 'state', 'location_type']:
                if step_1.get(field):
                    setattr(overview, field, step_1[field])

            overview.save()
            section.status = 'completed'
            section.save(update_fields=['status'])
        except Exception as e:
            errors.append(f'incident_overview: {str(e)}')

    # Step 2: Who → Defendants + Witnesses
    step_2 = interview.get('step_2', {})
    if step_2:
        # Defendants
        try:
            section = document.sections.get(section_type='defendants')
            for d_data in step_2.get('defendants', []):
                if d_data.get('name'):
                    Defendant.objects.create(
                        section=section,
                        name=d_data.get('name', ''),
                        badge_number=d_data.get('badge_number', ''),
                        title_rank=d_data.get('title_rank', ''),
                        agency_name=d_data.get('agency_name', d_data.get('agency', '')),
                        description=d_data.get('description', ''),
                        defendant_type=d_data.get('defendant_type', 'individual'),
                        agency_inferred=d_data.get('agency_inferred', False),
                    )
            if section.defendants.exists():
                section.status = 'completed'
                section.save(update_fields=['status'])
        except Exception as e:
            errors.append(f'defendants: {str(e)}')

        # Witnesses
        try:
            section = document.sections.get(section_type='witnesses')
            for w_data in step_2.get('witnesses', []):
                if w_data.get('name'):
                    Witness.objects.create(
                        section=section,
                        name=w_data.get('name', ''),
                        relationship=w_data.get('relationship', ''),
                        what_they_witnessed=w_data.get('what_they_witnessed',
                                                        w_data.get('what_they_saw', '')),
                        contact_info=w_data.get('contact_info', ''),
                    )
            if section.witnesses.exists():
                section.status = 'completed'
                section.save(update_fields=['status'])
        except Exception as e:
            errors.append(f'witnesses: {str(e)}')

    # Step 3: What → IncidentNarrative
    step_3 = interview.get('step_3', {})
    if step_3:
        try:
            section = document.sections.get(section_type='incident_narrative')
            narrative, _ = IncidentNarrative.objects.get_or_create(section=section)
            for field in ['summary', 'detailed_narrative', 'what_were_you_doing',
                          'initial_contact', 'what_was_said', 'physical_actions', 'how_it_ended']:
                if step_3.get(field):
                    setattr(narrative, field, step_3[field])
            narrative.save()
            if narrative.detailed_narrative and len(narrative.detailed_narrative) >= 50:
                section.status = 'completed'
            else:
                section.status = 'in_progress'
            section.save(update_fields=['status'])
        except Exception as e:
            errors.append(f'incident_narrative: {str(e)}')

    # Step 4: Why → RightsViolated
    step_4 = interview.get('step_4', {})
    if step_4:
        try:
            section = document.sections.get(section_type='rights_violated')
            rights, _ = RightsViolated.objects.get_or_create(section=section)
            selections = step_4.get('selections', [])
            additional = step_4.get('additional_text', '')

            for selection in selections:
                mapping = VIOLATION_MAP.get(selection)
                if mapping:
                    amendment_field = f"{mapping['amendment']}_amendment"
                    setattr(rights, amendment_field, True)
                    if mapping.get('sub'):
                        setattr(rights, mapping['sub'], True)

            if additional:
                rights.other_rights = additional

            # Also apply INCLUDED AI analysis violations
            analysis = session.ai_analysis
            ai_violations = analysis.get('violations', [])
            # Collect details per amendment from included violations
            amendment_details = {}
            for v in ai_violations:
                if v.get('included') is False:
                    continue
                amendment_str = (v.get('amendment') or '').lower()
                violation_type = (v.get('violation_type') or '').lower()
                description = v.get('description', '')

                # Map AI amendment names to model field prefixes
                amendment_key = None
                if 'fourth' in amendment_str:
                    amendment_key = 'fourth'
                elif 'first' in amendment_str:
                    amendment_key = 'first'
                elif 'fifth' in amendment_str:
                    amendment_key = 'fifth'
                elif 'fourteenth' in amendment_str:
                    amendment_key = 'fourteenth'

                if amendment_key:
                    setattr(rights, f'{amendment_key}_amendment', True)

                    # Try to set specific sub-violation fields
                    sub_field = _map_ai_violation_to_field(amendment_key, violation_type)
                    if sub_field and hasattr(rights, sub_field):
                        setattr(rights, sub_field, True)

                    # Collect descriptions for amendment details
                    if description:
                        if amendment_key not in amendment_details:
                            amendment_details[amendment_key] = []
                        label = v.get('violation_type', '')
                        amendment_details[amendment_key].append(
                            f"{label}: {description}" if label else description
                        )

            # Write collected details to amendment detail fields
            for amendment_key, details in amendment_details.items():
                details_field = f'{amendment_key}_amendment_details'
                if hasattr(rights, details_field):
                    existing = getattr(rights, details_field) or ''
                    new_details = '\n'.join(details)
                    if existing:
                        setattr(rights, details_field, f"{existing}\n{new_details}")
                    else:
                        setattr(rights, details_field, new_details)

            rights.save()
            if any(getattr(rights, f'{a}_amendment', False)
                   for a in ['first', 'fourth', 'fifth', 'fourteenth']):
                section.status = 'completed'
            else:
                section.status = 'in_progress'
            section.save(update_fields=['status'])
        except Exception as e:
            errors.append(f'rights_violated: {str(e)}')

    # Step 5: Impact → Damages
    step_5 = interview.get('step_5', {})
    if step_5:
        try:
            section = document.sections.get(section_type='damages')
            damages, _ = Damages.objects.get_or_create(section=section)

            if step_5.get('physical_injuries'):
                damages.physical_injury = True
                damages.physical_injury_description = step_5['physical_injuries']
            if step_5.get('medical_treatment'):
                damages.medical_treatment = True
                damages.medical_treatment_description = step_5['medical_treatment']
            if step_5.get('emotional_distress'):
                damages.emotional_distress = True
                damages.emotional_distress_description = step_5['emotional_distress']
            if step_5.get('financial_losses'):
                damages.property_damage = True
                damages.property_damage_description = step_5['financial_losses']
            if step_5.get('ongoing_effects'):
                damages.other_damages = step_5['ongoing_effects']

            damages.save()
            section.status = 'completed'
            section.save(update_fields=['status'])
        except Exception as e:
            errors.append(f'damages: {str(e)}')

    # Step 6: Evidence
    step_6 = interview.get('step_6', {})
    if step_6:
        try:
            section = document.sections.get(section_type='evidence')
            for e_data in step_6.get('items', []):
                if e_data.get('title') or e_data.get('description'):
                    Evidence.objects.create(
                        section=section,
                        evidence_type=e_data.get('evidence_type', 'other'),
                        title=e_data.get('title', ''),
                        description=e_data.get('description', ''),
                        is_in_possession=e_data.get('is_in_possession', True),
                    )
            if section.evidence_items.exists():
                section.status = 'completed'
                section.save(update_fields=['status'])
        except Exception as e:
            errors.append(f'evidence: {str(e)}')

    # Apply relief recommendations from AI analysis
    analysis = session.ai_analysis
    if analysis.get('relief_recommendations'):
        try:
            section = document.sections.get(section_type='relief_sought')
            relief, _ = ReliefSought.objects.get_or_create(section=section)
            for rec in analysis['relief_recommendations']:
                relief_type = rec.get('type', '')
                recommended = rec.get('recommended', False)
                if relief_type and recommended:
                    if hasattr(relief, relief_type):
                        setattr(relief, relief_type, True)
                    if relief_type == 'jury_trial':
                        relief.jury_trial_demanded = True
            relief.attorney_fees = True  # Always recommend
            relief.save()
            section.status = 'completed'
            section.save(update_fields=['status'])
        except Exception as e:
            errors.append(f'relief_sought: {str(e)}')

    # Invalidate any cached complaint
    document.invalidate_generated_complaint()


def _ensure_sections_exist(document):
    """Make sure all document sections exist."""
    from documents.views import SECTION_CONFIG
    for section_type, config in SECTION_CONFIG.items():
        DocumentSection.objects.get_or_create(
            document=document,
            section_type=section_type,
            defaults={
                'order': config.get('order', 0),
                'status': 'not_started',
            }
        )
