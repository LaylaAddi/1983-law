from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


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
