from django.db import models
from django.urls import reverse
from ckeditor.fields import RichTextField


class CivilRightsPage(models.Model):
    """
    A CMS-managed page for civil rights content.
    Each page can have multiple sections of different types.
    """
    # Basic fields
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)

    # Hero section (optional - can also use PageSection for hero)
    hero_title = models.CharField(max_length=200, blank=True, help_text="Override title for hero section")
    hero_subtitle = models.TextField(blank=True, help_text="Subtitle text shown in hero section")

    # SEO fields
    meta_description = models.TextField(
        max_length=160,
        blank=True,
        help_text="SEO meta description (max 160 chars)"
    )
    meta_keywords = models.CharField(
        max_length=255,
        blank=True,
        help_text="Comma-separated keywords for SEO"
    )

    # Publishing
    is_published = models.BooleanField(default=False, help_text="Uncheck to hide this page")
    is_featured = models.BooleanField(default=False, help_text="Show on homepage featured section")
    order = models.PositiveIntegerField(default=0, help_text="Order in navigation/listings")

    # Navigation
    show_in_nav = models.BooleanField(default=True, help_text="Show in main navigation")
    nav_title = models.CharField(max_length=50, blank=True, help_text="Short title for navigation (uses title if blank)")

    # Category for grouping
    CATEGORY_CHOICES = [
        ('rights', 'Know Your Rights'),
        ('legal', 'Legal Information'),
        ('action', 'Take Action'),
        ('resources', 'Resources'),
        ('auditors', 'First Amendment Auditors'),
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='rights')

    # Icon for cards/listings
    icon = models.CharField(
        max_length=50,
        default='bi-file-text',
        help_text="Bootstrap icon class (e.g., bi-camera-video)"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'title']
        verbose_name = "Civil Rights Page"
        verbose_name_plural = "Civil Rights Pages"

    def __str__(self):
        status = "✓" if self.is_published else "✗"
        return f"[{status}] {self.title}"

    def get_absolute_url(self):
        return reverse('cms_page', kwargs={'slug': self.slug})

    def get_nav_title(self):
        return self.nav_title or self.title

    def get_hero_title(self):
        return self.hero_title or self.title


class PageSection(models.Model):
    """
    A section within a CMS page.
    Different section types render differently using template partials.
    """
    page = models.ForeignKey(
        CivilRightsPage,
        on_delete=models.CASCADE,
        related_name='sections'
    )

    # Section type determines which template partial to use
    SECTION_TYPES = [
        ('hero', 'Hero Section'),
        ('content', 'Rich Text Content'),
        ('cards', 'Card Grid'),
        ('rights_cards', 'Rights Cards (with amendment badge)'),
        ('article_cards', 'Article Cards (with category badge)'),
        ('quote', 'Quote/Blockquote'),
        ('cta', 'Call to Action'),
        ('resources', 'Resource Links'),
        ('stats', 'Statistics Row'),
        ('two_column', 'Two Column Layout'),
        ('checklist', 'Checklist (Do/Don\'t)'),
        ('alert', 'Alert/Notice Box'),
        ('accordion', 'Accordion/FAQ'),
    ]
    section_type = models.CharField(max_length=20, choices=SECTION_TYPES)

    # Common fields
    title = models.CharField(max_length=200, blank=True)
    subtitle = models.TextField(blank=True)

    # Rich text content (for content, two_column left side, etc.)
    content = RichTextField(blank=True, help_text="Main content (for content sections)")

    # Secondary content (for two_column right side)
    content_secondary = RichTextField(blank=True, help_text="Secondary content (for two-column layouts)")

    # JSON data for structured content (cards, resources, stats, etc.)
    data = models.JSONField(
        blank=True,
        null=True,
        help_text="""
        JSON data for structured sections. Examples:
        - cards: [{"title": "...", "icon": "bi-...", "text": "...", "badge": "...", "url": "..."}]
        - resources: [{"name": "...", "url": "...", "description": "..."}]
        - stats: [{"number": "42", "label": "..."}]
        - accordion: [{"question": "...", "answer": "..."}]
        """
    )

    # Styling
    BACKGROUND_CHOICES = [
        ('light', 'White'),
        ('cream', 'Cream/Off-white'),
        ('blue', 'Light Blue'),
        ('dark', 'Dark (for CTAs)'),
    ]
    background = models.CharField(max_length=10, choices=BACKGROUND_CHOICES, default='light')
    css_class = models.CharField(max_length=100, blank=True, help_text="Additional CSS classes")

    # CTA fields (for cta sections)
    cta_text = models.CharField(max_length=100, blank=True)
    cta_url = models.CharField(max_length=200, blank=True)
    cta_icon = models.CharField(max_length=50, blank=True, default='bi-shield-check')

    # Secondary CTA (optional)
    cta_secondary_text = models.CharField(max_length=100, blank=True)
    cta_secondary_url = models.CharField(max_length=200, blank=True)

    # Quote fields (for quote sections)
    quote_source = models.CharField(max_length=200, blank=True)

    # Alert fields
    ALERT_TYPES = [
        ('info', 'Info (Blue)'),
        ('warning', 'Warning (Yellow)'),
        ('danger', 'Danger (Red)'),
        ('success', 'Success (Green)'),
    ]
    alert_type = models.CharField(max_length=10, choices=ALERT_TYPES, default='info')

    # Visibility and ordering
    is_visible = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = "Page Section"
        verbose_name_plural = "Page Sections"

    def __str__(self):
        visible = "✓" if self.is_visible else "✗"
        return f"[{visible}] {self.page.title} - {self.get_section_type_display()}: {self.title or '(no title)'}"

    def get_background_class(self):
        """Return CSS class for section background."""
        mapping = {
            'light': 'section-light',
            'cream': 'section-cream',
            'blue': 'section-blue',
            'dark': 'cta-section',
        }
        return mapping.get(self.background, 'section-light')
