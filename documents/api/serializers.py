from rest_framework import serializers
from documents.models import WizardSession


class WizardStartSerializer(serializers.Serializer):
    """Input for starting a wizard session."""
    story = serializers.CharField(min_length=50)


class StepWhenWhereSerializer(serializers.Serializer):
    """Step 1: When and where did it happen?"""
    incident_date = serializers.DateField(required=False, allow_null=True)
    incident_time = serializers.TimeField(required=False, allow_null=True)
    incident_location = serializers.CharField(required=False, allow_blank=True, max_length=500)
    city = serializers.CharField(required=False, allow_blank=True, max_length=200)
    state = serializers.CharField(required=False, allow_blank=True, max_length=2)
    location_type = serializers.CharField(required=False, allow_blank=True, max_length=100)
    federal_district_court = serializers.CharField(required=False, allow_blank=True, max_length=255)
    use_manual_court = serializers.BooleanField(required=False, default=False)
    court_district_confirmed = serializers.BooleanField(required=False, default=False)


class DefendantEntrySerializer(serializers.Serializer):
    """A single defendant/officer entry."""
    name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    badge_number = serializers.CharField(required=False, allow_blank=True, max_length=100)
    title_rank = serializers.CharField(required=False, allow_blank=True, max_length=100)
    agency_name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    defendant_type = serializers.ChoiceField(
        choices=[('individual', 'Individual'), ('agency', 'Agency')],
        required=False,
        default='individual'
    )


class WitnessEntrySerializer(serializers.Serializer):
    """A single witness entry."""
    name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    relationship = serializers.CharField(required=False, allow_blank=True, max_length=255)
    what_they_witnessed = serializers.CharField(required=False, allow_blank=True)
    contact_info = serializers.CharField(required=False, allow_blank=True)


class StepWhoSerializer(serializers.Serializer):
    """Step 2: Who was involved?"""
    defendants = DefendantEntrySerializer(many=True, required=False, default=list)
    witnesses = WitnessEntrySerializer(many=True, required=False, default=list)


class StepWhatSerializer(serializers.Serializer):
    """Step 3: What happened?"""
    summary = serializers.CharField(required=False, allow_blank=True)
    detailed_narrative = serializers.CharField(required=False, allow_blank=True)
    what_were_you_doing = serializers.CharField(required=False, allow_blank=True)
    initial_contact = serializers.CharField(required=False, allow_blank=True)
    what_was_said = serializers.CharField(required=False, allow_blank=True)
    physical_actions = serializers.CharField(required=False, allow_blank=True)
    how_it_ended = serializers.CharField(required=False, allow_blank=True)


class StepWhySerializer(serializers.Serializer):
    """Step 4: Why was it wrong? Plain-language violation selection."""
    selections = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text='List of violation keys: searched_without_warrant, arrested_no_cause, '
                  'excessive_force, punished_for_speech, punished_for_recording, '
                  'racial_discrimination, gender_discrimination, forced_statements, '
                  'denied_medical_care, retaliation, other'
    )
    additional_text = serializers.CharField(required=False, allow_blank=True)


class StepImpactSerializer(serializers.Serializer):
    """Step 5: How did it affect you?"""
    physical_injuries = serializers.CharField(required=False, allow_blank=True)
    medical_treatment = serializers.CharField(required=False, allow_blank=True)
    emotional_distress = serializers.CharField(required=False, allow_blank=True)
    financial_losses = serializers.CharField(required=False, allow_blank=True)
    lost_wages = serializers.CharField(required=False, allow_blank=True)
    ongoing_effects = serializers.CharField(required=False, allow_blank=True)


class EvidenceEntrySerializer(serializers.Serializer):
    """A single evidence item."""
    evidence_type = serializers.CharField(required=False, allow_blank=True, max_length=50)
    title = serializers.CharField(required=False, allow_blank=True, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    is_in_possession = serializers.BooleanField(required=False, default=True)
    youtube_url = serializers.URLField(required=False, allow_blank=True)


class StepEvidenceSerializer(serializers.Serializer):
    """Step 6: What evidence do you have?"""
    evidence_types = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text='Checklist: video, photo, audio, body_cam, dash_cam, medical_records, '
                  'police_report, witness_statements, social_media, other'
    )
    items = EvidenceEntrySerializer(many=True, required=False, default=list)
    youtube_url = serializers.URLField(required=False, allow_blank=True)


class StepPreferencesSerializer(serializers.Serializer):
    """Step 7: Case law and preferences."""
    use_case_law = serializers.BooleanField(default=True)


# Maps step numbers to their serializers
STEP_SERIALIZERS = {
    1: StepWhenWhereSerializer,
    2: StepWhoSerializer,
    3: StepWhatSerializer,
    4: StepWhySerializer,
    5: StepImpactSerializer,
    6: StepEvidenceSerializer,
    7: StepPreferencesSerializer,
}

# Step metadata for the frontend
STEP_META = {
    1: {'title': 'When & Where', 'icon': 'bi-geo-alt', 'description': 'When and where did the incident happen?'},
    2: {'title': 'Who Was Involved', 'icon': 'bi-people', 'description': 'Who were the officers or officials involved?'},
    3: {'title': 'What Happened', 'icon': 'bi-journal-text', 'description': 'Describe what happened in detail.'},
    4: {'title': 'Why It Was Wrong', 'icon': 'bi-shield-exclamation', 'description': 'Why do you believe your rights were violated?'},
    5: {'title': 'How It Affected You', 'icon': 'bi-heart-pulse', 'description': 'What harm or damages did you experience?'},
    6: {'title': 'Evidence & Proof', 'icon': 'bi-camera', 'description': 'What evidence do you have to support your case?'},
    7: {'title': 'Preferences', 'icon': 'bi-gear', 'description': 'Choose how you want your complaint prepared.'},
}


class WizardSessionSerializer(serializers.ModelSerializer):
    """Full wizard session state for the frontend."""
    progress_percent = serializers.ReadOnlyField()
    steps = serializers.SerializerMethodField()

    class Meta:
        model = WizardSession
        fields = [
            'slug', 'status', 'current_step', 'progress_percent',
            'raw_story', 'ai_extracted', 'interview_data',
            'use_case_law', 'ai_analysis', 'analysis_status',
            'steps', 'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_steps(self, obj):
        """Return step metadata with completion status."""
        steps = []
        for i in range(1, WizardSession.TOTAL_STEPS + 1):
            step_data = obj.get_step_data(i)
            steps.append({
                'number': i,
                **STEP_META[i],
                'completed': bool(step_data),
                'data': step_data,
                'ai_suggested': obj.ai_extracted.get(f'step_{i}', {}),
            })
        return steps
