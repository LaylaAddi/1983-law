from django.conf import settings


def app_branding(request):
    """Make app branding and site settings available to all templates."""
    from accounts.models import SiteSettings

    return {
        'app_name': settings.APP_NAME,
        'header_app_name': settings.HEADER_APP_NAME,
        'site_settings': SiteSettings.get_settings(),
    }
