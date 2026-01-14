from django.conf import settings


def app_branding(request):
    """Make app branding variables available to all templates."""
    return {
        'app_name': settings.APP_NAME,
        'header_app_name': settings.HEADER_APP_NAME,
    }
