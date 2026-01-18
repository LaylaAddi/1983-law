# Generated manually for user terms agreement tracking

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_legaldocument'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='agreed_to_terms',
            field=models.BooleanField(default=False, help_text='User agreed to Terms of Service'),
        ),
        migrations.AddField(
            model_name='user',
            name='agreed_to_privacy',
            field=models.BooleanField(default=False, help_text='User agreed to Privacy Policy'),
        ),
        migrations.AddField(
            model_name='user',
            name='terms_agreed_at',
            field=models.DateTimeField(blank=True, null=True, help_text='When user agreed to terms'),
        ),
        migrations.AddField(
            model_name='user',
            name='terms_agreed_ip',
            field=models.GenericIPAddressField(blank=True, null=True, help_text='IP address when terms were agreed'),
        ),
    ]
