from django.contrib import admin
from .models import (
    Document, DocumentSection, PlaintiffInfo, IncidentOverview,
    Defendant, IncidentNarrative, RightsViolated, Witness,
    Evidence, Damages, PriorComplaints, ReliefSought,
    PromoCode, PromoCodeUsage, PayoutRequest
)


class DocumentSectionInline(admin.TabularInline):
    model = DocumentSection
    extra = 0
    fields = ['section_type', 'status', 'order', 'notes']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'user', 'payment_status', 'get_completion_percentage',
        'ai_generations_used', 'amount_paid', 'created_at'
    ]
    list_filter = ['payment_status', 'created_at']
    search_fields = ['title', 'user__email']
    readonly_fields = ['stripe_payment_id', 'paid_at', 'finalized_at', 'ai_cost_used']
    inlines = [DocumentSectionInline]

    fieldsets = (
        (None, {
            'fields': ('user', 'title', 'payment_status')
        }),
        ('Story', {
            'fields': ('story_text', 'story_told_at'),
            'classes': ('collapse',)
        }),
        ('Payment', {
            'fields': ('stripe_payment_id', 'promo_code_used', 'amount_paid', 'paid_at', 'finalized_at')
        }),
        ('AI Usage', {
            'fields': ('ai_generations_used', 'ai_cost_used')
        }),
    )

    def get_completion_percentage(self, obj):
        return f"{obj.get_completion_percentage()}%"
    get_completion_percentage.short_description = 'Completion'


@admin.register(DocumentSection)
class DocumentSectionAdmin(admin.ModelAdmin):
    list_display = ['document', 'section_type', 'status', 'updated_at']
    list_filter = ['section_type', 'status']


@admin.register(PlaintiffInfo)
class PlaintiffInfoAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'middle_name', 'last_name', 'email', 'is_pro_se']


@admin.register(Defendant)
class DefendantAdmin(admin.ModelAdmin):
    list_display = ['name', 'defendant_type', 'badge_number', 'agency_name']
    list_filter = ['defendant_type']


@admin.register(Witness)
class WitnessAdmin(admin.ModelAdmin):
    list_display = ['name', 'relationship', 'willing_to_testify']


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ['title', 'evidence_type', 'is_in_possession', 'needs_subpoena']
    list_filter = ['evidence_type', 'is_in_possession', 'needs_subpoena']


class PromoCodeUsageInline(admin.TabularInline):
    model = PromoCodeUsage
    extra = 0
    readonly_fields = ['document', 'user', 'stripe_payment_id', 'amount_paid', 'referral_amount', 'created_at']
    fields = ['document', 'user', 'amount_paid', 'referral_amount', 'payout_status', 'payout_reference', 'created_at']
    can_delete = False


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'owner', 'is_active', 'times_used', 'total_earned', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['code', 'owner__email']
    readonly_fields = ['times_used', 'total_earned', 'created_at']
    inlines = [PromoCodeUsageInline]


@admin.register(PromoCodeUsage)
class PromoCodeUsageAdmin(admin.ModelAdmin):
    list_display = [
        'promo_code', 'user', 'amount_paid', 'referral_amount',
        'payout_status', 'payout_date', 'created_at'
    ]
    list_filter = ['payout_status', 'created_at']
    search_fields = ['promo_code__code', 'user__email', 'stripe_payment_id']
    readonly_fields = ['promo_code', 'document', 'user', 'stripe_payment_id', 'amount_paid', 'referral_amount', 'created_at']
    actions = ['mark_as_paid']

    fieldsets = (
        ('Usage Details', {
            'fields': ('promo_code', 'document', 'user', 'stripe_payment_id', 'amount_paid', 'referral_amount', 'created_at')
        }),
        ('Payout', {
            'fields': ('payout_status', 'payout_reference', 'payout_date', 'payout_notes')
        }),
    )

    @admin.action(description='Mark selected usages as paid')
    def mark_as_paid(self, request, queryset):
        updated = queryset.filter(payout_status='pending').update(payout_status='paid')
        self.message_user(request, f'{updated} usage(s) marked as paid.')


@admin.register(PayoutRequest)
class PayoutRequestAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'amount_requested', 'payment_method', 'status',
        'amount_paid', 'processed_by', 'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['user__email', 'payment_reference']
    readonly_fields = ['user', 'amount_requested', 'created_at', 'updated_at']
    actions = ['mark_as_processing', 'mark_as_completed']

    fieldsets = (
        ('Request Details', {
            'fields': ('user', 'amount_requested', 'payment_method', 'payment_details', 'created_at')
        }),
        ('Processing', {
            'fields': ('status', 'amount_paid', 'payment_reference', 'admin_notes', 'processed_by', 'processed_at')
        }),
    )

    @admin.action(description='Mark selected as processing')
    def mark_as_processing(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='processing')
        self.message_user(request, f'{updated} request(s) marked as processing.')

    @admin.action(description='Mark selected as completed')
    def mark_as_completed(self, request, queryset):
        # This is a simple bulk action - for proper completion, use the admin_referrals view
        updated = queryset.filter(status__in=['pending', 'processing']).update(status='completed')
        self.message_user(request, f'{updated} request(s) marked as completed.')
