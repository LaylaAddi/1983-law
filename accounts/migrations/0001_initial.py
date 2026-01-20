# Generated manually - squashed from multiple migrations
# Initial migration for accounts app

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('first_name', models.CharField(blank=True, max_length=30)),
                ('middle_name', models.CharField(blank=True, max_length=30)),
                ('last_name', models.CharField(blank=True, max_length=30)),
                ('street_address', models.CharField(blank=True, max_length=255)),
                ('city', models.CharField(blank=True, max_length=100)),
                ('state', models.CharField(blank=True, max_length=50)),
                ('zip_code', models.CharField(blank=True, max_length=20)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('use_different_mailing_address', models.BooleanField(default=False)),
                ('mailing_street_address', models.CharField(blank=True, max_length=255)),
                ('mailing_city', models.CharField(blank=True, max_length=100)),
                ('mailing_state', models.CharField(blank=True, max_length=50)),
                ('mailing_zip_code', models.CharField(blank=True, max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('is_staff', models.BooleanField(default=False)),
                ('is_test_user', models.BooleanField(default=False, help_text='Enable test features like auto-fill sample data')),
                ('agreed_to_terms', models.BooleanField(default=False, help_text='User agreed to Terms of Service')),
                ('agreed_to_privacy', models.BooleanField(default=False, help_text='User agreed to Privacy Policy')),
                ('terms_agreed_at', models.DateTimeField(blank=True, help_text='When user agreed to terms', null=True)),
                ('terms_agreed_ip', models.GenericIPAddressField(blank=True, help_text='IP address when terms were agreed', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
            },
        ),
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
        migrations.CreateModel(
            name='LegalDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('document_type', models.CharField(choices=[('terms', 'Terms of Service'), ('privacy', 'Privacy Policy'), ('disclaimer', 'Legal Disclaimer'), ('cookies', 'Cookie Policy')], help_text='Type of legal document', max_length=20, unique=True)),
                ('title', models.CharField(help_text='Document title displayed at top of page', max_length=255)),
                ('content', models.TextField(help_text='Full document content (HTML allowed)')),
                ('effective_date', models.DateField(blank=True, help_text='When this version became effective', null=True)),
                ('is_active', models.BooleanField(default=True, help_text='Whether this document is currently active')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Legal Document',
                'verbose_name_plural': 'Legal Documents',
                'ordering': ['document_type'],
            },
        ),
    ]
