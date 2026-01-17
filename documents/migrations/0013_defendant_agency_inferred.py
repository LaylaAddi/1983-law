# Generated manually for agency suggestion feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0012_document_parsing_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='defendant',
            name='agency_inferred',
            field=models.BooleanField(
                default=False,
                help_text='True if agency was AI-inferred and needs review',
            ),
        ),
    ]
