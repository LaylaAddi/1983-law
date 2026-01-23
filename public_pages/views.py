from django.shortcuts import render, redirect
from datetime import datetime, timedelta


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
        },
        {
            'title': 'Understanding Section 1983',
            'summary': 'Section 1983 is the federal law that allows you to sue government officials who violate your constitutional rights. Here\'s how it works.',
            'icon': 'bi-journal-text',
            'category': 'Legal Basics',
        },
        {
            'title': 'What to Do If Your Rights Are Violated',
            'summary': 'Step-by-step guide on documenting incidents, preserving evidence, and understanding your options when police or government officials violate your rights.',
            'icon': 'bi-shield-check',
            'category': 'Take Action',
        },
        {
            'title': 'Know Your Fourth Amendment Rights',
            'summary': 'Protection against unreasonable searches and seizures is fundamental to American freedom. Learn when police can and cannot search you or your property.',
            'icon': 'bi-search',
            'category': 'Fourth Amendment',
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
        },
        {
            'amendment': '4th',
            'title': 'Protection from Unreasonable Search',
            'description': 'Police generally need a warrant to search you or your property. You can refuse consent to searches.',
            'icon': 'bi-shield-lock',
        },
        {
            'amendment': '5th',
            'title': 'Right to Remain Silent',
            'description': 'You cannot be forced to incriminate yourself. You have the right to remain silent during police encounters.',
            'icon': 'bi-chat-square-dots',
        },
        {
            'amendment': '14th',
            'title': 'Equal Protection & Due Process',
            'description': 'Government must treat you fairly and cannot discriminate. You have the right to due process of law.',
            'icon': 'bi-balance-scale',
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
