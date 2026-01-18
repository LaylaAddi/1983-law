# Generated manually for editable legal documents

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_sitesettings'),
    ]

    operations = [
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
