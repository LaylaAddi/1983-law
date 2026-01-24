"""
XML Sitemap configuration for SEO.

Includes all public-facing pages. Excludes:
- Admin URLs (dynamic path for security)
- User-specific pages (login, register, profile, documents)
- API endpoints
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    """Sitemap for static pages that don't change frequently."""

    priority = 0.8
    changefreq = 'monthly'

    def items(self):
        """Return list of static page URL names."""
        return [
            'public_pages:home',
            'accounts:pricing',
            'legal:terms',
            'legal:privacy',
            'legal:disclaimer',
            'legal:cookies',
        ]

    def location(self, item):
        """Return the URL for each item."""
        return reverse(item)


class KnowYourRightsSitemap(Sitemap):
    """Sitemap for know your rights educational pages."""

    priority = 0.9
    changefreq = 'monthly'

    def items(self):
        """Return list of know your rights page URL names."""
        return [
            'public_pages:know_your_rights',
            'public_pages:right_to_record',
            'public_pages:section_1983',
            'public_pages:rights_violated',
            'public_pages:first_amendment_auditors',
            'public_pages:fourth_amendment',
            'public_pages:fifth_amendment',
        ]

    def location(self, item):
        """Return the URL for each item."""
        return reverse(item)


class CivilRightsPageSitemap(Sitemap):
    """Sitemap for CMS-managed civil rights pages."""

    changefreq = 'weekly'
    priority = 0.7

    def items(self):
        """Return all published CivilRightsPage objects."""
        from public_pages.models import CivilRightsPage
        return CivilRightsPage.objects.filter(is_published=True)

    def location(self, obj):
        """Return the URL for each page."""
        return reverse('public_pages:cms_page', kwargs={'slug': obj.slug})

    def lastmod(self, obj):
        """Return the last modified date."""
        return obj.updated_at if hasattr(obj, 'updated_at') else None


# Dictionary of all sitemaps for URL configuration
sitemaps = {
    'static': StaticViewSitemap,
    'know_your_rights': KnowYourRightsSitemap,
    'rights': CivilRightsPageSitemap,
}
