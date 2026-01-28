from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import models as db_models
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from decimal import Decimal, InvalidOperation
import stripe
import json
import threading
from .help_content import get_section_help
from django.core.mail import send_mail
from django.contrib.admin.views.decorators import staff_member_required
from .models import (
    Document, DocumentSection, PlaintiffInfo, IncidentOverview,
    Defendant, IncidentNarrative, RightsViolated, Witness,
    Evidence, Damages, PriorComplaints, ReliefSought,
    PromoCode, PromoCodeUsage, PayoutRequest,
    VideoEvidence, VideoCapture, VideoSpeaker
)

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


def get_ai_usage_info(document):
    """Get AI usage info for including in API responses."""
    return {
        'ai_remaining': document.user.get_free_ai_remaining(),
        'ai_usage_display': document.get_ai_usage_display(),
    }


def check_section_complete(section, obj):
    """
    Check if a section has enough data to be auto-marked as complete.
    Returns True if the section should be marked complete.
    """
    section_type = section.section_type

    if section_type == 'plaintiff_info':
        # Complete if first and last name provided, plus at least one contact method
        has_name = bool(obj.first_name and obj.last_name)
        has_contact = bool(obj.phone or obj.email)
        return has_name and has_contact

    elif section_type == 'incident_overview':
        # Complete if date and location are filled
        return bool(obj.incident_date and obj.incident_location and obj.city)

    elif section_type == 'incident_narrative':
        # Complete if main narrative is filled (at least 50 chars)
        return bool(obj.detailed_narrative and len(obj.detailed_narrative) >= 50)

    elif section_type == 'rights_violated':
        # Complete if at least one amendment is checked
        return any([
            obj.first_amendment,
            obj.fourth_amendment,
            obj.fifth_amendment,
            obj.fourteenth_amendment
        ])

    elif section_type == 'damages':
        # Complete if at least one damage type is indicated
        return any([
            obj.physical_injury,
            obj.emotional_distress,
            obj.property_damage,
            obj.lost_wages,
            obj.reputation_harm
        ])

    elif section_type == 'prior_complaints':
        # Always complete - it's ok to have none
        return True

    elif section_type == 'relief_sought':
        # Complete if attorney_fees is checked AND at least one relief type
        has_relief = any([
            obj.compensatory_damages,
            obj.punitive_damages,
            obj.declaratory_relief,
            obj.injunctive_relief
        ])
        return obj.attorney_fees and has_relief

    # For multiple-item sections (defendants, witnesses, evidence),
    # completion is checked separately
    return False


def check_multiple_section_complete(section):
    """Check if a multiple-item section has at least one item."""
    section_type = section.section_type

    if section_type == 'defendants':
        return Defendant.objects.filter(section=section).exists()
    elif section_type == 'witnesses':
        # Witnesses are optional - can be marked N/A
        return Witness.objects.filter(section=section).exists()
    elif section_type == 'evidence':
        return Evidence.objects.filter(section=section).exists()

    return False


from .forms import (
    DocumentForm, PlaintiffInfoForm, PlaintiffAttorneyForm, IncidentOverviewForm,
    DefendantForm, IncidentNarrativeForm, RightsViolatedForm,
    WitnessForm, EvidenceForm, DamagesForm, PriorComplaintsForm,
    ReliefSoughtForm, SectionStatusForm
)


# Section type to model/form mapping
SECTION_CONFIG = {
    'plaintiff_info': {
        'model': PlaintiffInfo,
        'form': PlaintiffAttorneyForm,  # Only attorney form - plaintiff info from profile
        'title': 'Plaintiff Information',
        'description': 'Your information from your profile will be used. Select if you have an attorney.',
        'profile_based': True,  # Flag to indicate this section uses profile data
    },
    'incident_overview': {
        'model': IncidentOverview,
        'form': IncidentOverviewForm,
        'title': 'Incident Overview',
        'description': 'Provide basic details about when and where the incident occurred.',
    },
    'defendants': {
        'model': Defendant,
        'form': DefendantForm,
        'title': 'Government Defendants',
        'description': 'Identify the government agencies and individual officers involved.',
        'multiple': True,
    },
    'incident_narrative': {
        'model': IncidentNarrative,
        'form': IncidentNarrativeForm,
        'title': 'Incident Narrative',
        'description': 'Describe in detail what happened during the incident.',
    },
    'rights_violated': {
        'model': RightsViolated,
        'form': RightsViolatedForm,
        'title': 'Rights Violated',
        'description': 'Identify which constitutional rights were violated.',
    },
    'witnesses': {
        'model': Witness,
        'form': WitnessForm,
        'title': 'Witnesses',
        'description': 'List any witnesses to the incident.',
        'multiple': True,
    },
    'evidence': {
        'model': Evidence,
        'form': EvidenceForm,
        'title': 'Evidence',
        'description': 'Document any evidence you have related to the incident.',
        'multiple': True,
    },
    'damages': {
        'model': Damages,
        'form': DamagesForm,
        'title': 'Damages',
        'description': 'Describe any injuries, losses, or harm you suffered.',
    },
    'prior_complaints': {
        'model': PriorComplaints,
        'form': PriorComplaintsForm,
        'title': 'Prior Complaints',
        'description': 'Document any prior complaints or attempts to resolve the matter.',
    },
    'relief_sought': {
        'model': ReliefSought,
        'form': ReliefSoughtForm,
        'title': 'Relief Sought',
        'description': 'Specify what outcome you are seeking from this case.',
    },
}


@login_required
def document_list(request):
    """List all documents for the current user."""
    documents = Document.objects.filter(user=request.user)
    return render(request, 'documents/document_list.html', {'documents': documents})


@login_required
def document_create(request):
    """Create a new document with all sections."""
    # Check if user has completed their profile
    if not request.user.has_complete_profile():
        messages.warning(request, 'Please complete your profile before creating a document. Your profile information will appear on legal documents.')
        return redirect('accounts:profile_complete')

    # Check if user needs to see purchase prompt (soft gate)
    # Skip if user already chose to continue with limited access in this session
    skip_purchase_prompt = request.session.get('skip_purchase_prompt', False)

    if request.user.needs_purchase_prompt() and not skip_purchase_prompt:
        # Handle "continue with limited access" form submission
        if request.method == 'POST' and 'continue_limited' in request.POST:
            # User chose to continue with limited access - set session flag and redirect to GET
            request.session['skip_purchase_prompt'] = True
            return redirect('documents:document_create')
        else:
            # Show purchase interstitial
            prices = {
                'single': int(settings.DOCUMENT_PRICE_SINGLE),
                'pack': int(settings.DOCUMENT_PRICE_3PACK),
                'pack_per_doc': int(settings.DOCUMENT_PRICE_3PACK / 3),
                'pack_savings': int(settings.DOCUMENT_PRICE_SINGLE * 3 - settings.DOCUMENT_PRICE_3PACK),
                'monthly': int(settings.SUBSCRIPTION_PRICE_MONTHLY),
                'annual': int(settings.SUBSCRIPTION_PRICE_ANNUAL),
            }
            return render(request, 'documents/purchase_required.html', {'prices': prices})

    if request.method == 'POST':
        form = DocumentForm(request.POST)
        if form.is_valid():
            document = form.save(commit=False)
            document.user = request.user
            document.save()

            # Create all sections for the document
            section_types = [choice[0] for choice in DocumentSection.SECTION_TYPES]
            for order, section_type in enumerate(section_types):
                DocumentSection.objects.create(
                    document=document,
                    section_type=section_type,
                    order=order
                )

            # Auto-populate plaintiff info from user profile
            plaintiff_section = document.sections.get(section_type='plaintiff_info')
            PlaintiffInfo.objects.create(
                section=plaintiff_section,
                first_name=request.user.first_name,
                middle_name=request.user.middle_name,
                last_name=request.user.last_name,
                street_address=request.user.street_address,
                city=request.user.city,
                state=request.user.state,
                zip_code=request.user.zip_code,
                phone=request.user.phone,
                email=request.user.email,
                is_pro_se=True  # Default to pro se
            )
            # Mark plaintiff_info as complete since we have all required data
            plaintiff_section.status = 'completed'
            plaintiff_section.save()

            messages.success(request, 'Document created! Your information has been pre-filled from your profile.')
            return redirect('documents:tell_your_story', document_id=document.id)
    else:
        form = DocumentForm()

    return render(request, 'documents/document_create.html', {'form': form})


@login_required
def document_detail(request, document_id):
    """Overview of document with all sections and their status."""
    document = get_object_or_404(Document, id=document_id, user=request.user)

    # Redirect to Tell Your Story if not completed
    if not document.has_story():
        messages.info(request, 'Please tell your story first. This helps us understand your case and pre-fill relevant sections.')
        return redirect('documents:tell_your_story', document_id=document.id)

    # Get sections and order them according to SECTION_TYPES
    sections_queryset = document.sections.all()
    section_type_order = [choice[0] for choice in DocumentSection.SECTION_TYPES]
    sections = sorted(sections_queryset, key=lambda s: section_type_order.index(s.section_type) if s.section_type in section_type_order else 999)

    # Check for defendants with AI-inferred agencies that need review
    defendants_needing_review = []
    defendants_missing_address = []
    defendants_section = sections_queryset.filter(section_type='defendants').first()
    if defendants_section:
        defendants_needing_review = defendants_section.defendants.filter(agency_inferred=True)
        # Check for defendants missing address (required for serving legal documents)
        from django.db.models import Q
        defendants_missing_address = defendants_section.defendants.filter(
            Q(address__isnull=True) | Q(address='')
        )

    # Check for court district issues
    court_district_filled = False
    court_district_confirmed = False
    court_district_issue = False
    incident_section = sections_queryset.filter(section_type='incident_overview').first()
    if incident_section:
        try:
            incident_overview = incident_section.incident_overview
            court_district_filled = bool(incident_overview.federal_district_court)
            court_district_confirmed = incident_overview.court_district_confirmed
            court_district_issue = not court_district_filled or not court_district_confirmed
        except Exception:
            court_district_issue = True

    # Add config info to each section
    sections_with_config = []
    for section in sections:
        config = SECTION_CONFIG.get(section.section_type, {})
        sections_with_config.append({
            'section': section,
            'title': config.get('title', section.get_section_type_display()),
            'description': config.get('description', ''),
        })

    return render(request, 'documents/document_detail.html', {
        'document': document,
        'sections': sections_with_config,
        'defendants_needing_review': defendants_needing_review,
        'defendants_missing_address': defendants_missing_address,
        'court_district_filled': court_district_filled,
        'court_district_confirmed': court_district_confirmed,
        'court_district_issue': court_district_issue,
    })


@login_required
def section_edit(request, document_id, section_type):
    """Edit a specific section of the document (interview style)."""
    document = get_object_or_404(Document, id=document_id, user=request.user)

    # Block editing for finalized or expired documents
    if not document.can_edit():
        if document.payment_status == 'finalized':
            messages.info(request, 'This document has been finalized and cannot be edited.')
        elif document.payment_status == 'expired':
            messages.warning(request, 'This document has expired. Please upgrade to continue editing.')
        return redirect('documents:document_detail', document_id=document.id)

    # Block section access until user tells their story
    if not document.has_story():
        messages.info(request, 'Please tell your story first. This helps us understand your case and pre-fill relevant sections.')
        return redirect('documents:tell_your_story', document_id=document.id)

    section = get_object_or_404(DocumentSection, document=document, section_type=section_type)

    config = SECTION_CONFIG.get(section_type)
    if not config:
        messages.error(request, 'Invalid section type.')
        return redirect('documents:document_detail', document_id=document.id)

    Model = config['model']
    Form = config['form']
    is_multiple = config.get('multiple', False)
    profile_prefilled = False

    # Get or create the section data
    is_profile_based = config.get('profile_based', False)

    if is_multiple:
        # For multiple items (defendants, witnesses, evidence)
        items = Model.objects.filter(section=section)
        # For evidence section, prefetch video_evidence and captures for YouTube integration
        if section_type == 'evidence':
            items = items.prefetch_related('video_evidence__captures')
        form = Form()
        instance = None
    else:
        # For single item sections
        try:
            instance = Model.objects.get(section=section)
        except Model.DoesNotExist:
            instance = None
        items = None

        # For plaintiff_info, ensure the PlaintiffInfo record exists with profile data
        if section_type == 'plaintiff_info' and instance is None:
            # Create PlaintiffInfo from user profile
            user = request.user
            instance = Model.objects.create(
                section=section,
                first_name=user.first_name,
                middle_name=user.middle_name,
                last_name=user.last_name,
                street_address=user.street_address,
                city=user.city,
                state=user.state,
                zip_code=user.zip_code,
                phone=user.phone,
                email=user.email,
                is_pro_se=True
            )
            profile_prefilled = True

        form = Form(instance=instance)

    if request.method == 'POST':
        if 'save_and_continue' in request.POST or 'save' in request.POST:
            form = Form(request.POST, instance=instance)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.section = section
                obj.save()

                # Invalidate cached complaint since data changed
                document.invalidate_generated_complaint()

                # Auto-update section status based on completeness
                if section.status not in ['completed', 'not_applicable']:
                    if check_section_complete(section, obj):
                        section.status = 'completed'
                        section.save()
                        messages.success(request, f'{config["title"]} saved and marked complete!')
                    elif section.status == 'not_started':
                        section.status = 'in_progress'
                        section.save()
                        messages.success(request, f'{config["title"]} saved.')
                    else:
                        messages.success(request, f'{config["title"]} saved.')
                else:
                    messages.success(request, f'{config["title"]} saved.')

                if 'save_and_continue' in request.POST:
                    # Go to next section
                    next_section = document.sections.filter(order__gt=section.order).first()
                    if next_section:
                        return redirect('documents:section_edit',
                                       document_id=document.id,
                                       section_type=next_section.section_type)
                    else:
                        # Check if all sections are actually completed
                        all_sections = document.sections.all()
                        completed_count = all_sections.filter(status__in=['completed', 'not_applicable']).count()
                        if completed_count == all_sections.count():
                            messages.success(request, 'All sections completed! Your document is ready for review.')
                        else:
                            messages.info(request, 'You\'ve reached the last section. Review your document to see what still needs attention.')
                        return redirect('documents:document_detail', document_id=document.id)

                return redirect('documents:section_edit',
                               document_id=document.id,
                               section_type=section_type)

    # Get previous and next sections for navigation
    prev_section = document.sections.filter(order__lt=section.order).last()
    next_section = document.sections.filter(order__gt=section.order).first()

    # Get help content for this section
    help_content = get_section_help(section_type)

    # Get ordered sections for sidebar navigation
    sections_queryset = document.sections.all()
    section_type_order = [choice[0] for choice in DocumentSection.SECTION_TYPES]
    ordered_sections = sorted(sections_queryset, key=lambda s: section_type_order.index(s.section_type) if s.section_type in section_type_order else 999)

    context = {
        'document': document,
        'section': section,
        'form': form,
        'items': items,
        'is_multiple': is_multiple,
        'config': config,
        'prev_section': prev_section,
        'next_section': next_section,
        'status_form': SectionStatusForm(instance=section),
        'help_content': help_content,
        'profile_prefilled': profile_prefilled,
        'is_profile_based': is_profile_based,
        'can_use_video_analysis': request.user.can_use_video_analysis(),
        'ordered_sections': ordered_sections,
    }

    # For profile-based sections, add user profile data for read-only display
    if is_profile_based:
        context['user_profile'] = request.user

    # For evidence section, add video evidences for sidebar display
    if section_type == 'evidence' and request.user.can_use_video_analysis():
        video_evidences = VideoEvidence.objects.filter(
            evidence__section=section
        ).prefetch_related('captures').select_related('evidence')
        context['video_evidences'] = video_evidences

    return render(request, 'documents/section_edit.html', context)


@login_required
def add_multiple_item(request, document_id, section_type):
    """Add an item to a multiple-item section (defendants, witnesses, evidence)."""
    document = get_object_or_404(Document, id=document_id, user=request.user)
    section = get_object_or_404(DocumentSection, document=document, section_type=section_type)

    config = SECTION_CONFIG.get(section_type)
    if not config or not config.get('multiple'):
        messages.error(request, 'Invalid section type.')
        return redirect('documents:document_detail', document_id=document.id)

    Form = config['form']

    if request.method == 'POST':
        form = Form(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.section = section
            obj.save()

            # For evidence in possession with no location, default to incident location
            if section_type == 'evidence' and hasattr(obj, 'is_in_possession'):
                if obj.is_in_possession and not obj.location_obtained:
                    try:
                        overview_section = document.sections.get(section_type='incident_overview')
                        incident_overview = IncidentOverview.objects.get(section=overview_section)
                        location_parts = []
                        if incident_overview.incident_location:
                            location_parts.append(incident_overview.incident_location)
                        if incident_overview.city:
                            location_parts.append(incident_overview.city)
                        if incident_overview.state:
                            location_parts.append(incident_overview.state)
                        if location_parts:
                            obj.location_obtained = ', '.join(location_parts)
                            obj.save()
                    except (DocumentSection.DoesNotExist, IncidentOverview.DoesNotExist):
                        pass

            # Invalidate cached complaint since data changed
            document.invalidate_generated_complaint()

            # Auto-update section status based on completeness
            if section.status not in ['completed', 'not_applicable']:
                if check_multiple_section_complete(section):
                    section.status = 'completed'
                    section.save()
                    messages.success(request, f'{config["title"][:-1]} added. Section marked complete!')
                elif section.status == 'not_started':
                    section.status = 'in_progress'
                    section.save()
                    messages.success(request, f'{config["title"][:-1]} added.')
                else:
                    messages.success(request, f'{config["title"][:-1]} added.')
            else:
                messages.success(request, f'{config["title"][:-1]} added.')

            # Return JSON for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'item_id': obj.id,
                    'item_str': str(obj),
                    'message': f'{config["title"][:-1]} added.'
                })

            return redirect('documents:section_edit',
                           document_id=document.id,
                           section_type=section_type)

    return redirect('documents:section_edit',
                   document_id=document.id,
                   section_type=section_type)


@login_required
def delete_multiple_item(request, document_id, section_type, item_id):
    """Delete an item from a multiple-item section."""
    document = get_object_or_404(Document, id=document_id, user=request.user)
    section = get_object_or_404(DocumentSection, document=document, section_type=section_type)

    config = SECTION_CONFIG.get(section_type)
    if not config or not config.get('multiple'):
        messages.error(request, 'Invalid section type.')
        return redirect('documents:document_detail', document_id=document.id)

    Model = config['model']
    item = get_object_or_404(Model, id=item_id, section=section)
    item.delete()

    # Invalidate cached complaint since data changed
    document.invalidate_generated_complaint()

    messages.success(request, 'Item deleted.')
    return redirect('documents:section_edit',
                   document_id=document.id,
                   section_type=section_type)


@login_required
def edit_defendant(request, document_id, defendant_id):
    """Edit a specific defendant with agency suggestion support."""
    from .forms import DefendantForm

    document = get_object_or_404(Document, id=document_id, user=request.user)
    defendant = get_object_or_404(Defendant, id=defendant_id, section__document=document)
    section = defendant.section

    # Get incident overview for city/state context
    incident_overview = None
    try:
        overview_section = document.sections.get(section_type='incident_overview')
        incident_overview = IncidentOverview.objects.get(section=overview_section)
    except (DocumentSection.DoesNotExist, IncidentOverview.DoesNotExist):
        pass

    if request.method == 'POST':
        form = DefendantForm(request.POST, instance=defendant)
        if form.is_valid():
            form.save()
            # Invalidate cached complaint since data changed
            document.invalidate_generated_complaint()
            messages.success(request, 'Defendant updated successfully.')
            return redirect('documents:section_edit', document_id=document.id, section_type='defendants')
    else:
        form = DefendantForm(instance=defendant)

    return render(request, 'documents/edit_defendant.html', {
        'document': document,
        'defendant': defendant,
        'form': form,
        'incident_overview': incident_overview,
        'section': section,
    })


@login_required
@require_POST
def accept_defendant_agency(request, document_id, defendant_id):
    """Accept/confirm an AI-suggested agency as correct."""
    document = get_object_or_404(Document, id=document_id, user=request.user)
    defendant = get_object_or_404(Defendant, id=defendant_id, section__document=document)

    # Mark the agency as verified (no longer AI-inferred) and address as verified
    defendant.agency_inferred = False
    defendant.address_verified = True
    defendant.save()

    # Invalidate cached complaint since data changed
    document.invalidate_generated_complaint()

    messages.success(request, f'Agency for {defendant.name} confirmed.')
    return redirect('documents:section_edit', document_id=document.id, section_type='defendants')


@login_required
def edit_witness(request, document_id, witness_id):
    """Edit a specific witness with enhanced fields."""
    from .forms import WitnessForm

    document = get_object_or_404(Document, id=document_id, user=request.user)
    witness = get_object_or_404(Witness, id=witness_id, section__document=document)
    section = witness.section

    if request.method == 'POST':
        form = WitnessForm(request.POST, instance=witness)
        if form.is_valid():
            form.save()
            # Invalidate cached complaint since data changed
            document.invalidate_generated_complaint()
            messages.success(request, 'Witness updated successfully.')
            return redirect('documents:section_edit', document_id=document.id, section_type='witnesses')
    else:
        form = WitnessForm(instance=witness)

    return render(request, 'documents/edit_witness.html', {
        'document': document,
        'witness': witness,
        'form': form,
        'section': section,
    })


@login_required
def edit_evidence(request, document_id, evidence_id):
    """Edit a specific piece of evidence."""
    from .forms import EvidenceForm

    document = get_object_or_404(Document, id=document_id, user=request.user)
    evidence = get_object_or_404(Evidence, id=evidence_id, section__document=document)
    section = evidence.section

    # Get incident location, date, and time for "Use Incident" buttons
    incident_location_str = ''
    incident_date = None
    incident_time = None
    incident_time_display = ''
    try:
        overview_section = document.sections.get(section_type='incident_overview')
        incident_overview = IncidentOverview.objects.get(section=overview_section)
        location_parts = []
        if incident_overview.incident_location:
            location_parts.append(incident_overview.incident_location)
        if incident_overview.city:
            location_parts.append(incident_overview.city)
        if incident_overview.state:
            location_parts.append(incident_overview.state)
        incident_location_str = ', '.join(location_parts) if location_parts else ''
        incident_date = incident_overview.incident_date
        incident_time = incident_overview.incident_time
        if incident_time:
            incident_time_display = incident_time.strftime('%I:%M %p').lstrip('0')
    except (DocumentSection.DoesNotExist, IncidentOverview.DoesNotExist):
        pass

    # Get video evidence if it exists
    video_evidence = None
    try:
        video_evidence = evidence.video_evidence
    except VideoEvidence.DoesNotExist:
        pass

    if request.method == 'POST':
        form = EvidenceForm(request.POST, instance=evidence)
        if form.is_valid():
            form.save()
            # Invalidate cached complaint since data changed
            document.invalidate_generated_complaint()
            messages.success(request, 'Evidence updated successfully.')
            return redirect('documents:section_edit', document_id=document.id, section_type='evidence')
    else:
        form = EvidenceForm(instance=evidence)

    return render(request, 'documents/edit_evidence.html', {
        'document': document,
        'evidence': evidence,
        'form': form,
        'section': section,
        'incident_location': incident_location_str,
        'incident_date': incident_date,
        'incident_time': incident_time,
        'incident_time_display': incident_time_display,
        'video_evidence': video_evidence,
        'can_use_video_analysis': request.user.can_use_video_analysis(),
    })


@login_required
@require_POST
def update_section_status(request, document_id, section_type):
    """Update the status of a section (AJAX endpoint)."""
    document = get_object_or_404(Document, id=document_id, user=request.user)
    section = get_object_or_404(DocumentSection, document=document, section_type=section_type)

    status = request.POST.get('status')
    notes = request.POST.get('notes', '')

    if status in dict(DocumentSection.STATUS_CHOICES):
        section.status = status
        section.notes = notes
        section.save()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'status': status,
                'status_display': section.get_status_display()
            })

        messages.success(request, f'Section marked as {section.get_status_display()}.')
    else:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Invalid status'})
        messages.error(request, 'Invalid status.')

    return redirect('documents:section_edit',
                   document_id=document.id,
                   section_type=section_type)


@login_required
def document_delete(request, document_id):
    """Delete a document."""
    document = get_object_or_404(Document, id=document_id, user=request.user)

    if request.method == 'POST':
        document.delete()
        messages.success(request, 'Document deleted.')
        return redirect('documents:document_list')

    return render(request, 'documents/document_confirm_delete.html', {'document': document})


@login_required
@require_POST
def fill_test_data(request, document_id):
    """Fill document with realistic test data (test users only)."""
    document = get_object_or_404(Document, id=document_id, user=request.user)

    # Check if user is a test user
    if not request.user.is_test_user:
        messages.error(request, 'Test data feature is only available for test users.')
        return redirect('documents:document_detail', document_id=document.id)

    try:
        from .test_data import populate_test_data
        populate_test_data(document)
        messages.success(request, 'Document filled with sample test data!')
    except Exception as e:
        messages.error(request, f'Error filling test data: {str(e)}')

    return redirect('documents:document_detail', document_id=document.id)


@login_required
def document_preview(request, document_id):
    """Show preview for finalized documents, redirect others to final_review."""
    document = get_object_or_404(Document, id=document_id, user=request.user)

    # Finalized documents show the preview/PDF view (read-only)
    if document.payment_status == 'finalized':
        document_data = _collect_document_data(document)

        # Check if user wants to generate/download PDF
        generate_pdf = request.GET.get('generate') == 'true'

        return render(request, 'documents/document_preview.html', {
            'document': document,
            'document_data': document_data,
            'generate_pdf': generate_pdf,
        })

    # Non-finalized documents go to final review for editing
    return redirect('documents:final_review', document_id=document_id)


@login_required
def document_review(request, document_id):
    """Review and edit the complete document with inline editing.

    Shows the full legal complaint with edit buttons for each section.
    No AI involvement - just displays and edits saved data.
    """
    document = get_object_or_404(Document, id=document_id, user=request.user)

    # Finalized documents go to preview/PDF view (no editing allowed)
    if document.payment_status == 'finalized':
        messages.info(request, 'This document has been finalized. You can view or download the PDF.')
        return redirect('documents:document_preview', document_id=document.id)

    # Collect all document data from the database
    document_data = _collect_document_data(document)

    # Load section data with forms for editing (in SECTION_TYPES order)
    sections_data = {}
    section_type_order = [choice[0] for choice in DocumentSection.SECTION_TYPES]
    ordered_sections = sorted(document.sections.all(), key=lambda s: section_type_order.index(s.section_type) if s.section_type in section_type_order else 999)
    for section in ordered_sections:
        config = SECTION_CONFIG.get(section.section_type, {})
        Model = config.get('model')
        Form = config.get('form')
        is_multiple = config.get('multiple', False)

        if Model and Form:
            if is_multiple:
                items = list(Model.objects.filter(section=section))
                form = Form()  # Empty form for adding new items
                sections_data[section.section_type] = {
                    'section': section,
                    'config': config,
                    'items': items,
                    'form': form,
                    'is_multiple': True,
                }
            else:
                try:
                    instance = Model.objects.get(section=section)
                    form = Form(instance=instance)
                except Model.DoesNotExist:
                    instance = None
                    form = Form()

                sections_data[section.section_type] = {
                    'section': section,
                    'config': config,
                    'data': instance,
                    'form': form,
                    'is_multiple': False,
                }

    context = {
        'document': document,
        'sections_data': sections_data,
        'section_config': SECTION_CONFIG,
        'document_data': document_data,
    }

    return render(request, 'documents/document_review.html', context)


def _collect_document_data(document):
    """Collect all document data for the generator."""
    data = {
        'has_minimum_data': False,
        'plaintiff': {},
        'defendants': [],
        'incident': {},
        'narrative': {},
        'rights_violated': {},
        'damages': {},
        'relief': {},
        'court': '',
    }

    # Plaintiff info
    try:
        plaintiff_section = document.sections.get(section_type='plaintiff_info')
        pi = plaintiff_section.plaintiff_info
        data['plaintiff'] = {
            'first_name': pi.first_name,
            'middle_name': pi.middle_name,
            'last_name': pi.last_name,
            'street_address': pi.street_address,
            'city': pi.city,
            'state': pi.state,
            'zip_code': pi.zip_code,
            'phone': pi.phone,
            'email': pi.email,
            'is_pro_se': pi.is_pro_se,
            'attorney_name': pi.attorney_name,
            'attorney_bar_number': pi.attorney_bar_number,
            'attorney_firm_name': pi.attorney_firm_name,
            'attorney_street_address': pi.attorney_street_address,
            'attorney_city': pi.attorney_city,
            'attorney_state': pi.attorney_state,
            'attorney_zip_code': pi.attorney_zip_code,
            'attorney_phone': pi.attorney_phone,
            'attorney_email': pi.attorney_email,
        }
    except (DocumentSection.DoesNotExist, PlaintiffInfo.DoesNotExist):
        pass

    # Defendants
    try:
        defendants_section = document.sections.get(section_type='defendants')
        for d in Defendant.objects.filter(section=defendants_section):
            data['defendants'].append({
                'name': d.name,
                'defendant_type': d.defendant_type,
                'badge_number': d.badge_number,
                'title_rank': d.title_rank,
                'agency_name': d.agency_name,
                'address': d.address,
                'description': d.description,
            })
    except DocumentSection.DoesNotExist:
        pass

    # Incident overview
    try:
        incident_section = document.sections.get(section_type='incident_overview')
        io = incident_section.incident_overview
        data['incident'] = {
            'incident_date': str(io.incident_date) if io.incident_date else '',
            'incident_time': io.incident_time,  # Keep as time object for template filter
            'incident_location': io.incident_location,
            'city': io.city,
            'state': io.state,
            'location_type': io.location_type,
            'was_recording': io.was_recording,
            'recording_device': io.recording_device,
        }
        data['court'] = io.federal_district_court or ''
    except (DocumentSection.DoesNotExist, IncidentOverview.DoesNotExist):
        pass

    # Incident narrative
    try:
        narrative_section = document.sections.get(section_type='incident_narrative')
        n = narrative_section.incident_narrative
        data['narrative'] = {
            'summary': n.summary,
            'detailed_narrative': n.detailed_narrative,
            'what_were_you_doing': n.what_were_you_doing,
            'initial_contact': n.initial_contact,
            'what_was_said': n.what_was_said,
            'physical_actions': n.physical_actions,
            'how_it_ended': n.how_it_ended,
        }
    except (DocumentSection.DoesNotExist, IncidentNarrative.DoesNotExist):
        pass

    # Rights violated
    try:
        rights_section = document.sections.get(section_type='rights_violated')
        rv = rights_section.rights_violated
        data['rights_violated'] = {
            'first_amendment': rv.first_amendment,
            'first_amendment_speech': rv.first_amendment_speech,
            'first_amendment_press': rv.first_amendment_press,
            'first_amendment_assembly': rv.first_amendment_assembly,
            'first_amendment_petition': rv.first_amendment_petition,
            'first_amendment_details': rv.first_amendment_details,
            'fourth_amendment': rv.fourth_amendment,
            'fourth_amendment_search': rv.fourth_amendment_search,
            'fourth_amendment_seizure': rv.fourth_amendment_seizure,
            'fourth_amendment_arrest': rv.fourth_amendment_arrest,
            'fourth_amendment_force': rv.fourth_amendment_force,
            'fourth_amendment_details': rv.fourth_amendment_details,
            'fifth_amendment': rv.fifth_amendment,
            'fifth_amendment_self_incrimination': rv.fifth_amendment_self_incrimination,
            'fifth_amendment_due_process': rv.fifth_amendment_due_process,
            'fifth_amendment_details': rv.fifth_amendment_details,
            'fourteenth_amendment': rv.fourteenth_amendment,
            'fourteenth_amendment_due_process': rv.fourteenth_amendment_due_process,
            'fourteenth_amendment_equal_protection': rv.fourteenth_amendment_equal_protection,
            'fourteenth_amendment_details': rv.fourteenth_amendment_details,
        }
    except (DocumentSection.DoesNotExist, RightsViolated.DoesNotExist):
        pass

    # Damages
    try:
        damages_section = document.sections.get(section_type='damages')
        d = damages_section.damages
        data['damages'] = {
            'physical_injury': d.physical_injury,
            'physical_injury_description': d.physical_injury_description,
            'emotional_distress': d.emotional_distress,
            'emotional_distress_description': d.emotional_distress_description,
            'property_damage': d.property_damage,
            'property_damage_description': d.property_damage_description,
            'lost_wages': d.lost_wages,
            'lost_wages_amount': float(d.lost_wages_amount) if d.lost_wages_amount else 0,
            'medical_expenses': float(d.medical_expenses) if d.medical_expenses else 0,
        }
    except (DocumentSection.DoesNotExist, Damages.DoesNotExist):
        pass

    # Relief sought
    try:
        relief_section = document.sections.get(section_type='relief_sought')
        rs = relief_section.relief_sought
        data['relief'] = {
            'compensatory_damages': rs.compensatory_damages,
            'compensatory_amount': float(rs.compensatory_amount) if rs.compensatory_amount else None,
            'punitive_damages': rs.punitive_damages,
            'punitive_amount': float(rs.punitive_amount) if rs.punitive_amount else None,
            'attorney_fees': rs.attorney_fees,
            'injunctive_relief': rs.injunctive_relief,
            'injunctive_description': rs.injunctive_description,
            'declaratory_relief': rs.declaratory_relief,
            'declaratory_description': rs.declaratory_description,
            'jury_trial_demanded': rs.jury_trial_demanded,
        }
    except (DocumentSection.DoesNotExist, ReliefSought.DoesNotExist):
        pass

    # Witnesses (with enhanced fields for evidence capture)
    data['witnesses'] = []
    try:
        witnesses_section = document.sections.get(section_type='witnesses')
        for w in Witness.objects.filter(section=witnesses_section):
            data['witnesses'].append({
                'name': w.name,
                'contact_info': w.contact_info,
                'relationship': w.relationship,
                'what_they_witnessed': w.what_they_witnessed,
                'willing_to_testify': w.willing_to_testify,
                'has_evidence': w.has_evidence,
                'evidence_description': w.evidence_description,
                'prior_interactions': w.prior_interactions,
                'additional_notes': w.additional_notes,
            })
    except DocumentSection.DoesNotExist:
        pass

    # Video Evidence (YouTube transcript extractions)
    data['video_transcripts'] = []
    try:
        evidence_section = document.sections.get(section_type='evidence')
        for evidence in evidence_section.evidence_items.filter(evidence_type='video'):
            try:
                video_evidence = evidence.video_evidence
                for capture in video_evidence.captures.filter(extraction_status='completed'):
                    # Build speaker mapping for this capture
                    speaker_map = {}
                    for speaker in video_evidence.speakers.all():
                        if speaker.defendant:
                            speaker_map[speaker.label] = speaker.defendant.name
                        elif speaker.is_plaintiff:
                            speaker_map[speaker.label] = "Plaintiff"
                        else:
                            speaker_map[speaker.label] = speaker.label

                    data['video_transcripts'].append({
                        'video_title': video_evidence.video_title,
                        'video_url': video_evidence.youtube_url,
                        'start_time': capture.start_time_display,
                        'end_time': capture.end_time_display,
                        'transcript': capture.attributed_transcript or capture.raw_transcript,
                        'speakers': speaker_map,
                    })
            except VideoEvidence.DoesNotExist:
                pass
    except DocumentSection.DoesNotExist:
        pass

    # Check if we have minimum data to generate
    has_plaintiff = bool(data['plaintiff'].get('first_name') and data['plaintiff'].get('last_name'))
    has_narrative = bool(data['narrative'].get('detailed_narrative') or document.story_text)
    has_rights = any([
        data['rights_violated'].get('first_amendment'),
        data['rights_violated'].get('fourth_amendment'),
        data['rights_violated'].get('fifth_amendment'),
        data['rights_violated'].get('fourteenth_amendment'),
    ])

    data['has_minimum_data'] = has_plaintiff and has_narrative and has_rights

    return data


def _generate_rendered_document_text(document_data):
    """
    Generate the actual rendered document text that appears to the user.
    This mirrors what's displayed in the document_review.html template.
    """
    sections = {}

    # CAPTION - Court and parties
    caption_parts = []
    if document_data.get('court'):
        caption_parts.append(document_data['court'])

    plaintiff = document_data.get('plaintiff', {})
    if plaintiff.get('first_name'):
        plaintiff_name = f"{plaintiff.get('first_name', '')} {plaintiff.get('middle_name', '')} {plaintiff.get('last_name', '')}".strip()
        plaintiff_name = ' '.join(plaintiff_name.split())  # Remove extra spaces
        caption_parts.append(f"{plaintiff_name.upper()}, Plaintiff")

    defendants = document_data.get('defendants', [])
    if defendants:
        if len(defendants) == 1:
            caption_parts.append(f"{defendants[0].get('name', '').upper()}, Defendant")
        else:
            caption_parts.append(f"{defendants[0].get('name', '').upper()}, et al., Defendants")

    sections['caption'] = '\n'.join(caption_parts)

    # PARTIES section
    parties_parts = []
    if plaintiff.get('first_name'):
        plaintiff_full = f"{plaintiff.get('first_name', '')} {plaintiff.get('middle_name', '')} {plaintiff.get('last_name', '')}".strip()
        plaintiff_full = ' '.join(plaintiff_full.split())
        address_parts = [plaintiff.get('street_address', '')]
        if plaintiff.get('city') and plaintiff.get('state'):
            address_parts.append(f"{plaintiff.get('city')}, {plaintiff.get('state')} {plaintiff.get('zip_code', '')}")
        address = ', '.join([p for p in address_parts if p])
        parties_parts.append(f"Plaintiff {plaintiff_full} is an individual residing at {address}.")

    for i, d in enumerate(defendants):
        name = d.get('name', '')
        title = d.get('title_rank', '')
        agency = d.get('agency_name', '')
        address = d.get('address', '')

        if title and agency:
            parties_parts.append(f"Defendant {name} is an individual who, at all times relevant hereto, held the position of {title} by {agency}. Defendant may be served at {address}.")
        elif agency:
            parties_parts.append(f"Defendant {name} is associated with {agency}. Defendant may be served at {address}.")
        else:
            parties_parts.append(f"Defendant {name} may be served at {address}.")

    sections['parties'] = '\n\n'.join(parties_parts)

    # JURISDICTION section
    incident = document_data.get('incident', {})
    jurisdiction_parts = [
        "This Court has jurisdiction pursuant to 28 U.S.C. §§ 1331 and 1343."
    ]
    if incident.get('city') and incident.get('state'):
        jurisdiction_parts.append(f"Venue is proper in this district pursuant to 28 U.S.C. § 1391(b) because the events occurred in {incident.get('city')}, {incident.get('state')}.")
    sections['jurisdiction'] = '\n\n'.join(jurisdiction_parts)

    # STATEMENT OF FACTS section
    facts_parts = []

    # Incident overview paragraph
    date_str = incident.get('incident_date', '')
    time_obj = incident.get('incident_time')
    location = incident.get('incident_location', '')
    city = incident.get('city', '')
    state = incident.get('state', '')

    fact_sentence = "On or about "
    if date_str:
        fact_sentence += date_str
    else:
        fact_sentence += "[DATE]"

    if time_obj:
        try:
            if hasattr(time_obj, 'strftime'):
                time_str = time_obj.strftime("%-I:%M %p")
            else:
                time_str = str(time_obj)
            fact_sentence += f", at approximately {time_str}"
        except:
            pass

    fact_sentence += ", Plaintiff was located at "
    if location:
        fact_sentence += location
    else:
        fact_sentence += "[LOCATION]"

    if city and state:
        fact_sentence += f", {city}, {state}"

    fact_sentence += "."
    facts_parts.append(fact_sentence)

    # Narrative
    narrative = document_data.get('narrative', {})
    if narrative.get('detailed_narrative'):
        facts_parts.append(narrative.get('detailed_narrative'))

    # Damages in facts
    damages = document_data.get('damages', {})
    if damages.get('physical_injury') or damages.get('emotional_distress'):
        damage_text = "As a result of Defendants' actions, Plaintiff suffered "
        damage_parts = []
        if damages.get('physical_injury'):
            desc = damages.get('physical_injury_description', '')
            if desc:
                damage_parts.append(f"physical injuries, specifically: {desc}")
            else:
                damage_parts.append("physical injuries")
        if damages.get('emotional_distress'):
            desc = damages.get('emotional_distress_description', '')
            if desc:
                damage_parts.append(f"emotional distress, including {desc}")
            else:
                damage_parts.append("emotional distress")
        damage_text += " and ".join(damage_parts) + "."
        facts_parts.append(damage_text)

    sections['statement_of_facts'] = '\n\n'.join(facts_parts)

    # CAUSES OF ACTION section
    rights = document_data.get('rights_violated', {})
    causes_parts = []

    if rights.get('fourth_amendment'):
        fourth_text = "FOURTH AMENDMENT VIOLATION\n\nDefendants violated Plaintiff's Fourth Amendment rights by: "
        violations = []
        if rights.get('fourth_amendment_search'):
            violations.append("unreasonable search")
        if rights.get('fourth_amendment_seizure'):
            violations.append("unlawful seizure")
        if rights.get('fourth_amendment_arrest'):
            violations.append("arrest without probable cause")
        if rights.get('fourth_amendment_force'):
            violations.append("excessive force")
        fourth_text += "; ".join(violations) if violations else "constitutional violations"
        if rights.get('fourth_amendment_details'):
            fourth_text += f"\n\n{rights.get('fourth_amendment_details')}"
        causes_parts.append(fourth_text)

    if rights.get('first_amendment'):
        first_text = "FIRST AMENDMENT VIOLATION\n\nDefendants violated Plaintiff's First Amendment rights by: "
        violations = []
        if rights.get('first_amendment_speech'):
            violations.append("suppressing free speech")
        if rights.get('first_amendment_press'):
            violations.append("interfering with right to record")
        if rights.get('first_amendment_assembly'):
            violations.append("restricting peaceful assembly")
        if rights.get('first_amendment_petition'):
            violations.append("retaliating for exercising petition rights")
        first_text += "; ".join(violations) if violations else "constitutional violations"
        if rights.get('first_amendment_details'):
            first_text += f"\n\n{rights.get('first_amendment_details')}"
        causes_parts.append(first_text)

    if rights.get('fifth_amendment'):
        fifth_text = "FIFTH AMENDMENT VIOLATION\n\nDefendants violated Plaintiff's Fifth Amendment rights by: "
        violations = []
        if rights.get('fifth_amendment_self_incrimination'):
            violations.append("compelling self-incrimination")
        if rights.get('fifth_amendment_due_process'):
            violations.append("denying due process")
        fifth_text += "; ".join(violations) if violations else "constitutional violations"
        if rights.get('fifth_amendment_details'):
            fifth_text += f"\n\n{rights.get('fifth_amendment_details')}"
        causes_parts.append(fifth_text)

    if rights.get('fourteenth_amendment'):
        fourteenth_text = "FOURTEENTH AMENDMENT VIOLATION\n\nDefendants violated Plaintiff's Fourteenth Amendment rights by: "
        violations = []
        if rights.get('fourteenth_amendment_due_process'):
            violations.append("denying due process")
        if rights.get('fourteenth_amendment_equal_protection'):
            violations.append("denying equal protection")
        fourteenth_text += "; ".join(violations) if violations else "constitutional violations"
        if rights.get('fourteenth_amendment_details'):
            fourteenth_text += f"\n\n{rights.get('fourteenth_amendment_details')}"
        causes_parts.append(fourteenth_text)

    sections['causes_of_action'] = '\n\n'.join(causes_parts)

    # PRAYER FOR RELIEF section
    relief = document_data.get('relief', {})
    relief_parts = ["WHEREFORE, Plaintiff requests:"]
    relief_parts.append("A. A declaration that Defendants' actions violated Plaintiff's constitutional rights;")

    if relief.get('compensatory_damages'):
        amount = relief.get('compensatory_amount')
        if amount:
            relief_parts.append(f"B. Compensatory damages in the amount of ${amount:,.2f};")
        else:
            relief_parts.append("B. Compensatory damages;")

    if relief.get('punitive_damages'):
        relief_parts.append("C. Punitive damages;")

    if relief.get('attorney_fees'):
        relief_parts.append("D. Attorney's fees pursuant to 42 U.S.C. § 1988;")

    if relief.get('injunctive_relief') and relief.get('injunctive_description'):
        relief_parts.append(f"E. Injunctive relief: {relief.get('injunctive_description')};")

    relief_parts.append("F. Such other relief as the Court deems just.")

    if relief.get('jury_trial_demanded'):
        relief_parts.append("\nJURY DEMAND: Plaintiff demands trial by jury.")

    sections['relief_sought'] = '\n\n'.join(relief_parts)

    # SIGNATURE section
    sig_parts = ["Respectfully submitted,"]
    if plaintiff.get('first_name'):
        plaintiff_full = f"{plaintiff.get('first_name', '')} {plaintiff.get('last_name', '')}".strip()
        if plaintiff.get('is_pro_se'):
            sig_parts.append(f"\n{plaintiff_full}, Pro Se")
        else:
            sig_parts.append(f"\n{plaintiff_full}")

        if plaintiff.get('street_address'):
            sig_parts.append(plaintiff.get('street_address'))
        if plaintiff.get('city') and plaintiff.get('state'):
            sig_parts.append(f"{plaintiff.get('city')}, {plaintiff.get('state')} {plaintiff.get('zip_code', '')}")

    sections['signature'] = '\n'.join(sig_parts)

    return sections


def _update_section_relevance(document, extracted_data):
    """
    Update story_relevance field for sections based on what was extracted from the story.

    Sections that always apply (set to 'relevant'):
    - plaintiff_info, incident_overview, incident_narrative, rights_violated, relief_sought, defendants

    Sections that may not apply (based on extracted data):
    - witnesses: 'may_not_apply' if no witnesses extracted
    - evidence: 'may_not_apply' if no evidence extracted
    - damages: 'relevant' if any damages mentioned, else 'may_not_apply'
    - prior_complaints: typically 'may_not_apply' (rarely mentioned in stories)
    """
    # Sections that always apply
    always_relevant = ['plaintiff_info', 'incident_overview', 'incident_narrative',
                       'rights_violated', 'relief_sought', 'defendants']

    # Check what was extracted
    witnesses = extracted_data.get('witnesses', [])
    has_witnesses = bool(witnesses and any(w.get('name') or w.get('description') for w in witnesses))

    evidence = extracted_data.get('evidence', [])
    has_evidence = bool(evidence and any(e.get('type') or e.get('description') for e in evidence))

    damages = extracted_data.get('damages', {})
    has_damages = bool(
        damages.get('physical_injuries') or
        damages.get('emotional_distress') or
        damages.get('financial_losses') or
        damages.get('other_damages')
    )

    # Update each section
    for section in document.sections.all():
        if section.section_type in always_relevant:
            section.story_relevance = 'relevant'
        elif section.section_type == 'witnesses':
            section.story_relevance = 'relevant' if has_witnesses else 'may_not_apply'
        elif section.section_type == 'evidence':
            section.story_relevance = 'relevant' if has_evidence else 'may_not_apply'
        elif section.section_type == 'damages':
            # Damages usually apply even if not mentioned - people often have at least emotional distress
            section.story_relevance = 'relevant' if has_damages else 'may_not_apply'
        elif section.section_type == 'prior_complaints':
            # Prior complaints are rarely mentioned in stories
            section.story_relevance = 'may_not_apply'
        else:
            section.story_relevance = 'unknown'

        section.save(update_fields=['story_relevance'])


@login_required
@require_POST
def section_save_ajax(request, document_id, section_type):
    """Save section data via AJAX."""
    document = get_object_or_404(Document, id=document_id, user=request.user)
    section = get_object_or_404(DocumentSection, document=document, section_type=section_type)

    config = SECTION_CONFIG.get(section_type)
    if not config:
        return JsonResponse({'success': False, 'error': 'Invalid section type'})

    Model = config['model']
    Form = config['form']
    is_multiple = config.get('multiple', False)

    if is_multiple:
        # For multiple items, we're adding a new item
        form = Form(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.section = section
            obj.save()

            # Invalidate cached complaint since data changed
            document.invalidate_generated_complaint()

            if section.status == 'not_started':
                section.status = 'in_progress'
                section.save()

            return JsonResponse({
                'success': True,
                'message': 'Item added successfully',
                'item_id': obj.id,
                'item_str': str(obj),
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors,
            })
    else:
        # For single items, update or create
        try:
            instance = Model.objects.get(section=section)
        except Model.DoesNotExist:
            instance = None

        form = Form(request.POST, instance=instance)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.section = section
            obj.save()

            # Invalidate cached complaint since data changed
            document.invalidate_generated_complaint()

            if section.status == 'not_started':
                section.status = 'in_progress'
                section.save()

            return JsonResponse({
                'success': True,
                'message': 'Section saved successfully',
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors,
            })


@login_required
@require_POST
def delete_item_ajax(request, document_id, section_type, item_id):
    """Delete a multiple-item via AJAX."""
    document = get_object_or_404(Document, id=document_id, user=request.user)
    section = get_object_or_404(DocumentSection, document=document, section_type=section_type)

    config = SECTION_CONFIG.get(section_type)
    if not config or not config.get('multiple'):
        return JsonResponse({'success': False, 'error': 'Invalid section type'})

    Model = config['model']
    item = get_object_or_404(Model, id=item_id, section=section)
    item.delete()

    return JsonResponse({
        'success': True,
        'message': 'Item deleted successfully',
    })


@login_required
@require_POST
def analyze_rights(request, document_id):
    """AJAX endpoint to analyze document and suggest rights violations."""
    import json

    try:
        # Get the document and verify ownership
        document = get_object_or_404(Document, id=document_id, user=request.user)

        # Check AI usage limits for free users
        if not document.can_use_ai():
            remaining = document.user.get_free_ai_remaining()
            return JsonResponse({
                'success': False,
                'error': 'You have used all 3 free AI analyses. Please upgrade your document to continue using AI features.',
                'limit_reached': True,
                'remaining': remaining,
            })

        # Get the incident narrative section
        try:
            narrative_section = document.sections.get(section_type='incident_narrative')
            narrative = narrative_section.incident_narrative
        except (DocumentSection.DoesNotExist, AttributeError):
            return JsonResponse({
                'success': False,
                'error': 'Please fill out the Incident Narrative section first. We need to know what happened before we can identify which rights were violated.',
            })

        # Build document data from incident narrative
        document_data = {
            'summary': narrative.summary or '',
            'detailed_narrative': narrative.detailed_narrative or '',
            'what_were_you_doing': narrative.what_were_you_doing or '',
            'initial_contact': narrative.initial_contact or '',
            'what_was_said': narrative.what_was_said or '',
            'physical_actions': narrative.physical_actions or '',
            'how_it_ended': narrative.how_it_ended or '',
        }

        # Check if there's any content to analyze
        if not any(document_data.values()):
            return JsonResponse({
                'success': False,
                'error': 'The Incident Narrative section is empty. Please describe what happened first.',
            })

        # Call OpenAI service to analyze
        from .services.openai_service import OpenAIService
        service = OpenAIService()
        result = service.analyze_rights_violations(document_data)

        # Record AI usage on success and include updated usage info
        if result.get('success'):
            document.record_ai_usage()
            result.update(get_ai_usage_info(document))

        return JsonResponse(result)

    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}',
        })


@login_required
@require_POST
def suggest_agency(request, document_id):
    """AJAX endpoint to suggest defendants (agencies and individuals) based on story and location."""

    try:
        # Verify document ownership
        document = get_object_or_404(Document, id=document_id, user=request.user)

        # Check AI usage limits for free users
        if not document.can_use_ai():
            remaining = document.user.get_free_ai_remaining()
            return JsonResponse({
                'success': False,
                'error': 'You have used all 3 free AI analyses. Please upgrade your document to continue using AI features.',
                'limit_reached': True,
                'remaining': remaining,
            })

        data = json.loads(request.body)

        # Get incident location from document for context
        city = ''
        state = ''
        try:
            incident_section = document.sections.get(section_type='incident_overview')
            incident = incident_section.incident_overview
            city = data.get('city') or (incident.city if incident else '')
            state = data.get('state') or (incident.state if incident else '')
        except (DocumentSection.DoesNotExist, AttributeError):
            city = data.get('city', '')
            state = data.get('state', '')

        # Get the story text from the document - this contains defendant names
        story_text = document.story_text or ''

        # Get existing defendants to avoid duplicates
        existing_defendants = []
        try:
            defendants_section = document.sections.get(section_type='defendants')
            for defendant in defendants_section.defendants.all():
                existing_defendants.append({
                    'name': defendant.name,
                    'type': defendant.defendant_type,
                })
        except DocumentSection.DoesNotExist:
            pass

        context = {
            'city': city,
            'state': state,
            'story_text': story_text,
            'existing_defendants': existing_defendants,
            'defendant_name': data.get('defendant_name', ''),
            'title': data.get('title', ''),
            'description': data.get('description', ''),
        }

        if not city and not state:
            return JsonResponse({
                'success': False,
                'error': 'Please fill out the Incident Overview section first (city and state are needed to suggest defendants).',
            })

        from .services.openai_service import OpenAIService
        service = OpenAIService()
        result = service.suggest_agency(context)

        # Record AI usage on success and include updated usage info
        if result.get('success'):
            document.record_ai_usage()
            result.update(get_ai_usage_info(document))

        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid request format.',
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}',
        })


@login_required
@require_POST
def suggest_section_content(request, document_id, section_type):
    """AJAX endpoint to suggest content for a specific section based on story analysis."""

    # Allowed section types for AI suggestions
    allowed_sections = ['damages', 'witnesses', 'evidence', 'rights_violated']

    if section_type not in allowed_sections:
        return JsonResponse({
            'success': False,
            'error': f'AI suggestions not available for section type: {section_type}',
        })

    try:
        document = get_object_or_404(Document, id=document_id, user=request.user)

        # Check AI usage limits for free users
        if not document.can_use_ai():
            remaining = document.user.get_free_ai_remaining()
            return JsonResponse({
                'success': False,
                'error': 'You have used all 3 free AI analyses. Please upgrade your document to continue using AI features.',
                'limit_reached': True,
                'remaining': remaining,
            })

        # Get the story text
        story_text = document.story_text or ''

        if not story_text:
            return JsonResponse({
                'success': False,
                'error': 'Please complete the "Tell Your Story" section first.',
            })

        # Get existing data for the section to avoid duplicates
        existing_data = {'existing': 'None yet'}

        try:
            section = document.sections.get(section_type=section_type)

            if section_type == 'damages':
                damages = section.damages
                existing_items = []
                if damages.physical_injuries:
                    existing_items.append(f"Physical: {damages.physical_injuries}")
                if damages.emotional_distress:
                    existing_items.append(f"Emotional: {damages.emotional_distress}")
                if damages.economic_losses:
                    existing_items.append(f"Economic: {damages.economic_losses}")
                if existing_items:
                    existing_data['existing'] = "; ".join(existing_items)

            elif section_type == 'witnesses':
                witnesses = list(section.witnesses.values_list('name', flat=True))
                if witnesses:
                    existing_data['existing'] = ", ".join(witnesses)

            elif section_type == 'evidence':
                evidence_items = list(section.evidence_items.values_list('description', flat=True))
                if evidence_items:
                    existing_data['existing'] = ", ".join(evidence_items)

            elif section_type == 'rights_violated':
                rights = section.rights_violated
                existing_items = []
                if rights.first_amendment:
                    existing_items.append("1st Amendment")
                if rights.fourth_amendment:
                    existing_items.append("4th Amendment")
                if rights.fifth_amendment:
                    existing_items.append("5th Amendment")
                if rights.eighth_amendment:
                    existing_items.append("8th Amendment")
                if rights.fourteenth_amendment:
                    existing_items.append("14th Amendment")
                if existing_items:
                    existing_data['existing'] = ", ".join(existing_items)

        except (DocumentSection.DoesNotExist, AttributeError):
            pass

        from .services.openai_service import OpenAIService
        service = OpenAIService()
        result = service.suggest_section_content(section_type, story_text, existing_data)

        # Record AI usage on success and include updated usage info
        if result.get('success'):
            document.record_ai_usage()
            result.update(get_ai_usage_info(document))

        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid request format.',
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}',
        })


@login_required
@require_http_methods(["POST"])
def ai_review_document(request, document_id):
    """AJAX endpoint to perform AI review of the complete document.

    Analyzes legal strength, clarity, and completeness.
    Returns structured feedback with issues keyed by section.
    """
    try:
        document = get_object_or_404(Document, id=document_id, user=request.user)

        # Check AI usage limits for free users
        if not document.can_use_ai():
            remaining = document.user.get_free_ai_remaining()
            return JsonResponse({
                'success': False,
                'error': 'You have used all 3 free AI analyses. Please upgrade your document to continue using AI features.',
                'limit_reached': True,
                'remaining': remaining,
            })

        # Collect all document data
        document_data = _collect_document_data(document)

        # Generate the actual rendered document text that the user sees
        rendered_sections = _generate_rendered_document_text(document_data)

        # Build the full document text as it appears to the user
        full_document_text = f"""
UNITED STATES DISTRICT COURT
{rendered_sections.get('caption', '')}

COMPLAINT FOR VIOLATION OF CIVIL RIGHTS UNDER 42 U.S.C. § 1983

PARTIES

{rendered_sections.get('parties', '')}

JURISDICTION AND VENUE

{rendered_sections.get('jurisdiction', '')}

STATEMENT OF FACTS

{rendered_sections.get('statement_of_facts', '')}

CAUSES OF ACTION

{rendered_sections.get('causes_of_action', '')}

PRAYER FOR RELIEF

{rendered_sections.get('relief_sought', '')}

{rendered_sections.get('signature', '')}
"""

        # Pass the rendered document text to the AI, not raw database fields
        review_data = {
            'rendered_document': full_document_text,
            'sections': rendered_sections,
        }

        from .services.openai_service import OpenAIService
        service = OpenAIService()
        result = service.review_document(review_data)

        # Record AI usage on success and include updated usage info
        if result.get('success'):
            document.record_ai_usage()
            result.update(get_ai_usage_info(document))

        return JsonResponse(result)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}',
        })


@login_required
@require_http_methods(["POST"])
def generate_fix(request, document_id):
    """AJAX endpoint to generate AI-suggested fix for an issue.

    Takes issue details and returns rewritten section content.
    """
    try:
        document = get_object_or_404(Document, id=document_id, user=request.user)

        # Check AI usage limits for free users
        if not document.can_use_ai():
            remaining = document.user.get_free_ai_remaining()
            return JsonResponse({
                'success': False,
                'error': 'You have used all 3 free AI analyses. Please upgrade your document to continue using AI features.',
                'limit_reached': True,
                'remaining': remaining,
            })

        data = json.loads(request.body)

        section_type = data.get('section_type', '')
        issue = {
            'title': data.get('issue_title', ''),
            'description': data.get('issue_description', ''),
            'suggestion': data.get('issue_suggestion', ''),
        }

        # Get current content for the section
        current_content = _get_section_content(document, section_type)

        # Get full document data for context
        document_data = _collect_document_data(document)

        from .services.openai_service import OpenAIService
        service = OpenAIService()
        result = service.rewrite_section(
            section_type=section_type,
            current_content=current_content,
            issue=issue,
            document_data=document_data
        )

        # Include the original content for diff comparison
        result['original_content'] = current_content

        # Validate and fix field_updates - the AI often returns wrong field names
        # because it doesn't know the actual database field names.
        # Always ensure field_updates uses correct model field names.
        if result.get('success'):
            rewritten = result.get('rewritten_content', '')
            ai_field_updates = result.get('field_updates', {})

            # Check if AI-provided field_updates use valid model field names
            valid_ai_updates = {}
            if ai_field_updates and section_type in SECTION_CONFIG:
                Model = SECTION_CONFIG[section_type].get('model')
                if Model:
                    model_fields = {f.name for f in Model._meta.get_fields()}
                    for k, v in ai_field_updates.items():
                        if k in model_fields:
                            valid_ai_updates[k] = v

            # If AI provided valid field names, use those; otherwise build from defaults
            if valid_ai_updates:
                result['field_updates'] = valid_ai_updates
            elif rewritten:
                # Map section types to their primary TEXT field only
                default_field_map = {
                    'incident_narrative': 'detailed_narrative',
                    'damages': 'physical_injury_description',
                    'rights_violated': 'fourth_amendment_details',
                }
                default_field = default_field_map.get(section_type)
                if default_field:
                    result['field_updates'] = {default_field: rewritten}
                elif section_type == 'incident_overview':
                    # For incident_overview, try to parse the rewritten content to extract fields
                    # Format: "Location: value\nCity: value\nState: value"
                    field_updates = {}
                    for line in rewritten.split('\n'):
                        line = line.strip()
                        if line.startswith('Location:'):
                            field_updates['incident_location'] = line.replace('Location:', '').strip()
                        elif line.startswith('City:'):
                            field_updates['city'] = line.replace('City:', '').strip()
                        elif line.startswith('State:'):
                            field_updates['state'] = line.replace('State:', '').strip()
                        elif line.startswith('Date:'):
                            date_str = line.replace('Date:', '').strip()
                            field_updates['incident_date'] = _convert_date_format(date_str)
                        elif line.startswith('Time:'):
                            time_str = line.replace('Time:', '').strip()
                            field_updates['incident_time'] = _convert_time_format(time_str)
                    if field_updates:
                        result['field_updates'] = field_updates

        # Record AI usage on success and include updated usage info
        if result.get('success'):
            document.record_ai_usage()
            result.update(get_ai_usage_info(document))

        return JsonResponse(result)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}',
        })


@login_required
@require_http_methods(["POST"])
def apply_fix(request, document_id):
    """AJAX endpoint to apply an AI-suggested fix to a section.

    Saves the field_updates to the database.
    """
    try:
        document = get_object_or_404(Document, id=document_id, user=request.user)
        data = json.loads(request.body)

        section_type = data.get('section_type', '')
        field_updates = data.get('field_updates', {})

        # Map AI section names to database section types
        section_type_mapping = {
            'statement_of_facts': 'incident_narrative',
            'statement of facts': 'incident_narrative',
            'facts': 'incident_narrative',
            'factual allegations': 'incident_narrative',
            'narrative': 'incident_narrative',
            'caption': 'incident_overview',
            'parties': 'plaintiff_info',
            'jurisdiction': 'incident_overview',
            'causes_of_action': 'rights_violated',
            'causes of action': 'rights_violated',
            'relief': 'relief_sought',
            'prayer for relief': 'relief_sought',
        }
        # Normalize and map the section type
        normalized_section = section_type.strip().lower().replace('_', ' ')
        if normalized_section in section_type_mapping:
            section_type = section_type_mapping[normalized_section]
        elif section_type.strip().lower() in section_type_mapping:
            section_type = section_type_mapping[section_type.strip().lower()]

        if not section_type:
            return JsonResponse({
                'success': False,
                'error': 'Missing section_type in request',
            })

        # If no field_updates, still return success so the UI can update
        # Some sections (like relief_sought with booleans) can't be auto-updated
        if not field_updates:
            return JsonResponse({
                'success': True,
                'message': 'No automatic updates available for this section. Please review and edit manually.',
                'updated_fields': [],
            })

        # Get the section and its model instance
        config = SECTION_CONFIG.get(section_type)
        if not config:
            return JsonResponse({
                'success': False,
                'error': f'Unknown section type: {section_type}',
            })

        Model = config.get('model')
        if not Model:
            return JsonResponse({
                'success': False,
                'error': f'No model for section type: {section_type}',
            })

        try:
            section = document.sections.get(section_type=section_type)

            # Handle multiple-item sections differently
            if config.get('multiple', False):
                # For multiple items, we can't directly update - return info for manual handling
                return JsonResponse({
                    'success': False,
                    'error': 'Multiple-item sections require manual editing',
                })

            # Get the model instance
            instance = Model.objects.get(section=section)

            # Apply field updates
            updated_fields = []
            skipped_fields = []
            for field_name, new_value in field_updates.items():
                if hasattr(instance, field_name):
                    # Convert time formats like "09:30 AM" to "09:30:00" for TimeField
                    if field_name.endswith('_time') or field_name == 'incident_time':
                        new_value = _convert_time_format(new_value)
                    # Convert date formats like "August 24, 2025" to "2025-08-24" for DateField
                    if field_name.endswith('_date') or field_name == 'incident_date':
                        new_value = _convert_date_format(new_value)
                    setattr(instance, field_name, new_value)
                    updated_fields.append(field_name)
                else:
                    skipped_fields.append(field_name)

            if updated_fields:
                instance.save()
                # Invalidate cached complaint
                document.invalidate_generated_complaint()

            response_data = {
                'success': True,
                'updated_fields': updated_fields,
            }
            if skipped_fields:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f'apply_fix: Skipped invalid field names for {section_type}: {skipped_fields}. '
                    f'Requested: {list(field_updates.keys())}. '
                    f'Valid: {[f.name for f in Model._meta.get_fields()]}'
                )
                if not updated_fields:
                    response_data['success'] = False
                    response_data['error'] = (
                        f'Could not update fields: {", ".join(skipped_fields)}. '
                        f'These field names do not match the {section_type} model.'
                    )
            return JsonResponse(response_data)

        except DocumentSection.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Section not found: {section_type}',
            })
        except Model.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'No data found for section: {section_type}',
            })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}',
        })


def _convert_time_format(time_str):
    """Convert time formats like '09:30 AM' or '2:30 PM' to 'HH:MM:SS' for Django TimeField."""
    if not time_str or not isinstance(time_str, str):
        return time_str

    import re
    from datetime import datetime

    time_str = time_str.strip()

    # Already in HH:MM:SS format
    if re.match(r'^\d{2}:\d{2}:\d{2}$', time_str):
        return time_str

    # Already in HH:MM format (24-hour)
    if re.match(r'^\d{2}:\d{2}$', time_str):
        return time_str + ':00'

    # Try parsing AM/PM formats
    for fmt in ['%I:%M %p', '%I:%M:%S %p', '%I:%M%p', '%I %p']:
        try:
            parsed = datetime.strptime(time_str.upper(), fmt)
            return parsed.strftime('%H:%M:%S')
        except ValueError:
            continue

    # Try formats like "9:30 AM" (single digit hour)
    for fmt in ['%I:%M %p', '%I:%M%p']:
        try:
            parsed = datetime.strptime(time_str.upper(), fmt)
            return parsed.strftime('%H:%M:%S')
        except ValueError:
            continue

    # Return original if we can't parse
    return time_str


def _convert_date_format(date_str):
    """Convert date formats like 'August 24, 2025' or 'Aug 24 2025' to 'YYYY-MM-DD' for Django DateField."""
    if not date_str or not isinstance(date_str, str):
        return date_str

    import re
    from datetime import datetime

    date_str = date_str.strip()

    # Already in YYYY-MM-DD format
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str

    # Try various date formats
    date_formats = [
        '%B %d, %Y',      # August 24, 2025
        '%B %d %Y',       # August 24 2025
        '%b %d, %Y',      # Aug 24, 2025
        '%b %d %Y',       # Aug 24 2025
        '%m/%d/%Y',       # 08/24/2025
        '%m-%d-%Y',       # 08-24-2025
        '%d %B %Y',       # 24 August 2025
        '%d %b %Y',       # 24 Aug 2025
        '%Y/%m/%d',       # 2025/08/24
    ]

    for fmt in date_formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            return parsed.strftime('%Y-%m-%d')
        except ValueError:
            continue

    # Return original if we can't parse
    return date_str


def _get_section_content(document, section_type):
    """Get the current text content of a section for AI rewriting."""
    try:
        section = document.sections.get(section_type=section_type)

        if section_type == 'incident_narrative':
            narrative = section.incident_narrative
            return narrative.detailed_narrative or narrative.summary or ''

        elif section_type == 'incident_overview':
            overview = section.incident_overview
            parts = []
            if overview.incident_date:
                parts.append(f"Date: {overview.incident_date}")
            if overview.incident_time:
                # Format time in 12-hour AM/PM format for display
                formatted_time = overview.incident_time.strftime('%I:%M %p').lstrip('0')
                parts.append(f"Time: {formatted_time}")
            if overview.incident_location:
                parts.append(f"Location: {overview.incident_location}")
            if overview.city:
                parts.append(f"City: {overview.city}")
            if overview.state:
                parts.append(f"State: {overview.state}")
            return '\n'.join(parts)

        elif section_type == 'damages':
            damages = section.damages
            parts = []
            if damages.physical_injury and damages.physical_injury_description:
                parts.append(f"Physical: {damages.physical_injury_description}")
            if damages.emotional_distress and damages.emotional_distress_description:
                parts.append(f"Emotional: {damages.emotional_distress_description}")
            if damages.property_damage and damages.property_damage_description:
                parts.append(f"Property: {damages.property_damage_description}")
            return '\n'.join(parts)

        elif section_type == 'rights_violated':
            rights = section.rights_violated
            parts = []
            if rights.fourth_amendment and rights.fourth_amendment_details:
                parts.append(f"4th Amendment: {rights.fourth_amendment_details}")
            if rights.first_amendment and rights.first_amendment_details:
                parts.append(f"1st Amendment: {rights.first_amendment_details}")
            if rights.fourteenth_amendment and rights.fourteenth_amendment_details:
                parts.append(f"14th Amendment: {rights.fourteenth_amendment_details}")
            return '\n'.join(parts)

        elif section_type == 'plaintiff_info':
            plaintiff = section.plaintiff_info
            return f"{plaintiff.first_name} {plaintiff.last_name}, residing at {plaintiff.street_address}, {plaintiff.city}, {plaintiff.state} {plaintiff.zip_code}"

        elif section_type == 'relief_sought':
            relief = section.relief_sought
            parts = []
            if relief.compensatory_damages:
                parts.append(f"Compensatory damages: ${relief.compensatory_amount or 'unspecified'}")
            if relief.punitive_damages:
                parts.append(f"Punitive damages: ${relief.punitive_amount or 'unspecified'}")
            if relief.injunctive_relief and relief.injunctive_description:
                parts.append(f"Injunctive relief: {relief.injunctive_description}")
            return '\n'.join(parts)

        return ''

    except (DocumentSection.DoesNotExist, AttributeError):
        return ''


@login_required
@require_http_methods(["POST"])
def lookup_address(request, document_id):
    """AJAX endpoint to lookup agency address using web search.

    If agency_name is not provided but officer info is available,
    will attempt to identify the agency first based on location and officer details.
    """

    try:
        # Verify document ownership
        document = get_object_or_404(Document, id=document_id, user=request.user)

        # Check AI usage limits for free users
        if not document.can_use_ai():
            remaining = document.user.get_free_ai_remaining()
            return JsonResponse({
                'success': False,
                'error': 'You have used all 3 free AI analyses. Please upgrade your document to continue using AI features.',
                'limit_reached': True,
                'remaining': remaining,
            })

        data = json.loads(request.body)
        agency_name = data.get('agency_name', '').strip()
        officer_name = data.get('officer_name', '').strip()
        officer_title = data.get('officer_title', '').strip()
        officer_description = data.get('officer_description', '').strip()

        # Get city/state from incident overview for context
        city = ''
        state = ''
        try:
            incident_section = document.sections.get(section_type='incident_overview')
            incident = incident_section.incident_overview
            city = incident.city if incident else ''
            state = incident.state if incident else ''
        except (DocumentSection.DoesNotExist, AttributeError):
            pass

        # If no agency name and no location context, we can't proceed
        if not agency_name and not city and not state:
            return JsonResponse({
                'success': False,
                'error': 'Please enter an agency name or complete the Incident Overview section with location info.',
            })

        from .services.openai_service import OpenAIService
        service = OpenAIService()
        result = service.lookup_agency_address(
            agency_name=agency_name,
            city=city,
            state=state,
            officer_name=officer_name,
            officer_title=officer_title,
            officer_description=officer_description
        )

        # Record AI usage on success and include updated usage info
        if result.get('success'):
            document.record_ai_usage()
            result.update(get_ai_usage_info(document))

        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid request format.',
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}',
        })


@login_required
def lookup_district_court(request):
    """AJAX endpoint to lookup federal district court based on city and state."""
    city = request.GET.get('city', '').strip()
    state = request.GET.get('state', '').strip().upper()

    if not city or not state:
        return JsonResponse({
            'success': False,
            'error': 'City and state are required',
        })

    try:
        from .services.court_lookup_service import CourtLookupService
        result = CourtLookupService.lookup_court_by_location(city, state)

        if result:
            return JsonResponse({
                'success': True,
                'court_name': result.get('court_name', ''),
                'confidence': result.get('confidence', 'low'),
                'district': result.get('district', ''),
                'method': result.get('method', ''),
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f'Could not find federal district court for {city}, {state}',
            })
    except ImportError:
        return JsonResponse({
            'success': False,
            'error': 'Court lookup service not available',
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
        })


@login_required
def tell_your_story(request, document_id):
    """Page for users to tell their story and have AI extract form fields."""
    document = get_object_or_404(Document, id=document_id, user=request.user)

    # Block editing for finalized or expired documents
    if not document.can_edit():
        if document.payment_status == 'finalized':
            messages.info(request, 'This document has been finalized and cannot be edited.')
        elif document.payment_status == 'expired':
            messages.warning(request, 'This document has expired. Please upgrade to continue editing.')
        return redirect('documents:document_detail', document_id=document.id)

    context = {
        'document': document,
    }

    # Include test stories for test users
    if request.user.is_test_user:
        from .test_stories import get_test_stories
        context['test_stories'] = get_test_stories()

    return render(request, 'documents/tell_your_story.html', context)


def _process_story_background(document_id, story_text):
    """
    Background function to process story with OpenAI.
    Runs in a separate thread to avoid blocking the request.
    """
    import django
    django.setup()  # Ensure Django is set up in this thread

    from datetime import datetime
    from .models import Document, DocumentSection, IncidentOverview
    from .services.openai_service import OpenAIService
    from .services.court_lookup_service import CourtLookupService

    try:
        document = Document.objects.get(id=document_id)

        service = OpenAIService()
        result = service.parse_story(story_text)

        if result.get('success'):
            # Save story text
            document.story_text = story_text
            document.story_told_at = timezone.now()

            # Get extracted sections
            extracted = result.get('sections', {})

            # Call suggest_relief with extracted data
            relief_result = service.suggest_relief(extracted)
            if relief_result.get('success'):
                result['relief_suggestions'] = relief_result.get('relief', {})

            # Auto-apply incident_overview fields
            incident_data = extracted.get('incident_overview', {})

            if incident_data:
                try:
                    doc_section = DocumentSection.objects.get(
                        document=document, section_type='incident_overview'
                    )
                    obj, created = IncidentOverview.objects.get_or_create(section=doc_section)

                    # Apply extracted fields
                    if incident_data.get('incident_date'):
                        date_str = incident_data['incident_date']
                        parsed_date = None

                        # Try various date formats
                        date_formats = [
                            '%Y-%m-%d',       # 2024-03-15
                            '%m/%d/%Y',       # 03/15/2024
                            '%m-%d-%Y',       # 03-15-2024
                            '%B %d, %Y',      # March 15, 2024
                            '%b %d, %Y',      # Mar 15, 2024
                            '%d %B %Y',       # 15 March 2024
                            '%d %b %Y',       # 15 Mar 2024
                            '%Y/%m/%d',       # 2024/03/15
                        ]

                        for fmt in date_formats:
                            try:
                                parsed_date = datetime.strptime(date_str, fmt).date()
                                break
                            except ValueError:
                                continue

                        if parsed_date:
                            obj.incident_date = parsed_date
                    if incident_data.get('incident_time'):
                        # Parse various time formats to TimeField
                        time_str = incident_data['incident_time']
                        try:
                            from datetime import time as dt_time
                            import re

                            # Try various formats
                            parsed_time = None

                            # Format: HH:MM or H:MM
                            if re.match(r'^\d{1,2}:\d{2}$', time_str):
                                parts = time_str.split(':')
                                parsed_time = dt_time(int(parts[0]), int(parts[1]))
                            # Format: HH:MM:SS
                            elif re.match(r'^\d{1,2}:\d{2}:\d{2}$', time_str):
                                parts = time_str.split(':')
                                parsed_time = dt_time(int(parts[0]), int(parts[1]), int(parts[2]))
                            # Format: HH:MM AM/PM or H:MM AM/PM
                            elif re.match(r'^\d{1,2}:\d{2}\s*(AM|PM|am|pm)$', time_str, re.IGNORECASE):
                                match = re.match(r'^(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)$', time_str, re.IGNORECASE)
                                hour = int(match.group(1))
                                minute = int(match.group(2))
                                ampm = match.group(3).upper()
                                if ampm == 'PM' and hour != 12:
                                    hour += 12
                                elif ampm == 'AM' and hour == 12:
                                    hour = 0
                                parsed_time = dt_time(hour, minute)

                            if parsed_time:
                                obj.incident_time = parsed_time
                        except (ValueError, AttributeError):
                            pass  # Can't parse time, skip it
                    if incident_data.get('incident_location'):
                        obj.incident_location = incident_data['incident_location']
                    if incident_data.get('city'):
                        obj.city = incident_data['city']
                    if incident_data.get('state'):
                        obj.state = incident_data['state']
                    if incident_data.get('location_type'):
                        obj.location_type = incident_data['location_type']
                    if incident_data.get('was_recording') is not None:
                        obj.was_recording = incident_data['was_recording'] in [True, 'true', 'True']
                    if incident_data.get('recording_device'):
                        obj.recording_device = incident_data['recording_device']

                    # Auto-lookup federal district court
                    if obj.city and obj.state and not obj.federal_district_court:
                        try:
                            court_result = CourtLookupService.lookup_court_by_location(obj.city, obj.state)
                            if court_result and court_result.get('court_name'):
                                obj.federal_district_court = court_result['court_name']
                                obj.district_lookup_confidence = court_result.get('confidence', 'medium')
                        except Exception:
                            pass

                    obj.save()

                    # Update section status
                    if check_section_complete(doc_section, obj):
                        doc_section.status = 'completed'
                    elif doc_section.status == 'not_started':
                        doc_section.status = 'in_progress'
                    doc_section.save()

                    # Add auto-applied notice
                    result['auto_applied'] = {
                        'incident_overview': True,
                        'fields_applied': [k for k, v in incident_data.items() if v]
                    }
                except Exception:
                    pass  # Don't fail if incident overview update fails

            # Update story_relevance for all sections
            _update_section_relevance(document, extracted)

            # Record AI usage for billing/limits
            document.record_ai_usage()

            # Add updated AI usage info to result
            result['ai_remaining'] = document.user.get_free_ai_remaining()
            result['ai_usage_display'] = document.get_ai_usage_display()

            # Store successful result
            document.parsing_status = 'completed'
            document.parsing_result = result
            document.parsing_error = ''
            document.save(update_fields=[
                'story_text', 'story_told_at',
                'parsing_status', 'parsing_result', 'parsing_error'
            ])
        else:
            # Store failed result
            document.parsing_status = 'failed'
            document.parsing_error = result.get('error', 'Unknown error during parsing')
            document.parsing_result = None
            document.save(update_fields=['parsing_status', 'parsing_error', 'parsing_result'])

    except Exception as e:
        # Handle unexpected errors
        try:
            document = Document.objects.get(id=document_id)
            document.parsing_status = 'failed'
            document.parsing_error = str(e)
            document.parsing_result = None
            document.save(update_fields=['parsing_status', 'parsing_error', 'parsing_result'])
        except Exception:
            pass  # Can't save error status


@login_required
@require_POST
def parse_story(request, document_id):
    """AJAX endpoint to start story parsing (returns immediately, processes in background)."""

    try:
        # Verify document ownership
        document = get_object_or_404(Document, id=document_id, user=request.user)

        # Check AI usage limits for free users
        if not document.can_use_ai():
            remaining = document.user.get_free_ai_remaining()
            return JsonResponse({
                'success': False,
                'error': 'You have used all 3 free AI analyses. Please upgrade your document to continue using AI features.',
                'limit_reached': True,
                'remaining': remaining,
            })

        data = json.loads(request.body)
        story_text = data.get('story', '').strip()

        if not story_text:
            return JsonResponse({
                'success': False,
                'error': 'Please enter your story first.',
            })

        # Check if already processing (prevent duplicate requests)
        if document.parsing_status == 'processing':
            # Check if it's been processing for more than 2 minutes (stale)
            if document.parsing_started_at:
                elapsed = (timezone.now() - document.parsing_started_at).total_seconds()
                if elapsed < 120:  # Less than 2 minutes, still processing
                    return JsonResponse({
                        'success': True,
                        'status': 'processing',
                        'message': 'Analysis already in progress...'
                    })

        # Mark as processing and start background thread
        document.parsing_status = 'processing'
        document.parsing_started_at = timezone.now()
        document.parsing_result = None
        document.parsing_error = ''
        document.save(update_fields=['parsing_status', 'parsing_started_at', 'parsing_result', 'parsing_error'])

        # Start background processing
        thread = threading.Thread(
            target=_process_story_background,
            args=(document_id, story_text),
            daemon=True
        )
        thread.start()

        return JsonResponse({
            'success': True,
            'status': 'processing',
            'message': 'Analysis started...'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid request format.',
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}',
        })


@login_required
@require_GET
def parse_story_status(request, document_id):
    """AJAX endpoint to check story parsing status (for polling)."""
    try:
        document = get_object_or_404(Document, id=document_id, user=request.user)

        if document.parsing_status == 'processing':
            return JsonResponse({
                'success': True,
                'status': 'processing',
                'message': 'Analysis in progress...'
            })
        elif document.parsing_status == 'completed':
            # Return the stored result
            result = document.parsing_result or {}
            result['success'] = True
            result['status'] = 'completed'

            # Reset parsing status for next time
            document.parsing_status = 'idle'
            document.save(update_fields=['parsing_status'])

            return JsonResponse(result)
        elif document.parsing_status == 'failed':
            error = document.parsing_error or 'Unknown error occurred'

            # Reset parsing status for next time
            document.parsing_status = 'idle'
            document.save(update_fields=['parsing_status'])

            return JsonResponse({
                'success': False,
                'status': 'failed',
                'error': error
            })
        else:
            # Idle - no parsing in progress
            return JsonResponse({
                'success': True,
                'status': 'idle',
                'message': 'Ready to analyze'
            })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}',
        })


@login_required
@require_POST
def apply_story_fields(request, document_id):
    """Save selected fields from story parsing to the database."""
    import json
    from datetime import datetime

    try:
        document = get_object_or_404(Document, id=document_id, user=request.user)
        data = json.loads(request.body)
        fields = data.get('fields', [])

        if not fields:
            return JsonResponse({
                'success': False,
                'error': 'No fields to apply.',
            })

        saved_count = 0
        errors = []

        # Group fields by section
        sections_data = {}
        for field in fields:
            section = field.get('section')
            if section not in sections_data:
                sections_data[section] = []
            sections_data[section].append(field)

        # Process each section
        for section_type, section_fields in sections_data.items():
            try:
                doc_section = DocumentSection.objects.get(document=document, section_type=section_type)

                if section_type == 'incident_overview':
                    obj, created = IncidentOverview.objects.get_or_create(section=doc_section)
                    for f in section_fields:
                        field_name = f.get('field')
                        value = f.get('value')
                        if field_name == 'incident_date' and value:
                            try:
                                obj.incident_date = datetime.strptime(value, '%Y-%m-%d').date()
                            except ValueError:
                                pass  # Skip invalid dates
                        elif field_name == 'incident_time' and value:
                            obj.incident_time = value
                        elif field_name == 'incident_location' and value:
                            obj.incident_location = value
                        elif field_name == 'city' and value:
                            obj.city = value
                        elif field_name == 'state' and value:
                            obj.state = value
                        elif field_name == 'location_type' and value:
                            obj.location_type = value
                        elif field_name == 'was_recording' and value is not None:
                            obj.was_recording = value in [True, 'true', 'True', 1, '1']
                        elif field_name == 'recording_device' and value:
                            obj.recording_device = value
                        saved_count += 1
                    obj.save()
                    # Auto-complete if criteria met
                    if check_section_complete(doc_section, obj):
                        doc_section.status = 'completed'
                    else:
                        doc_section.status = 'in_progress'
                    doc_section.save()

                elif section_type == 'incident_narrative':
                    obj, created = IncidentNarrative.objects.get_or_create(section=doc_section)
                    for f in section_fields:
                        field_name = f.get('field')
                        value = f.get('value')
                        if hasattr(obj, field_name) and value:
                            setattr(obj, field_name, value)
                            saved_count += 1
                    obj.save()
                    # Auto-complete if criteria met
                    if check_section_complete(doc_section, obj):
                        doc_section.status = 'completed'
                    else:
                        doc_section.status = 'in_progress'
                    doc_section.save()

                elif section_type == 'defendants':
                    # Track which defendants have inferred agencies
                    defendant_agency_inferred = {}
                    for f in section_fields:
                        if f.get('field') == 'agency_inferred':
                            idx = f.get('itemIndex')
                            if idx is not None:
                                defendant_agency_inferred[int(idx)] = f.get('value') in [True, 'true', 'True', 1, '1']

                    for f in section_fields:
                        item_index = f.get('itemIndex')
                        field_name = f.get('field')
                        value = f.get('value')
                        if field_name == 'agency_inferred':
                            continue  # Already processed above
                        if item_index is not None and value:
                            defendants = list(Defendant.objects.filter(section=doc_section))
                            idx = int(item_index)
                            if idx < len(defendants):
                                defendant = defendants[idx]
                            else:
                                defendant = Defendant(section=doc_section, defendant_type='individual')
                            if field_name == 'name':
                                defendant.name = value
                            elif field_name == 'badge_number':
                                defendant.badge_number = value
                            elif field_name == 'title':
                                defendant.title_rank = value
                            elif field_name == 'agency':
                                defendant.agency_name = value
                                # Set agency_inferred if this defendant's agency was AI-inferred
                                if idx in defendant_agency_inferred:
                                    defendant.agency_inferred = defendant_agency_inferred[idx]
                            elif field_name == 'description':
                                defendant.description = value
                            defendant.save()
                            saved_count += 1
                    # Auto-complete if at least one defendant with name
                    if Defendant.objects.filter(section=doc_section, name__isnull=False).exclude(name='').exists():
                        doc_section.status = 'completed'
                    else:
                        doc_section.status = 'in_progress'
                    doc_section.save()

                elif section_type == 'witnesses':
                    for f in section_fields:
                        item_index = f.get('itemIndex')
                        field_name = f.get('field')
                        value = f.get('value')
                        if item_index is not None and value:
                            witnesses = list(Witness.objects.filter(section=doc_section))
                            idx = int(item_index)
                            if idx < len(witnesses):
                                witness = witnesses[idx]
                            else:
                                witness = Witness(section=doc_section, name='Unknown')
                            if field_name == 'name':
                                witness.name = value
                            elif field_name == 'description':
                                witness.relationship = value
                            elif field_name == 'what_they_saw':
                                witness.what_they_witnessed = value
                            witness.save()
                            saved_count += 1
                    # Auto-complete if at least one witness added
                    if Witness.objects.filter(section=doc_section).exists():
                        doc_section.status = 'completed'
                    else:
                        doc_section.status = 'in_progress'
                    doc_section.save()

                elif section_type == 'evidence':
                    for f in section_fields:
                        item_index = f.get('itemIndex')
                        field_name = f.get('field')
                        value = f.get('value')
                        if item_index is not None and value is not None:
                            evidence_items = list(Evidence.objects.filter(section=doc_section))
                            idx = int(item_index)
                            if idx < len(evidence_items):
                                evidence = evidence_items[idx]
                            else:
                                evidence = Evidence(section=doc_section, evidence_type='other', title='Evidence')

                            if field_name == 'type' or field_name == 'evidence_type':
                                # Map common types to model choices
                                type_map = {
                                    'video': 'video', 'video recording': 'video', 'cell phone video': 'video',
                                    'audio': 'audio', 'audio recording': 'audio',
                                    'photo': 'photo', 'photograph': 'photo', 'photos': 'photo',
                                    'document': 'document', 'documents': 'document',
                                    'body_cam': 'body_cam', 'body camera': 'body_cam', 'bodycam': 'body_cam',
                                    'dash_cam': 'dash_cam', 'dash camera': 'dash_cam', 'dashcam': 'dash_cam',
                                    'surveillance': 'surveillance', 'security camera': 'surveillance',
                                    'social_media': 'social_media',
                                }
                                evidence.evidence_type = type_map.get(value.lower(), 'other')
                            elif field_name == 'title':
                                evidence.title = value
                            elif field_name == 'description':
                                evidence.description = value
                            elif field_name == 'date_created' and value:
                                try:
                                    evidence.date_created = datetime.strptime(value, '%Y-%m-%d').date()
                                except ValueError:
                                    pass  # Skip invalid dates
                            elif field_name == 'is_in_possession':
                                evidence.is_in_possession = value in [True, 'true', 'True', 1, '1']
                            elif field_name == 'needs_subpoena':
                                evidence.needs_subpoena = value in [True, 'true', 'True', 1, '1']
                            elif field_name == 'notes':
                                evidence.notes = value
                            elif field_name == 'location_obtained':
                                evidence.location_obtained = value

                            evidence.save()
                            saved_count += 1

                    # Default location_obtained to incident location for evidence in possession
                    try:
                        overview_section = document.sections.get(section_type='incident_overview')
                        incident_overview = IncidentOverview.objects.get(section=overview_section)
                        # Build location string from incident overview
                        location_parts = []
                        if incident_overview.incident_location:
                            location_parts.append(incident_overview.incident_location)
                        if incident_overview.city:
                            location_parts.append(incident_overview.city)
                        if incident_overview.state:
                            location_parts.append(incident_overview.state)
                        incident_location_str = ', '.join(location_parts) if location_parts else ''

                        if incident_location_str:
                            # Update evidence items in possession with blank location
                            Evidence.objects.filter(
                                section=doc_section,
                                is_in_possession=True,
                                location_obtained=''
                            ).update(location_obtained=incident_location_str)
                    except (DocumentSection.DoesNotExist, IncidentOverview.DoesNotExist):
                        pass  # No incident overview available

                    # Auto-complete if at least one evidence item added
                    if Evidence.objects.filter(section=doc_section).exists():
                        doc_section.status = 'completed'
                    else:
                        doc_section.status = 'in_progress'
                    doc_section.save()

                elif section_type == 'damages':
                    obj, created = Damages.objects.get_or_create(section=doc_section)
                    for f in section_fields:
                        field_name = f.get('field')
                        value = f.get('value')
                        if field_name == 'physical_injuries' and value:
                            obj.physical_injury = True
                            obj.physical_injury_description = value
                        elif field_name == 'emotional_distress' and value:
                            obj.emotional_distress = True
                            obj.emotional_distress_description = value
                        elif field_name == 'financial_losses' and value:
                            obj.property_damage = True
                            obj.property_damage_description = value
                        elif field_name == 'other_damages' and value:
                            obj.other_damages = value
                        saved_count += 1
                    obj.save()
                    # Auto-complete if criteria met
                    if check_section_complete(doc_section, obj):
                        doc_section.status = 'completed'
                    else:
                        doc_section.status = 'in_progress'
                    doc_section.save()

                elif section_type == 'rights_violated':
                    obj, created = RightsViolated.objects.get_or_create(section=doc_section)
                    for f in section_fields:
                        field_name = f.get('field')
                        amendment = f.get('amendment')
                        reason = f.get('reason', '')

                        if hasattr(obj, field_name):
                            setattr(obj, field_name, True)

                        if amendment == 'first':
                            obj.first_amendment = True
                            if reason and not obj.first_amendment_details:
                                obj.first_amendment_details = reason
                        elif amendment == 'fourth':
                            obj.fourth_amendment = True
                            if reason and not obj.fourth_amendment_details:
                                obj.fourth_amendment_details = reason
                        elif amendment == 'fifth':
                            obj.fifth_amendment = True
                            if reason and not obj.fifth_amendment_details:
                                obj.fifth_amendment_details = reason
                        elif amendment == 'fourteenth':
                            obj.fourteenth_amendment = True
                            if reason and not obj.fourteenth_amendment_details:
                                obj.fourteenth_amendment_details = reason

                        saved_count += 1
                    obj.save()
                    # Auto-complete if criteria met
                    if check_section_complete(doc_section, obj):
                        doc_section.status = 'completed'
                    else:
                        doc_section.status = 'in_progress'
                    doc_section.save()

                elif section_type == 'relief_sought':
                    obj, created = ReliefSought.objects.get_or_create(section=doc_section)
                    for f in section_fields:
                        field_name = f.get('field')
                        value = f.get('value')
                        reason = f.get('reason', '')

                        if field_name == 'compensatory_damages':
                            obj.compensatory_damages = value in [True, 'true', 'True']
                        elif field_name == 'punitive_damages':
                            obj.punitive_damages = value in [True, 'true', 'True']
                        elif field_name == 'declaratory_relief':
                            obj.declaratory_relief = value in [True, 'true', 'True']
                            if reason:
                                obj.declaratory_description = reason
                        elif field_name == 'injunctive_relief':
                            obj.injunctive_relief = value in [True, 'true', 'True']
                            if reason:
                                obj.injunctive_description = reason
                        elif field_name == 'attorney_fees':
                            obj.attorney_fees = value in [True, 'true', 'True']
                        elif field_name == 'jury_trial':
                            obj.jury_trial_demanded = value in [True, 'true', 'True']

                        saved_count += 1
                    obj.save()
                    # Auto-complete relief_sought section
                    doc_section.status = 'completed'
                    doc_section.save()

            except Exception as e:
                errors.append(f"{section_type}: {str(e)}")

        # Invalidate cached complaint since data changed
        document.invalidate_generated_complaint()

        return JsonResponse({
            'success': True,
            'saved_count': saved_count,
            'errors': errors if errors else None,
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid request format.',
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}',
        })


# ============================================================================
# Payment Views
# ============================================================================

@login_required
def checkout(request, document_id):
    """Display checkout page with promo code option."""
    document = get_object_or_404(Document, id=document_id, user=request.user)

    # Check/update expiry status
    document.check_and_update_expiry()

    # Allow checkout for draft or expired documents
    if document.payment_status not in ['draft', 'expired']:
        messages.info(request, 'This document has already been paid for.')
        return redirect('documents:document_detail', document_id=document.id)

    # Check if user has exhausted free AI uses - if so, allow checkout regardless of completion
    # This prevents a catch-22 where users can't complete sections without AI
    ai_limit_reached = not document.user.can_use_free_ai()

    # Check document completion before allowing checkout (skip if AI limit reached)
    if not ai_limit_reached:
        from django.db.models import Q
        sections = document.sections.all()
        incomplete_sections = sections.exclude(status__in=['completed', 'not_applicable'])

        # Check for defendants missing addresses
        defendants_section = sections.filter(section_type='defendants').first()
        defendants_missing_address = []
        if defendants_section:
            defendants_missing_address = list(
                defendants_section.defendants.filter(
                    Q(address__isnull=True) | Q(address='')
                ).values_list('name', flat=True)
            )

        # Check for court district issues
        court_district_issue = None
        incident_section = sections.filter(section_type='incident_overview').first()
        if incident_section:
            try:
                incident_overview = incident_section.incident_overview
                if not incident_overview.federal_district_court:
                    court_district_issue = "Federal district court has not been looked up"
                elif not incident_overview.court_district_confirmed:
                    court_district_issue = "Federal district court needs confirmation"
            except Exception:
                court_district_issue = "Incident overview incomplete"

        if incomplete_sections.exists() or defendants_missing_address or court_district_issue:
            # Build error message
            error_parts = []
            if incomplete_sections.exists():
                section_names = [s.get_section_type_display() for s in incomplete_sections]
                error_parts.append(f"incomplete sections: {', '.join(section_names)}")
            if defendants_missing_address:
                error_parts.append(f"defendants missing address: {', '.join(defendants_missing_address)}")
            if court_district_issue:
                error_parts.append(court_district_issue)

            messages.error(
                request,
                f"Cannot proceed to checkout. Please complete all sections first. Issues: {'; '.join(error_parts)}"
            )
            return redirect('documents:document_detail', document_id=document.id)

    # Calculate prices
    base_price = Decimal(str(settings.DOCUMENT_PRICE))
    discount_percent = Decimal(str(settings.PROMO_DISCOUNT_PERCENT))
    discounted_price = base_price - (base_price * discount_percent / 100)

    context = {
        'document': document,
        'base_price': base_price,
        'discounted_price': discounted_price,
        'discount_percent': int(discount_percent),
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
    }

    if request.method == 'POST':
        promo_code_str = request.POST.get('promo_code', '').strip().upper()
        no_promo_confirmed = request.POST.get('no_promo_confirmed') == 'on'

        # Validate promo code or confirmation
        promo_code = None
        final_price = base_price

        if promo_code_str:
            try:
                promo_code = PromoCode.objects.get(code=promo_code_str, is_active=True)
                # Check user hasn't already used a promo code
                if PromoCodeUsage.objects.filter(user=request.user).exists():
                    messages.error(request, 'You have already used a promo code on a previous purchase.')
                    return render(request, 'documents/checkout.html', context)
                # Check user isn't using their own code
                if promo_code.owner == request.user:
                    messages.error(request, 'You cannot use your own referral code.')
                    return render(request, 'documents/checkout.html', context)
                final_price = discounted_price
            except PromoCode.DoesNotExist:
                messages.error(request, 'Invalid promo code.')
                return render(request, 'documents/checkout.html', context)
        elif not no_promo_confirmed:
            messages.error(request, 'Please enter a promo code or confirm you do not have one.')
            return render(request, 'documents/checkout.html', context)

        # Create Stripe Checkout Session
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'unit_amount': int(final_price * 100),  # Stripe uses cents
                        'product_data': {
                            'name': f'Section 1983 Complaint: {document.title}',
                            'description': 'Complete legal document with AI assistance',
                        },
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=request.build_absolute_uri(
                    reverse('documents:checkout_success', args=[document.id])
                ) + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=request.build_absolute_uri(
                    reverse('documents:checkout_cancel', args=[document.id])
                ),
                metadata={
                    'document_id': str(document.id),
                    'user_id': str(request.user.id),
                    'promo_code': promo_code.code if promo_code else '',
                },
            )

            # Store promo code in session for later use
            if promo_code:
                request.session['pending_promo_code'] = promo_code.code

            return redirect(checkout_session.url)

        except stripe.error.StripeError as e:
            messages.error(request, f'Payment error: {str(e)}')
            return render(request, 'documents/checkout.html', context)

    return render(request, 'documents/checkout.html', context)


@login_required
def checkout_success(request, document_id):
    """Handle successful payment."""
    document = get_object_or_404(Document, id=document_id, user=request.user)

    session_id = request.GET.get('session_id')
    if not session_id:
        messages.error(request, 'Invalid checkout session.')
        return redirect('documents:document_detail', document_id=document.id)

    try:
        session = stripe.checkout.Session.retrieve(session_id)

        if session.payment_status == 'paid':
            # Update document status
            document.payment_status = 'paid'
            document.stripe_payment_id = session.payment_intent
            document.amount_paid = Decimal(str(session.amount_total / 100))
            document.paid_at = timezone.now()

            # Handle promo code
            promo_code_str = session.metadata.get('promo_code', '')
            if promo_code_str:
                try:
                    promo_code = PromoCode.objects.get(code=promo_code_str)
                    document.promo_code_used = promo_code

                    # Record promo usage (use the code's custom referral amount)
                    PromoCodeUsage.objects.create(
                        promo_code=promo_code,
                        document=document,
                        user=request.user,
                        stripe_payment_id=session.payment_intent,
                        amount_paid=document.amount_paid,
                        referral_amount=promo_code.referral_amount,
                    )

                    # Update promo code stats
                    promo_code.record_usage(promo_code.referral_amount)

                except PromoCode.DoesNotExist:
                    pass

            document.save()

            # Clear session data
            if 'pending_promo_code' in request.session:
                del request.session['pending_promo_code']

            messages.success(request, 'Payment successful! You now have full access to edit and finalize your document.')
            return redirect('documents:document_detail', document_id=document.id)

    except stripe.error.StripeError as e:
        messages.error(request, f'Error verifying payment: {str(e)}')

    return redirect('documents:document_detail', document_id=document.id)


@login_required
def checkout_cancel(request, document_id):
    """Handle cancelled payment."""
    messages.info(request, 'Payment was cancelled. You can try again when ready.')
    return redirect('documents:checkout', document_id=document_id)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Handle Stripe webhooks for payment confirmation."""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        # Get document and update status
        document_id = session['metadata'].get('document_id')
        if document_id:
            try:
                document = Document.objects.get(id=document_id)
                if document.payment_status in ['draft', 'expired']:
                    document.payment_status = 'paid'
                    document.stripe_payment_id = session.get('payment_intent', '')
                    document.amount_paid = Decimal(str(session['amount_total'] / 100))
                    document.paid_at = timezone.now()
                    document.save()
            except Document.DoesNotExist:
                pass

    return HttpResponse(status=200)


@login_required
def finalize_document(request, document_id):
    """Display finalization confirmation and handle PDF generation."""
    document = get_object_or_404(Document, id=document_id, user=request.user)

    if document.payment_status != 'paid':
        messages.error(request, 'You must complete payment before finalizing your document.')
        return redirect('documents:checkout', document_id=document.id)

    # Check for incomplete sections (ordered by SECTION_TYPES)
    section_type_order = [choice[0] for choice in DocumentSection.SECTION_TYPES]
    all_sections = list(document.sections.all())
    incomplete_sections = sorted(
        [s for s in all_sections if s.status not in ['completed', 'not_applicable']],
        key=lambda s: section_type_order.index(s.section_type) if s.section_type in section_type_order else 999
    )
    sections = document.sections.all()  # Keep for filter operations below

    # Check for defendants missing addresses
    from django.db.models import Q
    defendants_section = sections.filter(section_type='defendants').first()
    defendants_missing_address = []
    if defendants_section:
        defendants_missing_address = list(
            defendants_section.defendants.filter(
                Q(address__isnull=True) | Q(address='')
            ).values_list('name', flat=True)
        )

    # Check for court district issues
    court_district_issue = None
    incident_section = sections.filter(section_type='incident_overview').first()
    if incident_section:
        try:
            incident_overview = incident_section.incident_overview
            if not incident_overview.federal_district_court:
                court_district_issue = "Federal district court has not been looked up"
            elif not incident_overview.court_district_confirmed:
                court_district_issue = "Federal district court needs confirmation"
        except Exception:
            court_district_issue = "Incident overview incomplete"

    # Determine if document can be finalized
    can_finalize = not incomplete_sections and not defendants_missing_address and not court_district_issue

    if request.method == 'POST':
        # Block finalization if sections are incomplete
        if not can_finalize:
            messages.error(request, 'Please complete all sections and ensure all defendants have addresses before finalizing.')
            return render(request, 'documents/finalize.html', {
                'document': document,
                'incomplete_sections': incomplete_sections,
                'defendants_missing_address': defendants_missing_address,
                'court_district_issue': court_district_issue,
                'can_finalize': can_finalize,
            })

        confirmed = request.POST.get('confirm_finalize') == 'on'

        if not confirmed:
            messages.error(request, 'Please confirm that you have reviewed your document.')
            return render(request, 'documents/finalize.html', {
                'document': document,
                'incomplete_sections': incomplete_sections,
                'defendants_missing_address': defendants_missing_address,
                'court_district_issue': court_district_issue,
                'can_finalize': can_finalize,
            })

        # Finalize the document
        document.payment_status = 'finalized'
        document.finalized_at = timezone.now()
        document.save()

        messages.success(request, 'Your document has been finalized! You can now download or print your PDF.')
        return redirect('documents:document_preview', document_id=document.id)

    return render(request, 'documents/finalize.html', {
        'document': document,
        'incomplete_sections': incomplete_sections,
        'defendants_missing_address': defendants_missing_address,
        'court_district_issue': court_district_issue,
        'can_finalize': can_finalize,
    })


# ============================================================================
# Promo Code Views
# ============================================================================

@login_required
def my_referral_code(request):
    """Manage user's referral/promo codes (dashboard)."""
    # Get all promo codes for user
    promo_codes = PromoCode.objects.filter(owner=request.user).order_by('-created_at')

    if request.method == 'POST':
        new_code = request.POST.get('code', '').strip().upper()
        code_name = request.POST.get('name', '').strip()

        if not new_code:
            messages.error(request, 'Please enter a code.')
        elif len(new_code) < 4:
            messages.error(request, 'Code must be at least 4 characters.')
        elif len(new_code) > 20:
            messages.error(request, 'Code must be 20 characters or less.')
        elif not new_code.isalnum():
            messages.error(request, 'Code can only contain letters and numbers.')
        elif PromoCode.objects.filter(code=new_code).exists():
            messages.error(request, 'This code is already taken. Please choose another.')
        else:
            PromoCode.objects.create(
                owner=request.user,
                code=new_code,
                name=code_name,
            )
            messages.success(request, f'Your referral code "{new_code}" has been created!')
            return redirect('documents:my_referral_code')

    # Get all usages across all codes
    all_usages = PromoCodeUsage.objects.filter(
        promo_code__owner=request.user
    ).select_related('promo_code', 'user').order_by('-created_at')[:20]

    # Calculate totals
    total_earned = request.user.get_total_referral_earnings()
    pending_earnings = request.user.get_pending_referral_earnings()
    paid_earnings = request.user.get_paid_referral_earnings()

    # Get pending payout requests
    pending_requests = PayoutRequest.objects.filter(
        user=request.user, status__in=['pending', 'processing']
    )

    context = {
        'promo_codes': promo_codes,
        'all_usages': all_usages,
        'total_earned': total_earned,
        'pending_earnings': pending_earnings,
        'paid_earnings': paid_earnings,
        'pending_requests': pending_requests,
        'referral_payout': settings.REFERRAL_PAYOUT,
        'discount_percent': settings.PROMO_DISCOUNT_PERCENT,
    }

    return render(request, 'documents/my_referral_code.html', context)


@login_required
@require_POST
def toggle_promo_code(request, code_id):
    """Toggle a promo code's active status."""
    promo_code = get_object_or_404(PromoCode, id=code_id, owner=request.user)
    promo_code.is_active = not promo_code.is_active
    promo_code.save()
    status = 'activated' if promo_code.is_active else 'deactivated'
    messages.success(request, f'Code "{promo_code.code}" has been {status}.')
    return redirect('documents:my_referral_code')


@login_required
def request_payout(request):
    """Request a payout for pending referral earnings."""
    pending_earnings = request.user.get_pending_referral_earnings()

    if request.method == 'POST':
        if pending_earnings < 15:
            messages.error(request, 'Minimum payout amount is $15.00.')
            return redirect('documents:my_referral_code')

        # Check for existing pending request
        existing = PayoutRequest.objects.filter(
            user=request.user, status__in=['pending', 'processing']
        ).first()
        if existing:
            messages.warning(request, 'You already have a pending payout request.')
            return redirect('documents:my_referral_code')

        payment_method = request.POST.get('payment_method', '').strip()
        payment_details = request.POST.get('payment_details', '').strip()

        if not payment_method:
            messages.error(request, 'Please specify how you want to be paid.')
            return render(request, 'documents/request_payout.html', {
                'pending_earnings': pending_earnings
            })

        # Create payout request
        payout_request = PayoutRequest.objects.create(
            user=request.user,
            amount_requested=pending_earnings,
            payment_method=payment_method,
            payment_details=payment_details,
        )

        # Send email to admin
        try:
            send_mail(
                subject=f'Payout Request: ${pending_earnings} from {request.user.email}',
                message=f'''A user has requested a payout.

User: {request.user.email}
Amount: ${pending_earnings}
Payment Method: {payment_method}
Details: {payment_details}

Review and process at: {request.build_absolute_uri(reverse('documents:admin_referrals'))}
''',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_EMAIL],
                fail_silently=True,
            )
        except Exception:
            pass  # Don't fail if email fails

        messages.success(request, f'Payout request for ${pending_earnings} has been submitted! We will process it within 3-5 business days.')
        return redirect('documents:my_referral_code')

    context = {
        'pending_earnings': pending_earnings,
    }
    return render(request, 'documents/request_payout.html', context)


# ============================================================================
# Admin Referral Management Views
# ============================================================================

@staff_member_required
def admin_referrals(request):
    """Admin view to manage all referrals and payouts."""
    from accounts.models import User

    # Get all promo codes with stats
    all_codes = PromoCode.objects.select_related('owner').order_by('-times_used')

    # Get all usages
    all_usages = PromoCodeUsage.objects.select_related(
        'promo_code', 'promo_code__owner', 'user', 'document'
    ).order_by('-created_at')

    # Get pending payout requests
    payout_requests = PayoutRequest.objects.select_related(
        'user', 'processed_by'
    ).order_by('-created_at')

    # Summary stats
    total_referrals = PromoCodeUsage.objects.count()
    total_pending = PromoCodeUsage.objects.filter(payout_status='pending').aggregate(
        total=db_models.Sum('referral_amount')
    )['total'] or 0
    total_paid = PromoCodeUsage.objects.filter(payout_status='paid').aggregate(
        total=db_models.Sum('referral_amount')
    )['total'] or 0
    total_codes = PromoCode.objects.count()

    # Get all users who have promo codes with their stats
    code_owners = User.objects.filter(
        promo_codes__isnull=False
    ).distinct().prefetch_related('promo_codes').order_by('-created_at')

    # Calculate stats for each owner
    for owner in code_owners:
        owner.total_uses = sum(code.times_used for code in owner.promo_codes.all())
        owner.total_earned = sum(code.total_earned for code in owner.promo_codes.all())
        owner.pending_amount = PromoCodeUsage.objects.filter(
            promo_code__owner=owner, payout_status='pending'
        ).aggregate(total=db_models.Sum('referral_amount'))['total'] or 0
        owner.paid_amount = PromoCodeUsage.objects.filter(
            promo_code__owner=owner, payout_status='paid'
        ).aggregate(total=db_models.Sum('referral_amount'))['total'] or 0

    context = {
        'all_codes': all_codes,
        'all_usages': all_usages[:50],  # Last 50
        'payout_requests': payout_requests,
        'total_referrals': total_referrals,
        'total_pending': total_pending,
        'total_paid': total_paid,
        'total_codes': total_codes,
        'code_owners': code_owners,
    }

    return render(request, 'documents/admin_referrals.html', context)


@staff_member_required
@require_POST
def admin_process_payout(request, request_id):
    """Process a payout request."""
    payout_request = get_object_or_404(PayoutRequest, id=request_id)

    action = request.POST.get('action')

    if action == 'complete':
        amount_paid = request.POST.get('amount_paid', '').strip()
        payment_reference = request.POST.get('payment_reference', '').strip()
        admin_notes = request.POST.get('admin_notes', '').strip()

        if not amount_paid:
            messages.error(request, 'Please enter the amount paid.')
            return redirect('documents:admin_referrals')

        try:
            amount_paid = Decimal(amount_paid)
        except:
            messages.error(request, 'Invalid amount.')
            return redirect('documents:admin_referrals')

        # Mark the payout request as completed
        payout_request.mark_completed(
            admin_user=request.user,
            amount_paid=amount_paid,
            reference=payment_reference,
            notes=admin_notes
        )

        # Mark all pending usages for this user's codes as paid
        PromoCodeUsage.objects.filter(
            promo_code__owner=payout_request.user,
            payout_status='pending'
        ).update(
            payout_status='paid',
            payout_date=timezone.now(),
            payout_reference=payment_reference,
            payout_notes=f'Paid via payout request #{payout_request.id}'
        )

        messages.success(request, f'Payout of ${amount_paid} to {payout_request.user.email} marked as complete.')

    elif action == 'reject':
        admin_notes = request.POST.get('admin_notes', '').strip()
        payout_request.status = 'rejected'
        payout_request.admin_notes = admin_notes
        payout_request.processed_by = request.user
        payout_request.processed_at = timezone.now()
        payout_request.save()
        messages.warning(request, f'Payout request from {payout_request.user.email} has been rejected.')

    elif action == 'processing':
        payout_request.status = 'processing'
        payout_request.save()
        messages.info(request, f'Payout request marked as processing.')

    return redirect('documents:admin_referrals')


@staff_member_required
@require_POST
def admin_mark_usage_paid(request, usage_id):
    """Mark a single usage as paid."""
    usage = get_object_or_404(PromoCodeUsage, id=usage_id)

    payment_reference = request.POST.get('payment_reference', '').strip()
    payout_notes = request.POST.get('payout_notes', '').strip()

    usage.mark_paid(reference=payment_reference, notes=payout_notes)

    messages.success(request, f'Usage marked as paid.')
    return redirect('documents:admin_referrals')


@staff_member_required
@require_POST
def admin_edit_promo_code(request, code_id):
    """Edit a promo code's referral amount."""
    promo_code = get_object_or_404(PromoCode, id=code_id)

    referral_amount = request.POST.get('referral_amount', '').strip()

    if referral_amount:
        try:
            promo_code.referral_amount = Decimal(referral_amount)
            promo_code.save(update_fields=['referral_amount'])
            messages.success(request, f'Referral rate for {promo_code.code} updated to ${promo_code.referral_amount}.')
        except (ValueError, InvalidOperation):
            messages.error(request, 'Invalid amount.')

    return redirect('documents:admin_referrals')


@require_GET
def validate_promo_code(request):
    """AJAX endpoint to validate a promo code."""
    code = request.GET.get('code', '').strip().upper()

    if not code:
        return JsonResponse({'valid': False, 'error': 'No code provided'})

    try:
        promo_code = PromoCode.objects.get(code=code, is_active=True)

        # Check if user is logged in and trying to use their own code
        if request.user.is_authenticated and promo_code.owner == request.user:
            return JsonResponse({'valid': False, 'error': 'You cannot use your own referral code'})

        # Check if user has already used a promo code
        if request.user.is_authenticated and PromoCodeUsage.objects.filter(user=request.user).exists():
            return JsonResponse({'valid': False, 'error': 'You have already used a promo code'})

        discounted_price = Decimal(str(settings.DOCUMENT_PRICE)) * (100 - settings.PROMO_DISCOUNT_PERCENT) / 100

        return JsonResponse({
            'valid': True,
            'discount_percent': settings.PROMO_DISCOUNT_PERCENT,
            'discounted_price': float(discounted_price),
        })

    except PromoCode.DoesNotExist:
        return JsonResponse({'valid': False, 'error': 'Invalid promo code'})


@login_required
def download_pdf(request, document_id):
    """Download the finalized document as a PDF."""
    import os
    import re

    document = get_object_or_404(Document, id=document_id, user=request.user)

    # Only allow PDF download for finalized documents
    if document.payment_status != 'finalized':
        messages.error(request, 'Only finalized documents can be downloaded as PDF.')
        return redirect('documents:document_preview', document_id=document.id)

    # Sanitize filename for response
    safe_title = re.sub(r'[^\w\s-]', '', document.title)
    safe_title = re.sub(r'\s+', '_', safe_title.strip())
    filename = f"{safe_title}_Section_1983_Complaint.pdf"

    # Check if we have a pre-generated PDF file
    if document.pdf_file_path and os.path.exists(document.pdf_file_path):
        # Serve the pre-generated file
        with open(document.pdf_file_path, 'rb') as pdf_file:
            pdf_bytes = pdf_file.read()

        # Clean up the temp file after serving
        try:
            os.remove(document.pdf_file_path)
            document.pdf_file_path = ''
            document.save(update_fields=['pdf_file_path'])
        except Exception:
            pass

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    # Fallback: Generate PDF synchronously (for direct URL access)
    from django.template.loader import render_to_string
    from weasyprint import HTML
    from .services.document_generator import DocumentGenerator

    document_data = _collect_document_data(document)

    if not document_data.get('has_minimum_data'):
        messages.error(request, 'Document is missing required data for PDF generation.')
        return redirect('documents:document_preview', document_id=document.id)

    generator = DocumentGenerator()
    result = generator.generate_complaint(document_data)

    if not result.get('success'):
        messages.error(request, f'Error generating document: {result.get("error", "Unknown error")}')
        return redirect('documents:document_preview', document_id=document.id)

    generated_document = result.get('document')

    html_string = render_to_string('documents/document_pdf.html', {
        'document': document,
        'generated_document': generated_document,
        'document_data': document_data,
    })

    html = HTML(string=html_string)
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response


def _generate_pdf_background(document_id):
    """
    Background function to generate PDF.
    Runs in a separate thread to avoid blocking the request.
    """
    import django
    django.setup()  # Ensure Django is set up in this thread

    import tempfile
    import re
    from django.template.loader import render_to_string
    from weasyprint import HTML
    from .models import Document
    from .services.document_generator import DocumentGenerator

    try:
        document = Document.objects.get(id=document_id)

        # Stage 1: Collecting document data
        document.pdf_progress_stage = 'collecting_data'
        document.save(update_fields=['pdf_progress_stage'])

        document_data = _collect_document_data(document)

        if not document_data.get('has_minimum_data'):
            document.pdf_status = 'failed'
            document.pdf_error = 'Document is missing required data for PDF generation.'
            document.pdf_progress_stage = ''
            document.save(update_fields=['pdf_status', 'pdf_error', 'pdf_progress_stage'])
            return

        # Stage 2: Generating legal document
        document.pdf_progress_stage = 'generating_document'
        document.save(update_fields=['pdf_progress_stage'])

        generator = DocumentGenerator()
        result = generator.generate_complaint(document_data)

        if not result.get('success'):
            document.pdf_status = 'failed'
            document.pdf_error = f'Error generating document: {result.get("error", "Unknown error")}'
            document.pdf_progress_stage = ''
            document.save(update_fields=['pdf_status', 'pdf_error', 'pdf_progress_stage'])
            return

        generated_document = result.get('document')

        # Stage 3: Rendering HTML
        document.pdf_progress_stage = 'rendering_html'
        document.save(update_fields=['pdf_progress_stage'])

        html_string = render_to_string('documents/document_pdf.html', {
            'document': document,
            'generated_document': generated_document,
            'document_data': document_data,
        })

        # Stage 4: Creating PDF file
        document.pdf_progress_stage = 'creating_pdf'
        document.save(update_fields=['pdf_progress_stage'])

        html = HTML(string=html_string)
        pdf_bytes = html.write_pdf()

        # Save to temp file
        safe_title = re.sub(r'[^\w\s-]', '', document.title)
        safe_title = re.sub(r'\s+', '_', safe_title.strip())
        filename = f"{safe_title}_Section_1983_Complaint.pdf"

        # Create temp file that persists
        temp_file = tempfile.NamedTemporaryFile(
            mode='wb',
            suffix='.pdf',
            prefix=f'doc_{document_id}_',
            delete=False
        )
        temp_file.write(pdf_bytes)
        temp_file.close()

        # Mark as completed
        document.pdf_status = 'completed'
        document.pdf_progress_stage = 'ready'
        document.pdf_error = ''
        document.pdf_file_path = temp_file.name
        document.save(update_fields=['pdf_status', 'pdf_progress_stage', 'pdf_error', 'pdf_file_path'])

    except Exception as e:
        # Handle unexpected errors
        try:
            document = Document.objects.get(id=document_id)
            document.pdf_status = 'failed'
            document.pdf_error = str(e)
            document.pdf_progress_stage = ''
            document.save(update_fields=['pdf_status', 'pdf_error', 'pdf_progress_stage'])
        except Exception:
            pass  # Can't save error status


@login_required
@require_POST
def start_pdf_generation(request, document_id):
    """AJAX endpoint to start PDF generation in background."""
    try:
        document = get_object_or_404(Document, id=document_id, user=request.user)

        # Only allow PDF generation for finalized documents
        if document.payment_status != 'finalized':
            return JsonResponse({
                'success': False,
                'error': 'Only finalized documents can be downloaded as PDF.'
            })

        # Check if already processing (prevent duplicate requests)
        if document.pdf_status == 'processing':
            # Check if it's been processing for more than 2 minutes (stale)
            if document.pdf_started_at:
                elapsed = (timezone.now() - document.pdf_started_at).total_seconds()
                if elapsed < 120:  # Less than 2 minutes, still processing
                    return JsonResponse({
                        'success': True,
                        'status': 'processing',
                        'stage': document.pdf_progress_stage,
                        'message': 'PDF generation already in progress...'
                    })

        # Clean up any old temp file
        if document.pdf_file_path:
            import os
            try:
                if os.path.exists(document.pdf_file_path):
                    os.remove(document.pdf_file_path)
            except Exception:
                pass

        # Mark as processing and start background thread
        document.pdf_status = 'processing'
        document.pdf_started_at = timezone.now()
        document.pdf_progress_stage = 'starting'
        document.pdf_error = ''
        document.pdf_file_path = ''
        document.save(update_fields=[
            'pdf_status', 'pdf_started_at', 'pdf_progress_stage',
            'pdf_error', 'pdf_file_path'
        ])

        # Start background processing
        thread = threading.Thread(
            target=_generate_pdf_background,
            args=(document_id,),
            daemon=True
        )
        thread.start()

        return JsonResponse({
            'success': True,
            'status': 'processing',
            'stage': 'starting',
            'message': 'PDF generation started...'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        })


@login_required
@require_GET
def pdf_generation_status(request, document_id):
    """AJAX endpoint to check PDF generation status (for polling)."""
    try:
        document = get_object_or_404(Document, id=document_id, user=request.user)

        # Map internal stages to user-friendly messages
        stage_messages = {
            'starting': 'Starting PDF generation...',
            'collecting_data': 'Collecting document data...',
            'generating_document': 'Generating legal document...',
            'rendering_html': 'Formatting document...',
            'creating_pdf': 'Creating PDF file...',
            'ready': 'PDF ready for download!'
        }

        if document.pdf_status == 'processing':
            return JsonResponse({
                'success': True,
                'status': 'processing',
                'stage': document.pdf_progress_stage,
                'message': stage_messages.get(document.pdf_progress_stage, 'Processing...')
            })
        elif document.pdf_status == 'completed':
            # Reset status for next time (but keep file path)
            document.pdf_status = 'idle'
            document.pdf_progress_stage = ''
            document.save(update_fields=['pdf_status', 'pdf_progress_stage'])

            return JsonResponse({
                'success': True,
                'status': 'completed',
                'message': 'PDF ready for download!',
                'download_url': reverse('documents:download_pdf', args=[document.id])
            })
        elif document.pdf_status == 'failed':
            error = document.pdf_error or 'Unknown error occurred'

            # Reset status for retry
            document.pdf_status = 'idle'
            document.pdf_progress_stage = ''
            document.save(update_fields=['pdf_status', 'pdf_progress_stage'])

            return JsonResponse({
                'success': False,
                'status': 'failed',
                'error': error
            })
        else:
            # Idle - no generation in progress
            return JsonResponse({
                'success': True,
                'status': 'idle',
                'message': 'Ready to generate PDF'
            })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        })


# =============================================================================
# Video Analysis Views (YouTube transcript extraction - subscribers only)
# =============================================================================

@login_required
def video_analysis(request, document_id):
    """
    Main video analysis page for extracting YouTube transcripts.
    Only available to subscribers (Monthly/Annual Pro).
    """
    document = get_object_or_404(Document, id=document_id, user=request.user)

    # Check subscriber access
    if not request.user.can_use_video_analysis():
        messages.warning(
            request,
            'Video Analysis is available for Pro subscribers. '
            'Upgrade to extract transcripts from YouTube videos.'
        )
        return redirect('accounts:pricing')

    # Get evidence section for this document
    evidence_section = document.sections.filter(section_type='evidence').first()

    # Get all video evidence for this document
    video_evidences = []
    if evidence_section:
        # Get evidence items that have video_evidence attached
        for evidence in evidence_section.evidence_items.all():
            try:
                video_evidences.append(evidence.video_evidence)
            except VideoEvidence.DoesNotExist:
                pass

    # Get defendants for speaker attribution dropdown
    defendants_section = document.sections.filter(section_type='defendants').first()
    defendants = []
    if defendants_section:
        defendants = list(defendants_section.defendants.all())

    context = {
        'document': document,
        'video_evidences': video_evidences,
        'defendants': defendants,
        'max_clip_seconds': 120,  # 2 minutes
    }

    return render(request, 'documents/video_analysis.html', context)


@login_required
@require_POST
def video_add(request, document_id):
    """
    Add a new YouTube video for transcript extraction.
    Creates Evidence + VideoEvidence records.
    """
    document = get_object_or_404(Document, id=document_id, user=request.user)

    # Check subscriber access
    if not request.user.can_use_video_analysis():
        return JsonResponse({
            'success': False,
            'error': 'Video Analysis requires a Pro subscription.'
        }, status=403)

    youtube_url = request.POST.get('youtube_url', '').strip()
    if not youtube_url:
        return JsonResponse({
            'success': False,
            'error': 'Please enter a YouTube URL.'
        })

    # Extract video ID
    video_id = VideoEvidence.extract_video_id(youtube_url)
    if not video_id:
        return JsonResponse({
            'success': False,
            'error': 'Invalid YouTube URL. Please enter a valid YouTube video link.'
        })

    # Get or create evidence section
    evidence_section, _ = DocumentSection.objects.get_or_create(
        document=document,
        section_type='evidence',
        defaults={'status': 'in_progress', 'order': 7}
    )

    # Check if this video already exists for this document
    existing = VideoEvidence.objects.filter(
        evidence__section=evidence_section,
        video_id=video_id
    ).first()

    if existing:
        return JsonResponse({
            'success': False,
            'error': 'This video has already been added to your document.'
        })

    # Fetch video info from Supadata
    try:
        from .services.youtube_service import YouTubeService
        service = YouTubeService()

        # Try to get transcript to check if captions available
        result = service.get_transcript(youtube_url, use_ai_fallback=False)
        has_captions = result.success

        # Create Evidence record
        evidence = Evidence.objects.create(
            section=evidence_section,
            evidence_type='video',
            title=f'YouTube Video: {video_id}',
            description='YouTube video for transcript extraction',
            is_in_possession=True
        )

        # Create VideoEvidence record
        video_evidence = VideoEvidence.objects.create(
            evidence=evidence,
            youtube_url=youtube_url,
            video_id=video_id,
            video_title=f'Video {video_id}',  # Will be updated when we have metadata API
            has_youtube_captions=has_captions
        )

        return JsonResponse({
            'success': True,
            'video_id': video_evidence.id,
            'youtube_video_id': video_id,
            'has_captions': has_captions,
            'message': 'Video added successfully!'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error adding video: {str(e)}'
        })


@login_required
@require_POST
def link_youtube_to_evidence(request, document_id, evidence_id):
    """
    Link a YouTube video to an existing Evidence record.
    Creates a VideoEvidence record linked to the specified evidence.
    """
    document = get_object_or_404(Document, id=document_id, user=request.user)
    evidence = get_object_or_404(Evidence, id=evidence_id, section__document=document)

    # Check subscriber access
    if not request.user.can_use_video_analysis():
        return JsonResponse({
            'success': False,
            'error': 'Video Analysis requires a Pro subscription.'
        }, status=403)

    # Check if evidence already has a video linked
    if hasattr(evidence, 'video_evidence'):
        return JsonResponse({
            'success': False,
            'error': 'This evidence already has a YouTube video linked.'
        })

    # Parse JSON body
    import json
    try:
        data = json.loads(request.body)
        youtube_url = data.get('youtube_url', '').strip()
    except json.JSONDecodeError:
        youtube_url = request.POST.get('youtube_url', '').strip()

    if not youtube_url:
        return JsonResponse({
            'success': False,
            'error': 'Please enter a YouTube URL.'
        })

    # Extract video ID
    video_id = VideoEvidence.extract_video_id(youtube_url)
    if not video_id:
        return JsonResponse({
            'success': False,
            'error': 'Invalid YouTube URL. Please enter a valid YouTube video link.'
        })

    # Check if this video already exists for this document
    evidence_section = evidence.section
    existing = VideoEvidence.objects.filter(
        evidence__section=evidence_section,
        video_id=video_id
    ).first()

    if existing:
        return JsonResponse({
            'success': False,
            'error': 'This video has already been added to your document.'
        })

    # Just create the VideoEvidence record - no API calls
    # Caption availability will be checked on the video analysis page when user extracts clips
    try:
        video_evidence = VideoEvidence.objects.create(
            evidence=evidence,
            youtube_url=youtube_url,
            video_id=video_id,
            video_title=evidence.title or f'Video {video_id}',
            has_youtube_captions=False  # Will be updated when user extracts transcript
        )

        # Update evidence type to video if not already
        if evidence.evidence_type != 'video':
            evidence.evidence_type = 'video'
            evidence.save()

        return JsonResponse({
            'success': True,
            'video_evidence_id': video_evidence.id,
            'youtube_video_id': video_id,
            'redirect_url': f'/documents/{document_id}/video-analysis/',
            'message': 'Video linked successfully!'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error linking video: {str(e)}'
        })


@login_required
@require_POST
def unlink_youtube_from_evidence(request, document_id, evidence_id):
    """
    Unlink a YouTube video from an Evidence record.
    Deletes the VideoEvidence record but keeps the Evidence record.
    """
    document = get_object_or_404(Document, id=document_id, user=request.user)
    evidence = get_object_or_404(Evidence, id=evidence_id, section__document=document)

    # Check if evidence has a video linked
    if not hasattr(evidence, 'video_evidence'):
        return JsonResponse({
            'success': False,
            'error': 'This evidence does not have a YouTube video linked.'
        })

    try:
        # Delete just the VideoEvidence record, not the Evidence
        video_evidence = evidence.video_evidence
        video_evidence.delete()

        return JsonResponse({
            'success': True,
            'message': 'YouTube video unlinked successfully.'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error unlinking video: {str(e)}'
        })


@login_required
@require_POST
def quick_add_youtube_evidence(request, document_id):
    """
    Create a new Video Evidence record with YouTube link in one step.
    Creates an Evidence record and VideoEvidence record together.
    """
    document = get_object_or_404(Document, id=document_id, user=request.user)

    # Check subscriber access
    if not request.user.can_use_video_analysis():
        return JsonResponse({
            'success': False,
            'error': 'Video Analysis requires a Pro subscription.'
        }, status=403)

    # Get the evidence section
    try:
        evidence_section = document.sections.get(section_type='evidence')
    except DocumentSection.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Evidence section not found.'
        }, status=404)

    # Parse JSON body
    import json
    try:
        data = json.loads(request.body)
        youtube_url = data.get('youtube_url', '').strip()
    except json.JSONDecodeError:
        youtube_url = request.POST.get('youtube_url', '').strip()

    if not youtube_url:
        return JsonResponse({
            'success': False,
            'error': 'Please enter a YouTube URL.'
        })

    # Extract video ID
    video_id = VideoEvidence.extract_video_id(youtube_url)
    if not video_id:
        return JsonResponse({
            'success': False,
            'error': 'Invalid YouTube URL. Please enter a valid YouTube video link.'
        })

    # Check if this video already exists for this document
    existing = VideoEvidence.objects.filter(
        evidence__section=evidence_section,
        video_id=video_id
    ).first()

    if existing:
        return JsonResponse({
            'success': False,
            'error': 'This video has already been added to your document.'
        })

    try:
        # Create Evidence record
        evidence = Evidence.objects.create(
            section=evidence_section,
            evidence_type='video',
            title=f'YouTube Video ({video_id})',
            description='Video evidence from YouTube',
            is_in_possession=True
        )

        # Create VideoEvidence record
        video_evidence = VideoEvidence.objects.create(
            evidence=evidence,
            youtube_url=youtube_url,
            video_id=video_id,
            video_title=f'YouTube Video {video_id}',
            has_youtube_captions=False
        )

        return JsonResponse({
            'success': True,
            'evidence_id': evidence.id,
            'video_evidence_id': video_evidence.id,
            'youtube_video_id': video_id,
            'redirect_url': f'/documents/{document_id}/video-analysis/',
            'message': 'Video evidence added successfully!'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error adding video evidence: {str(e)}'
        })


@login_required
@require_POST
def video_delete(request, document_id, video_id):
    """Delete a video and all its captures."""
    document = get_object_or_404(Document, id=document_id, user=request.user)
    video_evidence = get_object_or_404(VideoEvidence, id=video_id)

    # Verify ownership
    if video_evidence.evidence.section.document != document:
        return JsonResponse({'success': False, 'error': 'Access denied.'}, status=403)

    # Delete the evidence (cascades to VideoEvidence)
    video_evidence.evidence.delete()

    return JsonResponse({
        'success': True,
        'message': 'Video deleted successfully.'
    })


@login_required
@require_POST
def video_add_capture(request, document_id, video_id):
    """Add a new capture (time range) to a video."""
    document = get_object_or_404(Document, id=document_id, user=request.user)
    video_evidence = get_object_or_404(VideoEvidence, id=video_id)

    # Verify ownership
    if video_evidence.evidence.section.document != document:
        return JsonResponse({'success': False, 'error': 'Access denied.'}, status=403)

    # Parse time inputs
    start_time = request.POST.get('start_time', '').strip()
    end_time = request.POST.get('end_time', '').strip()

    if not start_time or not end_time:
        return JsonResponse({
            'success': False,
            'error': 'Please enter both start and end times.'
        })

    try:
        start_seconds = VideoCapture.parse_time_to_seconds(start_time)
        end_seconds = VideoCapture.parse_time_to_seconds(end_time)
    except ValueError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid time format. Use M:SS or MM:SS format.'
        })

    # Validate
    if end_seconds <= start_seconds:
        return JsonResponse({
            'success': False,
            'error': 'End time must be after start time.'
        })

    duration = end_seconds - start_seconds
    if duration > 120:
        return JsonResponse({
            'success': False,
            'error': 'Clip duration cannot exceed 2 minutes (120 seconds).'
        })

    # Create capture
    capture = VideoCapture.objects.create(
        video_evidence=video_evidence,
        start_time_seconds=start_seconds,
        end_time_seconds=end_seconds,
        extraction_status='pending'
    )

    return JsonResponse({
        'success': True,
        'capture_id': capture.id,
        'start_display': capture.start_time_display,
        'end_display': capture.end_time_display,
        'duration_display': capture.duration_display,
        'message': 'Capture added. Click Extract to get the transcript.'
    })


@login_required
@require_POST
def video_delete_capture(request, document_id, capture_id):
    """Delete a capture."""
    document = get_object_or_404(Document, id=document_id, user=request.user)
    capture = get_object_or_404(VideoCapture, id=capture_id)

    # Verify ownership
    if capture.video_evidence.evidence.section.document != document:
        return JsonResponse({'success': False, 'error': 'Access denied.'}, status=403)

    capture.delete()

    return JsonResponse({
        'success': True,
        'message': 'Capture deleted.'
    })


@login_required
@require_POST
def video_extract_transcript(request, document_id, capture_id):
    """
    Extract transcript for a capture using Supadata API.
    Counts as 1 AI use toward subscriber limit.
    """
    document = get_object_or_404(Document, id=document_id, user=request.user)
    capture = get_object_or_404(VideoCapture, id=capture_id)

    # Verify ownership
    if capture.video_evidence.evidence.section.document != document:
        return JsonResponse({'success': False, 'error': 'Access denied.'}, status=403)

    # Check AI usage limits
    if not document.can_use_ai():
        return JsonResponse({
            'success': False,
            'limit_reached': True,
            'error': 'AI limit reached. Please upgrade your plan to continue.'
        })

    # Mark as processing
    capture.extraction_status = 'processing'
    capture.save(update_fields=['extraction_status'])

    try:
        from .services.youtube_service import YouTubeService
        service = YouTubeService()

        # Extract transcript for time range
        result = service.get_transcript_for_range(
            capture.video_evidence.youtube_url,
            capture.start_time_seconds,
            capture.end_time_seconds
        )

        if result.success:
            capture.raw_transcript = result.full_text
            capture.attributed_transcript = result.full_text  # Start with raw, user can edit
            capture.extraction_method = result.extraction_method
            capture.extraction_status = 'completed'
            capture.extraction_error = ''

            # Record AI usage
            if not capture.ai_use_recorded:
                document.record_ai_usage()
                capture.ai_use_recorded = True

            capture.save()

            return JsonResponse({
                'success': True,
                'transcript': result.full_text,
                'extraction_method': result.extraction_method,
                'language': result.language,
                'ai_usage_display': document.get_ai_usage_display(),
                'message': 'Transcript extracted successfully!'
            })
        else:
            capture.extraction_status = 'failed'
            capture.extraction_error = result.error or 'Unknown error'
            capture.save(update_fields=['extraction_status', 'extraction_error'])

            return JsonResponse({
                'success': False,
                'error': result.error or 'Failed to extract transcript.'
            })

    except Exception as e:
        capture.extraction_status = 'failed'
        capture.extraction_error = str(e)
        capture.save(update_fields=['extraction_status', 'extraction_error'])

        return JsonResponse({
            'success': False,
            'error': f'Error extracting transcript: {str(e)}'
        })


@login_required
@require_POST
def video_update_capture(request, document_id, capture_id):
    """Update capture transcript (user edits with speaker attribution)."""
    document = get_object_or_404(Document, id=document_id, user=request.user)
    capture = get_object_or_404(VideoCapture, id=capture_id)

    # Verify ownership
    if capture.video_evidence.evidence.section.document != document:
        return JsonResponse({'success': False, 'error': 'Access denied.'}, status=403)

    attributed_transcript = request.POST.get('attributed_transcript', '').strip()
    capture.attributed_transcript = attributed_transcript
    capture.save(update_fields=['attributed_transcript'])

    return JsonResponse({
        'success': True,
        'message': 'Transcript updated.'
    })


@login_required
@require_POST
def video_add_speaker(request, document_id, video_id):
    """Add a speaker to a video."""
    document = get_object_or_404(Document, id=document_id, user=request.user)
    video_evidence = get_object_or_404(VideoEvidence, id=video_id)

    # Verify ownership
    if video_evidence.evidence.section.document != document:
        return JsonResponse({'success': False, 'error': 'Access denied.'}, status=403)

    label = request.POST.get('label', '').strip()
    if not label:
        return JsonResponse({
            'success': False,
            'error': 'Please enter a speaker label.'
        })

    # Check if label already exists
    if video_evidence.speakers.filter(label=label).exists():
        return JsonResponse({
            'success': False,
            'error': f'Speaker "{label}" already exists.'
        })

    speaker = VideoSpeaker.objects.create(
        video_evidence=video_evidence,
        label=label
    )

    return JsonResponse({
        'success': True,
        'speaker_id': speaker.id,
        'label': speaker.label,
        'message': 'Speaker added.'
    })


@login_required
@require_POST
def video_update_speaker(request, document_id, video_id, speaker_id):
    """Update speaker attribution (link to defendant or mark as plaintiff)."""
    document = get_object_or_404(Document, id=document_id, user=request.user)
    video_evidence = get_object_or_404(VideoEvidence, id=video_id)
    speaker = get_object_or_404(VideoSpeaker, id=speaker_id, video_evidence=video_evidence)

    # Verify ownership
    if video_evidence.evidence.section.document != document:
        return JsonResponse({'success': False, 'error': 'Access denied.'}, status=403)

    # Get attribution type
    attribution_type = request.POST.get('attribution_type', '')
    defendant_id = request.POST.get('defendant_id', '')
    notes = request.POST.get('notes', '').strip()

    speaker.notes = notes

    if attribution_type == 'plaintiff':
        speaker.is_plaintiff = True
        speaker.defendant = None
    elif attribution_type == 'defendant' and defendant_id:
        # Get defendant and verify it belongs to this document
        defendants_section = document.sections.filter(section_type='defendants').first()
        if defendants_section:
            try:
                defendant = defendants_section.defendants.get(id=defendant_id)
                speaker.defendant = defendant
                speaker.is_plaintiff = False
            except Defendant.DoesNotExist:
                pass
    else:
        # Unattributed
        speaker.is_plaintiff = False
        speaker.defendant = None

    speaker.save()

    return JsonResponse({
        'success': True,
        'display_name': speaker.get_display_name(),
        'message': 'Speaker updated.'
    })


@login_required
@require_POST
def analyze_video_evidence(request, document_id):
    """
    Analyze video transcripts and suggest document updates.
    Returns suggestions for narrative, evidence descriptions, rights violations, and damages.
    """
    document = get_object_or_404(Document, id=document_id, user=request.user)

    # Check AI usage limits
    if not document.can_use_ai():
        return JsonResponse({
            'success': False,
            'error': 'You have used all free AI analyses. Please upgrade to continue.',
            'limit_reached': True,
        })

    # Get all video evidence with completed transcripts
    evidence_section = document.sections.filter(section_type='evidence').first()
    if not evidence_section:
        return JsonResponse({
            'success': False,
            'error': 'No evidence section found.'
        })

    # Collect all transcripts with timestamps
    transcripts = []
    video_evidences = VideoEvidence.objects.filter(
        evidence__section=evidence_section
    ).prefetch_related('captures')

    for video in video_evidences:
        for capture in video.captures.filter(extraction_status='completed'):
            transcript_text = capture.attributed_transcript or capture.raw_transcript
            if transcript_text:
                transcripts.append({
                    'video_title': video.video_title,
                    'video_id': video.video_id,
                    'youtube_url': video.youtube_url,
                    'start_time': capture.start_time_display,
                    'end_time': capture.end_time_display,
                    'transcript': transcript_text,
                })

    if not transcripts:
        return JsonResponse({
            'success': False,
            'error': 'No video transcripts found. Please extract transcripts from your videos first.'
        })

    # Get current document context
    story_text = document.story_text or ''

    # Get defendants for context
    defendants = []
    defendants_section = document.sections.filter(section_type='defendants').first()
    if defendants_section:
        defendants = list(defendants_section.defendants.values_list('name', flat=True))

    # Build transcript context for AI
    transcript_context = ""
    for i, t in enumerate(transcripts, 1):
        transcript_context += f"\n--- Video Clip {i}: {t['video_title']} [{t['start_time']} - {t['end_time']}] ---\n"
        transcript_context += f"YouTube URL: {t['youtube_url']}&t={_time_to_seconds(t['start_time'])}\n"
        transcript_context += f"Transcript:\n{t['transcript']}\n"

    # Call OpenAI for analysis
    from .services.openai_service import OpenAIService
    service = OpenAIService()

    system_message = """You are a legal assistant helping a pro se plaintiff build a Section 1983 civil rights complaint.
Analyze the video transcript evidence and suggest specific additions to the legal document.

For each suggestion, provide:
1. The target section (narrative, evidence, rights_violated, or damages)
2. A direct quote from the transcript
3. The timestamp reference formatted as [Video Title, MM:SS-MM:SS]
4. Suggested text to add to that section

Focus on:
- Direct quotes showing rights violations (threats, unlawful orders, excessive force)
- Statements by officers that demonstrate unlawful conduct
- Evidence of damages (emotional distress, intimidation)
- Key moments that support the plaintiff's claims

Return JSON in this exact format:
{
    "suggestions": [
        {
            "section": "narrative|evidence|rights_violated|damages",
            "quote": "Direct quote from transcript",
            "timestamp_ref": "[Video Title, 1:23-1:45]",
            "youtube_link": "full youtube URL with timestamp",
            "suggested_text": "Text to add to the document section",
            "explanation": "Brief explanation of why this is relevant"
        }
    ],
    "summary": "Brief overall summary of what the video evidence shows"
}"""

    user_prompt = f"""Plaintiff's Story:
{story_text}

Defendants: {', '.join(defendants) if defendants else 'Not specified'}

VIDEO TRANSCRIPT EVIDENCE:
{transcript_context}

Analyze these video transcripts and provide specific suggestions for improving the legal complaint.
Focus on direct quotes and statements that support the plaintiff's Section 1983 claims.
Include the YouTube link with timestamp for each suggestion so it can be referenced in the legal document."""

    try:
        response = service.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=3000,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        # Record AI usage
        document.record_ai_usage()

        return JsonResponse({
            'success': True,
            'suggestions': result.get('suggestions', []),
            'summary': result.get('summary', ''),
            'transcript_count': len(transcripts),
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error analyzing video evidence: {str(e)}'
        })


def _time_to_seconds(time_str):
    """Convert MM:SS or HH:MM:SS to seconds for YouTube timestamp."""
    parts = time_str.split(':')
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0


@login_required
@require_POST
def apply_video_suggestion(request, document_id):
    """
    Apply a video evidence suggestion directly to a document section.
    Appends the suggested text to the appropriate field.
    """
    document = get_object_or_404(Document, id=document_id, user=request.user)

    try:
        data = json.loads(request.body)
        section_type = data.get('section', '').strip()
        text = data.get('text', '').strip()
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request format.'})

    if not section_type or not text:
        return JsonResponse({'success': False, 'error': 'Section and text are required.'})

    try:
        if section_type == 'narrative':
            section = document.sections.get(section_type='incident_narrative')
            # Get or create IncidentNarrative model if it doesn't exist
            try:
                narrative = section.incident_narrative
            except IncidentNarrative.DoesNotExist:
                narrative = IncidentNarrative.objects.create(section=section)
            if narrative.detailed_narrative:
                narrative.detailed_narrative += '\n\n' + text
            else:
                narrative.detailed_narrative = text
            narrative.save()
            return JsonResponse({
                'success': True,
                'message': 'Added to Incident Narrative',
                'section_url': f'/documents/{document_id}/section/incident_narrative/'
            })

        elif section_type == 'damages':
            section = document.sections.get(section_type='damages')
            # Get or create Damages model if it doesn't exist
            try:
                damages = section.damages
            except Damages.DoesNotExist:
                damages = Damages.objects.create(section=section)
            # Append to emotional distress field (most common for video evidence)
            if damages.emotional_distress:
                damages.emotional_distress += '\n\n' + text
            else:
                damages.emotional_distress = text
            damages.save()
            return JsonResponse({
                'success': True,
                'message': 'Added to Damages (Emotional Distress)',
                'section_url': f'/documents/{document_id}/section/damages/'
            })

        elif section_type == 'rights_violated':
            section = document.sections.get(section_type='rights_violated')
            # Get or create RightsViolated model if it doesn't exist
            try:
                rights = section.rights_violated
            except RightsViolated.DoesNotExist:
                rights = RightsViolated.objects.create(section=section)

            # Try to find the most appropriate amendment details field
            # Check which amendments are checked and append to the first one
            if rights.first_amendment:
                if rights.first_amendment_details:
                    rights.first_amendment_details += '\n\n' + text
                else:
                    rights.first_amendment_details = text
                field_name = '1st Amendment Details'
            elif rights.fourth_amendment:
                if rights.fourth_amendment_details:
                    rights.fourth_amendment_details += '\n\n' + text
                else:
                    rights.fourth_amendment_details = text
                field_name = '4th Amendment Details'
            elif rights.fourteenth_amendment:
                if rights.fourteenth_amendment_details:
                    rights.fourteenth_amendment_details += '\n\n' + text
                else:
                    rights.fourteenth_amendment_details = text
                field_name = '14th Amendment Details'
            else:
                # Default to first amendment if none checked
                if rights.first_amendment_details:
                    rights.first_amendment_details += '\n\n' + text
                else:
                    rights.first_amendment_details = text
                field_name = '1st Amendment Details'

            rights.save()
            return JsonResponse({
                'success': True,
                'message': f'Added to Rights Violated ({field_name})',
                'section_url': f'/documents/{document_id}/section/rights_violated/'
            })

        elif section_type == 'evidence':
            # For evidence, we can't easily pick which item, so just copy
            return JsonResponse({
                'success': False,
                'copy_only': True,
                'message': 'For evidence descriptions, please paste manually into the specific evidence item.'
            })

        else:
            return JsonResponse({'success': False, 'error': f'Unknown section type: {section_type}'})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ============================================================================
# FINAL DOCUMENT REVIEW - New pathway for reviewing/editing actual document text
# ============================================================================

@login_required
def final_review(request, document_id):
    """
    Final document review page where users can:
    1. View the complete generated legal document
    2. Edit any section text inline
    3. Get AI review of the actual document text
    4. Download the final PDF

    Auto-generates document on first visit if not already generated.
    """
    document = get_object_or_404(Document, id=document_id, user=request.user)

    # Check and update expiry status
    document.check_and_update_expiry()

    # Collect document data for context
    document_data = _collect_document_data(document)

    # Check completion percentage
    completion_pct = document.get_completion_percentage()

    # Auto-generate if not generated and completion is sufficient
    auto_generate_error = None
    if not document.has_final_document() and completion_pct >= 50 and document.can_use_ai():
        try:
            from .services.document_generator import DocumentGenerator
            generator = DocumentGenerator()
            result = generator.generate_complaint(document_data)

            if result.get('success'):
                sections = result.get('document', {})
                document.final_introduction = sections.get('introduction', '')
                document.final_jurisdiction = sections.get('jurisdiction', '')
                document.final_parties = sections.get('parties', '')
                document.final_facts = sections.get('facts', '')
                document.final_prayer = sections.get('prayer', '')
                document.final_jury_demand = sections.get('jury_demand', '')
                document.final_signature = sections.get('signature', '')
                document.final_causes_of_action = sections.get('causes_of_action', [])
                document.final_generated_at = timezone.now()
                document.save()
                document.record_ai_usage()
        except Exception as e:
            auto_generate_error = str(e)

    # Define the sections for display
    final_sections = [
        {'key': 'introduction', 'title': 'Introduction', 'field': 'final_introduction'},
        {'key': 'jurisdiction', 'title': 'Jurisdiction and Venue', 'field': 'final_jurisdiction'},
        {'key': 'parties', 'title': 'Parties', 'field': 'final_parties'},
        {'key': 'facts', 'title': 'Statement of Facts', 'field': 'final_facts'},
        {'key': 'causes_of_action', 'title': 'Causes of Action', 'field': 'final_causes_of_action', 'is_list': True},
        {'key': 'prayer', 'title': 'Prayer for Relief', 'field': 'final_prayer'},
        {'key': 'jury_demand', 'title': 'Jury Demand', 'field': 'final_jury_demand'},
        {'key': 'signature', 'title': 'Signature Block', 'field': 'final_signature'},
    ]

    # Add current values to sections
    for section in final_sections:
        if section.get('is_list'):
            section['value'] = getattr(document, section['field'], []) or []
        else:
            section['value'] = getattr(document, section['field'], '') or ''

    # Check if interview data changed since document was generated
    data_changed = False
    if document.has_final_document() and document.final_generated_at:
        if document.updated_at > document.final_generated_at:
            data_changed = True

    context = {
        'document': document,
        'document_data': document_data,
        'final_sections': final_sections,
        'completion_pct': completion_pct,
        'has_final_document': document.has_final_document(),
        'can_edit': document.can_edit(),
        'can_use_ai': document.can_use_ai(),
        'auto_generate_error': auto_generate_error,
        'data_changed': data_changed,
    }

    return render(request, 'documents/final_review.html', context)


@login_required
@require_POST
def generate_final_document(request, document_id):
    """
    Generate all final document sections using AI.
    Populates the final_* fields on the Document model.
    """
    document = get_object_or_404(Document, id=document_id, user=request.user)

    # Check permissions
    if not document.can_edit():
        return JsonResponse({
            'success': False,
            'error': 'Document cannot be edited.'
        })

    # Check AI limit
    if not document.can_use_ai():
        return JsonResponse({
            'success': False,
            'limit_reached': True,
            'error': 'AI limit reached. Please upgrade to continue.'
        })

    try:
        # Import generator
        from .services.document_generator import DocumentGenerator

        # Collect all document data
        document_data = _collect_document_data(document)

        # Generate the complaint
        generator = DocumentGenerator()
        result = generator.generate_complaint(document_data)

        if not result.get('success'):
            return JsonResponse({
                'success': False,
                'error': 'Failed to generate document.'
            })

        sections = result.get('document', {})

        # Save to final fields
        document.final_introduction = sections.get('introduction', '')
        document.final_jurisdiction = sections.get('jurisdiction', '')
        document.final_parties = sections.get('parties', '')
        document.final_facts = sections.get('facts', '')
        document.final_prayer = sections.get('prayer', '')
        document.final_jury_demand = sections.get('jury_demand', '')
        document.final_signature = sections.get('signature', '')

        # Causes of action is a list of dicts
        causes = sections.get('causes_of_action', [])
        document.final_causes_of_action = causes

        document.final_generated_at = timezone.now()
        document.final_edited_at = None  # Reset edited time
        document.save()

        # Record AI usage
        document.record_ai_usage()

        return JsonResponse({
            'success': True,
            'message': 'Document generated successfully.',
            **get_ai_usage_info(document)
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error generating document: {str(e)}'
        })


@login_required
@require_POST
def save_final_section(request, document_id):
    """
    Save a single section of the final document.
    AJAX endpoint for inline editing.
    """
    document = get_object_or_404(Document, id=document_id, user=request.user)

    if not document.can_edit():
        return JsonResponse({
            'success': False,
            'error': 'Document cannot be edited.'
        })

    try:
        data = json.loads(request.body)
        section_key = data.get('section', '').strip()
        content = data.get('content', '')
        cause_index = data.get('cause_index')  # For causes of action list
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request format.'})

    if not section_key:
        return JsonResponse({'success': False, 'error': 'Section key is required.'})

    # Map section keys to model fields
    field_map = {
        'introduction': 'final_introduction',
        'jurisdiction': 'final_jurisdiction',
        'parties': 'final_parties',
        'facts': 'final_facts',
        'prayer': 'final_prayer',
        'jury_demand': 'final_jury_demand',
        'signature': 'final_signature',
    }

    try:
        if section_key == 'causes_of_action':
            # Handle causes of action (list)
            if cause_index is not None:
                causes = document.final_causes_of_action or []
                if 0 <= cause_index < len(causes):
                    causes[cause_index]['content'] = content
                    document.final_causes_of_action = causes
        elif section_key in field_map:
            setattr(document, field_map[section_key], content)
        else:
            return JsonResponse({'success': False, 'error': f'Unknown section: {section_key}'})

        document.final_edited_at = timezone.now()
        document.save()

        return JsonResponse({
            'success': True,
            'message': 'Section saved successfully.'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error saving section: {str(e)}'
        })


@login_required
@require_POST
def ai_review_final(request, document_id):
    """
    AI reviews the actual final document text and suggests improvements.
    Reviews the generated/edited text, not the raw input data.
    Uses OpenAIService with prompts from database.
    """
    document = get_object_or_404(Document, id=document_id, user=request.user)

    if not document.can_use_ai():
        return JsonResponse({
            'success': False,
            'limit_reached': True,
            'error': 'AI limit reached. Please upgrade to continue.'
        })

    if not document.has_final_document():
        return JsonResponse({
            'success': False,
            'error': 'Please generate the document first before requesting AI review.'
        })

    try:
        from .services.openai_service import OpenAIService
        service = OpenAIService()

        result = service.review_final_document(document)

        if not result.get('success'):
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'AI review failed.')
            })

        # Record AI usage
        document.record_ai_usage()

        return JsonResponse({
            'success': True,
            'review': result.get('review', {}),
            **get_ai_usage_info(document)
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error during AI review: {str(e)}'
        })


@login_required
@require_POST
def regenerate_final_section(request, document_id):
    """
    Regenerate a single section of the final document using AI.
    """
    document = get_object_or_404(Document, id=document_id, user=request.user)

    if not document.can_edit():
        return JsonResponse({
            'success': False,
            'error': 'Document cannot be edited.'
        })

    if not document.can_use_ai():
        return JsonResponse({
            'success': False,
            'limit_reached': True,
            'error': 'AI limit reached. Please upgrade to continue.'
        })

    try:
        data = json.loads(request.body)
        section_key = data.get('section', '').strip()
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request format.'})

    if not section_key:
        return JsonResponse({'success': False, 'error': 'Section key is required.'})

    try:
        from .services.document_generator import DocumentGenerator

        # Collect document data
        document_data = _collect_document_data(document)
        generator = DocumentGenerator()

        # Regenerate specific section
        if section_key == 'introduction':
            new_content = generator._generate_introduction(document_data)
            document.final_introduction = new_content
        elif section_key == 'jurisdiction':
            new_content = generator._generate_jurisdiction(document_data)
            document.final_jurisdiction = new_content
        elif section_key == 'parties':
            new_content = generator._generate_parties(document_data)
            document.final_parties = new_content
        elif section_key == 'facts':
            new_content = generator._generate_facts(document_data)
            document.final_facts = new_content
        elif section_key == 'prayer':
            new_content = generator._generate_prayer(document_data)
            document.final_prayer = new_content
        elif section_key == 'jury_demand':
            new_content = generator._generate_jury_demand(document_data)
            document.final_jury_demand = new_content
        elif section_key == 'signature':
            new_content = generator._generate_signature(document_data)
            document.final_signature = new_content
        elif section_key == 'causes_of_action':
            new_content = generator._generate_causes_of_action(document_data)
            document.final_causes_of_action = new_content
        else:
            return JsonResponse({'success': False, 'error': f'Unknown section: {section_key}'})

        document.final_edited_at = timezone.now()
        document.save()

        # Record AI usage
        document.record_ai_usage()

        return JsonResponse({
            'success': True,
            'content': new_content,
            'message': f'{section_key.replace("_", " ").title()} regenerated successfully.',
            **get_ai_usage_info(document)
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error regenerating section: {str(e)}'
        })


@login_required
def download_final_pdf(request, document_id):
    """
    Generate and download PDF from the final document fields.
    """
    document = get_object_or_404(Document, id=document_id, user=request.user)

    if not document.has_final_document():
        messages.error(request, 'Please generate the document first.')
        return redirect('documents:final_review', document_id=document_id)

    # Check payment status for watermark
    is_draft = document.payment_status in ('draft', 'expired')

    try:
        from weasyprint import HTML
        from django.template.loader import render_to_string

        # Collect document data for caption
        document_data = _collect_document_data(document)

        # Render PDF template
        html_content = render_to_string('documents/final_pdf.html', {
            'document': document,
            'document_data': document_data,
            'is_draft': is_draft,
            'app_name': settings.APP_NAME,
        })

        # Generate PDF
        pdf = HTML(string=html_content).write_pdf()

        # Create response
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"complaint_{document.id}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        messages.error(request, f'Error generating PDF: {str(e)}')
        return redirect('documents:final_review', document_id=document_id)