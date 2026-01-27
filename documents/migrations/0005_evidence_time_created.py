# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0004_merge_20260125_0406'),
    ]

    operations = [
        migrations.AddField(
            model_name='evidence',
            name='time_created',
            field=models.TimeField(blank=True, null=True),
        ),
    ]
