from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404, HttpResponse
from datetime import datetime, timedelta

from .models import CivilRightsPage, PageSection


def robots_txt(request):
    """
    Serve robots.txt for search engine crawlers.
    Points to sitemap.xml and disallows private areas.
    """
    # Build the sitemap URL dynamically
    protocol = 'https' if request.is_secure() else 'http'
    host = request.get_host()
    sitemap_url = f"{protocol}://{host}/sitemap.xml"

    lines = [
        "User-agent: *",
        "Allow: /",
        "",
        "# Disallow private/user-specific areas",
        "Disallow: /accounts/",
        "Disallow: /documents/",
        "",
        "# Sitemap location",
        f"Sitemap: {sitemap_url}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def cms_page(request, slug):
    """
    Dynamic CMS page view.
    Renders a page with all its sections based on the slug.
    """
    page = get_object_or_404(CivilRightsPage, slug=slug, is_published=True)
    sections = page.sections.filter(is_visible=True).order_by('order')

    context = {
        'page': page,
        'sections': sections,
    }
    return render(request, 'public_pages/cms_page.html', context)


def get_nav_pages():
    """Get pages that should appear in navigation."""
    return CivilRightsPage.objects.filter(
        is_published=True,
        show_in_nav=True
    ).order_by('order')


def landing_page(request):
    """
    Main public landing page with civil rights information.
    For now, uses hardcoded sample data. Will be replaced with CMS + News API later.

    Authenticated users are redirected to their documents list.
    """
    # Redirect authenticated users to their documents
    if request.user.is_authenticated:
        return redirect('documents:document_list')

    # Sample featured articles (will come from CMS later)
    featured_articles = [
        {
            'title': 'Your Right to Record Police',
            'summary': 'The First Amendment protects your right to record police officers performing their duties in public. Learn what the courts have said and how to protect yourself.',
            'icon': 'bi-camera-video',
            'category': 'First Amendment',
            'url': 'right_to_record',
        },
        {
            'title': 'Understanding Section 1983',
            'summary': 'Section 1983 is the federal law that allows you to sue government officials who violate your constitutional rights. Here\'s how it works.',
            'icon': 'bi-journal-text',
            'category': 'Legal Basics',
            'url': 'section_1983',
        },
        {
            'title': 'What to Do If Your Rights Are Violated',
            'summary': 'Step-by-step guide on documenting incidents, preserving evidence, and understanding your options when police or government officials violate your rights.',
            'icon': 'bi-shield-check',
            'category': 'Take Action',
            'url': 'rights_violated',
        },
        {
            'title': 'First Amendment Auditors',
            'summary': 'Meet the everyday Americans who test and protect our constitutional rights through peaceful First Amendment audits.',
            'icon': 'bi-camera-video',
            'category': 'Freedom Fighters',
            'url': 'first_amendment_auditors',
        },
    ]

    # Sample news items (will come from News API later)
    sample_news = [
        {
            'title': 'Federal Court Rules Citizens Have Right to Record Traffic Stops',
            'source': 'ACLU',
            'date': datetime.now() - timedelta(days=1),
            'url': '#',
        },
        {
            'title': 'Supreme Court to Hear Qualified Immunity Case This Term',
            'source': 'Reuters',
            'date': datetime.now() - timedelta(days=2),
            'url': '#',
        },
        {
            'title': 'New Body Camera Footage Requirements Take Effect in Three States',
            'source': 'AP News',
            'date': datetime.now() - timedelta(days=3),
            'url': '#',
        },
        {
            'title': 'Civil Rights Groups Call for Police Accountability Reforms',
            'source': 'NPR',
            'date': datetime.now() - timedelta(days=4),
            'url': '#',
        },
        {
            'title': 'First Amendment Audit Movement Grows Across America',
            'source': 'Washington Post',
            'date': datetime.now() - timedelta(days=5),
            'url': '#',
        },
    ]

    # Key rights for the "Know Your Rights" quick reference
    key_rights = [
        {
            'amendment': '1st',
            'title': 'Freedom of Speech & Press',
            'description': 'You have the right to record police, attend public meetings, and speak freely on matters of public concern.',
            'icon': 'bi-megaphone',
            'url': 'right_to_record',
        },
        {
            'amendment': '4th',
            'title': 'Protection from Unreasonable Search',
            'description': 'Police generally need a warrant to search you or your property. You can refuse consent to searches.',
            'icon': 'bi-shield-lock',
            'url': 'fourth_amendment',
        },
        {
            'amendment': '5th',
            'title': 'Right to Remain Silent',
            'description': 'You cannot be forced to incriminate yourself. You have the right to remain silent during police encounters.',
            'icon': 'bi-chat-square-dots',
            'url': 'fifth_amendment',
        },
        {
            'amendment': '14th',
            'title': 'Equal Protection & Due Process',
            'description': 'Government must treat you fairly and cannot discriminate. You have the right to due process of law.',
            'icon': 'bi-balance-scale',
            'url': 'section_1983',
        },
    ]

    # Resources
    resources = [
        {
            'name': 'ACLU - Know Your Rights',
            'url': 'https://www.aclu.org/know-your-rights',
            'description': 'Comprehensive guides on your constitutional rights in various situations.',
        },
        {
            'name': 'Flex Your Rights',
            'url': 'https://www.flexyourrights.org/',
            'description': 'Educational resources about asserting your rights during police encounters.',
        },
        {
            'name': 'Electronic Frontier Foundation',
            'url': 'https://www.eff.org/',
            'description': 'Digital rights and privacy protection in the modern age.',
        },
        {
            'name': 'Cornell Law - Section 1983',
            'url': 'https://www.law.cornell.edu/uscode/text/42/1983',
            'description': 'The actual text of 42 U.S.C. Section 1983.',
        },
    ]

    context = {
        'featured_articles': featured_articles,
        'news_items': sample_news,
        'key_rights': key_rights,
        'resources': resources,
    }

    return render(request, 'public_pages/landing.html', context)


def know_your_rights(request):
    """Comprehensive Know Your Rights page with detailed information."""
    return render(request, 'public_pages/know_your_rights.html')


def right_to_record(request):
    """Detailed page about the right to record police and government officials."""
    return render(request, 'public_pages/right_to_record.html')


def section_1983(request):
    """Detailed page explaining Section 1983 and how to use it."""
    return render(request, 'public_pages/section_1983.html')


def rights_violated(request):
    """Guide for what to do when your rights have been violated."""
    return render(request, 'public_pages/rights_violated.html')


def first_amendment_auditors(request):
    """Tribute page to First Amendment auditors protecting our freedoms."""
    return render(request, 'public_pages/first_amendment_auditors.html')


def fourth_amendment(request):
    """Detailed page about Fourth Amendment rights."""
    return render(request, 'public_pages/fourth_amendment.html')


def fifth_amendment(request):
    """Detailed page about Fifth Amendment rights."""
    return render(request, 'public_pages/fifth_amendment.html')
