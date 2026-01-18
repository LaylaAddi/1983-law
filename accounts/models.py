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
        """Get total paid referral earnings."""
        from documents.models import PromoCodeUsage
        return PromoCodeUsage.objects.filter(
            promo_code__owner=self,
            payout_status='paid'
        ).aggregate(
            total=models.Sum('referral_amount')
        )['total'] or 0


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

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Site Settings'
        verbose_name_plural = 'Site Settings'

    def __str__(self):
        return f"Site Settings ({self.company_name})"

    def save(self, *args, **kwargs):
        """Ensure only one instance exists."""
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings instance."""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings
