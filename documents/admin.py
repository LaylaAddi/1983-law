from django.contrib import admin
from .models import (
    Document, DocumentSection, PlaintiffInfo, IncidentOverview,
    Defendant, IncidentNarrative, RightsViolated, Witness,
    Evidence, Damages, PriorComplaints, ReliefSought
)


class DocumentSectionInline(admin.TabularInline):
    model = DocumentSection
    extra = 0
    fields = ['section_type', 'status', 'order', 'notes']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'status', 'get_completion_percentage', 'created_at', 'updated_at']
    list_filter = ['status', 'created_at']
    search_fields = ['title', 'user__email']
    inlines = [DocumentSectionInline]

    def get_completion_percentage(self, obj):
        return f"{obj.get_completion_percentage()}%"
    get_completion_percentage.short_description = 'Completion'


@admin.register(DocumentSection)
class DocumentSectionAdmin(admin.ModelAdmin):
    list_display = ['document', 'section_type', 'status', 'updated_at']
    list_filter = ['section_type', 'status']


@admin.register(PlaintiffInfo)
class PlaintiffInfoAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'is_pro_se']


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
