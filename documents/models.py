from django.db import models
from django.conf import settings


class Document(models.Model):
    """Main document representing a Section 1983 civil rights complaint."""

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('review', 'Ready for Review'),
        ('complete', 'Complete'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)  # Required field
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} - {self.user.email}"

    def get_completion_percentage(self):
        """Calculate overall completion percentage based on sections."""
        sections = self.sections.all()
        if not sections:
            return 0
        # Count both 'completed' and 'not_applicable' as done
        done = sections.filter(status__in=['completed', 'not_applicable']).count()
        return int((done / sections.count()) * 100)

    def get_sections_needing_work(self):
        """Return sections flagged as needing work."""
        return self.sections.filter(status='needs_work')

    def has_sections_needing_work(self):
        """Check if any sections need work."""
        return self.sections.filter(status='needs_work').exists()


class DocumentSection(models.Model):
    """Individual sections of the document with their own status tracking."""

    SECTION_TYPES = [
        ('plaintiff_info', 'Plaintiff Information'),
        ('incident_overview', 'Incident Overview'),
        ('defendants', 'Government Defendants'),
        ('incident_narrative', 'Incident Narrative'),
        ('rights_violated', 'Rights Violated'),
        ('witnesses', 'Witnesses'),
        ('evidence', 'Evidence'),
        ('damages', 'Damages'),
        ('prior_complaints', 'Prior Complaints'),
        ('relief_sought', 'Relief Sought'),
    ]

    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('needs_work', 'Needs Work'),
        ('completed', 'Completed'),
        ('not_applicable', 'Not Applicable'),
    ]

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='sections')
    section_type = models.CharField(max_length=30, choices=SECTION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    order = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True, help_text='Internal notes about what needs work')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        unique_together = ['document', 'section_type']

    def __str__(self):
        return f"{self.get_section_type_display()} - {self.get_status_display()}"


# Section-specific data models

class PlaintiffInfo(models.Model):
    """Plaintiff (auditor) information."""

    section = models.OneToOneField(DocumentSection, on_delete=models.CASCADE, related_name='plaintiff_info')
    first_name = models.CharField(max_length=50, blank=True)
    middle_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    street_address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=50, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    is_pro_se = models.BooleanField(default=True, help_text='Representing yourself without an attorney')

    def __str__(self):
        return self.get_full_name() or "Plaintiff Info"

    def get_full_name(self):
        """Return the full name combining first, middle, and last names."""
        name_parts = [self.first_name, self.middle_name, self.last_name]
        return ' '.join(part for part in name_parts if part)


class IncidentOverview(models.Model):
    """Basic incident information."""

    section = models.OneToOneField(DocumentSection, on_delete=models.CASCADE, related_name='incident_overview')
    incident_date = models.DateField(null=True, blank=True)
    incident_time = models.TimeField(null=True, blank=True)
    incident_location = models.CharField(max_length=500, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=50, blank=True)
    location_type = models.CharField(max_length=100, blank=True, help_text='e.g., Public sidewalk, Government building, etc.')
    was_recording = models.BooleanField(default=False)
    recording_device = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Incident on {self.incident_date}"


class Defendant(models.Model):
    """Government defendants (agencies and individual officers)."""

    DEFENDANT_TYPES = [
        ('agency', 'Government Agency'),
        ('individual', 'Individual Officer'),
    ]

    section = models.ForeignKey(DocumentSection, on_delete=models.CASCADE, related_name='defendants')
    defendant_type = models.CharField(max_length=20, choices=DEFENDANT_TYPES)
    name = models.CharField(max_length=255, help_text='Agency name or officer name')
    badge_number = models.CharField(max_length=50, blank=True)
    title_rank = models.CharField(max_length=100, blank=True, help_text='e.g., Sergeant, Detective, etc.')
    agency_name = models.CharField(max_length=255, blank=True, help_text='For individual officers, their employing agency')
    address = models.TextField(blank=True, help_text='Official address for service')
    description = models.TextField(blank=True, help_text='Physical description or identifying information')

    def __str__(self):
        return self.name


class IncidentNarrative(models.Model):
    """Detailed narrative of what happened."""

    section = models.OneToOneField(DocumentSection, on_delete=models.CASCADE, related_name='incident_narrative')
    summary = models.TextField(blank=True, help_text='Brief summary of the incident (2-3 sentences)')
    detailed_narrative = models.TextField(blank=True, help_text='Full detailed account of what happened')
    what_were_you_doing = models.TextField(blank=True, help_text='What were you doing before/during the incident?')
    initial_contact = models.TextField(blank=True, help_text='How did the encounter begin?')
    what_was_said = models.TextField(blank=True, help_text='What was said by officers and by you?')
    physical_actions = models.TextField(blank=True, help_text='Describe any physical actions taken')
    how_it_ended = models.TextField(blank=True, help_text='How did the encounter end?')

    def __str__(self):
        return "Incident Narrative"


class RightsViolated(models.Model):
    """Constitutional rights that were violated."""

    section = models.OneToOneField(DocumentSection, on_delete=models.CASCADE, related_name='rights_violated')

    # First Amendment
    first_amendment = models.BooleanField(default=False, verbose_name='First Amendment')
    first_amendment_speech = models.BooleanField(default=False, verbose_name='Freedom of Speech')
    first_amendment_press = models.BooleanField(default=False, verbose_name='Freedom of Press')
    first_amendment_assembly = models.BooleanField(default=False, verbose_name='Freedom of Assembly')
    first_amendment_petition = models.BooleanField(default=False, verbose_name='Right to Petition')
    first_amendment_details = models.TextField(blank=True, help_text='Explain how First Amendment rights were violated')

    # Fourth Amendment
    fourth_amendment = models.BooleanField(default=False, verbose_name='Fourth Amendment')
    fourth_amendment_search = models.BooleanField(default=False, verbose_name='Unreasonable Search')
    fourth_amendment_seizure = models.BooleanField(default=False, verbose_name='Unreasonable Seizure')
    fourth_amendment_arrest = models.BooleanField(default=False, verbose_name='False Arrest')
    fourth_amendment_force = models.BooleanField(default=False, verbose_name='Excessive Force')
    fourth_amendment_details = models.TextField(blank=True, help_text='Explain how Fourth Amendment rights were violated')

    # Fifth Amendment
    fifth_amendment = models.BooleanField(default=False, verbose_name='Fifth Amendment')
    fifth_amendment_self_incrimination = models.BooleanField(default=False, verbose_name='Self-Incrimination')
    fifth_amendment_due_process = models.BooleanField(default=False, verbose_name='Due Process')
    fifth_amendment_details = models.TextField(blank=True, help_text='Explain how Fifth Amendment rights were violated')

    # Fourteenth Amendment
    fourteenth_amendment = models.BooleanField(default=False, verbose_name='Fourteenth Amendment')
    fourteenth_amendment_due_process = models.BooleanField(default=False, verbose_name='Due Process')
    fourteenth_amendment_equal_protection = models.BooleanField(default=False, verbose_name='Equal Protection')
    fourteenth_amendment_details = models.TextField(blank=True, help_text='Explain how Fourteenth Amendment rights were violated')

    other_rights = models.TextField(blank=True, help_text='Any other rights or laws violated')

    def __str__(self):
        return "Rights Violated"


class Witness(models.Model):
    """Witnesses to the incident."""

    section = models.ForeignKey(DocumentSection, on_delete=models.CASCADE, related_name='witnesses')
    name = models.CharField(max_length=255)
    contact_info = models.TextField(blank=True, help_text='Phone, email, or address')
    relationship = models.CharField(max_length=100, blank=True, help_text='How do you know this person?')
    what_they_witnessed = models.TextField(blank=True)
    willing_to_testify = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Evidence(models.Model):
    """Evidence related to the incident (metadata only for now, file upload later)."""

    EVIDENCE_TYPES = [
        ('video', 'Video Recording'),
        ('audio', 'Audio Recording'),
        ('photo', 'Photograph'),
        ('document', 'Document'),
        ('social_media', 'Social Media Post'),
        ('body_cam', 'Body Camera Footage'),
        ('dash_cam', 'Dash Camera Footage'),
        ('surveillance', 'Surveillance Footage'),
        ('other', 'Other'),
    ]

    section = models.ForeignKey(DocumentSection, on_delete=models.CASCADE, related_name='evidence_items')
    evidence_type = models.CharField(max_length=20, choices=EVIDENCE_TYPES)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    date_created = models.DateField(null=True, blank=True)
    location_obtained = models.CharField(max_length=255, blank=True)
    is_in_possession = models.BooleanField(default=True)
    needs_subpoena = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.get_evidence_type_display()}: {self.title}"


class Damages(models.Model):
    """Damages and injuries suffered."""

    section = models.OneToOneField(DocumentSection, on_delete=models.CASCADE, related_name='damages')

    # Physical injuries
    physical_injury = models.BooleanField(default=False)
    physical_injury_description = models.TextField(blank=True)
    medical_treatment = models.BooleanField(default=False)
    medical_treatment_description = models.TextField(blank=True)
    ongoing_medical_issues = models.BooleanField(default=False)
    ongoing_medical_description = models.TextField(blank=True)

    # Emotional/psychological
    emotional_distress = models.BooleanField(default=False)
    emotional_distress_description = models.TextField(blank=True)

    # Financial
    property_damage = models.BooleanField(default=False)
    property_damage_description = models.TextField(blank=True)
    lost_wages = models.BooleanField(default=False)
    lost_wages_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    legal_fees = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    medical_expenses = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    other_expenses = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    other_expenses_description = models.TextField(blank=True)

    # Reputation/Other
    reputation_harm = models.BooleanField(default=False)
    reputation_harm_description = models.TextField(blank=True)
    other_damages = models.TextField(blank=True)

    def get_total_financial_damages(self):
        total = 0
        if self.lost_wages_amount:
            total += self.lost_wages_amount
        if self.legal_fees:
            total += self.legal_fees
        if self.medical_expenses:
            total += self.medical_expenses
        if self.other_expenses:
            total += self.other_expenses
        return total

    def __str__(self):
        return "Damages"


class PriorComplaints(models.Model):
    """Prior complaints or attempts to resolve."""

    section = models.OneToOneField(DocumentSection, on_delete=models.CASCADE, related_name='prior_complaints')

    filed_internal_complaint = models.BooleanField(default=False)
    internal_complaint_date = models.DateField(null=True, blank=True)
    internal_complaint_description = models.TextField(blank=True)
    internal_complaint_outcome = models.TextField(blank=True)

    filed_civilian_complaint = models.BooleanField(default=False)
    civilian_complaint_date = models.DateField(null=True, blank=True)
    civilian_complaint_description = models.TextField(blank=True)
    civilian_complaint_outcome = models.TextField(blank=True)

    contacted_media = models.BooleanField(default=False)
    media_contact_description = models.TextField(blank=True)

    other_actions = models.TextField(blank=True, help_text='Any other actions taken to address the incident')

    def __str__(self):
        return "Prior Complaints"


class ReliefSought(models.Model):
    """What relief/outcome the plaintiff is seeking."""

    section = models.OneToOneField(DocumentSection, on_delete=models.CASCADE, related_name='relief_sought')

    # Monetary
    compensatory_damages = models.BooleanField(default=True)
    compensatory_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    punitive_damages = models.BooleanField(default=False)
    punitive_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    attorney_fees = models.BooleanField(default=True)

    # Injunctive
    injunctive_relief = models.BooleanField(default=False)
    injunctive_description = models.TextField(blank=True, help_text='What specific actions do you want the court to order?')

    # Declaratory
    declaratory_relief = models.BooleanField(default=False)
    declaratory_description = models.TextField(blank=True, help_text='What do you want the court to declare?')

    # Other
    other_relief = models.TextField(blank=True)

    jury_trial_demanded = models.BooleanField(default=True)

    def __str__(self):
        return "Relief Sought"
