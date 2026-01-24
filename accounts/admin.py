from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django import forms
from ckeditor.widgets import CKEditorWidget
from .models import SiteSettings, LegalDocument

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for custom User model."""

    list_display = ('email', 'first_name', 'last_name', 'agreed_to_terms', 'terms_agreed_at', 'is_staff', 'is_active', 'created_at')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_test_user', 'agreed_to_terms', 'agreed_to_privacy')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-created_at',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name')}),
        ('Terms Agreement', {
            'fields': ('agreed_to_terms', 'agreed_to_privacy', 'terms_agreed_at', 'terms_agreed_ip'),
            'description': 'User consent to Terms of Service and Privacy Policy'
        }),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_test_user', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login',)}),
    )
    readonly_fields = ('terms_agreed_at', 'terms_agreed_ip')

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """Admin for site-wide settings."""

    fieldsets = (
        ('Company Information', {
            'fields': ('company_name', 'company_type', 'company_state', 'company_address', 'contact_email', 'website_url')
        }),
        ('Footer Contact Information', {
            'fields': (
                'show_footer_contact',
                ('footer_address', 'show_footer_address'),
                ('footer_phone', 'show_footer_phone'),
                ('footer_email', 'show_footer_email'),
            ),
            'description': 'Contact information displayed in the website footer. Use toggles to show/hide each field.'
        }),
        ('Legal Settings', {
            'fields': ('minimum_age', 'governing_law_state', 'has_attorneys', 'attorney_states')
        }),
        ('Payment Settings', {
            'fields': ('payment_processor', 'refund_policy_days')
        }),
        ('Third-Party Services', {
            'fields': ('uses_google_analytics', 'uses_openai', 'hosting_provider')
        }),
        ('Policy Effective Dates', {
            'fields': ('terms_effective_date', 'privacy_effective_date')
        }),
    )

    def has_add_permission(self, request):
        # Only allow one instance
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Don't allow deleting the settings
        return False


class LegalDocumentAdminForm(forms.ModelForm):
    """Custom form for LegalDocument with CKEditor widget."""
    content = forms.CharField(widget=CKEditorWidget(config_name='legal'))

    class Meta:
        model = LegalDocument
        fields = '__all__'


@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    """Admin for editable legal documents with rich text editor."""

    form = LegalDocumentAdminForm
    list_display = ('document_type', 'title', 'effective_date', 'is_active', 'updated_at')
    list_filter = ('document_type', 'is_active')
    search_fields = ('title', 'content')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('document_type', 'title', 'is_active')
        }),
        ('Content', {
            'fields': ('content',),
            'classes': ('wide',),
        }),
        ('Dates', {
            'fields': ('effective_date', 'created_at', 'updated_at'),
        }),
    )

    class Media:
        css = {
            'all': ('css/admin-legal.css',)
        }
