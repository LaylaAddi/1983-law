from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


class Document(models.Model):
    """Main document representing a Section 1983 civil rights complaint."""

    PAYMENT_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('expired', 'Expired'),
        ('paid', 'Paid'),
        ('finalized', 'Finalized'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)  # Required field
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Story - mandatory first step before filling sections
    story_text = models.TextField(blank=True, help_text='Raw story text from user (voice or typed)')
    story_told_at = models.DateTimeField(null=True, blank=True, help_text='When the story was submitted')

    # Payment tracking
    stripe_payment_id = models.CharField(max_length=255, blank=True, help_text='Stripe Payment Intent ID')
    promo_code_used = models.ForeignKey(
        'PromoCode', on_delete=models.SET_NULL, null=True, blank=True, related_name='documents_used'
    )
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    # AI usage tracking
    ai_generations_used = models.IntegerField(default=0, help_text='Free tier: count of generations used')
    ai_cost_used = models.DecimalField(
        max_digits=10, decimal_places=4, default=0,
        help_text='Paid tier: actual API cost in dollars'
    )

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

    def has_story(self):
        """Check if user has told their story (required before filling sections)."""
        return bool(self.story_text and self.story_text.strip())

    # Payment and access control methods

    def get_expiry_time(self):
        """Get the expiry datetime based on payment status."""
        if self.payment_status == 'draft':
            return self.created_at + timedelta(hours=settings.DRAFT_EXPIRY_HOURS)
        elif self.payment_status == 'paid' and self.paid_at:
            return self.paid_at + timedelta(days=settings.PAID_EXPIRY_DAYS)
        return None

    def get_time_remaining(self):
        """Get time remaining as a timedelta, or None if expired/finalized."""
        expiry = self.get_expiry_time()
        if expiry:
            remaining = expiry - timezone.now()
            if remaining.total_seconds() > 0:
                return remaining
        return None

    def get_time_remaining_display(self):
        """Get human-readable time remaining."""
        remaining = self.get_time_remaining()
        if not remaining:
            return "Expired"

        total_seconds = int(remaining.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600

        if days > 0:
            return f"{days} day{'s' if days != 1 else ''}, {hours} hour{'s' if hours != 1 else ''}"
        elif hours > 0:
            minutes = (total_seconds % 3600) // 60
            return f"{hours} hour{'s' if hours != 1 else ''}, {minutes} min"
        else:
            minutes = total_seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''}"

    def is_expired(self):
        """Check if document has expired."""
        if self.payment_status in ['finalized']:
            return False
        if self.payment_status == 'expired':
            return True
        expiry = self.get_expiry_time()
        if expiry and timezone.now() > expiry:
            return True
        return False

    def check_and_update_expiry(self):
        """Check expiry and update status if needed. Call this on document access."""
        if self.payment_status == 'draft' and self.is_expired():
            self.payment_status = 'expired'
            self.save(update_fields=['payment_status'])
            return True
        return False

    def can_edit(self):
        """Check if document can be edited."""
        if self.payment_status == 'finalized':
            return False
        if self.payment_status == 'expired':
            return False
        if self.is_expired():
            return False
        return True

    def can_use_ai(self):
        """Check if AI features are available."""
        if not self.can_edit():
            return False
        # Admin/staff have unlimited access
        if self.user.has_unlimited_access():
            return True
        if self.payment_status == 'draft':
            # Check USER-level free AI limit (across all documents)
            return self.user.can_use_free_ai()
        elif self.payment_status == 'paid':
            return float(self.ai_cost_used) < settings.PAID_AI_BUDGET
        return False

    def get_ai_usage_display(self):
        """Get AI usage display string."""
        if self.user.has_unlimited_access():
            return "AI: Unlimited (Admin)"
        if self.payment_status == 'draft':
            remaining = self.user.get_free_ai_remaining()
            return f"{remaining} of {settings.FREE_AI_GENERATIONS} free AI uses remaining"
        elif self.payment_status == 'paid':
            budget = Decimal(str(settings.PAID_AI_BUDGET))
            remaining_pct = max(0, int(((budget - self.ai_cost_used) / budget) * 100))
            return f"AI: {remaining_pct}% remaining"
        return "AI unavailable"

    def get_ai_remaining_percent(self):
        """Get AI remaining as percentage (for paid tier)."""
        if self.payment_status == 'paid':
            budget = Decimal(str(settings.PAID_AI_BUDGET))
            return max(0, int(((budget - self.ai_cost_used) / budget) * 100))
        return 0

    def record_ai_usage(self, cost=None):
        """Record AI usage. For draft: increment count. For paid: add cost."""
        if self.payment_status == 'draft':
            self.ai_generations_used += 1
            self.save(update_fields=['ai_generations_used'])
        elif self.payment_status == 'paid' and cost:
            self.ai_cost_used += Decimal(str(cost))
            self.save(update_fields=['ai_cost_used'])

    def get_price(self, promo_code=None):
        """Calculate price with optional promo code discount."""
        base_price = Decimal(str(settings.DOCUMENT_PRICE))
        if promo_code:
            discount = base_price * Decimal(str(settings.PROMO_DISCOUNT_PERCENT)) / 100
            return base_price - discount
        return base_price


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

    RELEVANCE_CHOICES = [
        ('unknown', 'Not Analyzed'),
        ('relevant', 'Relevant'),
        ('may_not_apply', 'May Not Apply'),
    ]

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='sections')
    section_type = models.CharField(max_length=30, choices=SECTION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    story_relevance = models.CharField(
        max_length=20,
        choices=RELEVANCE_CHOICES,
        default='unknown',
        help_text='Whether this section appears relevant based on story analysis'
    )
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

    # Attorney information (used when is_pro_se is False)
    attorney_name = models.CharField(max_length=100, blank=True, help_text='Full name of attorney')
    attorney_bar_number = models.CharField(max_length=50, blank=True, help_text='State bar number')
    attorney_firm_name = models.CharField(max_length=200, blank=True, help_text='Law firm name')
    attorney_street_address = models.CharField(max_length=255, blank=True)
    attorney_city = models.CharField(max_length=100, blank=True)
    attorney_state = models.CharField(max_length=50, blank=True)
    attorney_zip_code = models.CharField(max_length=20, blank=True)
    attorney_phone = models.CharField(max_length=20, blank=True)
    attorney_fax = models.CharField(max_length=20, blank=True)
    attorney_email = models.EmailField(blank=True)

    def __str__(self):
        return self.get_full_name() or "Plaintiff Info"

    def get_full_name(self):
        """Return the full name combining first, middle, and last names."""
        name_parts = [self.first_name, self.middle_name, self.last_name]
        return ' '.join(part for part in name_parts if part)

    def get_attorney_full_address(self):
        """Return the full attorney address."""
        parts = [self.attorney_street_address]
        city_state_zip = ', '.join(filter(None, [self.attorney_city, self.attorney_state]))
        if city_state_zip:
            if self.attorney_zip_code:
                city_state_zip += ' ' + self.attorney_zip_code
            parts.append(city_state_zip)
        return '\n'.join(filter(None, parts))


class IncidentOverview(models.Model):
    """Basic incident information."""

    CONFIDENCE_CHOICES = [
        ('high', 'High Confidence'),
        ('medium', 'Medium Confidence'),
        ('low', 'Low Confidence'),
    ]

    section = models.OneToOneField(DocumentSection, on_delete=models.CASCADE, related_name='incident_overview')
    incident_date = models.DateField(null=True, blank=True)
    incident_time = models.TimeField(null=True, blank=True)
    incident_location = models.CharField(max_length=500, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=50, blank=True)
    location_type = models.CharField(max_length=100, blank=True, help_text='e.g., Public sidewalk, Government building, etc.')
    was_recording = models.BooleanField(default=False)
    recording_device = models.CharField(max_length=100, blank=True)

    # Federal district court lookup
    federal_district_court = models.CharField(max_length=255, blank=True, help_text='Federal district court for filing')
    district_lookup_confidence = models.CharField(max_length=20, blank=True, choices=CONFIDENCE_CHOICES)
    use_manual_court = models.BooleanField(default=False, help_text='Manually enter court instead of using lookup')

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

    # Standard Relief (pre-selected for most 1A cases)
    compensatory_damages = models.BooleanField(
        default=True,
        verbose_name='Compensatory Damages',
        help_text='Money to cover actual losses - medical bills, lost wages, emotional distress, damaged equipment'
    )
    compensatory_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name='Specific Amount (optional)',
        help_text='Leave blank to let the court/jury decide the amount'
    )
    punitive_damages = models.BooleanField(
        default=True,  # Changed to True - common in 1A cases
        verbose_name='Punitive Damages',
        help_text='Extra money to punish officers who clearly violated your rights'
    )
    punitive_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name='Specific Amount (optional)',
        help_text='Leave blank to let the court/jury decide the amount'
    )
    attorney_fees = models.BooleanField(
        default=True,
        verbose_name="Attorney's Fees",
        help_text='42 U.S.C. § 1988 allows recovery of legal fees in civil rights cases - ALWAYS include this'
    )
    declaratory_relief = models.BooleanField(
        default=True,  # Changed to True - establishes precedent
        verbose_name='Declaratory Judgment',
        help_text='Official court declaration that your constitutional rights were violated'
    )
    declaratory_description = models.TextField(
        blank=True,
        verbose_name='Declaration Details (optional)',
        help_text='Customize what you want declared, or leave blank for standard language'
    )
    jury_trial_demanded = models.BooleanField(
        default=True,
        verbose_name='Jury Trial',
        help_text='Have regular citizens decide your case - juries are often sympathetic to civil rights plaintiffs'
    )

    # Optional/Advanced Relief
    injunctive_relief = models.BooleanField(
        default=False,
        verbose_name='Injunctive Relief (Policy Changes)',
        help_text='Court orders forcing the department to change policies or training - harder to get but creates lasting change'
    )
    injunctive_description = models.TextField(
        blank=True,
        verbose_name='What changes do you want?',
        help_text='Example: Require training on First Amendment rights, revise filming policies'
    )

    # Other
    other_relief = models.TextField(
        blank=True,
        verbose_name='Other Relief',
        help_text='Any other relief not covered above'
    )

    def __str__(self):
        return "Relief Sought"


class CaseLaw(models.Model):
    """
    Curated database of landmark Section 1983 case law.
    These are verified, accurate citations that AI can select from.
    """

    AMENDMENT_CHOICES = [
        ('first', 'First Amendment'),
        ('fourth', 'Fourth Amendment'),
        ('fifth', 'Fifth Amendment'),
        ('fourteenth', 'Fourteenth Amendment'),
    ]

    RIGHT_CATEGORY_CHOICES = [
        # First Amendment
        ('speech', 'Freedom of Speech'),
        ('press', 'Freedom of Press'),
        ('assembly', 'Freedom of Assembly'),
        ('petition', 'Right to Petition'),
        ('recording', 'Right to Record Police'),
        # Fourth Amendment
        ('excessive_force', 'Excessive Force'),
        ('false_arrest', 'False Arrest'),
        ('unlawful_detention', 'Unlawful Detention'),
        ('unreasonable_search', 'Unreasonable Search'),
        ('unreasonable_seizure', 'Unreasonable Seizure'),
        # Fifth Amendment
        ('self_incrimination', 'Self-Incrimination'),
        ('due_process_fifth', 'Due Process (Fifth)'),
        # Fourteenth Amendment
        ('due_process', 'Due Process'),
        ('equal_protection', 'Equal Protection'),
        # General
        ('qualified_immunity', 'Qualified Immunity'),
        ('municipal_liability', 'Municipal Liability'),
        ('section_1983_general', 'Section 1983 General'),
    ]

    COURT_LEVEL_CHOICES = [
        ('supreme', 'U.S. Supreme Court'),
        ('circuit', 'Circuit Court of Appeals'),
        ('district', 'District Court'),
    ]

    # Case identification
    case_name = models.CharField(max_length=255, help_text='e.g., Graham v. Connor')
    citation = models.CharField(max_length=255, help_text='e.g., 490 U.S. 386 (1989)')
    year = models.PositiveIntegerField()
    court_level = models.CharField(max_length=20, choices=COURT_LEVEL_CHOICES)
    circuit = models.CharField(max_length=50, blank=True, help_text='e.g., 9th Circuit, if applicable')

    # Classification
    amendment = models.CharField(max_length=20, choices=AMENDMENT_CHOICES)
    right_category = models.CharField(max_length=50, choices=RIGHT_CATEGORY_CHOICES)

    # Content for AI matching
    key_holding = models.TextField(help_text='The main legal principle established')
    facts_summary = models.TextField(help_text='Brief summary of the case facts')
    relevance_keywords = models.TextField(help_text='Comma-separated keywords for AI matching')

    # For document generation
    citation_text = models.TextField(help_text='Ready-to-use citation paragraph for complaints')

    # Metadata
    is_landmark = models.BooleanField(default=False, help_text='Is this a foundational/frequently cited case?')
    is_active = models.BooleanField(default=True, help_text='Include in AI suggestions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_landmark', '-year']
        verbose_name = 'Case Law'
        verbose_name_plural = 'Case Law'

    def __str__(self):
        return f"{self.case_name}, {self.citation}"

    def get_full_citation(self):
        """Return formatted citation."""
        return f"{self.case_name}, {self.citation}"


class DocumentCaseLaw(models.Model):
    """
    Links case law citations to a specific document.
    AI suggests cases, user can accept/edit/remove.
    """

    STATUS_CHOICES = [
        ('suggested', 'AI Suggested'),
        ('accepted', 'Accepted'),
        ('edited', 'Edited by User'),
        ('rejected', 'Rejected'),
    ]

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='case_law_citations')
    case_law = models.ForeignKey(CaseLaw, on_delete=models.CASCADE, related_name='document_uses')

    # Which right this citation supports
    amendment = models.CharField(max_length=20, choices=CaseLaw.AMENDMENT_CHOICES)
    right_category = models.CharField(max_length=50, choices=CaseLaw.RIGHT_CATEGORY_CHOICES)

    # AI-generated explanation of why this case applies
    relevance_explanation = models.TextField(help_text='AI-generated explanation of how this case applies to the facts')

    # User can edit the explanation
    user_explanation = models.TextField(blank=True, help_text='User-edited explanation (overrides AI)')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='suggested')
    order = models.PositiveIntegerField(default=0, help_text='Display order within the document')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['amendment', 'order']
        unique_together = ['document', 'case_law']

    def __str__(self):
        return f"{self.case_law.case_name} - {self.document.title}"

    def get_explanation(self):
        """Return user explanation if edited, otherwise AI explanation."""
        return self.user_explanation if self.user_explanation else self.relevance_explanation


class PromoCode(models.Model):
    """Referral/promo codes created by users."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='promo_codes'
    )
    code = models.CharField(max_length=20, unique=True, help_text='Unique promo code (e.g., SMITH25)')
    name = models.CharField(max_length=100, blank=True, help_text='Optional friendly name for this code')
    referral_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=5.00,
        help_text='Amount earned per referral (default $5.00)'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Stats (denormalized for quick display)
    times_used = models.IntegerField(default=0)
    total_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} ({self.owner.email})"

    def record_usage(self, amount_earned):
        """Record a successful use of this promo code."""
        self.times_used += 1
        self.total_earned += Decimal(str(amount_earned))
        self.save(update_fields=['times_used', 'total_earned'])

    def get_pending_earnings(self):
        """Get total pending (unpaid) earnings for this code."""
        return self.usages.filter(payout_status='pending').aggregate(
            total=models.Sum('referral_amount')
        )['total'] or Decimal('0.00')

    def get_paid_earnings(self):
        """Get total paid earnings for this code."""
        return self.usages.filter(payout_status='paid').aggregate(
            total=models.Sum('referral_amount')
        )['total'] or Decimal('0.00')


class PromoCodeUsage(models.Model):
    """Tracks each use of a promo code for payout management."""

    PAYOUT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ]

    promo_code = models.ForeignKey(PromoCode, on_delete=models.CASCADE, related_name='usages')
    document = models.OneToOneField(Document, on_delete=models.CASCADE, related_name='promo_usage')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='promo_code_usages'
    )

    # Payment details
    stripe_payment_id = models.CharField(max_length=255)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    referral_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=settings.REFERRAL_PAYOUT
    )

    # Payout tracking
    payout_status = models.CharField(max_length=20, choices=PAYOUT_STATUS_CHOICES, default='pending')
    payout_reference = models.CharField(
        max_length=255, blank=True,
        help_text='Reference for payout (PayPal transaction ID, check number, etc.)'
    )
    payout_date = models.DateTimeField(null=True, blank=True)
    payout_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Promo Code Usage'
        verbose_name_plural = 'Promo Code Usages'

    def __str__(self):
        return f"{self.promo_code.code} used by {self.user.email}"

    def mark_paid(self, reference, notes=''):
        """Mark this usage as paid out."""
        self.payout_status = 'paid'
        self.payout_reference = reference
        self.payout_date = timezone.now()
        self.payout_notes = notes
        self.save()


class PayoutRequest(models.Model):
    """Tracks payout requests from users."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payout_requests'
    )
    amount_requested = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(
        max_length=100, blank=True,
        help_text='How user wants to be paid (PayPal email, Venmo, etc.)'
    )
    payment_details = models.TextField(
        blank=True,
        help_text='Additional payment details provided by user'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Admin processing
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_reference = models.CharField(
        max_length=255, blank=True,
        help_text='Transaction ID or reference number'
    )
    admin_notes = models.TextField(blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='processed_payouts'
    )
    processed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payout Request'
        verbose_name_plural = 'Payout Requests'

    def __str__(self):
        return f"${self.amount_requested} request by {self.user.email} ({self.status})"

    def mark_completed(self, admin_user, amount_paid, reference, notes=''):
        """Mark this payout request as completed."""
        self.status = 'completed'
        self.amount_paid = amount_paid
        self.payment_reference = reference
        self.admin_notes = notes
        self.processed_by = admin_user
        self.processed_at = timezone.now()
        self.save()
