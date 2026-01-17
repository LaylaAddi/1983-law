from django import forms
from .models import (
    Document, DocumentSection, PlaintiffInfo, IncidentOverview,
    Defendant, IncidentNarrative, RightsViolated, Witness,
    Evidence, Damages, PriorComplaints, ReliefSought
)


# US States for dropdown selection
US_STATES = [
    ('', 'Select State'),
    ('AL', 'Alabama'),
    ('AK', 'Alaska'),
    ('AZ', 'Arizona'),
    ('AR', 'Arkansas'),
    ('CA', 'California'),
    ('CO', 'Colorado'),
    ('CT', 'Connecticut'),
    ('DE', 'Delaware'),
    ('DC', 'District of Columbia'),
    ('FL', 'Florida'),
    ('GA', 'Georgia'),
    ('HI', 'Hawaii'),
    ('ID', 'Idaho'),
    ('IL', 'Illinois'),
    ('IN', 'Indiana'),
    ('IA', 'Iowa'),
    ('KS', 'Kansas'),
    ('KY', 'Kentucky'),
    ('LA', 'Louisiana'),
    ('ME', 'Maine'),
    ('MD', 'Maryland'),
    ('MA', 'Massachusetts'),
    ('MI', 'Michigan'),
    ('MN', 'Minnesota'),
    ('MS', 'Mississippi'),
    ('MO', 'Missouri'),
    ('MT', 'Montana'),
    ('NE', 'Nebraska'),
    ('NV', 'Nevada'),
    ('NH', 'New Hampshire'),
    ('NJ', 'New Jersey'),
    ('NM', 'New Mexico'),
    ('NY', 'New York'),
    ('NC', 'North Carolina'),
    ('ND', 'North Dakota'),
    ('OH', 'Ohio'),
    ('OK', 'Oklahoma'),
    ('OR', 'Oregon'),
    ('PA', 'Pennsylvania'),
    ('RI', 'Rhode Island'),
    ('SC', 'South Carolina'),
    ('SD', 'South Dakota'),
    ('TN', 'Tennessee'),
    ('TX', 'Texas'),
    ('UT', 'Utah'),
    ('VT', 'Vermont'),
    ('VA', 'Virginia'),
    ('WA', 'Washington'),
    ('WV', 'West Virginia'),
    ('WI', 'Wisconsin'),
    ('WY', 'Wyoming'),
]


class DocumentForm(forms.ModelForm):
    """Form for creating/editing a document."""

    title = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g., City Police Unlawful Detention Case'
        }),
        label='Case Title',
        help_text='Give your case a descriptive name. You can change this later.',
        error_messages={
            'required': 'Please enter a title for your case.',
            'max_length': 'Title must be 255 characters or less.',
        }
    )

    class Meta:
        model = Document
        fields = ['title']


class SectionStatusForm(forms.ModelForm):
    """Form for updating section status."""

    class Meta:
        model = DocumentSection
        fields = ['status', 'notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Notes about what needs work...'
            })
        }


class PlaintiffInfoForm(forms.ModelForm):
    """Form for plaintiff information."""

    # Custom field that inverts is_pro_se for better UX
    has_attorney = forms.BooleanField(
        required=False,
        label='I have an attorney representing me',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_has_attorney'})
    )

    class Meta:
        model = PlaintiffInfo
        exclude = ['section', 'is_pro_se']  # Exclude is_pro_se, we use has_attorney instead
        widgets = {
            # Plaintiff fields
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Middle name (optional)'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}),
            'street_address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.Select(choices=US_STATES, attrs={'class': 'form-select'}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ZIP Code'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(555) 123-4567'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'your.email@example.com'}),
            # Attorney fields
            'attorney_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Attorney full name'}),
            'attorney_bar_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State bar number'}),
            'attorney_firm_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Law firm name (if applicable)'}),
            'attorney_street_address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street address'}),
            'attorney_city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'attorney_state': forms.Select(choices=US_STATES, attrs={'class': 'form-select'}),
            'attorney_zip_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ZIP Code'}),
            'attorney_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(555) 123-4567'}),
            'attorney_fax': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(555) 123-4568'}),
            'attorney_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'attorney@lawfirm.com'}),
        }
        labels = {
            'attorney_name': 'Attorney Name',
            'attorney_bar_number': 'Bar Number',
            'attorney_firm_name': 'Law Firm',
            'attorney_street_address': 'Street Address',
            'attorney_city': 'City',
            'attorney_state': 'State',
            'attorney_zip_code': 'ZIP Code',
            'attorney_phone': 'Phone',
            'attorney_fax': 'Fax',
            'attorney_email': 'Email',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set has_attorney based on existing is_pro_se value (inverted)
        if self.instance and self.instance.pk:
            self.fields['has_attorney'].initial = not self.instance.is_pro_se

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Invert has_attorney to set is_pro_se
        instance.is_pro_se = not self.cleaned_data.get('has_attorney', False)
        if commit:
            instance.save()
        return instance


class PlaintiffAttorneyForm(forms.ModelForm):
    """Form for attorney information only - plaintiff info comes from profile."""

    # Custom field that inverts is_pro_se for better UX
    has_attorney = forms.BooleanField(
        required=False,
        label='I have an attorney representing me',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_has_attorney'})
    )

    class Meta:
        model = PlaintiffInfo
        fields = [
            'has_attorney',
            'attorney_name', 'attorney_bar_number', 'attorney_firm_name',
            'attorney_street_address', 'attorney_city', 'attorney_state',
            'attorney_zip_code', 'attorney_phone', 'attorney_fax', 'attorney_email'
        ]
        widgets = {
            'attorney_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Attorney full name'}),
            'attorney_bar_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State bar number'}),
            'attorney_firm_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Law firm name (if applicable)'}),
            'attorney_street_address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street address'}),
            'attorney_city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'attorney_state': forms.Select(choices=US_STATES, attrs={'class': 'form-select'}),
            'attorney_zip_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ZIP Code'}),
            'attorney_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(555) 123-4567'}),
            'attorney_fax': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(555) 123-4568'}),
            'attorney_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'attorney@lawfirm.com'}),
        }
        labels = {
            'attorney_name': 'Attorney Name',
            'attorney_bar_number': 'Bar Number',
            'attorney_firm_name': 'Law Firm',
            'attorney_street_address': 'Street Address',
            'attorney_city': 'City',
            'attorney_state': 'State',
            'attorney_zip_code': 'ZIP Code',
            'attorney_phone': 'Phone',
            'attorney_fax': 'Fax',
            'attorney_email': 'Email',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set has_attorney based on existing is_pro_se value (inverted)
        if self.instance and self.instance.pk:
            self.fields['has_attorney'].initial = not self.instance.is_pro_se

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Invert has_attorney to set is_pro_se
        instance.is_pro_se = not self.cleaned_data.get('has_attorney', False)
        if commit:
            instance.save()
        return instance


class IncidentOverviewForm(forms.ModelForm):
    """Form for incident overview."""

    class Meta:
        model = IncidentOverview
        exclude = ['section', 'district_lookup_confidence']
        # Order fields so court lookup appears right after state
        fields = [
            'incident_date', 'incident_time', 'incident_location',
            'city', 'state', 'federal_district_court', 'use_manual_court',
            'location_type', 'was_recording', 'recording_device'
        ]
        widgets = {
            'incident_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'incident_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'incident_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Specific location (e.g., 123 Main St, front entrance)'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City', 'id': 'id_city'}),
            'state': forms.Select(choices=US_STATES, attrs={'class': 'form-select', 'id': 'id_state'}),
            'location_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Public sidewalk, Government building lobby'}),
            'was_recording': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'recording_device': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., iPhone 14, GoPro Hero 10'}),
            'federal_district_court': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Select city & state, then click Lookup', 'id': 'id_federal_district_court', 'readonly': 'readonly'}),
            'use_manual_court': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_use_manual_court'}),
        }
        labels = {
            'federal_district_court': 'Federal District Court',
            'use_manual_court': 'Enter court manually (override auto-lookup)',
        }
        help_texts = {
            'federal_district_court': 'Click "Lookup Court" after selecting city and state.',
        }


class DefendantForm(forms.ModelForm):
    """Form for defendant information."""

    class Meta:
        model = Defendant
        exclude = ['section', 'agency_inferred']  # agency_inferred is cleared on manual save
        widgets = {
            'defendant_type': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Agency or officer name'}),
            'badge_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Badge/ID number if known'}),
            'title_rank': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Sergeant, Detective'}),
            'agency_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Employing agency'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Official address for service'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Physical description or identifying info'}),
        }

    def save(self, commit=True):
        """Clear agency_inferred flag when user manually saves/reviews a defendant."""
        instance = super().save(commit=False)
        instance.agency_inferred = False
        if commit:
            instance.save()
        return instance


class IncidentNarrativeForm(forms.ModelForm):
    """Form for incident narrative."""

    class Meta:
        model = IncidentNarrative
        exclude = ['section']
        widgets = {
            'summary': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Brief 2-3 sentence summary of what happened'
            }),
            'detailed_narrative': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Full detailed account of the incident from start to finish'
            }),
            'what_were_you_doing': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'What were you doing before and during the incident?'
            }),
            'initial_contact': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'How did the encounter with officers begin?'
            }),
            'what_was_said': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'What did officers say? What did you say?'
            }),
            'physical_actions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe any physical actions (handcuffing, pushing, etc.)'
            }),
            'how_it_ended': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'How did the encounter end?'
            }),
        }


class RightsViolatedForm(forms.ModelForm):
    """Form for rights violated."""

    class Meta:
        model = RightsViolated
        exclude = ['section']
        widgets = {
            'first_amendment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'first_amendment_speech': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'first_amendment_press': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'first_amendment_assembly': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'first_amendment_petition': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'first_amendment_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'fourth_amendment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'fourth_amendment_search': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'fourth_amendment_seizure': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'fourth_amendment_arrest': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'fourth_amendment_force': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'fourth_amendment_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'fifth_amendment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'fifth_amendment_self_incrimination': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'fifth_amendment_due_process': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'fifth_amendment_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'fourteenth_amendment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'fourteenth_amendment_due_process': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'fourteenth_amendment_equal_protection': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'fourteenth_amendment_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'other_rights': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class WitnessForm(forms.ModelForm):
    """Form for witness information."""

    class Meta:
        model = Witness
        exclude = ['section']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Witness name'}),
            'contact_info': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Phone, email, or address'}),
            'relationship': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Bystander, Fellow auditor, Store owner'}),
            'what_they_witnessed': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'What did this person see?'}),
            'willing_to_testify': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class EvidenceForm(forms.ModelForm):
    """Form for evidence information."""

    class Meta:
        model = Evidence
        exclude = ['section']
        widgets = {
            'evidence_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., My recording of the incident'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Describe this evidence'}),
            'date_created': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'location_obtained': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Where was this obtained?'}),
            'is_in_possession': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'needs_subpoena': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Additional notes'}),
        }


class DamagesForm(forms.ModelForm):
    """Form for damages information."""

    class Meta:
        model = Damages
        exclude = ['section']
        widgets = {
            'physical_injury': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'physical_injury_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'medical_treatment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'medical_treatment_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'ongoing_medical_issues': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ongoing_medical_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'emotional_distress': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'emotional_distress_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'property_damage': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'property_damage_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'lost_wages': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'lost_wages_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'legal_fees': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'medical_expenses': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'other_expenses': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'other_expenses_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'reputation_harm': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'reputation_harm_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'other_damages': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class PriorComplaintsForm(forms.ModelForm):
    """Form for prior complaints information."""

    class Meta:
        model = PriorComplaints
        exclude = ['section']
        widgets = {
            'filed_internal_complaint': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'internal_complaint_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'internal_complaint_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'internal_complaint_outcome': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'filed_civilian_complaint': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'civilian_complaint_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'civilian_complaint_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'civilian_complaint_outcome': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'contacted_media': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'media_contact_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'other_actions': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ReliefSoughtForm(forms.ModelForm):
    """Form for relief sought - written in plain English for non-lawyers."""

    class Meta:
        model = ReliefSought
        exclude = ['section']
        widgets = {
            'compensatory_damages': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'compensatory_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Dollar amount (optional)'}),
            'punitive_damages': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'punitive_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Dollar amount (optional)'}),
            'attorney_fees': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'injunctive_relief': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'injunctive_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Example: Order the police department to train officers on First Amendment rights'
            }),
            'declaratory_relief': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'declaratory_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Example: Declare that filming police in public is constitutionally protected'
            }),
            'other_relief': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Any other requests not covered above...'
            }),
            'jury_trial_demanded': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'compensatory_damages': 'I want money for my actual losses and suffering',
            'compensatory_amount': 'How much? (You can leave blank and let the court decide)',
            'punitive_damages': 'I want extra money to punish the officers for their bad behavior',
            'punitive_amount': 'How much? (You can leave blank and let the court decide)',
            'attorney_fees': 'I want the defendants to pay my legal fees if I win',
            'injunctive_relief': 'I want the court to ORDER the department to change something',
            'injunctive_description': 'What changes do you want?',
            'declaratory_relief': 'I want the court to officially DECLARE that my rights were violated',
            'declaratory_description': 'What do you want the court to declare?',
            'other_relief': 'Anything else you want to ask for?',
            'jury_trial_demanded': 'I want a jury (regular citizens) to decide my case, not just a judge',
        }
        help_texts = {
            'compensatory_damages': 'This covers medical bills, lost wages, emotional distress, damaged equipment, etc.',
            'punitive_damages': 'Courts award this when officers clearly knew their actions were wrong. Common in 1A audit cases.',
            'attorney_fees': 'Section 1983 allows winners to recover legal fees. ALWAYS select this!',
            'injunctive_relief': 'Use this to force real changes like new training or policy reforms.',
            'declaratory_relief': 'Creates an official court record. Helpful for future cases and public awareness.',
            'jury_trial_demanded': 'Most plaintiffs prefer a jury. Juries often sympathize with regular people whose rights were violated.',
        }
