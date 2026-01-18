# Generated manually for site settings

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_user_city_user_mailing_city_user_mailing_state_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company_name', models.CharField(default='1983law.org', help_text='Legal name of the company/organization', max_length=255)),
                ('company_type', models.CharField(blank=True, default='', help_text='e.g., LLC, Non-Profit, Corporation', max_length=100)),
                ('company_state', models.CharField(default='New York', help_text='State of incorporation/registration', max_length=50)),
                ('company_address', models.TextField(blank=True, default='', help_text='Physical business address (required for CAN-SPAM)')),
                ('contact_email', models.EmailField(default='contact@1983law.org', help_text='Contact email for legal/privacy inquiries', max_length=254)),
                ('website_url', models.URLField(default='https://www.1983law.org', help_text='Primary website URL')),
                ('minimum_age', models.PositiveIntegerField(default=18, help_text='Minimum age to use the service')),
                ('governing_law_state', models.CharField(default='New York', help_text='State whose laws govern the Terms of Service', max_length=50)),
                ('has_attorneys', models.BooleanField(default=False, help_text='Are licensed attorneys involved in the service?')),
                ('attorney_states', models.CharField(blank=True, default='', help_text='States where attorneys are licensed (comma-separated)', max_length=255)),
                ('payment_processor', models.CharField(default='Stripe', help_text='Payment processor used (e.g., Stripe, PayPal)', max_length=100)),
                ('refund_policy_days', models.PositiveIntegerField(default=0, help_text='Number of days for refund requests (0 = no refunds)')),
                ('uses_google_analytics', models.BooleanField(default=True, help_text='Does the site use Google Analytics?')),
                ('uses_openai', models.BooleanField(default=True, help_text='Does the site use OpenAI/AI services?')),
                ('hosting_provider', models.CharField(default='Render', help_text='Web hosting provider', max_length=100)),
                ('terms_effective_date', models.DateField(blank=True, help_text='Effective date of Terms of Service', null=True)),
                ('privacy_effective_date', models.DateField(blank=True, help_text='Effective date of Privacy Policy', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Site Settings',
                'verbose_name_plural': 'Site Settings',
            },
        ),
    ]
