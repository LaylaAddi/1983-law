from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import models as db_models
from .help_content import get_section_help
from .models import (
    Document, DocumentSection, PlaintiffInfo, IncidentOverview,
    Defendant, IncidentNarrative, RightsViolated, Witness,
    Evidence, Damages, PriorComplaints, ReliefSought,
    CaseLaw, DocumentCaseLaw
)


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

    messages.success(request, 'Item deleted.')
    return redirect('documents:section_edit',
                   document_id=document.id,
                   section_type=section_type)


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

    # Check if we should generate the legal document
    generate = request.GET.get('generate', 'true').lower() == 'true'

    # Collect all document data for the generator
    document_data = _collect_document_data(document)

    generated_document = None
    generation_error = None
    if generate and document_data.get('has_minimum_data'):
        try:
            from .services.document_generator import DocumentGenerator
            generator = DocumentGenerator()
            result = generator.generate_complaint(document_data)
            if result.get('success'):
                generated_document = result.get('document')
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

    # Get case law citations for this document
    case_law_citations = DocumentCaseLaw.objects.filter(
        document=document,
        status__in=['accepted', 'edited']
    ).select_related('case_law').order_by('amendment', 'order')

    context = {
        'document': document,
        'sections_data': sections_data,
        'section_config': SECTION_CONFIG,
        'case_law_citations': case_law_citations,
        'generated_document': generated_document,
        'document_data': document_data,
        'generation_error': generation_error,
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
        'case_law': [],
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

    # Case law citations
    case_law_citations = DocumentCaseLaw.objects.filter(
        document=document,
        status__in=['accepted', 'edited']
    ).select_related('case_law')

    for cl in case_law_citations:
        data['case_law'].append({
            'case_name': cl.case_law.case_name,
            'citation': cl.case_law.citation,
            'amendment': cl.amendment,
            'right_category': cl.right_category,
            'key_holding': cl.case_law.key_holding,
            'citation_text': cl.case_law.citation_text,
            'explanation': cl.get_explanation(),
        })

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
def rewrite_text(request):
    """AJAX endpoint to rewrite text using ChatGPT for legal format."""
    import json

    try:
        data = json.loads(request.body)
        text = data.get('text', '').strip()
        field_name = data.get('field_name', '')

        if not text:
            return JsonResponse({
                'success': False,
                'error': 'No text provided to rewrite',
            })

        from .services.openai_service import OpenAIService
        service = OpenAIService()
        result = service.rewrite_text(text, field_name)

        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body',
        })
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


@login_required
@require_POST
def parse_story(request, document_id):
    """AJAX endpoint to parse user's story and extract structured data."""
    import json
    from datetime import datetime

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

        from .services.openai_service import OpenAIService
        from .services.court_lookup_service import CourtLookupService
        from django.utils import timezone

        service = OpenAIService()
        result = service.parse_story(story_text)

        # Save story text to document if parsing was successful
        if result.get('success'):
            document.story_text = story_text
            document.story_told_at = timezone.now()
            document.save(update_fields=['story_text', 'story_told_at'])

            # Auto-apply incident_overview fields
            extracted = result.get('data', {})
            incident_data = extracted.get('incident_overview', {})

            if incident_data:
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

                # Auto-lookup federal district court if city/state are provided
                if obj.city and obj.state and not obj.federal_district_court:
                    try:
                        court_service = CourtLookupService()
                        court_result = court_service.lookup_court(obj.city, obj.state)
                        if court_result.get('success') and court_result.get('court'):
                            obj.federal_district_court = court_result['court']
                            obj.district_lookup_confidence = court_result.get('confidence', 'medium')
                    except Exception:
                        pass  # Don't fail if court lookup fails

                obj.save()

                # Update section status
                if check_section_complete(doc_section, obj):
                    doc_section.status = 'completed'
                elif doc_section.status == 'not_started':
                    doc_section.status = 'in_progress'
                doc_section.save()

                # Add auto-applied notice to result
                result['auto_applied'] = {
                    'incident_overview': True,
                    'fields_applied': [k for k, v in incident_data.items() if v]
                }

        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid request format.',
        })
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
                    for f in section_fields:
                        item_index = f.get('itemIndex')
                        field_name = f.get('field')
                        value = f.get('value')
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

            except Exception as e:
                errors.append(f"{section_type}: {str(e)}")

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


# ============================================================
# CASE LAW VIEWS
# ============================================================

@login_required
def case_law_list(request, document_id):
    """View and manage case law citations for a document."""
    document = get_object_or_404(Document, id=document_id, user=request.user)

    # Get existing citations for this document
    citations = DocumentCaseLaw.objects.filter(document=document).select_related('case_law')

    # Group by amendment for display
    citations_by_amendment = {}
    for citation in citations:
        amendment = citation.amendment
        if amendment not in citations_by_amendment:
            citations_by_amendment[amendment] = []
        citations_by_amendment[amendment].append(citation)

    context = {
        'document': document,
        'citations': citations,
        'citations_by_amendment': citations_by_amendment,
        'has_citations': citations.exists(),
    }

    return render(request, 'documents/case_law_list.html', context)


@login_required
@require_POST
def suggest_case_law(request, document_id):
    """AJAX endpoint to get AI-suggested case law based on document facts."""
    import json

    try:
        document = get_object_or_404(Document, id=document_id, user=request.user)

        # Build document context from various sources
        document_data = {
            'story_text': document.story_text or '',
        }

        # Get incident narrative if available
        try:
            narrative_section = document.sections.get(section_type='incident_narrative')
            narrative = narrative_section.incident_narrative
            document_data.update({
                'summary': narrative.summary or '',
                'detailed_narrative': narrative.detailed_narrative or '',
                'physical_actions': narrative.physical_actions or '',
            })
        except (DocumentSection.DoesNotExist, AttributeError):
            pass

        # Get rights violated if available
        try:
            rights_section = document.sections.get(section_type='rights_violated')
            rights = rights_section.rights_violated
            rights_list = []
            if rights.first_amendment:
                rights_list.append('First Amendment')
            if rights.fourth_amendment:
                rights_list.append('Fourth Amendment')
            if rights.fifth_amendment:
                rights_list.append('Fifth Amendment')
            if rights.fourteenth_amendment:
                rights_list.append('Fourteenth Amendment')
            document_data['rights_violated'] = ', '.join(rights_list)
        except (DocumentSection.DoesNotExist, AttributeError):
            pass

        # Check if we have enough context
        if not document_data.get('story_text') and not document_data.get('detailed_narrative'):
            return JsonResponse({
                'success': False,
                'error': 'Please tell your story or fill out the incident narrative before getting case law suggestions.',
            })

        # Get available cases from database
        available_cases = list(CaseLaw.objects.filter(is_active=True).values(
            'id', 'case_name', 'citation', 'amendment', 'right_category',
            'key_holding', 'facts_summary', 'relevance_keywords'
        ))

        if not available_cases:
            return JsonResponse({
                'success': False,
                'error': 'Case law database is not yet populated. Please run: python manage.py load_case_law',
            })

        # Call AI to suggest cases
        from .services.openai_service import OpenAIService
        service = OpenAIService()
        result = service.suggest_case_law(document_data, available_cases)

        if result.get('success'):
            # Enrich suggestions with full case data
            suggestions = result.get('suggestions', [])
            enriched = []
            for suggestion in suggestions:
                case_id = suggestion.get('case_id')
                try:
                    case = CaseLaw.objects.get(id=case_id)
                    enriched.append({
                        'case_id': case.id,
                        'case_name': case.case_name,
                        'citation': case.citation,
                        'amendment': case.amendment,
                        'amendment_display': case.get_amendment_display(),
                        'right_category': case.right_category,
                        'right_category_display': case.get_right_category_display(),
                        'key_holding': case.key_holding,
                        'citation_text': case.citation_text,
                        'is_landmark': case.is_landmark,
                        'relevance_explanation': suggestion.get('relevance_explanation', ''),
                    })
                except CaseLaw.DoesNotExist:
                    continue

            return JsonResponse({
                'success': True,
                'suggestions': enriched,
                'overall_strategy': result.get('overall_strategy', ''),
            })

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
def accept_case_law(request, document_id):
    """AJAX endpoint to accept suggested case law citations."""
    import json

    try:
        document = get_object_or_404(Document, id=document_id, user=request.user)
        data = json.loads(request.body)

        case_id = data.get('case_id')
        relevance_explanation = data.get('relevance_explanation', '')

        if not case_id:
            return JsonResponse({
                'success': False,
                'error': 'No case specified.',
            })

        case = get_object_or_404(CaseLaw, id=case_id)

        # Check if already added
        existing = DocumentCaseLaw.objects.filter(document=document, case_law=case).first()
        if existing:
            return JsonResponse({
                'success': False,
                'error': 'This case has already been added to your document.',
            })

        # Get the next order number
        max_order = DocumentCaseLaw.objects.filter(document=document).aggregate(
            max_order=db_models.Max('order')
        )['max_order'] or 0

        # Create the citation
        citation = DocumentCaseLaw.objects.create(
            document=document,
            case_law=case,
            amendment=case.amendment,
            right_category=case.right_category,
            relevance_explanation=relevance_explanation,
            status='accepted',
            order=max_order + 1,
        )

        return JsonResponse({
            'success': True,
            'message': f'{case.case_name} added to your document.',
            'citation_id': citation.id,
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
@require_POST
def update_case_law(request, document_id, citation_id):
    """AJAX endpoint to update a case law citation (edit explanation)."""
    import json

    try:
        document = get_object_or_404(Document, id=document_id, user=request.user)
        citation = get_object_or_404(DocumentCaseLaw, id=citation_id, document=document)

        data = json.loads(request.body)
        user_explanation = data.get('user_explanation', '').strip()

        citation.user_explanation = user_explanation
        citation.status = 'edited' if user_explanation else 'accepted'
        citation.save()

        return JsonResponse({
            'success': True,
            'message': 'Citation updated.',
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
@require_POST
def remove_case_law(request, document_id, citation_id):
    """AJAX endpoint to remove a case law citation from a document."""
    try:
        document = get_object_or_404(Document, id=document_id, user=request.user)
        citation = get_object_or_404(DocumentCaseLaw, id=citation_id, document=document)

        case_name = citation.case_law.case_name
        citation.delete()

        return JsonResponse({
            'success': True,
            'message': f'{case_name} removed from your document.',
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}',
        })