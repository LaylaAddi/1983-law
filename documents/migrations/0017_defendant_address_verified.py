# Generated manually for address verification feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0016_pdf_generation_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='defendant',
            name='address_verified',
            field=models.BooleanField(
                default=False,
                help_text='User confirmed they verified the address is correct',
            ),
        ),
    ]
