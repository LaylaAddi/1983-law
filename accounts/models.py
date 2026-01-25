from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.conf import settings


class CustomUserManager(BaseUserManager):
    """Manager for custom User model with email authentication."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom User model with email as the primary identifier."""

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True)
    middle_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)

    # Address (for legal documents)
    street_address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=50, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    # Mailing address (if different from street address)
    use_different_mailing_address = models.BooleanField(default=False)
    mailing_street_address = models.CharField(max_length=255, blank=True)
    mailing_city = models.CharField(max_length=100, blank=True)
    mailing_state = models.CharField(max_length=50, blank=True)
    mailing_zip_code = models.CharField(max_length=20, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_test_user = models.BooleanField(default=False, help_text='Enable test features like auto-fill sample data')

    # Terms agreement tracking
    agreed_to_terms = models.BooleanField(default=False, help_text='User agreed to Terms of Service')
    agreed_to_privacy = models.BooleanField(default=False, help_text='User agreed to Privacy Policy')
    terms_agreed_at = models.DateTimeField(null=True, blank=True, help_text='When user agreed to terms')
    terms_agreed_ip = models.GenericIPAddressField(null=True, blank=True, help_text='IP address when terms were agreed')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'

    def __str__(self):
        return self.email

    def get_full_name(self):
        name_parts = [self.first_name, self.middle_name, self.last_name]
        full_name = ' '.join(part for part in name_parts if part)
        return full_name or self.email

    def get_short_name(self):
        return self.first_name or self.email.split('@')[0]

    def has_complete_profile(self):
        """Check if user has filled required profile fields for legal documents."""
        return all([
            self.first_name,
            self.last_name,
            self.street_address,
            self.city,
            self.state,
            self.zip_code,
            self.phone
        ])

    def get_full_address(self):
        """Return formatted full address."""
        parts = [self.street_address]
        city_state_zip = ', '.join(filter(None, [self.city, self.state]))
        if city_state_zip:
            if self.zip_code:
                city_state_zip += ' ' + self.zip_code
            parts.append(city_state_zip)
        return '\n'.join(filter(None, parts))

    def get_mailing_address(self):
        """Return formatted mailing address (or regular address if same)."""
        if not self.use_different_mailing_address:
            return self.get_full_address()
        parts = [self.mailing_street_address]
        city_state_zip = ', '.join(filter(None, [self.mailing_city, self.mailing_state]))
        if city_state_zip:
            if self.mailing_zip_code:
                city_state_zip += ' ' + self.mailing_zip_code
            parts.append(city_state_zip)
        return '\n'.join(filter(None, parts))

    def has_unlimited_access(self):
        """Check if user has unlimited access (admin/staff)."""
        return self.is_staff or self.is_superuser

    def get_total_free_ai_uses(self):
        """Get total free AI generations used across all draft documents."""
        return self.documents.filter(
            payment_status='draft'
        ).aggregate(
            total=models.Sum('ai_generations_used')
        )['total'] or 0

    def can_use_free_ai(self):
        """Check if user can still use free AI generations."""
        if self.has_unlimited_access():
            return True
        return self.get_total_free_ai_uses() < settings.FREE_AI_GENERATIONS

    def get_free_ai_remaining(self):
        """Get remaining free AI generations for this user."""
        if self.has_unlimited_access():
            return 999  # Unlimited
        remaining = settings.FREE_AI_GENERATIONS - self.get_total_free_ai_uses()
        return max(0, remaining)

    def get_total_referral_earnings(self):
        """Get total earnings from all promo codes."""
        from documents.models import PromoCode
        return self.promo_codes.aggregate(
            total=models.Sum('total_earned')
        )['total'] or 0

    def get_pending_referral_earnings(self):
        """Get total pending (unpaid) referral earnings."""
        from documents.models import PromoCodeUsage
        return PromoCodeUsage.objects.filter(
            promo_code__owner=self,
            payout_status='pending'
        ).aggregate(
            total=models.Sum('referral_amount')
        )['total'] or 0

    def get_paid_referral_earnings(self):
        """Get total paid referral earnings from document purchases."""
        from documents.models import PromoCodeUsage
        return PromoCodeUsage.objects.filter(
            promo_code__owner=self,
            payout_status='paid'
        ).aggregate(
            total=models.Sum('referral_amount')
        )['total'] or 0

    def get_subscription_referral_earnings(self):
        """Get total earnings from subscription referrals."""
        return SubscriptionReferral.objects.filter(
            promo_code__owner=self
        ).aggregate(
            total=models.Sum('referral_amount')
        )['total'] or 0

    def get_pending_subscription_referral_earnings(self):
        """Get pending subscription referral earnings."""
        return SubscriptionReferral.objects.filter(
            promo_code__owner=self,
            payout_status='pending'
        ).aggregate(
            total=models.Sum('referral_amount')
        )['total'] or 0

    def get_all_referral_earnings(self):
        """Get total earnings from all referral types."""
        doc_earnings = self.get_total_referral_earnings() or 0
        sub_earnings = self.get_subscription_referral_earnings() or 0
        return doc_earnings + sub_earnings

    def get_all_pending_referral_earnings(self):
        """Get total pending earnings from all referral types."""
        doc_pending = self.get_pending_referral_earnings() or 0
        sub_pending = self.get_pending_subscription_referral_earnings() or 0
        return doc_pending + sub_pending

    # Subscription methods

    def has_active_subscription(self):
        """Check if user has an active subscription."""
        try:
            return self.subscription.is_active()
        except Subscription.DoesNotExist:
            return False

    def get_subscription(self):
        """Get user's subscription or None."""
        try:
            return self.subscription
        except Subscription.DoesNotExist:
            return None

    def get_document_credits(self):
        """Get total remaining document credits from packs."""
        return sum(
            pack.documents_remaining()
            for pack in self.document_packs.all()
        )

    def use_document_credit(self):
        """Use a document credit from oldest pack. Returns True if successful."""
        for pack in self.document_packs.order_by('created_at'):
            if pack.use_document():
                return True
        return False

    def can_create_document(self):
        """Check if user can create a new document (subscription or credits)."""
        if self.has_unlimited_access():
            return True
        if self.has_active_subscription():
            return True
        if self.get_document_credits() > 0:
            return True
        return False

    def get_subscription_ai_remaining(self):
        """Get remaining AI uses from subscription."""
        if self.has_active_subscription():
            return self.subscription.get_ai_remaining()
        return 0

    def can_use_subscription_ai(self):
        """Check if user can use AI via subscription."""
        if self.has_active_subscription():
            return self.subscription.can_use_ai()
        return False

    def can_use_video_analysis(self):
        """
        Check if user can use the video evidence extraction feature.
        Only available to Monthly and Annual Pro subscribers (or admin/staff).
        """
        if self.has_unlimited_access():
            return True
        return self.has_active_subscription()

    def needs_purchase_prompt(self):
        """Check if user should see the purchase interstitial when creating documents.

        Returns False if user has:
        - Unlimited access (staff/superuser)
        - Active subscription
        - Document pack credits remaining
        - Free AI uses remaining

        Returns True if user has exhausted all options and should be prompted to purchase.
        """
        if self.has_unlimited_access():
            return False
        if self.has_active_subscription():
            return False
        if self.get_document_credits() > 0:
            return False
        if self.can_use_free_ai():
            return False
        return True

    def get_access_summary(self):
        """Get a summary of user's current access for display."""
        summary = {
            'has_subscription': False,
            'subscription': None,
            'document_credits': 0,
            'free_ai_remaining': 0,
            'has_unlimited': self.has_unlimited_access(),
        }

        if self.has_active_subscription():
            summary['has_subscription'] = True
            summary['subscription'] = self.get_subscription()

        summary['document_credits'] = self.get_document_credits()
        summary['free_ai_remaining'] = self.get_free_ai_remaining()

        return summary


class SiteSettings(models.Model):
    """
    Singleton model for site-wide settings.
    Only one instance should exist - use SiteSettings.get_settings() to access.
    """

    # Company/Organization Info
    company_name = models.CharField(
        max_length=255,
        default='1983law.org',
        help_text='Legal name of the company/organization'
    )
    company_type = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='e.g., LLC, Non-Profit, Corporation'
    )
    company_state = models.CharField(
        max_length=50,
        default='New York',
        help_text='State of incorporation/registration'
    )
    company_address = models.TextField(
        blank=True,
        default='',
        help_text='Physical business address (required for CAN-SPAM)'
    )
    contact_email = models.EmailField(
        default='contact@1983law.org',
        help_text='Contact email for legal/privacy inquiries'
    )
    website_url = models.URLField(
        default='https://www.1983law.org',
        help_text='Primary website URL'
    )

    # Legal Settings
    minimum_age = models.PositiveIntegerField(
        default=18,
        help_text='Minimum age to use the service'
    )
    governing_law_state = models.CharField(
        max_length=50,
        default='New York',
        help_text='State whose laws govern the Terms of Service'
    )
    has_attorneys = models.BooleanField(
        default=False,
        help_text='Are licensed attorneys involved in the service?'
    )
    attorney_states = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='States where attorneys are licensed (comma-separated)'
    )

    # Payment Settings
    payment_processor = models.CharField(
        max_length=100,
        default='Stripe',
        help_text='Payment processor used (e.g., Stripe, PayPal)'
    )
    refund_policy_days = models.PositiveIntegerField(
        default=0,
        help_text='Number of days for refund requests (0 = no refunds)'
    )

    # Third-Party Services
    uses_google_analytics = models.BooleanField(
        default=True,
        help_text='Does the site use Google Analytics?'
    )
    uses_openai = models.BooleanField(
        default=True,
        help_text='Does the site use OpenAI/AI services?'
    )
    hosting_provider = models.CharField(
        max_length=100,
        default='Render',
        help_text='Web hosting provider'
    )

    # Policy Dates
    terms_effective_date = models.DateField(
        null=True,
        blank=True,
        help_text='Effective date of Terms of Service'
    )
    privacy_effective_date = models.DateField(
        null=True,
        blank=True,
        help_text='Effective date of Privacy Policy'
    )

    # Footer Contact Information
    footer_address = models.TextField(
        blank=True,
        default='123 Liberty Avenue, Suite 1983\nNew York, NY 10001',
        help_text='Address to display in footer (use line breaks for formatting)'
    )
    footer_phone = models.CharField(
        max_length=20,
        blank=True,
        default='585-204-7416',
        help_text='Phone number to display in footer'
    )
    footer_email = models.EmailField(
        blank=True,
        default='info@1983law.org',
        help_text='Email address to display in footer'
    )
    show_footer_contact = models.BooleanField(
        default=True,
        help_text='Show contact section in footer'
    )
    show_footer_address = models.BooleanField(
        default=False,
        help_text='Show address in footer contact section'
    )
    show_footer_phone = models.BooleanField(
        default=True,
        help_text='Show phone number in footer contact section'
    )
    show_footer_email = models.BooleanField(
        default=True,
        help_text='Show email in footer contact section'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Site Settings'
        verbose_name_plural = 'Site Settings'

    def __str__(self):
        return f"Site Settings ({self.company_name})"

    def save(self, *args, **kwargs):
        """Ensure only one instance exists and create default legal documents."""
        is_new = not SiteSettings.objects.filter(pk=1).exists()
        self.pk = 1
        super().save(*args, **kwargs)

        # Auto-create legal documents if this is the first save
        if is_new:
            self._create_default_legal_documents()

    def _create_default_legal_documents(self):
        """Create default legal documents with placeholder content."""
        from datetime import date

        defaults = [
            {
                'document_type': 'terms',
                'title': 'Terms of Service',
                'content': f'''<h2>Terms of Service for {self.company_name}</h2>
<p><strong>Effective Date:</strong> {date.today().strftime("%B %d, %Y")}</p>

<h3>1. Acceptance of Terms</h3>
<p>By accessing and using {self.website_url}, you agree to be bound by these Terms of Service.</p>

<h3>2. Description of Service</h3>
<p>{self.company_name} provides tools to help users create legal documents. We are not a law firm and do not provide legal advice.</p>

<h3>3. User Responsibilities</h3>
<p>You are responsible for the accuracy of information you provide and for reviewing all generated documents before use.</p>

<h3>4. Disclaimer</h3>
<p>Documents generated through this service are templates and starting points. We strongly recommend having an attorney review any legal document before filing.</p>

<h3>5. Governing Law</h3>
<p>These terms are governed by the laws of the State of {self.governing_law_state}.</p>

<h3>6. Contact</h3>
<p>Questions? Contact us at {self.contact_email}</p>
''',
            },
            {
                'document_type': 'privacy',
                'title': 'Privacy Policy',
                'content': f'''<h2>Privacy Policy for {self.company_name}</h2>
<p><strong>Effective Date:</strong> {date.today().strftime("%B %d, %Y")}</p>

<h3>1. Information We Collect</h3>
<p>We collect information you provide directly, including name, email, and document content.</p>

<h3>2. How We Use Your Information</h3>
<p>We use your information to provide our services, process payments, and improve our platform.</p>

<h3>3. Third-Party Services</h3>
<p>We use {self.payment_processor} for payment processing{" and OpenAI for AI-assisted features" if self.uses_openai else ""}.</p>

<h3>4. Data Security</h3>
<p>We implement industry-standard security measures to protect your information.</p>

<h3>5. Your Rights</h3>
<p>You may request access to, correction of, or deletion of your personal data by contacting {self.contact_email}.</p>

<h3>6. Contact</h3>
<p>Privacy questions? Contact us at {self.contact_email}</p>
''',
            },
            {
                'document_type': 'disclaimer',
                'title': 'Legal Disclaimer',
                'content': f'''<h2>Legal Disclaimer</h2>

<h3>Not Legal Advice</h3>
<p><strong>{self.company_name} is not a law firm and does not provide legal advice.</strong></p>

<p>The documents and information provided through this service are for informational purposes only and should not be construed as legal advice. Use of this service does not create an attorney-client relationship.</p>

<h3>No Guarantee of Results</h3>
<p>We cannot guarantee any particular outcome from using documents created through our service. Legal outcomes depend on many factors beyond document preparation.</p>

<h3>Recommendation</h3>
<p>We strongly recommend consulting with a licensed attorney in your jurisdiction before filing any legal documents.</p>

<h3>Contact</h3>
<p>Questions? Contact us at {self.contact_email}</p>
''',
            },
            {
                'document_type': 'cookies',
                'title': 'Cookie Policy',
                'content': f'''<h2>Cookie Policy for {self.company_name}</h2>

<h3>What Are Cookies</h3>
<p>Cookies are small text files stored on your device when you visit our website.</p>

<h3>How We Use Cookies</h3>
<p>We use cookies for:</p>
<ul>
<li><strong>Essential cookies:</strong> Required for the website to function (login sessions, security)</li>
<li><strong>Analytics cookies:</strong> Help us understand how visitors use our site{" (Google Analytics)" if self.uses_google_analytics else ""}</li>
</ul>

<h3>Managing Cookies</h3>
<p>You can control cookies through your browser settings. Note that disabling cookies may affect website functionality.</p>

<h3>Contact</h3>
<p>Questions about cookies? Contact us at {self.contact_email}</p>
''',
            },
        ]

        for doc_data in defaults:
            LegalDocument.objects.get_or_create(
                document_type=doc_data['document_type'],
                defaults={
                    'title': doc_data['title'],
                    'content': doc_data['content'],
                    'effective_date': date.today(),
                    'is_active': True,
                }
            )

    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings instance."""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings


class LegalDocument(models.Model):
    """
    Editable legal documents (Terms, Privacy Policy, etc.)
    Content is stored in database and rendered with rich text formatting.
    """

    DOCUMENT_TYPES = [
        ('terms', 'Terms of Service'),
        ('privacy', 'Privacy Policy'),
        ('disclaimer', 'Legal Disclaimer'),
        ('cookies', 'Cookie Policy'),
    ]

    document_type = models.CharField(
        max_length=20,
        choices=DOCUMENT_TYPES,
        unique=True,
        help_text='Type of legal document'
    )
    title = models.CharField(
        max_length=255,
        help_text='Document title displayed at top of page'
    )
    content = models.TextField(
        help_text='Full document content (HTML allowed)'
    )
    effective_date = models.DateField(
        null=True,
        blank=True,
        help_text='When this version became effective'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this document is currently active'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Legal Document'
        verbose_name_plural = 'Legal Documents'
        ordering = ['document_type']

    def __str__(self):
        return self.get_document_type_display()

    @classmethod
    def get_document(cls, doc_type):
        """Get the active document of the specified type."""
        try:
            return cls.objects.get(document_type=doc_type, is_active=True)
        except cls.DoesNotExist:
            return None


class Subscription(models.Model):
    """
    User subscription for unlimited document access.
    Tracks Stripe subscription lifecycle.
    """

    PLAN_CHOICES = [
        ('monthly', 'Monthly ($29/mo)'),
        ('annual', 'Annual ($249/yr)'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('unpaid', 'Unpaid'),
        ('trialing', 'Trialing'),
        ('incomplete', 'Incomplete'),
        ('incomplete_expired', 'Incomplete Expired'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription'
    )
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='incomplete')

    # Stripe IDs
    stripe_subscription_id = models.CharField(
        max_length=255,
        unique=True,
        help_text='Stripe Subscription ID (sub_xxx)'
    )
    stripe_customer_id = models.CharField(
        max_length=255,
        help_text='Stripe Customer ID (cus_xxx)'
    )

    # Billing cycle
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(
        default=False,
        help_text='If true, subscription will cancel at period end'
    )

    # AI usage tracking (resets each billing period)
    ai_uses_this_period = models.IntegerField(default=0)
    ai_period_reset_at = models.DateTimeField(null=True, blank=True)

    # Promo code used for signup
    promo_code_used = models.ForeignKey(
        'documents.PromoCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subscriptions'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    canceled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'

    def __str__(self):
        return f"{self.user.email} - {self.get_plan_display()} ({self.status})"

    def is_active(self):
        """Check if subscription is currently active."""
        return self.status in ['active', 'trialing']

    def get_ai_limit(self):
        """Get AI usage limit based on plan."""
        if self.plan == 'annual':
            return settings.SUBSCRIPTION_ANNUAL_AI_USES
        return settings.SUBSCRIPTION_MONTHLY_AI_USES

    def get_ai_remaining(self):
        """Get remaining AI uses for this period."""
        return max(0, self.get_ai_limit() - self.ai_uses_this_period)

    def can_use_ai(self):
        """Check if subscriber can use AI."""
        if not self.is_active():
            return False
        return self.ai_uses_this_period < self.get_ai_limit()

    def record_ai_use(self):
        """Record an AI use."""
        self.ai_uses_this_period += 1
        self.save(update_fields=['ai_uses_this_period'])

    def reset_ai_usage(self):
        """Reset AI usage for new billing period."""
        from django.utils import timezone
        self.ai_uses_this_period = 0
        self.ai_period_reset_at = timezone.now()
        self.save(update_fields=['ai_uses_this_period', 'ai_period_reset_at'])


class DocumentPack(models.Model):
    """
    Track document pack purchases (e.g., 3-pack).
    Each pack gives the user a certain number of document credits.
    """

    PACK_TYPES = [
        ('single', 'Single Document'),
        ('3pack', '3-Document Pack'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='document_packs'
    )
    pack_type = models.CharField(max_length=20, choices=PACK_TYPES)
    documents_included = models.IntegerField(help_text='Number of documents included')
    documents_used = models.IntegerField(default=0, help_text='Number of documents used')

    # Payment info
    stripe_payment_id = models.CharField(max_length=255, help_text='Stripe Payment Intent ID')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)

    # Promo code
    promo_code_used = models.ForeignKey(
        'documents.PromoCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='document_packs'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.get_pack_type_display()} ({self.documents_remaining()} remaining)"

    def documents_remaining(self):
        """Get number of documents remaining in pack."""
        return max(0, self.documents_included - self.documents_used)

    def has_documents_available(self):
        """Check if pack has available documents."""
        return self.documents_remaining() > 0

    def use_document(self):
        """Use one document from the pack."""
        if self.has_documents_available():
            self.documents_used += 1
            self.save(update_fields=['documents_used'])
            return True
        return False


class SubscriptionReferral(models.Model):
    """
    Track referrals for subscription signups.
    Referrer gets payout on first payment only.
    """

    PAYOUT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ]

    promo_code = models.ForeignKey(
        'documents.PromoCode',
        on_delete=models.CASCADE,
        related_name='subscription_referrals'
    )
    subscription = models.OneToOneField(
        Subscription,
        on_delete=models.CASCADE,
        related_name='referral'
    )
    subscriber = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription_referrals_received'
    )

    # Payment details
    plan_type = models.CharField(max_length=20)  # 'monthly' or 'annual'
    first_payment_amount = models.DecimalField(max_digits=10, decimal_places=2)
    referral_amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Payout tracking
    payout_status = models.CharField(
        max_length=20,
        choices=PAYOUT_STATUS_CHOICES,
        default='pending'
    )
    payout_reference = models.CharField(max_length=255, blank=True)
    payout_date = models.DateTimeField(null=True, blank=True)
    payout_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Subscription Referral'
        verbose_name_plural = 'Subscription Referrals'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.promo_code.code} → {self.subscriber.email} ({self.plan_type})"

    def mark_paid(self, reference, notes=''):
        """Mark this referral as paid out."""
        from django.utils import timezone
        self.payout_status = 'paid'
        self.payout_reference = reference
        self.payout_date = timezone.now()
        self.payout_notes = notes
        self.save()
