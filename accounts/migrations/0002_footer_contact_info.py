# Generated manually for footer contact info fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='footer_address',
            field=models.TextField(blank=True, default='123 Liberty Avenue, Suite 1983\nNew York, NY 10001', help_text='Address to display in footer (use line breaks for formatting)'),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='footer_email',
            field=models.EmailField(blank=True, default='info@1983law.org', help_text='Email address to display in footer', max_length=254),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='footer_phone',
            field=models.CharField(blank=True, default='585-204-7416', help_text='Phone number to display in footer', max_length=20),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='show_footer_address',
            field=models.BooleanField(default=False, help_text='Show address in footer contact section'),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='show_footer_contact',
            field=models.BooleanField(default=True, help_text='Show contact section in footer'),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='show_footer_email',
            field=models.BooleanField(default=True, help_text='Show email in footer contact section'),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='show_footer_phone',
            field=models.BooleanField(default=True, help_text='Show phone number in footer contact section'),
        ),
    ]
