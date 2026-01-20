from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    UserCreationForm,
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
    PasswordChangeForm,
)

from common.constants import US_STATES

User = get_user_model()


class EmailAuthenticationForm(AuthenticationForm):
    """Login form using email instead of username."""

    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
        })
    )


class UserRegistrationForm(UserCreationForm):
    """Registration form with email as the primary field (no name fields - collected later)."""

    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email',
            'autofocus': True,
        })
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create a password',
        })
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password',
        })
    )
    agree_terms = forms.BooleanField(
        required=True,
        label='I agree to the Terms of Service',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
        error_messages={
            'required': 'You must agree to the Terms of Service to create an account.'
        }
    )
    agree_privacy = forms.BooleanField(
        required=True,
        label='I agree to the Privacy Policy',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
        error_messages={
            'required': 'You must agree to the Privacy Policy to create an account.'
        }
    )

    class Meta:
        model = User
        fields = ('email', 'password1', 'password2')

    def save(self, commit=True, ip_address=None):
        user = super().save(commit=False)
        user.agreed_to_terms = self.cleaned_data.get('agree_terms', False)
        user.agreed_to_privacy = self.cleaned_data.get('agree_privacy', False)
        if user.agreed_to_terms or user.agreed_to_privacy:
            from django.utils import timezone
            user.terms_agreed_at = timezone.now()
            user.terms_agreed_ip = ip_address
        if commit:
            user.save()
        return user


class CustomPasswordResetForm(PasswordResetForm):
    """Password reset form with Bootstrap styling."""

    email = forms.EmailField(
        label='Email',
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'autofocus': True,
        })
    )


class CustomSetPasswordForm(SetPasswordForm):
    """Set new password form with Bootstrap styling."""

    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password',
            'autofocus': True,
        })
    )
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
        })
    )


class CustomPasswordChangeForm(PasswordChangeForm):
    """Password change form with Bootstrap styling."""

    old_password = forms.CharField(
        label='Current Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter current password',
            'autofocus': True,
        })
    )
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password',
        })
    )
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
        })
    )


class ProfileEditForm(forms.ModelForm):
    """Form for editing user profile information."""

    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name',
        }),
        help_text='This will be used to pre-fill your name in legal documents.'
    )
    middle_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your middle name (optional)',
        }),
        help_text='Optional - include if you want it on legal documents.'
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name',
        }),
        help_text='This will be used to pre-fill your name in legal documents.'
    )
    street_address = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Street address',
        })
    )
    city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'City',
        })
    )
    state = forms.ChoiceField(
        choices=US_STATES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    zip_code = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ZIP Code',
        })
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '(555) 123-4567',
        })
    )
    use_different_mailing_address = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'id_use_different_mailing_address',
        }),
        label='My mailing address is different from my street address'
    )
    mailing_street_address = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mailing street address',
        })
    )
    mailing_city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'City',
        })
    )
    mailing_state = forms.ChoiceField(
        choices=US_STATES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    mailing_zip_code = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ZIP Code',
        })
    )

    class Meta:
        model = User
        fields = (
            'first_name', 'middle_name', 'last_name',
            'street_address', 'city', 'state', 'zip_code', 'phone',
            'use_different_mailing_address',
            'mailing_street_address', 'mailing_city', 'mailing_state', 'mailing_zip_code'
        )


class ProfileCompleteForm(forms.ModelForm):
    """Form for completing user profile (required before creating documents)."""

    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name',
        }),
        label='First Name'
    )
    middle_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Middle name (optional)',
        }),
        label='Middle Name'
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name',
        }),
        label='Last Name'
    )
    street_address = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Street address',
        }),
        label='Street Address'
    )
    city = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'City',
        }),
        label='City'
    )
    state = forms.ChoiceField(
        choices=US_STATES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
        label='State'
    )
    zip_code = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ZIP Code',
        }),
        label='ZIP Code'
    )
    phone = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '(555) 123-4567',
        }),
        label='Phone Number'
    )
    use_different_mailing_address = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'id_use_different_mailing_address',
        }),
        label='My mailing address is different from my street address'
    )
    mailing_street_address = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mailing street address',
        }),
        label='Mailing Street Address'
    )
    mailing_city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'City',
        }),
        label='City'
    )
    mailing_state = forms.ChoiceField(
        choices=US_STATES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
        label='State'
    )
    mailing_zip_code = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ZIP Code',
        }),
        label='ZIP Code'
    )

    class Meta:
        model = User
        fields = (
            'first_name', 'middle_name', 'last_name',
            'street_address', 'city', 'state', 'zip_code', 'phone',
            'use_different_mailing_address',
            'mailing_street_address', 'mailing_city', 'mailing_state', 'mailing_zip_code'
        )

    def clean_state(self):
        state = self.cleaned_data.get('state')
        if not state:
            raise forms.ValidationError('Please select a state.')
        return state
