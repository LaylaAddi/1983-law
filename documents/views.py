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
    PromoCode, PromoCodeUsage, PayoutRequest
)

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


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

    sections = document.sections.all()

    # Check for defendants with AI-inferred agencies that need review
    defendants_needing_review = []
    defendants_section = sections.filter(section_type='defendants').first()
    if defendants_section:
        defendants_needing_review = defendants_section.defendants.filter(agency_inferred=True)

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
    })


@login_required
def section_edit(request, document_id, section_type):
    """Edit a specific section of the document (interview style)."""
    document = get_object_or_404(Document, id=document_id, user=request.user)

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
    }

    # For profile-based sections, add user profile data for read-only display
    if is_profile_based:
        context['user_profile'] = request.user

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
    """Preview the complete document as a professionally written legal complaint."""
    document = get_object_or_404(Document, id=document_id, user=request.user)

    # Check if user wants to force regeneration
    regenerate = request.GET.get('regenerate', 'false').lower() == 'true'

    # Collect all document data for the generator
    document_data = _collect_document_data(document)

    generated_document = None
    generation_error = None
    used_cache = False

    # Check for cached version first (unless regenerating)
    if not regenerate and document.generated_complaint and document.generated_at:
        generated_document = document.generated_complaint
        used_cache = True
    elif document_data.get('has_minimum_data'):
        # Generate new document
        try:
            from .services.document_generator import DocumentGenerator
            generator = DocumentGenerator()
            result = generator.generate_complaint(document_data)
            if result.get('success'):
                generated_document = result.get('document')
                # Cache the generated document
                document.generated_complaint = generated_document
                document.generated_at = timezone.now()
                document.save(update_fields=['generated_complaint', 'generated_at'])
            else:
                generation_error = result.get('error', 'Unknown generation error')
        except Exception as e:
            # Log error but continue to show data view
            generation_error = str(e)
            import traceback
            traceback.print_exc()

    # Also load raw section data for reference/editing
    sections_data = {}
    for section in document.sections.all():
        config = SECTION_CONFIG.get(section.section_type, {})
        Model = config.get('model')
        Form = config.get('form')
        is_multiple = config.get('multiple', False)

        if Model and Form:
            if is_multiple:
                items = Model.objects.filter(section=section)
                form = Form()
                data = list(items)
            else:
                try:
                    instance = Model.objects.get(section=section)
                    form = Form(instance=instance)
                    data = instance
                except Model.DoesNotExist:
                    form = Form()
                    data = None

            sections_data[section.section_type] = {
                'section': section,
                'config': config,
                'data': data,
                'form': form,
                'is_multiple': is_multiple,
            }

    context = {
        'document': document,
        'sections_data': sections_data,
        'section_config': SECTION_CONFIG,
        'generated_document': generated_document,
        'document_data': document_data,
        'generation_error': generation_error,
        'used_cache': used_cache,
        'generated_at': document.generated_at,
    }

    return render(request, 'documents/document_preview.html', context)


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
            'incident_time': str(io.incident_time) if io.incident_time else '',
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
def lookup_address(request, document_id):
    """AJAX endpoint to lookup agency address using web search."""

    try:
        # Verify document ownership
        document = get_object_or_404(Document, id=document_id, user=request.user)

        data = json.loads(request.body)
        agency_name = data.get('agency_name', '').strip()

        if not agency_name:
            return JsonResponse({
                'success': False,
                'error': 'Agency name is required.',
            })

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

        from .services.openai_service import OpenAIService
        service = OpenAIService()
        result = service.lookup_agency_address(agency_name, city, state)

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
                        try:
                            obj.incident_date = datetime.strptime(
                                incident_data['incident_date'], '%Y-%m-%d'
                            ).date()
                        except ValueError:
                            pass
                    if incident_data.get('incident_time'):
                        obj.incident_time = incident_data['incident_time']
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
                            court_service = CourtLookupService()
                            court_result = court_service.lookup_court(obj.city, obj.state)
                            if court_result.get('success') and court_result.get('court'):
                                obj.federal_district_court = court_result['court']
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
                        if item_index is not None and value:
                            evidence_items = list(Evidence.objects.filter(section=doc_section))
                            idx = int(item_index)
                            if idx < len(evidence_items):
                                evidence = evidence_items[idx]
                            else:
                                evidence = Evidence(section=doc_section, evidence_type='other', title='Evidence')
                            if field_name == 'type':
                                evidence.evidence_type = value.lower()
                                evidence.title = value
                            elif field_name == 'description':
                                evidence.description = value
                            evidence.save()
                            saved_count += 1
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

    if request.method == 'POST':
        confirmed = request.POST.get('confirm_finalize') == 'on'

        if not confirmed:
            messages.error(request, 'Please confirm that you have reviewed your document.')
            return render(request, 'documents/finalize.html', {'document': document})

        # Finalize the document
        document.payment_status = 'finalized'
        document.finalized_at = timezone.now()
        document.save()

        messages.success(request, 'Your document has been finalized! You can now download or print your PDF.')
        return redirect('documents:document_preview', document_id=document.id)

    return render(request, 'documents/finalize.html', {'document': document})


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
    from django.http import HttpResponse
    from django.template.loader import render_to_string
    from weasyprint import HTML

    document = get_object_or_404(Document, id=document_id, user=request.user)

    # Only allow PDF download for finalized documents
    if document.payment_status != 'finalized':
        from django.contrib import messages
        messages.error(request, 'Only finalized documents can be downloaded as PDF.')
        return redirect('documents:document_preview', document_id=document.id)

    # Collect document data and generate the legal document
    document_data = _collect_document_data(document)

    if not document_data.get('has_minimum_data'):
        from django.contrib import messages
        messages.error(request, 'Document is missing required data for PDF generation.')
        return redirect('documents:document_preview', document_id=document.id)

    # Generate the legal document
    from .services.document_generator import DocumentGenerator
    generator = DocumentGenerator()
    result = generator.generate_complaint(document_data)

    if not result.get('success'):
        from django.contrib import messages
        messages.error(request, f'Error generating document: {result.get("error", "Unknown error")}')
        return redirect('documents:document_preview', document_id=document.id)

    generated_document = result.get('document')

    # Render the PDF template
    html_string = render_to_string('documents/document_pdf.html', {
        'document': document,
        'generated_document': generated_document,
        'document_data': document_data,
    })

    # Generate PDF
    html = HTML(string=html_string)
    pdf = html.write_pdf()

    # Create response with PDF
    response = HttpResponse(pdf, content_type='application/pdf')
    # Sanitize filename - remove special characters, replace spaces with underscores
    import re
    safe_title = re.sub(r'[^\w\s-]', '', document.title)  # Remove special chars
    safe_title = re.sub(r'\s+', '_', safe_title.strip())  # Replace spaces with underscores
    filename = f"{safe_title}_Section_1983_Complaint.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response