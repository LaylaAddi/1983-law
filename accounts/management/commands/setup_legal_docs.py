from django.core.management.base import BaseCommand
from accounts.models import SiteSettings


class Command(BaseCommand):
    help = 'Create default legal documents based on Site Settings'

    def handle(self, *args, **options):
        try:
            settings = SiteSettings.objects.get(pk=1)
        except SiteSettings.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                'Site Settings not found. Please create Site Settings in admin first.'
            ))
            return

        self.stdout.write('Creating default legal documents...')
        settings._create_default_legal_documents()
        self.stdout.write(self.style.SUCCESS(
            'Legal documents created successfully! You can now edit them in admin.'
        ))
