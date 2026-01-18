from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from .models import SiteSettings

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for custom User model."""

    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_test_user', 'is_active', 'created_at')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_test_user')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-created_at',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_test_user', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login',)}),
    )

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
