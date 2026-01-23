from django.contrib import admin
from django.utils.html import format_html
from .models import CivilRightsPage, PageSection


class PageSectionInline(admin.StackedInline):
    """Inline admin for page sections with drag-drop ordering."""
    model = PageSection
    extra = 0
    ordering = ['order']

    fieldsets = (
        ('Section Type & Visibility', {
            'fields': (('section_type', 'is_visible', 'order'), 'background', 'css_class'),
        }),
        ('Content', {
            'fields': ('title', 'subtitle', 'content', 'content_secondary'),
            'classes': ('collapse',),
        }),
        ('Structured Data (JSON)', {
            'fields': ('data',),
            'classes': ('collapse',),
            'description': 'For cards, resources, stats, accordion sections. See model help text for format.',
        }),
        ('Call to Action', {
            'fields': (('cta_text', 'cta_url', 'cta_icon'), ('cta_secondary_text', 'cta_secondary_url')),
            'classes': ('collapse',),
        }),
        ('Quote', {
            'fields': ('quote_source',),
            'classes': ('collapse',),
        }),
        ('Alert', {
            'fields': ('alert_type',),
            'classes': ('collapse',),
        }),
    )

    class Media:
        css = {
            'all': ('css/admin-cms.css',),
        }


@admin.register(CivilRightsPage)
class CivilRightsPageAdmin(admin.ModelAdmin):
    """Admin for CMS pages with inline sections."""

    list_display = [
        'title',
        'slug',
        'category',
        'is_published',
        'is_featured_display',
        'show_in_nav',
        'order',
        'section_count',
        'updated_at',
    ]
    list_filter = ['is_published', 'is_featured', 'category', 'show_in_nav']
    search_fields = ['title', 'slug', 'hero_subtitle', 'meta_description']
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ['order', 'is_published', 'show_in_nav']
    ordering = ['order', 'title']

    fieldsets = (
        ('Page Info', {
            'fields': ('title', 'slug', 'category', 'icon'),
        }),
        ('Hero Section', {
            'fields': ('hero_title', 'hero_subtitle'),
            'description': 'Optional hero section. Leave blank to use title.',
        }),
        ('SEO', {
            'fields': ('meta_description', 'meta_keywords'),
            'classes': ('collapse',),
        }),
        ('Publishing', {
            'fields': (('is_published', 'is_featured'), ('show_in_nav', 'nav_title'), 'order'),
        }),
    )

    inlines = [PageSectionInline]

    def is_published_display(self, obj):
        if obj.is_published:
            return format_html('<span style="color: green;">✓ Published</span>')
        return format_html('<span style="color: red;">✗ Draft</span>')
    is_published_display.short_description = 'Status'

    def is_featured_display(self, obj):
        if obj.is_featured:
            return format_html('<span style="color: gold;">★</span>')
        return ''
    is_featured_display.short_description = 'Featured'

    def section_count(self, obj):
        count = obj.sections.count()
        visible = obj.sections.filter(is_visible=True).count()
        if count == visible:
            return count
        return f"{visible}/{count}"
    section_count.short_description = 'Sections'

    class Media:
        css = {
            'all': ('css/admin-cms.css',),
        }


@admin.register(PageSection)
class PageSectionAdmin(admin.ModelAdmin):
    """Standalone admin for sections (for bulk editing)."""

    list_display = ['page', 'section_type', 'title', 'is_visible', 'order', 'background']
    list_filter = ['page', 'section_type', 'is_visible', 'background']
    list_editable = ['is_visible', 'order']
    ordering = ['page', 'order']
    search_fields = ['title', 'content', 'page__title']
