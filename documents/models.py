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

    # Story parsing status (for background processing)
    PARSING_STATUS_CHOICES = [
        ('idle', 'Idle'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    parsing_status = models.CharField(
        max_length=20, choices=PARSING_STATUS_CHOICES, default='idle',
        help_text='Current status of story parsing'
    )
    parsing_result = models.JSONField(
        null=True, blank=True,
        help_text='Parsed sections from AI (stored for polling retrieval)'
    )
    parsing_error = models.TextField(
        blank=True,
        help_text='Error message if parsing failed'
    )
    parsing_started_at = models.DateTimeField(
        null=True, blank=True,
        help_text='When parsing started (to detect stale jobs)'
    )

    # PDF generation status (for background processing)
    PDF_STATUS_CHOICES = [
        ('idle', 'Idle'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    pdf_status = models.CharField(
        max_length=20, choices=PDF_STATUS_CHOICES, default='idle',
        help_text='Current status of PDF generation'
    )
    pdf_progress_stage = models.CharField(
        max_length=50, blank=True, default='',
        help_text='Current stage of PDF generation for progress display'
    )
    pdf_error = models.TextField(
        blank=True, default='',
        help_text='Error message if PDF generation failed'
    )
    pdf_started_at = models.DateTimeField(
        null=True, blank=True,
        help_text='When PDF generation started (to detect stale jobs)'
    )
    pdf_file_path = models.CharField(
        max_length=500, blank=True, default='',
        help_text='Path to generated PDF file'
    )

    # Cached generated complaint (to avoid regenerating on every preview)
    generated_complaint = models.TextField(
        blank=True,
        help_text='Cached AI-generated legal complaint document'
    )
    generated_at = models.DateTimeField(
        null=True, blank=True,
        help_text='When the complaint was last generated'
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

    def has_sections_needing_work(self):
        """Check if any sections need work."""
        return self.sections.filter(status='needs_work').exists()

    def has_story(self):
        """Check if user has told their story (required before filling sections)."""
        return bool(self.story_text and self.story_text.strip())

    def invalidate_generated_complaint(self):
        """Clear cached complaint when document data changes."""
        if self.generated_complaint or self.generated_at:
            self.generated_complaint = ''
            self.generated_at = None
            self.save(update_fields=['generated_complaint', 'generated_at'])

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
        # Subscribers get AI based on their plan
        if self.user.can_use_subscription_ai():
            return True
        if self.payment_status == 'draft':
            # Check USER-level free AI limit (across all documents)
            return self.user.can_use_free_ai()
        elif self.payment_status == 'paid':
            # Paid documents get 100 AI uses per document
            return self.ai_generations_used < settings.PAID_AI_USES
        return False

    def get_ai_usage_display(self):
        """Get AI usage display string."""
        if self.user.has_unlimited_access():
            return "AI: Unlimited (Admin)"
        # Show subscription AI info for subscribers
        if self.user.has_active_subscription():
            remaining = self.user.get_subscription_ai_remaining()
            subscription = self.user.get_subscription()
            if subscription and subscription.plan == 'annual':
                return f"AI: {remaining} of {settings.SUBSCRIPTION_ANNUAL_AI_USES} uses remaining (Pro Annual)"
            return f"AI: {remaining} uses remaining this month (Pro)"
        if self.payment_status == 'draft':
            remaining = self.user.get_free_ai_remaining()
            return f"{remaining} of {settings.FREE_AI_GENERATIONS} free AI uses remaining"
        elif self.payment_status == 'paid':
            remaining = settings.PAID_AI_USES - self.ai_generations_used
            return f"AI: {remaining} of {settings.PAID_AI_USES} uses remaining"
        return "AI unavailable"

    def record_ai_usage(self, cost=None):
        """Record AI usage. For subscribers: use subscription tracking. For draft/paid: increment count."""
        # Subscribers track usage on their subscription
        if self.user.has_active_subscription():
            subscription = self.user.get_subscription()
            if subscription:
                subscription.record_ai_use()
            return
        # Both draft and paid documents use count-based tracking
        if self.payment_status in ('draft', 'paid'):
            self.ai_generations_used += 1
            self.save(update_fields=['ai_generations_used'])

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
    court_district_confirmed = models.BooleanField(default=False, help_text='User confirmed the court district is correct')

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
    agency_inferred = models.BooleanField(default=False, help_text='True if agency was AI-inferred and needs review')
    address = models.TextField(blank=True, help_text='Official address for service')
    address_verified = models.BooleanField(default=False, help_text='User confirmed they verified the address is correct')
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

    # Evidence captured by witness
    has_evidence = models.BooleanField(default=False, help_text='Did this witness capture video/photo evidence?')
    evidence_description = models.TextField(blank=True, help_text='Describe what they recorded (video, photos, audio)')

    # Prior interactions with defendants
    prior_interactions = models.TextField(blank=True, help_text='Any prior interactions this witness had with the defendant(s)')

    # Additional notes
    additional_notes = models.TextField(blank=True, help_text='Any other relevant information about this witness')

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


class AIPrompt(models.Model):
    """
    Database-stored AI prompts that can be edited in admin.
    Allows non-developers to tweak AI behavior without code changes.
    """

    PROMPT_TYPES = [
        ('parse_story', 'Parse Story - Analyzes user story and extracts structured data'),
        ('analyze_rights', 'Analyze Rights - Identifies constitutional violations'),
        ('suggest_agency', 'Suggest Agency - Finds defendants based on story'),
        ('suggest_relief', 'Suggest Relief - Recommends legal relief options'),
        ('find_law_enforcement', 'Find Law Enforcement - Identifies correct police/sheriff'),
        ('lookup_address', 'Lookup Address - Finds agency addresses'),
        ('lookup_federal_court', 'Lookup Federal Court - Finds federal district court for location'),
    ]

    prompt_type = models.CharField(
        max_length=50,
        choices=PROMPT_TYPES,
        unique=True,
        help_text='Which AI function this prompt is used for'
    )
    title = models.CharField(
        max_length=255,
        help_text='Human-readable title displayed in admin'
    )
    description = models.TextField(
        help_text='Detailed description of what this prompt does and when it is used'
    )
    system_message = models.TextField(
        help_text='The system role message that sets AI behavior/persona'
    )
    user_prompt_template = models.TextField(
        help_text='The main prompt template. Use {variable_name} for placeholders like {city}, {state}, {story_text}'
    )
    available_variables = models.TextField(
        blank=True,
        help_text='Comma-separated list of variables available for this prompt (e.g., city, state, story_text)'
    )
    model_name = models.CharField(
        max_length=50,
        default='gpt-4o-mini',
        help_text='OpenAI model to use (e.g., gpt-4o-mini, gpt-4o)'
    )
    temperature = models.FloatField(
        default=0.1,
        help_text='AI temperature (0.0-1.0). Lower = more consistent, higher = more creative'
    )
    max_tokens = models.IntegerField(
        default=2000,
        help_text='Maximum tokens in the response'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='If disabled, this prompt will not be used'
    )
    version = models.IntegerField(
        default=1,
        help_text='Version number for tracking changes'
    )
    last_edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Admin user who last edited this prompt'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'AI Prompt'
        verbose_name_plural = 'AI Prompts'
        ordering = ['prompt_type']

    def __str__(self):
        return f"{self.title} ({self.prompt_type})"

    @classmethod
    def get_prompt(cls, prompt_type: str) -> 'AIPrompt':
        """
        Get an active prompt by type, or None if not found/disabled.
        """
        try:
            return cls.objects.get(prompt_type=prompt_type, is_active=True)
        except cls.DoesNotExist:
            return None

    def format_prompt(self, **kwargs) -> str:
        """
        Format the user prompt template with provided variables.
        """
        try:
            return self.user_prompt_template.format(**kwargs)
        except KeyError as e:
            # If a variable is missing, return template as-is
            return self.user_prompt_template


# =============================================================================
# Video Evidence Models (YouTube transcript extraction for subscribers)
# =============================================================================

class VideoEvidence(models.Model):
    """
    Links a YouTube video to an existing Evidence record.
    Allows transcript extraction for subscriber users.
    """

    evidence = models.OneToOneField(
        Evidence,
        on_delete=models.CASCADE,
        related_name='video_evidence'
    )
    youtube_url = models.CharField(
        max_length=500,
        help_text='Full YouTube URL'
    )
    video_id = models.CharField(
        max_length=20,
        help_text='YouTube video ID (extracted from URL)'
    )
    video_title = models.CharField(
        max_length=255,
        blank=True,
        help_text='Video title fetched from YouTube'
    )
    video_duration_seconds = models.IntegerField(
        null=True,
        blank=True,
        help_text='Total video length in seconds'
    )
    has_youtube_captions = models.BooleanField(
        default=False,
        help_text='Whether YouTube captions are available'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Video Evidence'
        verbose_name_plural = 'Video Evidence'

    def __str__(self):
        return f"Video: {self.video_title or self.video_id}"

    @staticmethod
    def extract_video_id(url: str) -> str:
        """
        Extract YouTube video ID from various URL formats.
        Supports: youtube.com/watch?v=ID, youtu.be/ID, youtube.com/embed/ID
        """
        import re
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
            r'(?:youtube\.com\/watch\?.*v=)([a-zA-Z0-9_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return ''

    def get_document(self):
        """Get the parent Document for this video evidence."""
        return self.evidence.section.document


class VideoCapture(models.Model):
    """
    A time-stamped clip from a video with extracted transcript.
    Each capture counts as 1 AI use for the subscriber.
    Maximum clip length: 2 minutes.
    """

    EXTRACTION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    EXTRACTION_METHOD_CHOICES = [
        ('youtube', 'YouTube Captions'),
        ('whisper', 'Whisper Transcription'),
    ]

    video_evidence = models.ForeignKey(
        VideoEvidence,
        on_delete=models.CASCADE,
        related_name='captures'
    )
    start_time_seconds = models.IntegerField(
        help_text='Clip start time in seconds (e.g., 302 for 5:02)'
    )
    end_time_seconds = models.IntegerField(
        help_text='Clip end time in seconds (e.g., 333 for 5:33)'
    )
    raw_transcript = models.TextField(
        blank=True,
        help_text='Extracted transcript text (unedited)'
    )
    attributed_transcript = models.TextField(
        blank=True,
        help_text='User-edited transcript with speaker attributions'
    )
    extraction_method = models.CharField(
        max_length=20,
        choices=EXTRACTION_METHOD_CHOICES,
        blank=True,
        help_text='How the transcript was extracted'
    )
    extraction_status = models.CharField(
        max_length=20,
        choices=EXTRACTION_STATUS_CHOICES,
        default='pending',
        help_text='Current status of transcript extraction'
    )
    extraction_error = models.TextField(
        blank=True,
        help_text='Error message if extraction failed'
    )
    ai_use_recorded = models.BooleanField(
        default=False,
        help_text='Whether this extraction was counted toward AI usage limit'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Video Capture'
        verbose_name_plural = 'Video Captures'
        ordering = ['start_time_seconds']

    def __str__(self):
        return f"Capture {self.start_time_display} - {self.end_time_display}"

    @property
    def start_time_display(self) -> str:
        """Format start time as MM:SS or HH:MM:SS."""
        return self._seconds_to_display(self.start_time_seconds)

    @property
    def end_time_display(self) -> str:
        """Format end time as MM:SS or HH:MM:SS."""
        return self._seconds_to_display(self.end_time_seconds)

    @property
    def duration_seconds(self) -> int:
        """Get clip duration in seconds."""
        return self.end_time_seconds - self.start_time_seconds

    @property
    def duration_display(self) -> str:
        """Format duration as MM:SS."""
        return self._seconds_to_display(self.duration_seconds)

    @staticmethod
    def _seconds_to_display(seconds: int) -> str:
        """Convert seconds to MM:SS or HH:MM:SS format."""
        if seconds < 0:
            return "0:00"
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    @staticmethod
    def parse_time_to_seconds(time_str: str) -> int:
        """
        Parse time string to seconds.
        Accepts: "5:02", "5.02", "1:05:02", "1.05.02", "302", etc.
        Periods are treated as separators (same as colons).
        """
        time_str = time_str.strip()

        # Convert periods to colons for parsing (1.20 → 1:20, 1.23.52 → 1:23:52)
        time_str = time_str.replace('.', ':')

        # If it's just a number, assume seconds
        if time_str.isdigit():
            return int(time_str)

        parts = time_str.split(':')
        try:
            if len(parts) == 2:  # MM:SS
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:  # HH:MM:SS
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except (ValueError, IndexError):
            pass
        return 0

    def clean(self):
        """Validate clip length (max 2 minutes = 120 seconds)."""
        from django.core.exceptions import ValidationError
        if self.duration_seconds > 120:
            raise ValidationError({
                'end_time_seconds': 'Clip length cannot exceed 2 minutes (120 seconds).'
            })
        if self.start_time_seconds >= self.end_time_seconds:
            raise ValidationError({
                'end_time_seconds': 'End time must be after start time.'
            })


class VideoSpeaker(models.Model):
    """
    Maps speakers in the video to defendants or plaintiff.
    Persists across captures from the same video.
    """

    video_evidence = models.ForeignKey(
        VideoEvidence,
        on_delete=models.CASCADE,
        related_name='speakers'
    )
    label = models.CharField(
        max_length=100,
        help_text='Speaker label (e.g., "Speaker 1", "Male Officer")'
    )
    defendant = models.ForeignKey(
        Defendant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='video_speaker_attributions',
        help_text='Link to defendant if this speaker is a defendant'
    )
    is_plaintiff = models.BooleanField(
        default=False,
        help_text='Is this speaker the plaintiff (user)?'
    )
    notes = models.CharField(
        max_length=255,
        blank=True,
        help_text='Description (e.g., "Officer with mustache")'
    )

    class Meta:
        verbose_name = 'Video Speaker'
        verbose_name_plural = 'Video Speakers'
        unique_together = ['video_evidence', 'label']

    def __str__(self):
        if self.defendant:
            return f"{self.label} → {self.defendant.name}"
        elif self.is_plaintiff:
            return f"{self.label} → Plaintiff"
        return self.label

    def get_display_name(self) -> str:
        """Get the best display name for this speaker."""
        if self.defendant:
            return self.defendant.name
        elif self.is_plaintiff:
            return "Plaintiff"
        return self.label
